"""Health-check endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, get_sap_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    request: Request,
    pg_session: Session = Depends(get_pg_session),
    sap_ok: bool = Depends(get_sap_status),
):
    """Liveness / readiness probe.

    ``status`` is ``ok`` when Postgres is reachable and the last collector run
    succeeded recently; ``degraded`` otherwise.  Optional components (SAP probe,
    machine feed, publisher) are reported but do not fail the probe.
    """
    pg_ok = _check_postgres(pg_session)
    collector = _collector_status(pg_session) if pg_ok else {"status": "unknown"}

    checks = {
        "postgres": "ok" if pg_ok else "error",
        "sap_sqlserver": "ok" if sap_ok else "unknown",
        "collector": collector,
    }

    machine_adapter = getattr(request.app.state, "machine_adapter", None)
    if machine_adapter is not None:
        checks["machine_feed"] = "ok" if _safe(machine_adapter.health_check) else "error"
    else:
        checks["machine_feed"] = "disabled"

    publisher = getattr(request.app.state, "publisher", None)
    if publisher is not None and type(publisher).__name__ != "NullPublisher":
        checks["publisher"] = "ok" if _safe(publisher.health_check) else "error"
    else:
        checks["publisher"] = "disabled"

    quoter = getattr(request.app.state, "quoter_client", None)
    if quoter is not None and type(quoter).__name__ != "NullQuoterClient":
        checks["quoter"] = "ok" if _safe(quoter.health) else "error"
    else:
        checks["quoter"] = "disabled"

    status = "ok" if (pg_ok and collector.get("status") in ("ok", "unknown", "empty")) else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@router.get("/health/live")
def liveness():
    """Kubernetes liveness probe – always 200 if the process is running."""
    return {"alive": True}


def _check_postgres(session: Session) -> bool:
    try:
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _collector_status(session: Session, stale_after: timedelta = timedelta(hours=1)) -> dict:
    """Summarise the most recent collector run."""
    try:
        from bdx.models.events import SnapshotRun

        last = session.execute(
            select(SnapshotRun).order_by(SnapshotRun.started_at.desc()).limit(1)
        ).scalars().first()
    except Exception:
        return {"status": "unknown"}
    if last is None:
        return {"status": "empty"}
    now = datetime.now(timezone.utc)
    started = last.started_at if last.started_at.tzinfo else last.started_at.replace(tzinfo=timezone.utc)
    stale = now - started > stale_after
    status = "error" if last.error else ("stale" if stale else "ok")
    return {
        "status": status,
        "last_run_id": last.run_id,
        "mode": last.mode,
        "started_at": started.isoformat(),
        "finished_at": last.finished_at.isoformat() if last.finished_at else None,
        "orders_read": last.orders_read,
        "events_created": last.events_created,
        "error": last.error,
    }


def _safe(fn) -> bool:  # noqa: ANN001
    try:
        return bool(fn())
    except Exception:
        return False
