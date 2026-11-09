# BDX Intelligence

**Read-only SAP Business One production order collector, machine monitor and event engine.**

BDX Intelligence reads production orders from the SAP Business One SQL Server (read-only, incremental), reads the
live machine state of the Mazak CNC machines (XMSK feed via the SCADA proxy), derives BDE records from the SCADA
telemetry, turns everything into domain events (PostgreSQL event store, optional MQTT) and exposes it via REST API,
dashboard and CLI.

> **Status**: Sprints 001–003 delivered and verified against DEV (see [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)).

---

## Quick Start

### Prerequisites

- Python 3.11+
- ODBC Driver 17 or 18 for SQL Server
- PostgreSQL 14+ (event store) – at Leisinger: container `bdx-intelligence-postgres` on 192.168.82.33:5437
- SAP B1 SQL Server read access: Windows integrated auth on a domain-joined machine **or** a read-only SQL login
  (see [docs/SAP_MAPPING.md](docs/SAP_MAPPING.md))
- Optional: network access to the SCADA system (`http://192.168.82.33:3888`) for machines/BDE

### 1. Install

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"           # add  .[mqtt]  for the MQTT publisher
```

### 2. Configure

```bash
cp .env.example .env              # fill in credentials – NEVER commit .env
```

`.env` in the project root is loaded automatically (`python-dotenv`); real environment variables take precedence.

Minimum:

```env
SAP_DB_HOST=ldsap.leisinger.local
SAP_DB_NAME=DEV_SBO_LEISINGER
SAP_DB_TRUSTED_CONNECTION=yes                       # or SAP_DB_USER / SAP_DB_PASSWORD
SAP_DB_ODBC_DRIVER=ODBC Driver 17 for SQL Server
POSTGRES_DSN=postgresql+psycopg2://bdx:pw@192.168.82.33:5437/bdx_intelligence

MACHINE_ENABLED=true
MACHINE_XMSK_URL=http://192.168.82.33:3888/api/machstates
BDE_ENABLED=true
BDE_SCADA_BASE_URL=http://192.168.82.33:3888
```

### 3. Migrate, diagnose, run

```bash
alembic upgrade head              # schema 001 + 002
bdx-collect diagnose              # PG, SAP, XMSK feed, SCADA API, MQTT
bdx-collect collect --once        # one SAP cycle (first run = full load, then incremental ≈2 s)
bdx-collect machines --live       # one machine cycle + table
bdx-collect collect               # continuous: SAP every 60 s, machines every 15 s (Ctrl+C to stop)
```

### 4. Reports

```bash
bdx-collect report                # open orders (P/R) from order_state
bdx-collect report --all -s L     # closed orders
bdx-collect events -t MACHINE_STATE_CHANGED
bdx-collect machines
bdx-collect runs
```

### 4b. SAP write-back (Service Layer, DRY_RUN-safe)

```bash
# DRY_RUN=true (safe default) → audits the operation without touching SAP
bdx-collect release 38559              # P → R
bdx-collect close 38559                # → L
bdx-collect cancel 38559               # → C
bdx-collect report-production 38559 -q 25 -w W01   # book 25 pcs into warehouse W01
bdx-collect sl-operations             # audit log

# Real writes: set SL_DRY_RUN=false in .env (or env), then re-run
```

### 5. API + dashboard

```bash
bdx-collect serve                 # uvicorn on API_HOST:API_PORT (8085 on the dev machine)
```

- Dashboard: `http://localhost:8085/dashboard` · Q2P: `http://localhost:8085/q2p` · OpenAPI: `http://localhost:8085/docs`
- `GET /health` – readiness (Postgres, last collector run, machine feed, publisher)
- `GET /api/v1/orders` (`open_only`, `status`, `item_code`, `doc_num`), `/orders/summary`, `/orders/{doc_entry}`
- `GET /api/v1/events` (`event_type`, `machine_id`, `doc_entry`, `since`), `/events/summary`
- `GET /api/v1/machines`, `/machines/{id}`, `/machines/{id}/live`
- `GET /api/v1/bde/records?hours=24`
- `GET /api/v1/runs`
- `GET/PUT /api/v1/service-layer[/mode]`
- `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` — SAP write-back
- `GET /api/v1/service-layer/operations` — write-back audit log
- `POST/GET /api/v1/q2p/inquiries` — Quote-to-Promise inquiry cases (parallel evaluate)
- `POST /api/v1/q2p/inquiries/{id}/evaluate|decide` — re-evaluate / accept|reject|counter
- `GET /api/v1/q2p/promise?item_code=&qty=` — ad-hoc promise check

Set `API_KEY` to protect `/api/v1/*` (`X-API-Key` header or `?api_key=`; the dashboard stores it from the URL).

### Docker (prepared, not deployed)

```bash
docker compose --env-file .env up -d --build
```

Requires a SQL login (`SAP_DB_TRUSTED_CONNECTION=no`) – Windows integrated auth is not available in Linux containers.

---

## Running Tests

No SAP, PostgreSQL or SCADA required – tests use SQLite and mocked HTTP/SAP:

```bash
pytest                            # 87 tests
pytest --cov=bdx --cov-report=term-missing
```

---

## Project Structure

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py              # settings from env (SAP, PG, collector, machine, BDE, MQTT, app)
│   ├── db/                    # sap.py (read-only engine), postgres.py, queries.py
│   ├── models/                # sap.py (WorkOrder, status codes), events.py (ORM + EventType)
│   ├── collector/             # polling.py, snapshots.py, change_detector.py, machines.py
│   ├── adapters/              # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── publish/               # base.py, mqtt.py
│   ├── sap_sl/                # Service Layer client + mode registry
│   ├── api/                   # main.py, deps.py, routes/, static/dashboard.html
│   └── cli/report.py          # bdx-collect
├── alembic/                   # 001_initial, 002_state_tables_and_machines
├── tests/
├── Dockerfile · docker-compose.yml
└── docs/                      # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS
```

---

## Domain Events

| Event | Trigger |
|---|---|
| `ORDER_CREATED` | order seen for the first time |
| `ORDER_RELEASED` | SAP status `P` (Planned) → `R` (Released) |
| `ORDER_PARTIAL_COMPLETE` | `CmpltQty` increased while open |
| `QUANTITY_CHANGED` | `PlannedQty` changed |
| `DUE_DATE_CHANGED` | `DueDate` changed |
| `ORDER_CLOSED` | status → `L` (Closed) or `C` (Cancelled) |
| `MACHINE_ONLINE` / `MACHINE_OFFLINE` | machine appears in / disappears from the XMSK feed |
| `MACHINE_STATE_CHANGED` | running / idle / setup / off changed |
| `MACHINE_ORDER_STARTED` / `MACHINE_ORDER_FINISHED` | order reference on the machine set / cleared (linked to SAP `DocNum` when numeric) |
| `MACHINE_PIECES_REPORTED` | piece counter increased |

---

## Security

- **No write access to SAP**: application-level read-only guard blocks all DML/DDL; the DB account must be `SELECT` only.
  The Service Layer write channel is prepared but has no write operations and is guarded by `SL_DRY_RUN`.
- **No machine control**: machine and BDE adapters are read-only HTTP GET by interface contract.
- **Secrets from environment only**: `.env` is in `.gitignore`. Never commit credentials.
- **TLS for SAP**: enabled by default (`SAP_DB_TLS=yes`); `SL_ALLOW_INVALID_CERT` only for the internal self-signed cert.
- **API**: optional shared key; keep the API inside the LAN.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [SAP / shop-floor field mapping](docs/SAP_MAPPING.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Promise Platform Vision](docs/VISION_PROMISE_PLATFORM.md) – Offer/Gaps → Kundenportal, Einkauf, Vertrag

---

## Repository

Remote: `github.com/aeyhorn/Alyze` (branch `main`).

**Do not push without explicit approval** – this repository may contain environment-specific configuration references.
