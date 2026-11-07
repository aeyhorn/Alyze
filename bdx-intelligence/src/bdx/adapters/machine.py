"""Machine/CNC adapter stub.

Sprint 001: Interface definition only – no implementation.
Direct machine communication (OPC-UA, MTConnect, etc.) will be implemented
in a future sprint.  No machine control commands are issued from this module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MachineStatus:
    """Point-in-time status of a machine."""

    machine_id: str
    timestamp: datetime
    state: str  # e.g. "running", "idle", "fault", "setup"
    program_name: Optional[str]
    spindle_rpm: Optional[float]
    feed_rate: Optional[float]
    alarm_code: Optional[str]


class MachineAdapter(ABC):
    """Abstract adapter for reading machine status.

    IMPORTANT: This adapter is strictly READ-ONLY.  No methods for sending
    commands, changing parameters, or controlling machines will ever be added
    to this interface without an explicit security review.
    """

    @abstractmethod
    def get_status(self, machine_id: str) -> Optional[MachineStatus]:
        """Return current status of the given machine, or None if unreachable."""
        raise NotImplementedError

    @abstractmethod
    def list_machines(self) -> list[str]:
        """Return a list of known machine IDs."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the machine network layer is reachable."""
        raise NotImplementedError


class NullMachineAdapter(MachineAdapter):
    """No-op implementation used when no machine network is configured."""

    def get_status(self, machine_id: str) -> Optional[MachineStatus]:
        return None

    def list_machines(self) -> list[str]:
        return []

    def health_check(self) -> bool:
        return True
