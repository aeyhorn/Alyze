"""Machine/CNC adapter – read-only access to machine status.

Sprint 002 implements :class:`XmskMachineAdapter`, which reads the Mazak
``XmskSvr`` ``machstates`` XML feed (as proxied by the SCADA system on
``http://<host>:3888/api/machstates``).  No machine control commands are
issued from this module – it is strictly READ-ONLY.

XML shape (one ``<Device>`` per machine)::

    <XMSK Timestamp='2026-11-07T12:29:29' Version='1.0'>
      <Devices>
        <Device Name='Integrex i500S' MDE='1' Exec='Bereit' Order='38574'
                Oper='CNC' Part='10886/UEBERGABE' NCP='227' Pieces='243 / 44'
                User='' LastProdEnd='' Mode='MEM' Feed='100' Spindle='100'
                Rapid='50' State='Fertigen' LastMsg='' Load0='48' Load1='0' Load2='48'/>
      </Devices>
    </XMSK>
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MachineStatus:
    """Point-in-time status of a machine."""

    machine_id: str
    timestamp: datetime
    state: str  # normalised: running | idle | setup | off | unknown
    program_name: str | None = None
    spindle_rpm: float | None = None  # not available from XMSK (override % instead)
    feed_rate: float | None = None  # not available from XMSK (override % instead)
    alarm_code: str | None = None
    # ── XMSK raw / extended fields ───────────────────────────────────────────
    mde_enabled: bool = True
    exec_state: str | None = None  # Exec: AUS / Bereit / ...
    raw_state: str | None = None  # State: Fertigen / Auftrag / Ruesten / ''
    mode: str | None = None  # MEM / RAPID / 0
    order_ref: str | None = None  # Order as reported (may be SAP DocNum)
    operation: str | None = None
    part: str | None = None
    pieces: int | None = None  # first number of "243 / 44"
    pieces_raw: str | None = None
    operator: str | None = None
    feed_override: int | None = None
    spindle_override: int | None = None
    rapid_override: int | None = None
    load_spindle: float | None = None
    load_axis_1: float | None = None
    load_axis_2: float | None = None
    last_message: str | None = None
    last_prod_end: str | None = None
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def sap_doc_num(self) -> int | None:
        """Return the order reference as SAP DocNum when it is purely numeric."""
        if self.order_ref and re.fullmatch(r"\d{1,9}", self.order_ref.strip()):
            return int(self.order_ref.strip())
        return None


class MachineAdapter(ABC):
    """Abstract adapter for reading machine status.

    IMPORTANT: This adapter is strictly READ-ONLY.  No methods for sending
    commands, changing parameters, or controlling machines will ever be added
    to this interface without an explicit security review.
    """

    @abstractmethod
    def get_status(self, machine_id: str) -> MachineStatus | None:
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

    def get_all_status(self) -> list[MachineStatus]:
        """Return the status of every known machine (default: one call per machine)."""
        result = []
        for mid in self.list_machines():
            st = self.get_status(mid)
            if st is not None:
                result.append(st)
        return result


class NullMachineAdapter(MachineAdapter):
    """No-op implementation used when no machine network is configured."""

    def get_status(self, machine_id: str) -> MachineStatus | None:
        return None

    def list_machines(self) -> list[str]:
        return []

    def health_check(self) -> bool:
        return True


# ── XMSK ─────────────────────────────────────────────────────────────────────


def _to_int(v: str | None) -> int | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(str(v).strip()))
    except ValueError:
        return None


def _to_float(v: str | None) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _first_int(v: str | None) -> int | None:
    """'243 / 44' → 243 ; '0' → 0 ; '' → None."""
    if not v:
        return None
    m = re.search(r"-?\d+", v)
    return int(m.group()) if m else None


def normalise_state(exec_state: str | None, raw_state: str | None, mde: bool) -> str:
    """Map XMSK Exec/State pairs onto a small vocabulary."""
    if not mde:
        return "unknown"
    ex = (exec_state or "").strip().lower()
    st = (raw_state or "").strip().lower()
    if ex in ("aus", "off", ""):
        return "off"
    if st in ("fertigen", "auftrag", "produktion", "running"):
        return "running"
    if st in ("ruesten", "rüsten", "setup", "einrichten"):
        return "setup"
    if st in ("stoerung", "störung", "alarm", "fault"):
        return "fault"
    if ex in ("bereit", "ready", "idle"):
        return "idle"
    return "unknown"


def parse_xmsk(xml_text: str, now: datetime | None = None) -> list[MachineStatus]:
    """Parse a ``machstates`` XML document into MachineStatus objects."""
    now = now or datetime.now(UTC)
    text = xml_text.strip()
    if not text:
        return []
    root = ET.fromstring(text)
    ts_attr = root.get("Timestamp")
    try:
        # XmskSvr reports local wall-clock time without offset → interpret in the host's local zone
        source_ts = datetime.fromisoformat(ts_attr) if ts_attr else now
        if source_ts.tzinfo is None:
            source_ts = source_ts.replace(tzinfo=datetime.now().astimezone().tzinfo)
        source_ts = source_ts.astimezone(UTC)
    except ValueError:
        source_ts = now

    result: list[MachineStatus] = []
    for dev in root.iter("Device"):
        name = (dev.get("Name") or "").strip()
        if not name:
            continue
        mde = (dev.get("MDE") or "1").strip() not in ("0", "false", "False")
        exec_state = dev.get("Exec") or None
        raw_state = dev.get("State") or None
        result.append(
            MachineStatus(
                machine_id=name,
                timestamp=source_ts,
                state=normalise_state(exec_state, raw_state, mde),
                program_name=dev.get("NCP") or None,
                alarm_code=(dev.get("LastMsg") or None),
                mde_enabled=mde,
                exec_state=exec_state,
                raw_state=raw_state,
                mode=dev.get("Mode") or None,
                order_ref=(dev.get("Order") or "").strip() or None,
                operation=(dev.get("Oper") or "").strip() or None,
                part=(dev.get("Part") or "").strip() or None,
                pieces=_first_int(dev.get("Pieces")),
                pieces_raw=(dev.get("Pieces") or "").strip() or None,
                operator=(dev.get("User") or "").strip() or None,
                feed_override=_to_int(dev.get("Feed")),
                spindle_override=_to_int(dev.get("Spindle")),
                rapid_override=_to_int(dev.get("Rapid")),
                load_spindle=_to_float(dev.get("Load0")),
                load_axis_1=_to_float(dev.get("Load1")),
                load_axis_2=_to_float(dev.get("Load2")),
                last_message=(dev.get("LastMsg") or "").strip() or None,
                last_prod_end=(dev.get("LastProdEnd") or "").strip() or None,
            )
        )
    return result


class XmskMachineAdapter(MachineAdapter):
    """Reads all machines from a single XMSK ``machstates`` endpoint."""

    def __init__(self, url: str, timeout: float = 10.0, client=None) -> None:
        import httpx

        self._url = url
        self._http = client or httpx.Client(
            timeout=timeout, headers={"Accept": "text/plain, application/xml"}
        )
        self._cache: dict[str, MachineStatus] = {}

    def fetch(self) -> list[MachineStatus]:
        """GET the feed, parse it, refresh the cache.  Raises on transport errors."""
        resp = self._http.get(self._url)
        resp.raise_for_status()
        statuses = parse_xmsk(resp.text)
        self._cache = {s.machine_id: s for s in statuses}
        logger.debug("xmsk.fetched", machines=len(statuses))
        return statuses

    def get_all_status(self) -> list[MachineStatus]:
        try:
            return self.fetch()
        except Exception as exc:
            logger.warning("xmsk.fetch_failed", error=str(exc))
            return []

    def get_status(self, machine_id: str) -> MachineStatus | None:
        if not self._cache:
            self.get_all_status()
        return self._cache.get(machine_id)

    def list_machines(self) -> list[str]:
        if not self._cache:
            self.get_all_status()
        return sorted(self._cache)

    def health_check(self) -> bool:
        try:
            self.fetch()
            return True
        except Exception as exc:
            logger.warning("xmsk.health_failed", error=str(exc))
            return False
