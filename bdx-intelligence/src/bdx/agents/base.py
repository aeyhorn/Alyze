"""Common types for the quality-gate agents.

Every agent returns a :class:`CheckResult` - a list of :class:`Finding` objects
plus an aggregate :class:`Status`. Findings carry a :class:`Severity` so the
runner can decide whether the gate is green (passed), yellow (warnings only)
or red (at least one error).
"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from dataclasses import dataclass, field


class Severity(enum.Enum):
    """How bad a single finding is."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def is_blocking(self) -> bool:
        return self is Severity.ERROR


class Status(enum.Enum):
    """Aggregate status of an agent run."""

    PASSED = "passed"
    WARNED = "warned"
    FAILED = "failed"

    @classmethod
    def from_findings(cls, findings: Iterable[Finding]) -> Status:
        has_error = any(f.severity is Severity.ERROR for f in findings)
        has_warning = any(f.severity is Severity.WARNING for f in findings)
        if has_error:
            return cls.FAILED
        if has_warning:
            return cls.WARNED
        return cls.PASSED


@dataclass(frozen=True)
class Finding:
    """A single observation produced by an agent."""

    code: str
    """Stable, machine-readable identifier, e.g. ``"DOC.MISSING_DOCSTRING"``."""

    message: str
    """Human-readable description of the issue."""

    location: str = ""
    """File path, optionally with ``:line`` suffix."""

    severity: Severity = Severity.WARNING

    def render(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.severity.value.upper():7} {self.code}{loc} - {self.message}"


@dataclass
class CheckResult:
    """The full output of one agent run."""

    agent: str
    """Agent name, e.g. ``"documentation"``."""

    findings: list[Finding] = field(default_factory=list)
    summary: str = ""

    @property
    def status(self) -> Status:
        return Status.from_findings(self.findings)

    @property
    def passed(self) -> bool:
        return self.status is Status.PASSED

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is Severity.INFO)

    def add(
        self,
        code: str,
        message: str,
        *,
        location: str = "",
        severity: Severity = Severity.WARNING,
    ) -> Finding:
        f = Finding(code=code, message=message, location=location, severity=severity)
        self.findings.append(f)
        return f

    def render(self) -> str:
        lines = [
            f"== {self.agent} -> {self.status.value} =="
            f"  ({self.error_count} error, {self.warning_count} warn, {self.info_count} info)"
        ]
        if self.summary:
            lines.append(self.summary)
        if not self.findings:
            lines.append("  no findings")
        for f in self.findings:
            lines.append("  " + f.render())
        return "\n".join(lines)
