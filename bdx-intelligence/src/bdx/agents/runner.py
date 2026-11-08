"""Runner - orchestrates the documentation, test and quality agents.

Produces a single :class:`RunnerReport` that the CLI renders. The runner is
the only piece the outside world needs to know about; it wires sensible
defaults for the three agents based on the project root.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bdx.agents.base import CheckResult, Severity, Status
from bdx.agents.docs import DocumentationAgent, DocumentationConfig
from bdx.agents.quality import QualityAgent, QualityConfig
from bdx.agents.tests import TestAgent, TestConfig


@dataclass
class RunnerReport:
    """Aggregate result of one runner invocation."""

    results: list[CheckResult] = field(default_factory=list)
    durations: dict[str, float] = field(default_factory=dict)

    @property
    def status(self) -> Status:
        statuses = [r.status for r in self.results]
        if Status.FAILED in statuses:
            return Status.FAILED
        if Status.WARNED in statuses:
            return Status.WARNED
        return Status.PASSED

    @property
    def exit_code(self) -> int:
        # 0 = passed, 1 = warnings, 2 = failed (errors)
        s = self.status
        if s is Status.FAILED:
            return 2
        if s is Status.WARNED:
            return 1
        return 0

    def render(self) -> str:
        lines: list[str] = []
        for r in self.results:
            dur = self.durations.get(r.agent, 0.0)
            lines.append(f"\n[{r.agent}]  {r.status.value}  ({dur:.1f}s)")
            if r.summary:
                lines.append(f"  {r.summary}")
            for f in r.findings:
                lines.append("  " + f.render())
        lines.append("\n" + "=" * 60)
        lines.append(f"OVERALL: {self.status.value}  (exit code {self.exit_code})")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "exit_code": self.exit_code,
            "agents": [
                {
                    "name": r.agent,
                    "status": r.status.value,
                    "duration_s": self.durations.get(r.agent, 0.0),
                    "summary": r.summary,
                    "findings": [
                        {
                            "code": f.code,
                            "message": f.message,
                            "location": f.location,
                            "severity": f.severity.value,
                        }
                        for f in r.findings
                    ],
                }
                for r in self.results
            ],
        }


@dataclass
class RunnerConfig:
    """Which agents to run and where the project lives."""

    root: Path
    run_docs: bool = True
    run_tests: bool = True
    run_quality: bool = True
    min_coverage: float = 80.0
    enable_mypy: bool = True
    enable_ruff: bool = True


class AgentRunner:
    """Run the configured agents and produce a :class:`RunnerReport`."""

    def __init__(self, cfg: RunnerConfig | None = None, *, root: Path | None = None) -> None:
        if cfg is None:
            cfg = RunnerConfig(root=root or Path.cwd())
        self.cfg = cfg

    def run(self) -> RunnerReport:
        report = RunnerReport()
        if self.cfg.run_docs:
            self._timed(report, DocumentationAgent(DocumentationConfig(root=self.cfg.root)))
        if self.cfg.run_tests:
            self._timed(
                report,
                TestAgent(TestConfig(root=self.cfg.root, min_coverage=self.cfg.min_coverage)),
            )
        if self.cfg.run_quality:
            self._timed(
                report,
                QualityAgent(
                    QualityConfig(
                        root=self.cfg.root,
                        enable_mypy=self.cfg.enable_mypy,
                        enable_ruff=self.cfg.enable_ruff,
                    )
                ),
            )
        return report

    def _timed(self, report: RunnerReport, agent: Any) -> None:
        start = time.perf_counter()
        try:
            result = agent.run()
        except Exception as exc:  # never let an agent crash the runner
            result = CheckResult(agent=getattr(agent, "name", "unknown"))
            result.add("AGENT.CRASHED", f"{type(exc).__name__}: {exc}", severity=Severity.ERROR)
        report.durations[result.agent] = time.perf_counter() - start
        report.results.append(result)
        return None


def write_json_report(report: RunnerReport, path: Path) -> Path:
    """Persist a runner report as JSON for CI artifact collection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
