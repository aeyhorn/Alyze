"""Central configuration – all values loaded exclusively from environment variables.

No production credentials must ever appear in this file or anywhere in the repository.
"""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SAPSettings(BaseSettings):
    """SQL Server connection settings for SAP Business One (read-only)."""

    model_config = SettingsConfigDict(env_prefix="SAP_DB_", case_sensitive=False)

    host: str = Field(..., description="SQL Server hostname or IP")
    port: int = Field(1433, ge=1, le=65535)
    name: str = Field(..., description="SAP company database name")
    user: str = Field(..., description="Read-only SQL login")
    password: str = Field(..., description="SQL login password – from env only")
    tls: str = Field("yes", pattern=r"^(yes|no)$")
    tls_ca_cert: str = Field("", description="Path to CA cert bundle (optional)")
    connect_timeout: int = Field(10, ge=1, le=300)
    query_timeout: int = Field(30, ge=1, le=600)

    @field_validator("password", mode="before")
    @classmethod
    def _password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("SAP_DB_PASSWORD must not be empty")
        return v

    def odbc_connection_string(self) -> str:
        """Build an ODBC connection string.  TLS is enforced when tls='yes'."""
        encrypt = "yes" if self.tls == "yes" else "no"
        trust_cert = "no" if self.tls_ca_cert else "yes"
        ca_part = f";TrustServerCertificate=no;ServerCertificate={self.tls_ca_cert}" if self.tls_ca_cert else ""
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.name};"
            f"UID={self.user};"
            f"PWD={self.password};"
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
