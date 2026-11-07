"""Test agent - runs the suite independently and reports coverage gaps.

The agent shells out to ``pytest`` so it observes the *real* test run, not an
in-process import. It uses ``--co`` (collection-only) for a fast pre-flight and
``--json-report``-style parsing via the standard ``junitxml`` output that
pytest ships without extra plugins. Coverage is collected when
``pytest-cov`` is available; otherwise the agent degrades gracefully and just
reports pass/fail counts.
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bdx.agents.base import CheckResult, Severity


@dataclass
class TestConfig:
    """What the test agent runs."""

    root: Path
    test_paths: list[str] = field(default_factory=lambda: ["tests"])
    min_coverage: float = 80.0
    """Gate coverage percentage; below this → ERROR."""

    min_coverage_per_module: float = 50.0
    """Per-module floor; below this → WARNING."""

    max_skipped_ratio: float = 0.10
    """If more than 10 % of tests are skipped → WARNING."""

    coverage_source: str = "src/bdx"
    extra_args: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = Path(self.root)


class TestAgent:
    """Runs pytest and audits the result."""

    name = "tests"

    def __init__(self, cfg: TestConfig | None = None, *, root: Path | None = None) -> None:
        if cfg is None:
            cfg = TestConfig(root=root or Path.cwd())
        self.cfg = cfg

    def run(self) -> CheckResult:
        result = CheckResult(agent=self.name)
        junit_path = self.cfg.root / "build" / "agents" / "junit.xml"
        junit_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_cmd(junit_path)
        result.summary = f"running: {' '.join(cmd)}"
        completed = subprocess.run(
            cmd,
            cwd=str(self.cfg.root),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if completed.returncode not in (0, 1):
            # pytest returns 1 on test failures; anything else is infra error
            result.add(
                "TEST.RUNNER_ERROR",
                f"pytest exited with {completed.returncode}: "
                f"{(completed.stderr or completed.stdout)[-500:]}",
                severity=Severity.ERROR,
            )
            return result

        self._parse_junit(junit_path, result)
        self._parse_coverage(result)
        return result

    # ── helpers ────────────────────────────────────────────────────────────
    def _build_cmd(self, junit_path: Path) -> list[str]:
        cmd = [
            sys.executable, "-m", "pytest",
            *self.cfg.test_paths,
            f"--junitxml={junit_path}",
            "-q",
            "--no-header",
            "-p", "no:cacheprovider",
        ]
        # coverage is opt-in: only add if pytest-cov is importable
        if self._has_cov():
            cmd += [f"--cov={self.cfg.coverage_source}", "--cov-report=json:build/agents/coverage.json"]
        cmd += self.cfg.extra_args
        return cmd

    @staticmethod
    def _has_cov() -> bool:
        try:
            import pytest_cov  # noqa: F401
            return True
        except ImportError:
            return False

    def _parse_junit(self, junit_path: Path, result: CheckResult) -> None:
        if not junit_path.exists():
            result.add(
                "TEST.NO_JUNIT",
                f"junit report not produced at {junit_path}",
                severity=Severity.ERROR,
            )
            return
        try:
            tree = ET.parse(junit_path)
        except ET.ParseError as exc:
            result.add("TEST.JUNIT_PARSE", f"cannot parse junit xml: {exc}", severity=Severity.ERROR)
            return
        root = tree.getroot()
        # junitxml: <testsuites><testsuite ...><testcase .../>
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        total = skipped = failures = errors = 0
        skipped_cases: list[str] = []
        for suite in suites:
            total += int(suite.get("tests", "0"))
            skipped += int(suite.get("skipped", "0"))
            failures += int(suite.get("failures", "0"))
            errors += int(suite.get("errors", "0"))
            for tc in suite.findall("testcase"):
                if tc.find("skipped") is not None:
                    name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
                    skipped_cases.append(name)
        if failures or errors:
            result.add(
                "TEST.FAILURES",
                f"{failures} test failure(s), {errors} error(s) across {total} tests",
                severity=Severity.ERROR,
            )
        if total == 0:
            result.add("TEST.NO_TESTS", "no tests collected", severity=Severity.ERROR)
            return
        ratio = skipped / total
        if ratio > self.cfg.max_skipped_ratio:
            result.add(
                "TEST.TOO_MANY_SKIPPED",
                f"{skipped}/{total} tests skipped ({ratio:.0%} > "
                f"{self.cfg.max_skipped_ratio:.0%})",
                severity=Severity.WARNING,
            )
        result.summary = (
            f"{total} tests: {failures} failed, {errors} errors, {skipped} skipped"
        )

    def _parse_coverage(self, result: CheckResult) -> None:
        cov_path = self.cfg.root / "build" / "agents" / "coverage.json"
        if not cov_path.exists():
            result.add(
                "TEST.NO_COVERAGE",
                "coverage report not produced (pytest-cov not installed?)",
                severity=Severity.INFO,
            )
            return
        try:
            data: dict[str, Any] = json.loads(cov_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.add("TEST.COVERAGE_PARSE", f"cannot parse coverage.json: {exc}", severity=Severity.ERROR)
            return
        totals = data.get("totals", {})
        pct = float(totals.get("percent_covered", 0.0))
        if pct < self.cfg.min_coverage:
            result.add(
                "TEST.COVERAGE_LOW",
                f"overall coverage {pct:.1f}% < {self.cfg.min_coverage:.1f}% threshold",
                severity=Severity.ERROR,
            )
        else:
            result.add(
                "TEST.COVERAGE_OK",
                f"overall coverage {pct:.1f}% ≥ {self.cfg.min_coverage:.1f}%",
                severity=Severity.INFO,
            )
        files = data.get("files", {})
        weak: list[tuple[str, float]] = []
        for name, fdata in files.items():
            fpct = float(fdata.get("summary", {}).get("percent_covered", 0.0))
            # ignore tiny __init__ files
            if name.endswith("__init__.py"):
                continue
            if fpct < self.cfg.min_coverage_per_module:
                weak.append((name, fpct))
        weak.sort(key=lambda x: x[1])
        for name, fpct in weak[:15]:
            result.add(
                "TEST.MODULE_COVERAGE_LOW",
                f"{name}: {fpct:.0f}% < {self.cfg.min_coverage_per_module:.0f}%",
                location=name,
                severity=Severity.WARNING,
            )
        if len(weak) > 15:
            result.add(
                "TEST.MODULE_COVERAGE_LOW",
                f"... and {len(weak) - 15} more modules below "
                f"{self.cfg.min_coverage_per_module:.0f}%",
                severity=Severity.INFO,
            )
