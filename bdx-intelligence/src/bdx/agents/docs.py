"""Documentation agent - verifies docs against code, statically.

The agent never imports the package's runtime dependencies (no SAP/PG/MQTT);
it walks the source tree with :mod:`ast` and reads the markdown docs as plain
text. That keeps it independent from the development environment and safe to
run in CI without secrets.
"""

from __future__ import annotations

import ast
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from bdx.agents.base import CheckResult, Finding, Severity

# Modules that are allowed to ship without docstrings (entry-points, init
# files, generated Alembic migrations).
_NO_DOCSTRING_MODULES = {"__init__", "report", "logging_config"}


@dataclass
class DocumentationConfig:
    """Where the agent looks and what it enforces."""

    root: Path
    src_dir: Path = field(init=False)
    docs_dir: Path = field(init=False)
    readme: Path = field(init=False)
    required_docs: tuple[str, ...] = ("ARCHITECTURE.md", "PROJECT_STATUS.md", "SAP_MAPPING.md")
    max_status_age_days: int = 90
    """``PROJECT_STATUS.md`` must have been touched within this window."""

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.src_dir = self.root / "src" / "bdx"
        self.docs_dir = self.root / "docs"
        self.readme = self.root / "README.md"


class DocumentationAgent:
    """Static documentation audit."""

    name = "documentation"

    def __init__(self, cfg: DocumentationConfig | None = None, *, root: Path | None = None) -> None:
        if cfg is None:
            cfg = DocumentationConfig(root=root or Path.cwd())
        self.cfg = cfg

    # ── public API ──────────────────────────────────────────────────────────
    def run(self) -> CheckResult:
        result = CheckResult(agent=self.name)
        self._check_readme(result)
        self._check_required_docs(result)
        self._check_status_freshness(result)
        self._check_docstrings(result)
        self._check_api_routes_documented(result)
        self._check_config_documented(result)
        result.summary = (
            f"scanned {self._scanned_files} source files, {self._public_symbols} public symbols"
        )
        return result

    # ── individual checks ──────────────────────────────────────────────────
    def _check_readme(self, result: CheckResult) -> None:
        if not self.cfg.readme.exists():
            result.add(
                "DOC.MISSING_README",
                f"README.md not found at {self.cfg.readme}",
                severity=Severity.ERROR,
            )
            return
        size = self.cfg.readme.stat().st_size
        if size < 200:
            result.add(
                "DOC.STUB_README",
                f"README.md is only {size} bytes - likely a placeholder",
                location=str(self.cfg.readme),
                severity=Severity.WARNING,
            )

    def _check_required_docs(self, result: CheckResult) -> None:
        for name in self.cfg.required_docs:
            path = self.cfg.docs_dir / name
            if not path.exists():
                result.add(
                    "DOC.MISSING_REQUIRED",
                    f"required doc {name} missing (expected at {path})",
                    severity=Severity.ERROR,
                )

    def _check_status_freshness(self, result: CheckResult) -> None:
        status = self.cfg.docs_dir / "PROJECT_STATUS.md"
        if not status.exists():
            return  # already reported by _check_required_docs
        age_days = (time.time() - status.stat().st_mtime) / 86400
        if age_days > self.cfg.max_status_age_days:
            result.add(
                "DOC.STATUS_STALE",
                f"PROJECT_STATUS.md last updated {age_days:.0f} days ago "
                f"(> {self.cfg.max_status_age_days} days)",
                location=str(status),
                severity=Severity.WARNING,
            )

    def _check_docstrings(self, result: CheckResult) -> None:
        self._scanned_files = 0
        self._public_symbols = 0
        missing: list[Finding] = []
        for path in self._iter_python_files():
            self._scanned_files += 1
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                result.add(
                    "DOC.SYNTAX_ERROR",
                    f"cannot parse: {exc}",
                    location=str(path),
                    severity=Severity.ERROR,
                )
                continue
            rel = path.relative_to(self.cfg.root)
            if path.stem in _NO_DOCSTRING_MODULES:
                continue
            if not ast.get_docstring(tree):
                result.add(
                    "DOC.MODULE_DOCSTRING",
                    f"module {path.stem} has no module docstring",
                    location=str(rel),
                    severity=Severity.INFO,
                )
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if node.name.startswith("_"):
                    continue
                self._public_symbols += 1
                if not ast.get_docstring(node):
                    missing.append(
                        Finding(
                            code="DOC.MISSING_DOCSTRING",
                            message=f"{type(node).__name__} '{node.name}' has no docstring",
                            location=f"{rel}:{node.lineno}",
                            severity=Severity.WARNING,
                        )
                    )
        # cap to avoid flooding the report on a young codebase
        cap = 50
        for f in missing[:cap]:
            result.findings.append(f)
        if len(missing) > cap:
            result.add(
                "DOC.MISSING_DOCSTRING",
                f"... and {len(missing) - cap} more undocumented public symbols",
                severity=Severity.INFO,
            )

    def _check_api_routes_documented(self, result: CheckResult) -> None:
        routes = self._collect_api_routes()
        if not routes:
            return
        arch = self.cfg.docs_dir / "ARCHITECTURE.md"
        if not arch.exists():
            return  # already reported
        text = arch.read_text(encoding="utf-8")
        undocumented = [p for p in routes if p not in text]
        for path in undocumented[:20]:
            result.add(
                "DOC.ROUTE_UNDOCUMENTED",
                f"API route {path} not mentioned in ARCHITECTURE.md",
                location="src/bdx/api/routes",
                severity=Severity.WARNING,
            )
        if len(undocumented) > 20:
            result.add(
                "DOC.ROUTE_UNDOCUMENTED",
                f"... and {len(undocumented) - 20} more undocumented routes",
                severity=Severity.INFO,
            )

    def _check_config_documented(self, result: CheckResult) -> None:
        env_vars = self._collect_env_vars()
        if not env_vars:
            return
        arch = self.cfg.docs_dir / "ARCHITECTURE.md"
        if not arch.exists():
            return
        text = arch.read_text(encoding="utf-8")
        undocumented = [v for v in sorted(env_vars) if v not in text]
        for var in undocumented[:20]:
            result.add(
                "DOC.CONFIG_UNDOCUMENTED",
                f"env var {var} not mentioned in ARCHITECTURE.md",
                location="src/bdx/config.py",
                severity=Severity.WARNING,
            )
        if len(undocumented) > 20:
            result.add(
                "DOC.CONFIG_UNDOCUMENTED",
                f"... and {len(undocumented) - 20} more undocumented env vars",
                severity=Severity.INFO,
            )

    # ── helpers ────────────────────────────────────────────────────────────
    def _iter_python_files(self) -> Iterable[Path]:
        for path in sorted(self.cfg.src_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path

    def _collect_api_routes(self) -> list[str]:
        """Return route paths declared via @router.get/post/put/delete(...)."""
        routes_dir = self.cfg.src_dir / "api" / "routes"
        if not routes_dir.exists():
            return []
        paths: list[str] = []
        for path in sorted(routes_dir.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in {"get", "post", "put", "delete", "patch"}:
                    continue
                if not node.args:
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    paths.append(first.value)
        return paths

    def _collect_env_vars(self) -> set[str]:
        """Collect env-var names referenced via pydantic-settings Field(...).

        Each settings class declares its own ``env_prefix``; we only combine
        a class's prefix with that same class's annotated fields, never with
        fields from other classes.
        """
        config_path = self.cfg.src_dir / "config.py"
        if not config_path.exists():
            return set()
        try:
            tree = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
        except SyntaxError:
            return set()
        env_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            prefix = ""
            field_names: list[str] = []
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if (
                            isinstance(t, ast.Name)
                            and t.id == "model_config"
                            and isinstance(stmt.value, ast.Call)
                        ):
                            for kw in stmt.value.keywords:
                                if kw.arg == "env_prefix" and isinstance(kw.value, ast.Constant):
                                    prefix = kw.value.value or ""
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    field_names.append(stmt.target.id)
            for fname in field_names:
                env_names.add(f"{prefix}{fname}".upper())
        # also pick up os.environ / os.getenv literals
        text = config_path.read_text(encoding="utf-8")
        for m in re.finditer(r"os\.(?:environ|getenv)\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']", text):
            env_names.add(m.group(1))
        return env_names
