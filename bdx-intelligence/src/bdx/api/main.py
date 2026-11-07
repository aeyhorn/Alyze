"""FastAPI application factory."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bdx.api.routes import health, orders
from bdx.config import load_app_settings, load_postgres_settings
from bdx.db.postgres import create_pg_engine, make_session_factory
from bdx.logging_config import configure_logging

logger = structlog.get_logger(__name__)


def create_app(
    pg_dsn: str | None = None,
    sap_engine=None,  # noqa: ANN001
    pg_session_factory=None,  # noqa: ANN001
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        pg_dsn:              Override PostgreSQL DSN.
        sap_engine:          Pre-built SAP engine; health check skipped when None.
        pg_session_factory:  Inject a pre-built session factory (e.g. for tests
                             with a pre-populated SQLite engine).
    """
    app_cfg = load_app_settings()
    configure_logging(app_cfg.log_level, app_cfg.log_format)

    app = FastAPI(
        title="BDX Intelligence",
        description="Read-only SAP Business One production order collector and event API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    if pg_session_factory is not None:
        app.state.pg_session_factory = pg_session_factory
    else:
        pg_dsn = pg_dsn or load_postgres_settings().postgres_dsn
        pg_engine = create_pg_engine(pg_dsn)
        app.state.pg_session_factory = make_session_factory(pg_engine)

    app.state.sap_ok = False

    if sap_engine is not None:
        from bdx.db.sap import probe_sap_connection
        app.state.sap_ok = probe_sap_connection(sap_engine)

    app.include_router(health.router)
    app.include_router(orders.router, prefix="/api/v1")

    logger.info("app.ready", host=app_cfg.api_host, port=app_cfg.api_port)
    return app
