"""Quality-gate agents - documentation, tests and code quality.

These agents are intentionally decoupled from the running collector/API: they
operate purely on the source tree and the developer toolchain (pytest, ruff,
mypy) so they can be used as an independent pre-merge / CI check against the
state of development. None of them require a database, SAP, or any external
system.
"""

from __future__ import annotations

from bdx.agents.base import CheckResult, Finding, Severity, Status
from bdx.agents.docs import DocumentationAgent
from bdx.agents.quality import QualityAgent
from bdx.agents.runner import AgentRunner, RunnerReport
from bdx.agents.tests import TestAgent

__all__ = [
    "AgentRunner",
    "CheckResult",
    "DocumentationAgent",
    "Finding",
    "QualityAgent",
    "RunnerReport",
    "Severity",
    "Status",
    "TestAgent",
]
