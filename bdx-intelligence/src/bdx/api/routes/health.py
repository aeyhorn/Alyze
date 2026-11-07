"""Health-check endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bdx.api.deps import get_pg_session, get_sap_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    pg_session: Session = Depends(get_pg_session),
    sap_ok: bool = Depends(get_sap_status),
):
    """Liveness / readiness probe.  Returns 200 if both datastores are reachable."""
    pg_ok = _check_postgres(pg_session)
    status = "ok" if (pg_ok and sap_ok) else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "postgres": "ok" if pg_ok else "error",
            "sap_sqlserver": "ok" if sap_ok else "error",
        },
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
