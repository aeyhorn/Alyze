"""HTTP client for bdx-quoter (Docker service on :8020).

The quoter UI proxies ``/api`` to its Python web server. Exact route names were
not in the uploaded sources (``web/server.py`` missing), so paths are
configurable and the client tries a small set of known aliases.

Expected response shapes (any of):
- ``{kalkulation: {netto_eur, brutto_eur, offen: [...]}, ...}``  (projekt.json)
- ``{netto_eur, brutto_eur, offen: [...], positionen: [...]}``   (kalkulation.json)
- ``{job_id, status, kalkulation?: ...}``                        (async job)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import httpx
import structlog

from bdx.config import QuoterSettings

logger = structlog.get_logger(__name__)

_HEALTH_ALIASES = ("/api/health", "/health", "/api/v1/health")
_RUN_ALIASES = ("/api/run", "/api/v1/run", "/api/quote", "/api/v1/quote")
_PROJEKT_ALIASES = ("/api/projekt", "/api/v1/projekt", "/api/project")


@dataclass
class QuoterQuote:
    """Normalised quote result for Q2P."""

    ok: bool
    netto_eur: Optional[float] = None
    brutto_eur: Optional[float] = None
    offen: list[str] = field(default_factory=list)
    position_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)
    source_path: str = ""
    error: Optional[str] = None
    status: str = "done"  # done | running | error | unavailable


class QuoterClient(Protocol):
    def health(self) -> bool: ...

    def quote(
        self,
        *,
        datenraum: str,
        kunde: str | None = None,
        llm: bool = False,
        fresh: bool = False,
        item_code: str | None = None,
        qty: float | None = None,
    ) -> QuoterQuote: ...


class NullQuoterClient:
    """Disabled / unconfigured quoter."""

    def health(self) -> bool:
        return False

    def quote(self, **_: Any) -> QuoterQuote:
        return QuoterQuote(ok=False, status="unavailable", error="quoter disabled")


class HttpQuoterClient:
    """Read/trigger quotes against a running bdx-quoter container."""

    def __init__(self, settings: QuoterSettings, client: httpx.Client | None = None) -> None:
        self._cfg = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=settings.base_url.rstrip("/"),
            timeout=settings.timeout_seconds,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self._cfg.api_key:
            h["X-API-Key"] = self._cfg.api_key
        return h

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def health(self) -> bool:
        paths = [self._cfg.health_path] if self._cfg.health_path else []
        paths.extend(p for p in _HEALTH_ALIASES if p not in paths)
        for path in paths:
            try:
                resp = self._client.get(path)
                if resp.status_code < 400:
                    return True
            except Exception as exc:  # noqa: BLE001
                logger.debug("quoter.health_failed", path=path, error=str(exc))
        return False

    def quote(
        self,
        *,
        datenraum: str,
        kunde: str | None = None,
        llm: bool = False,
        fresh: bool = False,
        item_code: str | None = None,
        qty: float | None = None,
    ) -> QuoterQuote:
        datenraum = (datenraum or "").strip()
        if not datenraum:
            return QuoterQuote(ok=False, status="error", error="datenraum fehlt")

        # 1) Prefer cached projekt if the API exposes it
        cached = self._try_projekt(datenraum)
        if cached is not None and cached.ok and not fresh:
            return cached

        # 2) Trigger / run pipeline
        body: dict[str, Any] = {
            "datenraum": datenraum,
            "llm": bool(llm),
            "fresh": bool(fresh),
        }
        if kunde:
            body["kunde"] = kunde
        if item_code:
            body["item_code"] = item_code
        if qty is not None:
            body["qty"] = qty

        paths = [self._cfg.run_path] if self._cfg.run_path else []
        paths.extend(p for p in _RUN_ALIASES if p not in paths)

        last_err: str | None = None
        for path in paths:
            try:
                resp = self._client.post(path, json=body)
                if resp.status_code == 404:
                    continue
                if resp.status_code >= 400:
                    last_err = f"{path} → HTTP {resp.status_code}: {resp.text[:240]}"
                    continue
                data = resp.json()
                quote = _normalise(data, source_path=path)
                if quote.status == "running" and quote.raw.get("job_id"):
                    polled = self._poll_job(str(quote.raw["job_id"]))
                    if polled is not None:
                        return polled
                return quote
            except Exception as exc:  # noqa: BLE001
                last_err = f"{path}: {exc}"
                logger.warning("quoter.run_failed", path=path, error=str(exc))

        if cached is not None:
            return cached
        return QuoterQuote(
            ok=False,
            status="unavailable",
            error=last_err or "kein passender Quoter-Endpunkt (web/server.py Routen prüfen)",
        )

    def _try_projekt(self, datenraum: str) -> QuoterQuote | None:
        paths = [self._cfg.projekt_path] if self._cfg.projekt_path else []
        paths.extend(p for p in _PROJEKT_ALIASES if p not in paths)
        for path in paths:
            try:
                resp = self._client.get(path, params={"datenraum": datenraum})
                if resp.status_code == 404:
                    continue
                if resp.status_code >= 400:
                    continue
                return _normalise(resp.json(), source_path=path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("quoter.projekt_failed", path=path, error=str(exc))
        return None

    def _poll_job(self, job_id: str) -> QuoterQuote | None:
        """Poll async job endpoints if the run returned a job_id."""
        candidates = (
            f"/api/jobs/{job_id}",
            f"/api/v1/jobs/{job_id}",
            f"/api/run/{job_id}",
        )
        for path in candidates:
            try:
                resp = self._client.get(path)
                if resp.status_code >= 400:
                    continue
                return _normalise(resp.json(), source_path=path)
            except Exception:  # noqa: BLE001
                continue
        return None


def _normalise(data: Any, *, source_path: str) -> QuoterQuote:
    if not isinstance(data, dict):
        return QuoterQuote(ok=False, status="error", error="Antwort kein JSON-Objekt", source_path=source_path)

    status = str(data.get("status") or "done").lower()
    if status in {"queued", "running", "pending"}:
        return QuoterQuote(ok=False, status="running", raw=data, source_path=source_path)

    kalk = data.get("kalkulation") if isinstance(data.get("kalkulation"), dict) else data
    offen_raw = kalk.get("offen") if isinstance(kalk, dict) else None
    if offen_raw is None:
        offen_raw = data.get("offen") or []
    offen = [str(x) for x in offen_raw] if isinstance(offen_raw, list) else []

    netto = _as_float(kalk.get("netto_eur") if isinstance(kalk, dict) else None)
    brutto = _as_float(kalk.get("brutto_eur") if isinstance(kalk, dict) else None)
    positions = []
    if isinstance(kalk, dict):
        positions = kalk.get("positionen") or []
    if not positions:
        pos_block = data.get("positionen")
        if isinstance(pos_block, dict):
            positions = pos_block.get("positionen") or []
        elif isinstance(pos_block, list):
            positions = pos_block

    if netto is None and brutto is None and not positions and data.get("error"):
        return QuoterQuote(
            ok=False,
            status="error",
            error=str(data.get("error")),
            raw=data,
            source_path=source_path,
            offen=offen,
        )

    ok = netto is not None or brutto is not None or bool(positions)
    return QuoterQuote(
        ok=ok,
        netto_eur=netto,
        brutto_eur=brutto,
        offen=offen,
        position_count=len(positions) if isinstance(positions, list) else 0,
        raw=data,
        source_path=source_path,
        status="done" if ok else "error",
        error=None if ok else "Kalkulation ohne Netto/Positionen",
    )


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_quoter_client(settings: QuoterSettings | None = None) -> QuoterClient:
    from bdx.config import load_quoter_settings

    cfg = settings or load_quoter_settings()
    if not cfg.configured:
        return NullQuoterClient()
    return HttpQuoterClient(cfg)
