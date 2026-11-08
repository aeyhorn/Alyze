"""Shared agent result type."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    ok: bool
    summary: str
    gaps: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    needs_human: bool = False
    error: str | None = None
