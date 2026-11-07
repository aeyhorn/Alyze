"""Central configuration – all values loaded exclusively from environment variables.

No production credentials must ever appear in this file or anywhere in the repository.
"""
from __future__ import annotations

import enum

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
    def _credentials_present(self) -> "SAPSettings":
        if self.trusted_connection != "yes":
            if not self.user:
                raise ValueError("SAP_DB_USER must be set (or SAP_DB_TRUSTED_CONNECTION=yes)")
            if not self.password:
                raise ValueError("SAP_DB_PASSWORD must not be empty (or SAP_DB_TRUSTED_CONNECTION=yes)")
        return self

    def odbc_connection_string(self) -> str:
        """Build an ODBC connection string.  TLS is enforced when tls='yes'."""
        encrypt = "yes" if self.tls == "yes" else "no"
        trust_cert = "no" if self.tls_ca_cert else "yes"
        ca_part = f";TrustServerCertificate=no;ServerCertificate={self.tls_ca_cert}" if self.tls_ca_cert else ""
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

    postgres_dsn: str = Field(
        "postgresql+psycopg2://bdx:bdx_local@localhost:5432/bdx_intelligence"
    )


class CollectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    poll_interval_seconds: int = Field(60, ge=5)
    retry_max_attempts: int = Field(5, ge=1)
    retry_wait_min_seconds: float = Field(2.0, ge=0)
    retry_wait_max_seconds: float = Field(60.0, ge=1)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    log_level: str = Field("INFO")
    log_format: str = Field("console", pattern=r"^(json|console)$")
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8080, ge=1, le=65535)


def load_sap_settings() -> SAPSettings:
    return SAPSettings()  # type: ignore[call-arg]


def load_postgres_settings() -> PostgresSettings:
    return PostgresSettings()


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

    def company_db_for_mode(self, mode: "SapMode") -> str:
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
