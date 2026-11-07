# BDX Intelligence – Architecture

## Overview

BDX Intelligence bridges SAP Business One with a local PostgreSQL event store via two separate channels:

| Channel | Protocol | Direction | Used for |
|---|---|---|---|
| **Read** | MSSQL / pyodbc | SAP → BDX | Snapshots, change detection (OWOR, OITM) |
| **Write** | Service Layer OData v4 | BDX → SAP | Future write-back (releases, confirmations) |

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           BDX Intelligence                                   │
│                                                                              │
│         READ CHANNEL (MSSQL, read-only)                                      │
│  ┌────────────┐  SQL SELECT only   ┌──────────────────────────────────────┐  │
│  │  Collector │◄───────────────────│  SAP Business One SQL Server         │  │
│  │  60s poll  │  pyodbc/SQLAlchemy │  DEV_SBO_LEISINGER / SBO_LEISINGER   │  │
│  └─────┬──────┘                    │  Tables: OWOR, OITM                  │  │
│        │                           └──────────────────────────────────────┘  │
│        │ snapshots + events                                                   │
│        ▼                                                                      │
│  ┌─────────────┐           WRITE CHANNEL (Service Layer, OData v4)           │
│  │  PostgreSQL │    ┌────────────────┐    ┌──────────────────────────────┐   │
│  │  Event Store│    │  SL Client     │───►│  SAP Service Layer           │   │
│  │  app_setting│    │  (httpx)       │    │  https://…:50000/b1s/v2      │   │
│  │  order_snap.│    │  Session+CSRF  │    │  dev: DEV_SBO_LEISINGER      │   │
│  │  domain_ev. │    │  DRY_RUN guard │    │  prod: SBO_LEISINGER         │   │
│  └──────┬──────┘    └────────────────┘    └──────────────────────────────┘   │
│         │                                                                     │
│         ▼                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI REST API                                                     │    │
│  │  GET  /health                     GET  /api/v1/orders                │    │
│  │  GET  /api/v1/events              GET  /api/v1/service-layer         │    │
│  │  PUT  /api/v1/service-layer/mode                                     │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────┐  ┌──────────────┐                                          │
│  │ BDE Adapter │  │Machine Adapt.│  (stubs – Sprint 002+)                   │
│  │   (stub)    │  │   (stub)     │                                          │
│  └─────────────┘  └──────────────┘                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 0. SAP Mode Registry (`src/bdx/sap_sl/mode.py`)

Tracks the active SAP mode (`dev` | `prod`).  Resolution order:

1. Persisted in `app_setting.sapMode` (PostgreSQL)
2. `SAP_MODE` environment variable
3. Default: `dev`

Both the Service Layer client and the MSSQL read pool use the same active mode.  Mode switch via `PUT /api/v1/service-layer/mode` → clears SL session, sets new company DB.

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

On import, `config.py` (and `alembic/env.py`) call `python-dotenv`'s `load_dotenv()`, so a `.env` file in the project root is picked up automatically.  Variables already present in the real environment take precedence over `.env`.

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

### 3b. Service Layer Client (`src/bdx/sap_sl/client.py`)

Thread-safe HTTP client for the SAP B1 Service Layer (write channel):

| Feature | Detail |
|---|---|
| Login | `POST /Login` with CompanyDB + credentials → `B1SESSION`, `ROUTEID` cookies |
| Session TTL | 20 min (SAP internal); renewed 30 s before expiry |
| CSRF | `GET CompanyService_GetCompanyInfo` with `X-CSRF-Token: Fetch` after login |
| 401 handling | Discard session, re-login, retry request once |
| DRY_RUN | `SL_DRY_RUN=true` raises `DryRunError` on any write; GET/Login unaffected |
| TLS | `SL_ALLOW_INVALID_CERT=true` for self-signed internal certs |
| OData errors | `error.message.value` extracted and surfaced as `ServiceLayerError` |

### 4. API (`src/bdx/api/`)

FastAPI application with:
- `GET /health` – liveness + readiness (checks both datastores)
- `GET /health/live` – Kubernetes-compatible liveness probe
- `GET /api/v1/orders` – latest snapshot of production orders (filterable)
- `GET /api/v1/events` – domain events (filterable, paginated)
- `GET /api/v1/service-layer` – SL connection status (mode, companyDb, configured, dryRun)
- `PUT /api/v1/service-layer/mode` – switch dev/prod (body: `{"mode":"dev"}|{"mode":"prod"}`)

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

- **MSSQL read channel**: DB user has `SELECT` only; application write-guard blocks DML/DDL
- **Service Layer write channel**: guarded by `SL_DRY_RUN`; no writes without explicit enable
- No machine control commands (adapters are read-only by interface contract)
- All secrets from environment variables only; `.env` is in `.gitignore`
- TLS enforced for MSSQL (`SAP_DB_TLS=yes`); SL TLS skip only with `SL_ALLOW_INVALID_CERT=true`

## Configuration Reference

| Variable | Default | Purpose |
|---|---|---|
| `SL_BASE_URL` | – | Service Layer base URL |
| `SL_COMPANY_DB_DEV` | – | Company DB in dev mode |
| `SL_COMPANY_DB_PROD` | – | Company DB in prod mode |
| `SL_USERNAME` / `SL_PASSWORD` | – | SAP credentials |
| `SL_ALLOW_INVALID_CERT` | false | Self-signed TLS (internal only; required for LDSAP) |
| `SL_TIMEOUT_MS` | 20000 | Per-request timeout (use ≥120000 – SL cold start after idle takes >30 s) |
| `SL_DRY_RUN` | false | Block all writes to SAP |
| `SAP_MODE` | dev | Active mode (overridden by DB) |
| `SAP_DB_HOST` | – | MSSQL hostname |
| `SAP_DB_NAME` | – | MSSQL company database |
| `SAP_DB_TRUSTED_CONNECTION` | no | `yes` = Windows integrated auth (USER/PASSWORD ignored) |
| `SAP_DB_USER` / `SAP_DB_PASSWORD` | – | MSSQL read-only credentials (when not trusted) |
| `SAP_DB_TLS` | yes | TLS for MSSQL |
| `SAP_DB_ODBC_DRIVER` | ODBC Driver 18 for SQL Server | Installed ODBC driver name |
| `POSTGRES_DSN` | – | PostgreSQL event store |
| `POLL_INTERVAL_SECONDS` | 60 | Collector poll frequency |

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
