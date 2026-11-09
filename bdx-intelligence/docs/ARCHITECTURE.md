# BDX Intelligence – Architecture

## Overview

BDX Intelligence connects SAP Business One and the shop floor to a local PostgreSQL event store and exposes
the result as REST API, dashboard, CLI and (optionally) MQTT events.

| Channel | Protocol | Direction | Used for |
|---|---|---|---|
| **SAP read** | MSSQL / pyodbc | SAP → BDX | order state, change detection (OWOR, OITM) |
| **SAP write** | Service Layer OData v4 | BDX → SAP | prepared only (login, mode, DRY_RUN) – no writes yet |
| **Machine feed** | HTTP / XML (Mazak XmskSvr via SCADA proxy) | floor → BDX | live machine state, machine events |
| **BDE** | HTTP / JSON (SCADA telemetry API) | floor → BDX | derived BDE records (per order & machine) |
| **Publish** | MQTT (optional) | BDX → consumers | every new domain event |

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               BDX Intelligence                                    │
│                                                                                   │
│  SAP B1 SQL Server ──SELECT only──►┌──────────────────────┐                       │
│  (OWOR, OITM)        incremental   │ SAP collector        │                       │
│                                    │ full / incremental   │──► order_state        │
│  XmskSvr ─► SCADA nginx ─XML──────►│ Machine collector    │──► order_snapshots    │
│  /api/machstates     every 15 s    │ diff → events        │──► snapshot_runs      │
│                                    └──────────┬───────────┘──► machine_state      │
│                                               │                ──► domain_events  │
│                                               ▼                                   │
│                                    ┌──────────────────────┐    ┌───────────────┐  │
│                                    │ EventPublisher       │───►│ MQTT broker   │  │
│                                    │ Null | Mqtt          │    │ (optional)    │  │
│                                    └──────────────────────┘    └───────────────┘  │
│                                                                                   │
│  SCADA REST ─JSON─►┌────────────────┐     ┌───────────────────────────────────┐   │
│  /api/machines     │ BDE adapter    │────►│ FastAPI                           │   │
│  /telemetry        │ (derived)      │     │ /api/v1/orders  /events  /runs    │   │
│                    └────────────────┘     │ /api/v1/machines  /bde/records    │   │
│                                           │ /api/v1/service-layer  /health    │   │
│  SAP Service Layer ◄──httpx──────────────│ /dashboard (static HTML/JS)       │   │
│  (login, CSRF, mode, DRY_RUN)             └───────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 0. SAP Mode Registry (`src/bdx/sap_sl/mode.py`)

Tracks the active SAP mode (`dev` | `prod`). Resolution order: `app_setting.sapMode` (PostgreSQL) → `SAP_MODE` env →
`dev`. Mode switch via `PUT /api/v1/service-layer/mode` clears the SL session and sets the company DB.

### 1. SAP collector (`src/bdx/collector/`)

| Module | Responsibility |
|---|---|
| `polling.py` | main loop (SAP every `POLL_INTERVAL_SECONDS`, machines every `MACHINE_POLL_INTERVAL_SECONDS`), retry/backoff, `run_once()` |
| `snapshots.py` | `order_state` upsert (fingerprint), history rows on change, `snapshot_runs` bookkeeping |
| `change_detector.py` | diff `order_state` vs. current read → order events |
| `machines.py` | diff `machine_state` vs. XMSK feed → machine events, SAP link |

**SAP cycle (`run_once`)**

1. decide mode: `full` when `order_state` is empty, `--full`, or every `FULL_RELOAD_EVERY_CYCLES`; else `incremental`
2. read SAP: `fetch_all_orders_snapshot()` **or** `fetch_orders_incremental(since)` with
   `since = max(order_state.sap_update_date) − INCREMENTAL_LOOKBACK_DAYS` (open orders are always included)
3. incremental only: open orders known to BDX but missing from the result → `fetch_orders_by_docentries()` (closures are never missed)
4. `detect_changes(previous_state, orders)` → events
5. `apply_orders()` → upsert `order_state`, append `order_snapshots` for new/changed orders, one bulk UPDATE for the rest
6. `persist_events()` (idempotent by `event_id`) → `publisher.publish(new_events)` → `finish_run()`

Measured on DEV (38 561 orders, 871 open): full load 47 s, incremental cycle **≈2 s**.

**Machine cycle (`run_machine_cycle`)**: `XmskMachineAdapter.fetch()` → `detect_machine_changes()` (upsert
`machine_state`, offline detection after `MACHINE_OFFLINE_AFTER_SECONDS`) → `persist_events()` → publish.
A numeric XMSK `Order` is resolved against `order_state.doc_num`, so machine events carry `doc_entry`/`item_code`.

### 2. Configuration (`src/bdx/config.py`)

All configuration is loaded from environment variables via `pydantic-settings`; `.env` in the project root is picked up
by `load_dotenv()` (real environment wins). Settings classes: `SAPSettings`, `PostgresSettings`, `CollectorSettings`,
`MachineSettings`, `BdeSettings`, `MqttSettings`, `AppSettings`, `ServiceLayerSettings`, `SapModeSettings`.

### 3. Database layer (`src/bdx/db/`)

- `sap.py` – SQLAlchemy engine for SQL Server (pyodbc). An event listener blocks INSERT/UPDATE/DELETE/DDL at the
  Python layer; the DB account must be read-only as well.
- `queries.py` – fixed, parameterised `text()` queries (open, snapshot, incremental, by-DocEntry; OITM).
- `postgres.py` – engine/session factory for the event store.

**PostgreSQL schema** (Alembic `001` + `002`)

| Table | Purpose |
|---|---|
| `order_state` | current state, one row per order (`source_key` PK, `fingerprint`, `first_seen_at`, `last_changed_at`) |
| `order_snapshots` | history – a row whenever an order is first seen or changed |
| `snapshot_runs` | one row per collector cycle (mode, since, counts, duration, error) |
| `machine_state` | current state per machine (XMSK fields, normalised state, SAP link, online flag) |
| `domain_events` | append-only events; `event_type` VARCHAR, nullable `doc_entry`/`doc_num`/`item_code`, `machine_id` |
| `app_setting` | key/value (SAP mode) |

### 4. Adapters (`src/bdx/adapters/`)

| Adapter | Implementation | Source |
|---|---|---|
| `MachineAdapter` | `XmskMachineAdapter` (`parse_xmsk`, `normalise_state`) | `MACHINE_XMSK_URL` (SCADA proxy to XmskSvr) |
| `BDEAdapter` | `ScadaTelemetryBDEAdapter` (`telemetry_to_records`) | `BDE_SCADA_BASE_URL` (`/api/machines`, `/api/machines/{id}/telemetry`) |
| both | `Null*Adapter` when disabled | – |

Adapters are read-only by interface contract – there are no methods to control machines.

### 5. Publishing (`src/bdx/publish/`)

`EventPublisher.publish(events)` is fire-and-forget and never raises into the collector. `build_all_publishers()`
returns a single publisher or a composite covering every configured transport:

| Transport | Module | Extra | Topic / key |
|---|---|---|---|
| MQTT | `publish/mqtt.py` (`MqttPublisher`) | `.[mqtt]` (paho-mqtt) | `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>` |
| Kafka | `publish/kafka.py` (`KafkaPublisher`) | `.[kafka]` (confluent-kafka) | topic `KAFKA_TOPIC`, key = `source_key` (partition affinity) |

When both are enabled a `_Composite` publisher fans out to both. `NullPublisher` when none are on.

### 6. Service Layer client + write-back (`src/bdx/sap_sl/`)

Login/session (`B1SESSION`, `ROUTEID`), CSRF fetch, 401 re-login, `SL_DRY_RUN` guard, `SL_ALLOW_INVALID_CERT`,
OData error extraction. Write operations are implemented in `sap_sl/operations.py`:

| Operation | SL call | Effect |
|---|---|---|
| `release_order` | `PATCH ProductionOrders({DocEntry})` `{"Status":"R"}` | Planned → Released |
| `close_order` | `PATCH ProductionOrders({DocEntry})` `{"Status":"L"}` | → Closed |
| `cancel_order` | `PATCH ProductionOrders({DocEntry})` `{"Status":"C"}` | → Cancelled |
| `report_production` | `POST ReceiptFromProduction` | books produced qty into a warehouse |

Every call (success / failure / DRY_RUN) is recorded in the `sl_operations` audit table (migration 003).
`SL_DRY_RUN=true` is the safe default — writes only reach SAP with `SL_DRY_RUN=false`.

### 7. API (`src/bdx/api/`)

| Endpoint | Purpose |
|---|---|
| `GET /health`, `/health/live` | readiness (Postgres + last collector run), machine feed, publisher; liveness |
| `GET /api/v1/orders` | current state; `open_only=true` default, `status`, `item_code`, `doc_num`, paging |
| `GET /api/v1/orders/summary`, `/orders/{doc_entry}` | counts per status; one order with history + events |
| `GET /api/v1/events`, `/events/summary` | events (filter type/source/machine/doc_entry/since); counts |
| `GET /api/v1/machines`, `/machines/{id}`, `/machines/{id}/live` | machine state (+ linked SAP order), events, direct feed read |
| `GET /api/v1/bde/records?hours=` | derived BDE records |
| `GET /api/v1/runs` | collector runs |
| `GET/PUT /api/v1/service-layer[/mode]` | SL status, dev/prod switch |
| `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` | SAP write-back (DRY_RUN-safe) |
| `GET /api/v1/service-layer/operations` | write-back audit log |
| `POST /api/v1/q2p/inquiries` | create Quote-to-Promise inquiry case (+ optional parallel evaluate) |
| `GET /api/v1/q2p/inquiries` | list inquiry cases |
| `GET/PATCH /api/v1/q2p/inquiries/{id}` | get / update inquiry |
| `POST /api/v1/q2p/inquiries/{id}/evaluate` | re-run parallel domain checks |
| `POST /api/v1/q2p/inquiries/{id}/decide` | accept / reject / counter |
| `GET /api/v1/q2p/promise` | ad-hoc promise check (no persist) |
| `GET /dashboard` | static dashboard (auto-refresh) |
| `GET /vorgang` | Vorgangsleitstand: FA-Fenster auf der Zeitachse, Maschinenbelegung, gemeldeter Arbeitsgang |
| `GET /analytics` | process-weakness dashboard |
| `GET /q2p` | Quote-to-Promise cockpit |

### 7b. Quote-to-Promise (`src/bdx/q2p/`)

One **inquiry case** replaces serial email/phone clarification. `evaluate_promise()` fans out
domain checks in parallel (SAP live + PG machine/order state):

| Domain | Source | Eliminates asking… |
|---|---|---|
| item | OITM | „Existiert der Artikel?“ |
| material | OITW + OPOR/POR1 | Lager / Bestellung / Liefertermin / Preis |
| bom | OITT/ITT1 (+ OITW je Komponente) | Stücklisten-Klärung |
| capacity | `machine_state` + open `order_state` | „Wann können wir fertigen?“ |
| pricing | **bdx-quoter** (Datenraum) else ITM1/OPLN | Kalkulation / Listenpreis |
| personnel | *gap* → open question | Schicht / Qualifikation (noch Mensch) |

**bdx-quoter** (Docker `:8020`): optional `QUOTER_*` settings; adapter
`src/bdx/adapters/quoter.py`. Inquiry fields `datenraum` / `kunde` / `use_llm`
trigger a quote; quoter `offen[]` becomes Q2P `open_questions`. See
[Q2P_QUOTER.md](Q2P_QUOTER.md).

Missing SELECT grants degrade the domain to `unknown` + an explicit `open_questions` entry
instead of failing the whole evaluation. `bdx-collect serve` attaches the SAP engine so the
API can run live reads; without it, SAP domains become human questions.

`/api/v1/*` is protected by `API_KEY` when set (`X-API-Key` header or `?api_key=`); health and dashboard stay public.

### 8. CLI (`src/bdx/cli/report.py`)

```
bdx-collect report [--all] [-s P|R|L|C]   # orders from order_state (open by default)
bdx-collect events [-t TYPE] [-m MACHINE]  # recent domain events
bdx-collect machines [--live]              # machine state (optionally one live cycle first)
bdx-collect runs                           # collector runs
bdx-collect diagnose                       # PG, SAP, XMSK, SCADA, MQTT
bdx-collect collect [--once] [--full]      # collector loop (SAP + machines)
bdx-collect serve                          # API + dashboard
```

## Deployment

`Dockerfile` (python:3.11-slim + msodbcsql18) and `docker-compose.yml` (services `migrate`, `collector`, `api`) are
provided but **not deployed yet**: inside a Linux container Windows integrated authentication is unavailable, so the SQL
login `bdx_readonly` must exist first. PostgreSQL already runs as container `bdx-intelligence-postgres` on the Docker
host 192.168.82.33 (port 5437).

## Security constraints

- MSSQL read channel: SELECT only; application write-guard blocks DML/DDL
- Service Layer write channel: guarded by `SL_DRY_RUN`; no write operations implemented
- Machine/BDE adapters: read-only HTTP GET; direct XmskSvr access is not used (SCADA proxy only)
- Secrets only from environment (`.env` is gitignored); passwords are masked in logs
- API key optional; API is LAN-only without a gateway/mTLS

## Configuration reference

| Variable | Default | Purpose |
|---|---|---|
| `SL_BASE_URL`, `SL_COMPANY_DB_DEV/PROD`, `SL_USERNAME`, `SL_PASSWORD` | – | Service Layer |
| `SL_ALLOW_INVALID_CERT` | false | self-signed TLS (required for LDSAP) |
| `SL_TIMEOUT_MS` | 20000 | use ≥120000 – SL cold start >30 s |
| `SL_DRY_RUN` | false | block all SAP writes |
| `SAP_MODE` | dev | active mode (overridden by DB) |
| `SAP_DB_HOST`, `SAP_DB_NAME` | – | MSSQL |
| `SAP_DB_TRUSTED_CONNECTION` | no | `yes` = Windows integrated auth |
| `SAP_DB_USER` / `SAP_DB_PASSWORD` | – | SQL login (when not trusted) |
| `SAP_DB_TLS` | yes | TLS for MSSQL |
| `SAP_DB_ODBC_DRIVER` | ODBC Driver 18 for SQL Server | installed driver name (17 on the dev machine) |
| `POSTGRES_DSN` | – | event store |
| `POLL_INTERVAL_SECONDS` | 60 | SAP poll interval |
| `INCREMENTAL_LOOKBACK_DAYS` | 2 | incremental window below max known UpdateDate |
| `FULL_RELOAD_EVERY_CYCLES` | 0 | periodic full reload (0 = never) |
| `RETRY_MAX_ATTEMPTS`, `RETRY_WAIT_MIN/MAX_SECONDS` | 5 / 2 / 60 | tenacity |
| `MACHINE_ENABLED`, `MACHINE_XMSK_URL` | false / – | machine feed |
| `MACHINE_POLL_INTERVAL_SECONDS` | 15 | machine poll interval |
| `MACHINE_TIMEOUT_SECONDS`, `MACHINE_OFFLINE_AFTER_SECONDS` | 10 / 120 | |
| `BDE_ENABLED`, `BDE_SCADA_BASE_URL` | false / – | BDE source |
| `BDE_TIMEOUT_SECONDS`, `BDE_GAP_SECONDS` | 30 / 900 | |
| `MQTT_ENABLED`, `MQTT_HOST`, `MQTT_PORT` | false / – / 1883 | publisher (MQTT) |
| `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_TLS`, `MQTT_CLIENT_ID` | – / – / false / bdx-intelligence | |
| `MQTT_TOPIC_PREFIX`, `MQTT_QOS` | bdx/intelligence / 1 | |
| `KAFKA_ENABLED`, `KAFKA_BOOTSTRAP_SERVERS` | false / – | publisher (Kafka) |
| `KAFKA_TOPIC`, `KAFKA_CLIENT_ID` | bdx-intelligence-events / bdx-intelligence | |
| `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_MECHANISM` | PLAINTEXT / PLAIN | |
| `KAFKA_ACKS`, `KAFKA_REQUEST_TIMEOUT` | 1 / 10 | |
| `SL_DRY_RUN` | false | **set to `true` for safety** — blocks all SAP writes |
| `API_HOST`, `API_PORT` | 0.0.0.0 / 8080 (8085 on the dev machine) | |
| `API_KEY` | – | optional API protection |
| `LOG_LEVEL`, `LOG_FORMAT` | INFO / console | structlog |

## Data flow – domain events

```
previous state      current read           events produced
──────────────────────────────────────────────────────────────────
(absent)            R, qty=100          → ORDER_CREATED
P, qty=100          R, qty=100          → ORDER_RELEASED
R, cmplt=10         R, cmplt=25         → ORDER_PARTIAL_COMPLETE
R, qty=100          R, qty=150          → QUANTITY_CHANGED
R, due=Dec 1        R, due=Dec 15       → DUE_DATE_CHANGED
R, cmplt=10         L, cmplt=100        → ORDER_CLOSED

machine (absent)    Order=38574         → MACHINE_ONLINE, MACHINE_ORDER_STARTED (doc_entry 38574)
idle                Fertigen            → MACHINE_STATE_CHANGED
pieces=243          pieces=245          → MACHINE_PIECES_REPORTED (+2)
Order=38574         Order=38600         → MACHINE_ORDER_FINISHED, MACHINE_ORDER_STARTED
seen 12:00          missing >120 s      → MACHINE_OFFLINE
```

Events are keyed by a UUID `event_id`; `persist_events()` skips existing IDs (idempotent).
