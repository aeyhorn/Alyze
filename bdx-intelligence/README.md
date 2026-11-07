# BDX Intelligence

**Read-only SAP Business One production order collector and event engine.**

BDX Intelligence connects to your SAP Business One SQL Server database (read-only), detects changes in production orders, generates domain events, and exposes them via a REST API and CLI reports.

> **Sprint 001**: SAP read-only collector with polling, change detection, PostgreSQL event store, FastAPI API, and CLI reporting.

---

## Quick Start

### Prerequisites

- Python 3.11+
- ODBC Driver 18 for SQL Server ([install guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server))
- PostgreSQL 14+ (for the event store)
- A SAP B1 SQL Server read-only database user (see [docs/SAP_MAPPING.md](docs/SAP_MAPPING.md))

### 1. Install

```bash
# Clone and set up a virtual environment
git clone <your-gitea-repo>/bdx-intelligence.git
cd bdx-intelligence
python -m venv .venv
source .venv/bin/activate

# Install the package
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your SAP and PostgreSQL credentials
# NEVER commit .env to version control
```

Minimum required environment variables:

```env
SAP_DB_HOST=your-sap-server
SAP_DB_NAME=SBO_YourCompany
SAP_DB_USER=bdx_readonly
SAP_DB_PASSWORD=your_password
POSTGRES_DSN=postgresql+psycopg2://bdx:pw@localhost:5432/bdx_intelligence
```

### 3. Run Database Migrations

```bash
export POSTGRES_DSN="postgresql+psycopg2://bdx:pw@localhost:5432/bdx_intelligence"
alembic upgrade head
```

### 4. Diagnose Connectivity

```bash
bdx-collect diagnose
```

This one-shot command checks both SAP and PostgreSQL connectivity and runs sample queries. Use `--skip-sap` if you only want to verify PostgreSQL.

### 5. Run the Collector

```bash
# Single cycle (useful for testing)
bdx-collect collect --once

# Continuous polling (60-second intervals, Ctrl+C to stop)
bdx-collect collect
```

### 6. View Reports

```bash
# Open production orders from latest snapshot
bdx-collect report

# Filter by status
bdx-collect report --status R

# Domain events
bdx-collect events

# Filter by event type
bdx-collect events --type ORDER_CREATED
```

### 7. Start the API Server

```bash
uvicorn bdx.api.main:create_app --factory --host 0.0.0.0 --port 8080
```

API endpoints:
- `GET /health` – readiness probe
- `GET /health/live` – liveness probe
- `GET /api/v1/orders` – latest order snapshot
- `GET /api/v1/events` – domain events

Interactive docs at `http://localhost:8080/docs`.

---

## Running Tests

No SAP or PostgreSQL instance required – tests use SQLite and mock data:

```bash
pytest
# With coverage
pytest --cov=bdx --cov-report=term-missing
```

---

## Project Structure

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py          # All settings from environment variables
│   ├── logging_config.py  # Structured logging (structlog)
│   ├── db/
│   │   ├── sap.py         # SAP SQL Server engine (read-only guard)
│   │   ├── postgres.py    # PostgreSQL engine + session factory
│   │   └── queries.py     # Parameterized OWOR / OITM queries
│   ├── models/
│   │   ├── sap.py         # WorkOrder, ItemMaster Pydantic models
│   │   └── events.py      # DomainEvent ORM + EventType enum
│   ├── collector/
│   │   ├── snapshots.py   # Snapshot persistence
│   │   ├── change_detector.py  # Idempotent event generation
│   │   └── polling.py     # 60-second polling loop with retry/backoff
│   ├── api/
│   │   ├── main.py        # FastAPI application factory
│   │   ├── deps.py        # Dependency injection helpers
│   │   └── routes/        # health, orders endpoints
│   ├── adapters/
│   │   ├── bde.py         # BDE adapter interface stub
│   │   └── machine.py     # Machine adapter interface stub (read-only)
│   └── cli/
│       └── report.py      # Typer CLI commands
├── alembic/               # Database schema migrations
├── tests/                 # pytest tests (SQLite, no real SAP)
└── docs/
    ├── ARCHITECTURE.md
    ├── SAP_MAPPING.md
    └── PROJECT_STATUS.md
```

---

## Domain Events

The collector generates these events by comparing consecutive snapshots:

| Event | Trigger |
|---|---|
| `ORDER_CREATED` | Order appears for the first time |
| `ORDER_RELEASED` | Status changes `L` → `R` |
| `QUANTITY_CHANGED` | `PlannedQty` changes |
| `DUE_DATE_CHANGED` | `DueDate` changes |
| `ORDER_CLOSED` | Status changes to `C` or `X` |

---

## Security

- **No write access to SAP**: the application-level read-only guard blocks all DML/DDL.  The database user must have `SELECT` only.
- **No machine control**: machine and BDE adapters are read-only by interface contract.
- **Secrets from environment only**: `.env` is in `.gitignore`.  Never commit credentials.
- **TLS for SAP**: enabled by default (`SAP_DB_TLS=yes`).

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [SAP Field Mapping](docs/SAP_MAPPING.md)
- [Project Status](docs/PROJECT_STATUS.md)

---

## Gitea Repository Setup

This project is designed for a local Gitea instance:

```bash
# After creating the repository in Gitea
git remote add origin http://your-gitea/your-org/bdx-intelligence.git
# Push only after explicit approval
```

**Do not push without explicit approval** – this repository may contain environment-specific configuration references.
