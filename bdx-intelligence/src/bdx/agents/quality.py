"""Quality agent - lint, type-check and code-smell scan, independent of runtime.

Shells out to ``ruff`` and ``mypy`` (the project's existing toolchain declared
in ``pyproject.toml``) and adds a few lightweight AST/regex heuristics for
smells that the linters do not flag by default. The agent never imports the
runtime package, so it works in a clean CI image with only the dev extras
installed.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from bdx.agents.base import CheckResult, Severity


@dataclass
class QualityConfig:
    """What the quality agent runs."""

    root: Path
    src_dir: Path = field(init=False)
    enable_ruff: bool = True
    enable_mypy: bool = True
    enable_smells: bool = True
    ruff_args: list[str] = field(default_factory=list)
    mypy_args: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.src_dir = self.root / "src" / "bdx"


class QualityAgent:
    """Lint + type-check + smell scan."""

    name = "quality"

    def __init__(self, cfg: QualityConfig | None = None, *, root: Path | None = None) -> None:
        if cfg is None:
            cfg = QualityConfig(root=root or Path.cwd())
        self.cfg = cfg

    def run(self) -> CheckResult:
        result = CheckResult(agent=self.name)
        if self.cfg.enable_ruff:
            self._run_ruff(result)
        else:
            result.add("QUALITY.RUFF_DISABLED", "ruff check skipped", severity=Severity.INFO)
        if self.cfg.enable_mypy:
            self._run_mypy(result)
        else:
            result.add("QUALITY.MYPY_DISABLED", "mypy check skipped", severity=Severity.INFO)
        if self.cfg.enable_smells:
            self._scan_smells(result)
        return result

    # ── ruff ───────────────────────────────────────────────────────────────
    def _run_ruff(self, result: CheckResult) -> None:
        cmd = [sys.executable, "-m", "ruff", "check", "--output-format=json",
               "src/bdx", "tests", *self.cfg.ruff_args]
        try:
            completed = subprocess.run(
                cmd, cwd=str(self.cfg.root), capture_output=True, text=True, timeout=180
            )
        except FileNotFoundError:
            result.add("QUALITY.RUFF_MISSING", "ruff not installed", severity=Severity.WARNING)
            return
        except subprocess.TimeoutExpired:
            result.add("QUALITY.RUFF_TIMEOUT", "ruff timed out after 180s", severity=Severity.ERROR)
            return
        # ruff returns 0 = clean, 1 = violations found, >1 = error
        if completed.returncode > 1:
            result.add(
                "QUALITY.RUFF_ERROR",
                f"ruff exited {completed.returncode}: {(completed.stderr or '')[-300:]}",
                severity=Severity.ERROR,
            )
            return
        try:
            findings = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError:
            # non-JSON output (e.g. when ruff is too old) → fall back to stderr
            result.add(
                "QUALITY.RUFF_UNPARSED",
                f"could not parse ruff output: {(completed.stdout or completed.stderr)[-300:]}",
                severity=Severity.WARNING,
            )
            return
        for f in findings:
            sev = Severity.ERROR if f.get("fix") is None and f.get("url") else Severity.WARNING
            # E/F-class rules are real errors; the rest are style warnings
            code = f.get("code", "RUFF")
            if code.startswith(("E", "F", "B")):
                sev = Severity.ERROR
            elif code.startswith(("I", "UP", "SIM", "C4", "TID", "RUF")):
                sev = Severity.WARNING
            loc = f"{f.get('filename', '')}:{f.get('location', {}).get('row', '?')}"
            result.add(
                f"RUFF.{code}",
                f.get("message", "ruff finding"),
                location=loc,
                severity=sev,
            )
        if not findings:
            result.add("QUALITY.RUFF_CLEAN", "ruff: no issues", severity=Severity.INFO)

    # ── mypy ───────────────────────────────────────────────────────────────
    def _run_mypy(self, result: CheckResult) -> None:
        cmd = [sys.executable, "-m", "mypy", "src/bdx", *self.cfg.mypy_args]
        try:
            completed = subprocess.run(
                cmd, cwd=str(self.cfg.root), capture_output=True, text=True, timeout=300
            )
        except FileNotFoundError:
            result.add("QUALITY.MYPY_MISSING", "mypy not installed", severity=Severity.WARNING)
            return
        except subprocess.TimeoutExpired:
            result.add("QUALITY.MYPY_TIMEOUT", "mypy timed out after 300s", severity=Severity.ERROR)
            return
        # mypy: 0 = clean, 1 = issues found
        if completed.returncode not in (0, 1):
            result.add(
                "QUALITY.MYPY_ERROR",
                f"mypy exited {completed.returncode}: {(completed.stderr or '')[-300:]}",
                severity=Severity.ERROR,
            )
            return
        out = completed.stdout or ""
        if not out.strip():
            result.add("QUALITY.MYPY_CLEAN", "mypy: no issues", severity=Severity.INFO)
            return
        # parse lines like:  src/bdx/foo.py:12: error: ...  [attr-defined]
        pattern = re.compile(
            r"^(?P<file>[^:]+):(?P<line>\d+): (?P<level>error|warning|note): (?P<msg>.*?)(?:  \[(?P<code>[^\]]+)\])?$"
        )
        counts = {"error": 0, "warning": 0, "note": 0}
        for line in out.splitlines():
            m = pattern.match(line)
            if not m:
                continue
            level = m.group("level")
            counts[level] = counts.get(level, 0) + 1
            sev = {"error": Severity.ERROR, "warning": Severity.WARNING, "note": Severity.INFO}[level]
            code = f"MYPY.{m.group('code') or 'ISSUE'}"
            result.add(code, m.group("msg"), location=f"{m.group('file')}:{m.group('line')}", severity=sev)
        result.summary = (
            f"mypy: {counts['error']} error, {counts['warning']} warning, {counts['note']} note"
        )

    # ── smell scan ─────────────────────────────────────────────────────────
    def _scan_smells(self, result: CheckResult) -> None:
        todo_re = re.compile(r"#\s*TODO(?:\(([^)]+)\))?:?\s*(.+)")
        for path in self._iter_python_files():
            rel = path.relative_to(self.cfg.root)
            try:
                src = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            # bare TODOs without an owner (comment-level, regex is fine here)
            for i, line in enumerate(src.splitlines(), 1):
                m = todo_re.search(line)
                if m and not m.group(1):
                    result.add(
                        "SMELL.TODO_NO_OWNER",
                        f"TODO without owner: {m.group(2).strip()[:80]}",
                        location=f"{rel}:{i}",
                        severity=Severity.INFO,
                    )
            # AST-based checks: only real call nodes are flagged, so string
            # literals or regex patterns containing "print(" are not matched.
            try:
                tree = ast.parse(src, filename=str(path))
            except SyntaxError:
                continue
            is_test = "tests" in path.parts
            for node in ast.walk(tree):
                # bare print() calls (not method calls like console.print())
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                    and not is_test
                ):
                    result.add(
                        "SMELL.PRINT_STATEMENT",
                        "print() in production code - use structlog",
                        location=f"{rel}:{node.lineno}",
                        severity=Severity.WARNING,
                    )
                if not isinstance(node, ast.ExceptHandler):
                    continue
                body = node.body
                if (
                    len(body) == 1
                    and isinstance(body[0], ast.Pass)
                ):
                    result.add(
                        "SMELL.EMPTY_EXCEPT",
                        f"empty except (line {node.lineno}) swallows errors",
                        location=f"{rel}:{node.lineno}",
                        severity=Severity.WARNING,
                    )

    def _iter_python_files(self) -> Iterable[Path]:
        for path in sorted(self.cfg.src_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path
