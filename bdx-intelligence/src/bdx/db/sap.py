"""SAP Business One SQL Server connection factory (read-only, no writes permitted)."""
from __future__ import annotations

import structlog
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from bdx.config import SAPSettings

logger = structlog.get_logger(__name__)

# Safety guard: block any DML/DDL from accidentally reaching SAP
_FORBIDDEN_KEYWORDS = frozenset(
    ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "EXEC", "EXECUTE"]
)


def _assert_readonly(statement: str) -> None:
    upper = statement.upper().strip()
    for kw in _FORBIDDEN_KEYWORDS:
        if kw in upper.split():
            raise PermissionError(f"Write operation '{kw}' is not allowed on the SAP read-only connection.")


def create_sap_engine(settings: SAPSettings) -> Engine:
    """Create a SQLAlchemy engine for the SAP SQL Server database.

    The engine is configured:
    - read-only connection (service account must have read-only SQL permissions)
    - statement-level write guard (belt-and-suspenders)
    - pool pre-ping for reliability
    - explicit connect/query timeouts
    """
    url = settings.sqlalchemy_url()
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
        pool_timeout=settings.connect_timeout,
        connect_args={
            "timeout": settings.connect_timeout,
        },
        echo=False,
    )

    @event.listens_for(engine, "before_cursor_execute")
    def _guard_writes(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        _assert_readonly(statement)
        logger.debug("sap.query", statement=statement[:200])

    logger.info(
        "sap.engine.created",
        host=settings.host,
        port=settings.port,
        database=settings.name,
        tls=settings.tls,
    )
    return engine


def probe_sap_connection(engine: Engine) -> bool:
    """Return True if the SAP database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("sap.probe.ok")
        return True
    except Exception as exc:
        logger.warning("sap.probe.failed", error=str(exc))
        return False
