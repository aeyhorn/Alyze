"""FastAPI application factory."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bdx.api.routes import health, orders, service_layer
from bdx.config import load_app_settings, load_postgres_settings, load_sap_mode_settings, load_service_layer_settings
from bdx.db.postgres import create_pg_engine, make_session_factory
from bdx.logging_config import configure_logging

logger = structlog.get_logger(__name__)


def create_app(
    pg_dsn: str | None = None,
    sap_engine=None,  # noqa: ANN001
    pg_session_factory=None,  # noqa: ANN001
    sl_client=None,  # noqa: ANN001  – inject for tests
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        pg_dsn:              Override PostgreSQL DSN.
        sap_engine:          Pre-built SAP (MSSQL) engine; health check skipped when None.
        pg_session_factory:  Inject a pre-built session factory (e.g. for tests).
        sl_client:           Inject a pre-built ServiceLayerClient (e.g. for tests).
    """
    app_cfg = load_app_settings()
    configure_logging(app_cfg.log_level, app_cfg.log_format)

    app = FastAPI(
        title="BDX Intelligence",
        description="SAP Business One read-only collector and event API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "PUT"],
        allow_headers=["*"],
    )

    # ── PostgreSQL session factory ────────────────────────────────────────────
    if pg_session_factory is not None:
        app.state.pg_session_factory = pg_session_factory
    else:
        pg_dsn = pg_dsn or load_postgres_settings().postgres_dsn
        pg_engine = create_pg_engine(pg_dsn)
        app.state.pg_session_factory = make_session_factory(pg_engine)

    # ── MSSQL (SAP read) ──────────────────────────────────────────────────────
    app.state.sap_ok = False
    if sap_engine is not None:
        from bdx.db.sap import probe_sap_connection
        app.state.sap_ok = probe_sap_connection(sap_engine)

    # ── Service Layer write client ────────────────────────────────────────────
    if sl_client is not None:
        app.state.sl_client = sl_client
        app.state.sap_mode_registry = None
    else:
        _init_service_layer(app)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(service_layer.router, prefix="/api/v1")

    logger.info("app.ready", host=app_cfg.api_host, port=app_cfg.api_port)
    return app


def _init_service_layer(app: FastAPI) -> None:
    """Initialise ServiceLayerClient and SapModeRegistry from environment."""
    try:
        from bdx.config import SapMode
        from bdx.sap_sl.client import ServiceLayerClient
        from bdx.sap_sl.mode import SapModeRegistry

        sl_cfg = load_service_layer_settings()
        mode_cfg = load_sap_mode_settings()

        client = ServiceLayerClient(sl_cfg, mode=mode_cfg.sap_mode)
        registry = SapModeRegistry(sl_cfg, default_mode=mode_cfg.sap_mode)

        app.state.sl_client = client
        app.state.sap_mode_registry = registry
        logger.info(
            "service_layer.init",
            configured=sl_cfg.configured,
            dry_run=sl_cfg.dry_run,
            mode=mode_cfg.sap_mode.value,
        )
    except Exception as exc:
        logger.warning("service_layer.init_failed", error=str(exc))
        app.state.sl_client = None
        app.state.sap_mode_registry = None
