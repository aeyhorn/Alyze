# BDX Intelligence – Architecture

## Overview

BDX Intelligence is a **read-only data collector and event engine** that bridges SAP Business One (SQL Server) with a local PostgreSQL event store.  It exposes a FastAPI REST API and a CLI for reporting and diagnostics.

```
┌─────────────────────────────────────────────────────────────────┐
│                     BDX Intelligence                            │
│                                                                 │
│  ┌────────────┐    SQL (read-only)    ┌─────────────────────┐  │
│  │  Collector │◄──────────────────────│  SAP Business One   │  │
│  │  Polling   │   pyodbc / SQLAlchemy │  SQL Server (OWOR,  │  │
│  │  Loop 60s  │                       │  OITM tables)       │  │
│  └─────┬──────┘                       └─────────────────────┘  │
│        │                                                        │
│        │ persist snapshots + domain events                      │
│        ▼                                                        │
│  ┌─────────────┐                                               │
│  │  PostgreSQL │                                               │
│  │  Event Store│  order_snapshots, domain_events tables        │
│  └──────┬──────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  FastAPI    │  GET /health, /api/v1/orders, /api/v1/events  │
│  │  REST API   │                                               │
│  └─────────────┘                                               │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐                            │
│  │ BDE Adapter │  │Machine Adapt.│  (stubs – Sprint 002+)     │
│  │   (stub)    │  │   (stub)     │                            │
│  └─────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Collector (`src/bdx/collector/`)

| Module | Responsibility |
|---|---|
| `polling.py` | Main loop: poll SAP every 60 s, retry with exponential backoff |
| `snapshots.py` | Persist and retrieve full order snapshots in PostgreSQL |
| `change_detector.py` | Idempotent diff of previous vs. current snapshot → domain events |

**Flow per cycle:**
1. `fetch_all_orders_snapshot()` → reads all OWOR rows from SAP (read-only)
2. `load_latest_snapshot()` → retrieves the previous snapshot from PostgreSQL
3. `detect_changes()` → compares and produces domain events
4. `save_snapshot()` → persists the new snapshot batch
5. `persist_events()` → upserts domain events (idempotent via `event_id`)

### 2. Configuration (`src/bdx/config.py`)

All configuration is loaded **exclusively from environment variables** via `pydantic-settings`.  No secrets appear in source code or configuration files committed to the repository.

| Prefix | Purpose |
|---|---|
| `SAP_DB_*` | SQL Server connection (host, port, user, password, TLS) |
| `POSTGRES_DSN` | PostgreSQL DSN for the event store |
| `POLL_INTERVAL_SECONDS` | How often to poll SAP (default 60) |
| `RETRY_MAX_ATTEMPTS` | Tenacity retry limit (default 5) |
| `LOG_LEVEL`, `LOG_FORMAT` | Structlog settings |

### 3. Database Layer (`src/bdx/db/`)

- **`sap.py`**: Creates a SQLAlchemy engine for SQL Server via pyodbc.  A SQLAlchemy event listener blocks any INSERT/UPDATE/DELETE/DDL statement at the Python layer (belt-and-suspenders).  The database user must also have read-only SQL Server permissions.
- **`queries.py`**: Fixed, parameterized `text()` queries for OWOR and OITM.  No string interpolation; all parameters use `:name` placeholders.
- **`postgres.py`**: PostgreSQL engine and session factory for the event store.

### 4. API (`src/bdx/api/`)

FastAPI application with:
- `GET /health` – liveness + readiness (checks both datastores)
- `GET /health/live` – Kubernetes-compatible liveness probe
- `GET /api/v1/orders` – latest snapshot of production orders (filterable)
- `GET /api/v1/events` – domain events (filterable, paginated)

### 5. CLI (`src/bdx/cli/report.py`)

```
bdx-collect report    # table of open orders from latest snapshot
bdx-collect events    # recent domain events
bdx-collect diagnose  # one-shot connectivity and query diagnostic
bdx-collect collect   # start the polling loop
```

### 6. Adapters (`src/bdx/adapters/`)

Sprint 001 ships only abstract base classes and null implementations:
- `BDEAdapter` / `NullBDEAdapter` – shop-floor data collection
- `MachineAdapter` / `NullMachineAdapter` – CNC / machine network (read-only)

## Security Constraints

- No write operations to SAP (enforced at both DB-user and application level)
- No machine control commands (adapters are read-only by interface contract)
- All secrets from environment variables only; `.env` is in `.gitignore`
- TLS enforced for SAP SQL Server connections (`SAP_DB_TLS=yes`)

## Data Flow – Domain Events

```
Snapshot N-1   Snapshot N      Events produced
─────────────────────────────────────────────────────
(absent)       R, qty=100   → ORDER_CREATED
L, qty=100     R, qty=100   → ORDER_RELEASED
R, qty=100     R, qty=150   → QUANTITY_CHANGED
R, due=Dec 1   R, due=Dec15 → DUE_DATE_CHANGED
R, qty=100     C, qty=100   → ORDER_CLOSED
```

Events are keyed by a UUID `event_id` generated at detection time.  `persist_events()` checks for existing IDs before inserting, making the operation idempotent.
