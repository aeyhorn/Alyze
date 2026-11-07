"""BDE (Betriebsdatenerfassung / Manufacturing Data Collection) adapter.

Sprint 002 implements :class:`ScadaTelemetryBDEAdapter`.  There is no classic
BDE terminal system on the shop floor; instead the SCADA system stores one
telemetry point per machine every few seconds (``state``, ``order``,
``pieces``, …).  The adapter turns that history into BDE records:

* consecutive telemetry points of one machine with the same ``order`` form a
  record (start = first point, end = last point);
* a gap longer than ``gap_seconds`` or a change of ``order`` closes the record;
* ``quantity_good`` is the piece-counter delta within the record.

Source: ``GET <scada>/api/machines`` and ``GET <scada>/api/machines/{id}/telemetry?hours=N``
(read-only; the SCADA backend persists to SQL Server ``BXProduction``).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional
from urllib.parse import quote

import structlog

logger = structlog.get_logger(__name__)


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
    # extended
    sample_count: int = 0
    last_state: Optional[str] = None

    @property
    def sap_doc_num(self) -> Optional[int]:
        return int(self.order_id) if self.order_id.isdigit() else None

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or self.start_time
        return (end - self.start_time).total_seconds()


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


# ── SCADA telemetry → BDE records ────────────────────────────────────────────

def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def telemetry_to_records(
    machine_id: str,
    points: Iterable[dict],
    gap_seconds: int = 900,
) -> list[BDERecord]:
    """Group telemetry points into BDE records (pure function, unit-testable)."""
    records: list[BDERecord] = []
    current: dict | None = None

    def close(cur: dict) -> None:
        records.append(
            BDERecord(
                machine_id=machine_id,
                order_id=cur["order"],
                operation_id=cur.get("operation") or "",
                start_time=cur["start"],
                end_time=cur["end"],
                quantity_good=float(max(0, (cur["pieces_last"] or 0) - (cur["pieces_first"] or 0))),
                quantity_scrap=0.0,
                operator_id=cur.get("operator") or None,
                sample_count=cur["n"],
                last_state=cur.get("state"),
            )
        )

    for p in sorted(points, key=lambda x: x.get("timestamp") or ""):
        order = (p.get("order") or "").strip()
        if not order:
            if current:
                close(current)
                current = None
            continue
        ts = _parse_ts(p["timestamp"])
        pieces = p.get("pieces")
        if current and (current["order"] != order or (ts - current["end"]).total_seconds() > gap_seconds):
            close(current)
            current = None
        if current is None:
            current = {
                "order": order,
                "start": ts,
                "end": ts,
                "pieces_first": pieces,
                "pieces_last": pieces,
                "n": 0,
                "state": p.get("state"),
                "operator": p.get("operator") or p.get("user"),
            }
        current["end"] = ts
        if pieces is not None:
            if current["pieces_first"] is None:
                current["pieces_first"] = pieces
            current["pieces_last"] = pieces
        current["n"] += 1
        current["state"] = p.get("state")

    if current:
        close(current)
    return records


class ScadaTelemetryBDEAdapter(BDEAdapter):
    """Derives BDE records from the SCADA telemetry REST API."""

    def __init__(self, base_url: str, timeout: float = 30.0, gap_seconds: int = 900, client=None) -> None:  # noqa: ANN001
        import httpx

        self._base = base_url.rstrip("/")
        self._gap = gap_seconds
        self._http = client or httpx.Client(timeout=timeout, headers={"Accept": "application/json"})

    def list_machines(self) -> list[str]:
        resp = self._http.get(f"{self._base}/api/machines")
        resp.raise_for_status()
        return [m["machineId"] for m in resp.json() if m.get("machineId")]

    def fetch_telemetry(self, machine_id: str, hours: int) -> list[dict]:
        url = f"{self._base}/api/machines/{quote(machine_id, safe='')}/telemetry?hours={hours}"
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def fetch_recent(self, since: datetime) -> list[BDERecord]:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        hours = max(1, math.ceil((datetime.now(timezone.utc) - since).total_seconds() / 3600))
        records: list[BDERecord] = []
        try:
            machines = self.list_machines()
        except Exception as exc:  # noqa: BLE001
            logger.warning("bde.machines_failed", error=str(exc))
            return []
        for mid in machines:
            try:
                points = self.fetch_telemetry(mid, hours)
            except Exception as exc:  # noqa: BLE001
                logger.warning("bde.telemetry_failed", machine_id=mid, error=str(exc))
                continue
            recs = telemetry_to_records(mid, points, self._gap)
            records.extend(r for r in recs if (r.end_time or r.start_time) >= since)
        logger.info("bde.fetched", machines=len(machines), records=len(records), hours=hours)
        return records

    def health_check(self) -> bool:
        try:
            self.list_machines()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("bde.health_failed", error=str(exc))
            return False


def build_bde_adapter(settings=None) -> BDEAdapter:  # noqa: ANN001
    from bdx.config import load_bde_settings

    settings = settings or load_bde_settings()
    if settings.configured:
        return ScadaTelemetryBDEAdapter(settings.scada_base_url, settings.timeout_seconds, settings.gap_seconds)
    return NullBDEAdapter()


def build_machine_adapter(settings=None):  # noqa: ANN001, ANN201
    from bdx.adapters.machine import NullMachineAdapter, XmskMachineAdapter
    from bdx.config import load_machine_settings

    settings = settings or load_machine_settings()
    if settings.configured:
        return XmskMachineAdapter(settings.xmsk_url, settings.timeout_seconds)
    return NullMachineAdapter()


__all__ = [
    "BDERecord",
    "BDEAdapter",
    "NullBDEAdapter",
    "ScadaTelemetryBDEAdapter",
    "telemetry_to_records",
    "build_bde_adapter",
    "build_machine_adapter",
]
