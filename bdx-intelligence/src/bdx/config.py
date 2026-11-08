"""Central configuration – all values loaded exclusively from environment variables.

No production credentials must ever appear in this file or anywhere in the repository.
"""

from __future__ import annotations

import enum
import os

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load ./.env (searched upwards from this file) into the process environment.
# Variables that are already set in the real environment take precedence.
load_dotenv()


class SAPSettings(BaseSettings):
    """SQL Server connection settings for SAP Business One (read-only)."""

    model_config = SettingsConfigDict(env_prefix="SAP_DB_", case_sensitive=False)

    host: str = Field(..., description="SQL Server hostname or IP")
    port: int = Field(1433, ge=1, le=65535)
    name: str = Field(..., description="SAP company database name")
    user: str = Field("", description="Read-only SQL login (not needed with trusted_connection)")
    password: str = Field("", description="SQL login password – from env only")
    trusted_connection: str = Field(
        "no",
        pattern=r"^(yes|no)$",
        description="Use Windows integrated authentication (current user) instead of UID/PWD",
    )
    tls: str = Field("yes", pattern=r"^(yes|no)$")
    tls_ca_cert: str = Field("", description="Path to CA cert bundle (optional)")
    connect_timeout: int = Field(10, ge=1, le=300)
    query_timeout: int = Field(30, ge=1, le=600)
    odbc_driver: str = Field(
        "ODBC Driver 18 for SQL Server",
        description="Installed ODBC driver name, e.g. 'ODBC Driver 17 for SQL Server'",
    )

    @model_validator(mode="after")
    def _credentials_present(self) -> SAPSettings:
        if self.trusted_connection != "yes":
            if not self.user:
                raise ValueError("SAP_DB_USER must be set (or SAP_DB_TRUSTED_CONNECTION=yes)")
            if not self.password:
                raise ValueError(
                    "SAP_DB_PASSWORD must not be empty (or SAP_DB_TRUSTED_CONNECTION=yes)"
                )
        return self

    def odbc_connection_string(self) -> str:
        """Build an ODBC connection string.  TLS is enforced when tls='yes'."""
        encrypt = "yes" if self.tls == "yes" else "no"
        trust_cert = "no" if self.tls_ca_cert else "yes"
        ca_part = (
            f";TrustServerCertificate=no;ServerCertificate={self.tls_ca_cert}"
            if self.tls_ca_cert
            else ""
        )
        if self.trusted_connection == "yes":
            auth_part = "Trusted_Connection=yes;"
        else:
            auth_part = f"UID={self.user};PWD={self.password};"
        return (
            f"DRIVER={{{self.odbc_driver}}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.name};"
            f"{auth_part}"
            f"Encrypt={encrypt};"
            f"TrustServerCertificate={trust_cert};"
            f"ConnectTimeout={self.connect_timeout};"
            f"CommandTimeout={self.query_timeout}"
            f"{ca_part}"
        )

    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy connection URL using pyodbc."""
        from urllib.parse import quote_plus

        cs = quote_plus(self.odbc_connection_string())
        return f"mssql+pyodbc:///?odbc_connect={cs}"


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    postgres_dsn: str = Field("postgresql+psycopg2://bdx:bdx_local@localhost:5432/bdx_intelligence")
    # Separate event store for PROD mode (empty = reuse postgres_dsn for both modes)
    postgres_dsn_prod: str = Field("")


def _active_sap_mode() -> str:
    """Return the SAP mode from the environment (cheap, pre-DB).

    The authoritative mode lives in ``app_setting.sapMode`` (resolved by the
    registry at runtime); this is only used at startup before the DB is
    available to pick the right PG DSN.
    """
    return (os.environ.get("SAP_MODE") or "dev").lower()


def load_postgres_settings() -> PostgresSettings:
    """Return PG settings, selecting the PROD DSN when SAP_MODE=prod and one is set."""
    settings = PostgresSettings()
    if _active_sap_mode() == "prod" and settings.postgres_dsn_prod:
        settings.postgres_dsn = settings.postgres_dsn_prod
    return settings


class CollectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    poll_interval_seconds: int = Field(60, ge=5)
    retry_max_attempts: int = Field(5, ge=1)
    retry_wait_min_seconds: float = Field(2.0, ge=0)
    retry_wait_max_seconds: float = Field(60.0, ge=1)
    # Incremental reads: look back this many days behind the newest known
    # SAP UpdateDate (UpdateDate has day granularity) – safety margin.
    incremental_lookback_days: int = Field(2, ge=1, le=60)
    # Force a full OWOR read every N cycles (0 = never, only on empty state)
    full_reload_every_cycles: int = Field(0, ge=0)


class MachineSettings(BaseSettings):
    """MDE / machine feed (Mazak XMSK ``machstates`` XML, read-only)."""

    model_config = SettingsConfigDict(env_prefix="MACHINE_", case_sensitive=False)

    enabled: bool = Field(False)
    xmsk_url: str = Field(
        "",
        description="e.g. http://192.168.82.33:3888/api/machstates (SCADA nginx proxy to XmskSvr)",
    )
    poll_interval_seconds: int = Field(15, ge=2)
    timeout_seconds: float = Field(10.0, ge=1)
    # Machine is reported offline when no XMSK data arrived for this long
    offline_after_seconds: int = Field(120, ge=10)

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.xmsk_url)


class BdeSettings(BaseSettings):
    """BDE source: telemetry history of the SCADA system (REST, read-only)."""

    model_config = SettingsConfigDict(env_prefix="BDE_", case_sensitive=False)

    enabled: bool = Field(False)
    scada_base_url: str = Field("", description="e.g. http://192.168.82.33:3888")
    timeout_seconds: float = Field(30.0, ge=1)
    # Two telemetry points further apart than this start a new BDE record
    gap_seconds: int = Field(900, ge=60)

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.scada_base_url)


class MqttSettings(BaseSettings):
    """Optional MQTT event publishing."""

    model_config = SettingsConfigDict(env_prefix="MQTT_", case_sensitive=False)

    enabled: bool = Field(False)
    host: str = Field("")
    port: int = Field(1883, ge=1, le=65535)
    username: str = Field("")
    password: str = Field("")
    tls: bool = Field(False)
    client_id: str = Field("bdx-intelligence")
    topic_prefix: str = Field("bdx/intelligence")
    qos: int = Field(1, ge=0, le=2)


class KafkaSettings(BaseSettings):
    """Optional Kafka event publishing (alternative to MQTT)."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_", case_sensitive=False)

    enabled: bool = Field(False)
    bootstrap_servers: str = Field("")
    topic: str = Field("bdx-intelligence-events")
    username: str = Field("")
    password: str = Field("")
    security_protocol: str = Field(
        "PLAINTEXT", pattern=r"^(PLAINTEXT|SASL_PLAINTEXT|SASL_SSL|SSL)$"
    )
    sasl_mechanism: str = Field("PLAIN", pattern=r"^(PLAIN|SCRAM-SHA-256|SCRAM-SHA-512)$")
    client_id: str = Field("bdx-intelligence")
    # Round-up acks: 0 = fire-and-forget, 1 = leader, -1 = all ISR (default)
    acks: str = Field("1")
    # How long to block waiting for the broker (seconds)
    request_timeout: float = Field(10.0, ge=1.0, le=120.0)

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.bootstrap_servers)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    log_level: str = Field("INFO")
    log_format: str = Field("console", pattern=r"^(json|console)$")
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8080, ge=1, le=65535)
    # When set, every /api/* request must carry header "X-API-Key: <value>"
    api_key: str = Field("", description="Empty = API is unauthenticated (LAN only!)")


def load_machine_settings() -> MachineSettings:
    return MachineSettings()


def load_bde_settings() -> BdeSettings:
    return BdeSettings()


def load_mqtt_settings() -> MqttSettings:
    return MqttSettings()


def load_kafka_settings() -> KafkaSettings:
    return KafkaSettings()


def load_sap_settings() -> SAPSettings:
    return SAPSettings()  # type: ignore[call-arg]


def load_collector_settings() -> CollectorSettings:
    return CollectorSettings()


def load_app_settings() -> AppSettings:
    return AppSettings()


class SapMode(str, enum.Enum):
    DEV = "dev"
    PROD = "prod"


class ServiceLayerSettings(BaseSettings):
    """SAP Business One Service Layer – write channel (OData v4 / REST).

    Read channel is MSSQL (SAPSettings above).
    Session management, CSRF and DRY_RUN are handled in sap_sl/client.py.
    """

    model_config = SettingsConfigDict(env_prefix="SL_", case_sensitive=False)

    base_url: str = Field(
        "",
        description="e.g. https://ldsap.leisinger.local:50000/b1s/v2 (no trailing slash)",
    )
    company_db_dev: str = Field("", description="Company DB for dev mode")
    company_db_prod: str = Field("", description="Company DB for prod mode")
    company_db: str = Field("", description="Fallback company DB")
    username: str = Field("", description="SAP login user")
    password: str = Field("", description="SAP login password – from env only")
    allow_invalid_cert: bool = Field(
        False, description="Disable TLS verification (self-signed certs only)"
    )
    timeout_ms: int = Field(20_000, ge=1_000, description="Per-request timeout in ms")
    dry_run: bool = Field(
        False,
        description="Block all writes to SAP (GET and Login still work)",
    )

    # SAP_MODE lives in the top-level namespace (no SL_ prefix)
    model_config = SettingsConfigDict(env_prefix="SL_", case_sensitive=False)

    @property
    def timeout_seconds(self) -> float:
        return self.timeout_ms / 1000.0

    def company_db_for_mode(self, mode: SapMode) -> str:
        """Return the correct company DB for the given mode."""
        if mode == SapMode.DEV:
            return self.company_db_dev or self.company_db
        return self.company_db_prod or self.company_db

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.username)

    @property
    def write_enabled(self) -> bool:
        return self.configured and not self.dry_run


class SapModeSettings(BaseSettings):
    """Top-level SAP mode from environment (overridden by DB-persisted value)."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    sap_mode: SapMode = Field(SapMode.DEV, description="'dev' or 'prod'")


def load_service_layer_settings() -> ServiceLayerSettings:
    return ServiceLayerSettings()  # type: ignore[call-arg]


def load_sap_mode_settings() -> SapModeSettings:
    return SapModeSettings()
