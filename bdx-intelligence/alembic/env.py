"""Alembic environment – DSN loaded from POSTGRES_DSN environment variable."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Ensure the src package is on sys.path when running via alembic CLI
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load <project>/.env so POSTGRES_DSN does not have to be exported manually
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from bdx.db.postgres import Base  # noqa: E402  – after sys.path adjustment
import bdx.models.events  # noqa: F401,E402  – register ORM models with metadata
from bdx.config import load_postgres_settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override the placeholder URL with the real DSN from the environment.
# When SAP_MODE=prod and POSTGRES_DSN_PROD is set, use the PROD event store.
_dsn = load_postgres_settings().postgres_dsn
if not _dsn:
    raise EnvironmentError("POSTGRES_DSN environment variable is required for Alembic migrations.")

config.set_main_option("sqlalchemy.url", _dsn)


def run_migrations_offline() -> None:
    context.configure(
        url=_dsn,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
