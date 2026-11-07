"""SAP mode registry – dev | prod – persisted in dbo.AppSetting (PostgreSQL).

The persisted value overrides the SAP_MODE environment variable.
Switching mode invalidates the Service Layer session and forces a SQL pool rebuild.
"""
from __future__ import annotations

import threading
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from bdx.config import SapMode, ServiceLayerSettings

logger = structlog.get_logger(__name__)

_SETTING_KEY = "sapMode"
_lock = threading.Lock()


# ── ORM-less helpers using raw SQL ────────────────────────────────────────────

def _ensure_table(session: Session) -> None:
    """Create AppSetting table if it doesn't exist (idempotent)."""
    session.execute(text(
        """
        CREATE TABLE IF NOT EXISTS app_setting (
            key   VARCHAR(64) PRIMARY KEY,
            value VARCHAR(256) NOT NULL
        )
        """
    ))
    session.commit()


def get_persisted_mode(session: Session) -> Optional[SapMode]:
    """Return the persisted SAP mode, or None if not set."""
    _ensure_table(session)
    row = session.execute(
        text("SELECT value FROM app_setting WHERE key = :k"),
        {"k": _SETTING_KEY},
    ).fetchone()
    if row is None:
        return None
    try:
        return SapMode(row[0])
    except ValueError:
        logger.warning("sap_mode.invalid_persisted_value", value=row[0])
        return None


def persist_mode(session: Session, mode: SapMode) -> None:
    """Upsert the SAP mode into app_setting."""
    _ensure_table(session)
    session.execute(
        text(
            """
            INSERT INTO app_setting (key, value) VALUES (:k, :v)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """
        ),
        {"k": _SETTING_KEY, "v": mode.value},
    )
    session.commit()
    logger.info("sap_mode.persisted", mode=mode.value)


class SapModeRegistry:
    """Thread-safe registry that holds the active SAP mode and company DB.

    Resolution order:
      1. Persisted in PostgreSQL (app_setting.sapMode)
      2. SAP_MODE environment variable (SapModeSettings)
      3. Default: dev
    """

    def __init__(
        self,
        sl_settings: ServiceLayerSettings,
        default_mode: SapMode = SapMode.DEV,
    ) -> None:
        self._sl = sl_settings
        self._active_mode: Optional[SapMode] = None
        self._default_mode = default_mode

    def resolve(self, session: Session) -> SapMode:
        """Return the active mode, consulting the DB if not yet resolved."""
        with _lock:
            if self._active_mode is not None:
                return self._active_mode
            persisted = get_persisted_mode(session)
            self._active_mode = persisted or self._default_mode
            logger.info(
                "sap_mode.resolved",
                mode=self._active_mode.value,
                source="db" if persisted else "default",
            )
            return self._active_mode

    def switch(self, session: Session, mode: SapMode) -> None:
        """Persist and activate a new mode."""
        with _lock:
            persist_mode(session, mode)
            self._active_mode = mode

    @property
    def active_mode(self) -> Optional[SapMode]:
        return self._active_mode

    def company_db(self, mode: Optional[SapMode] = None) -> str:
        m = mode or self._active_mode or self._default_mode
        return self._sl.company_db_for_mode(m)

    def sql_database(self, mode: Optional[SapMode] = None) -> str:
        """Return the MSSQL database name for the given mode."""
        return self.company_db(mode)
