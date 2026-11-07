"""BDE (Betriebsdatenerfassung / Manufacturing Data Collection) adapter stub.

Sprint 001: Interface definition only – no implementation.
The actual BDE system integration will be implemented in a future sprint.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class BDERecord:
    """A single BDE event as reported by the shop-floor system."""

    machine_id: str
    order_id: str
    operation_id: str
    start_time: datetime
    end_time: Optional[datetime]
    quantity_good: float
    quantity_scrap: float
    operator_id: Optional[str]


class BDEAdapter(ABC):
    """Abstract adapter for receiving BDE data from the shop-floor system."""

    @abstractmethod
    def fetch_recent(self, since: datetime) -> list[BDERecord]:
        """Return BDE records reported since *since*."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the BDE system is reachable."""
        raise NotImplementedError


class NullBDEAdapter(BDEAdapter):
    """No-op implementation used when no BDE system is configured."""

    def fetch_recent(self, since: datetime) -> list[BDERecord]:
        return []

    def health_check(self) -> bool:
        return True
