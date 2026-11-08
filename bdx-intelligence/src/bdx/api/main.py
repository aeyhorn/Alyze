"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from bdx.api.routes import analytics, health, machines, orders, service_layer
from bdx.config import (
    load_app_settings,
    load_bde_settings,
    load_machine_settings,
    load_postgres_settings,
    load_sap_mode_settings,
    load_service_layer_settings,
)
from bdx.db.postgres import create_pg_engine, make_session_factory
from bdx.logging_config import configure_logging

logger = structlog.get_logger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    pg_dsn: str | None = None,
    sap_engine=None,
    pg_session_factory=None,
    sl_client=None,
    machine_adapter=None,
    bde_adapter=None,
    publisher=None,
    api_key: str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        pg_dsn:              Override PostgreSQL DSN.
        sap_engine:          Pre-built SAP (MSSQL) engine; health check skipped when None.
        pg_session_factory:  Inject a pre-built session factory (e.g. for tests).
        sl_client:           Inject a pre-built ServiceLayerClient (e.g. for tests).
        machine_adapter:     Inject a MachineAdapter (default: built from MACHINE_* env).
        bde_adapter:         Inject a BDEAdapter (default: built from BDE_* env).
        publisher:           Inject an EventPublisher (default: built from MQTT_* env).
        api_key:             Override API_KEY (empty string disables auth).
    """
    app_cfg = load_app_settings()
    configure_logging(app_cfg.log_level, app_cfg.log_format)

    app = FastAPI(
        title="BDX Intelligence",
        description="SAP Business One read-only collector, machine monitor and event API.",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "PUT"],
        allow_headers=["*"],
    )

    app.state.api_key = api_key if api_key is not None else app_cfg.api_key

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

    # ── Machine / BDE adapters, publisher ─────────────────────────────────────
    _init_adapters(app, machine_adapter, bde_adapter, publisher)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(machines.router, prefix="/api/v1")
    app.include_router(service_layer.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def _root():
        return RedirectResponse(url="/dashboard")

    @app.get("/dashboard", include_in_schema=False)
    def _dashboard():
        return FileResponse(_STATIC_DIR / "dashboard.html", media_type="text/html")

    @app.get("/analytics", include_in_schema=False)
    def _analytics():
        return FileResponse(_STATIC_DIR / "analytics.html", media_type="text/html")

    logger.info(
        "app.ready",
        host=app_cfg.api_host,
        port=app_cfg.api_port,
        api_key_enabled=bool(app.state.api_key),
    )
    return app


def _init_adapters(app: FastAPI, machine_adapter, bde_adapter, publisher) -> None:
    from bdx.adapters.bde import NullBDEAdapter, build_bde_adapter, build_machine_adapter
    from bdx.adapters.machine import NullMachineAdapter

    try:
        machine_cfg = load_machine_settings()
        app.state.machine_adapter = machine_adapter or (
            build_machine_adapter(machine_cfg) if machine_cfg.configured else None
        )
        if isinstance(app.state.machine_adapter, NullMachineAdapter):
            app.state.machine_adapter = None
    except Exception as exc:
        logger.warning("machine_adapter.init_failed", error=str(exc))
        app.state.machine_adapter = None

    try:
        bde_cfg = load_bde_settings()
        app.state.bde_adapter = bde_adapter or (
            build_bde_adapter(bde_cfg) if bde_cfg.configured else None
        )
        if isinstance(app.state.bde_adapter, NullBDEAdapter):
            app.state.bde_adapter = None
    except Exception as exc:
        logger.warning("bde_adapter.init_failed", error=str(exc))
        app.state.bde_adapter = None

    try:
        from bdx.publish.mqtt import build_all_publishers

        app.state.publisher = publisher or build_all_publishers()
    except Exception as exc:
        logger.warning("publisher.init_failed", error=str(exc))
        app.state.publisher = None


def _init_service_layer(app: FastAPI) -> None:
    """Initialise ServiceLayerClient and SapModeRegistry from environment."""
    try:
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
