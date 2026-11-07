# BDX Intelligence – Project Status

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT), dashboard UI | ✅ complete (MQTT built, no broker configured yet) |
| TBD | ORDER_PARTIAL_COMPLETE | ✅ delivered with 002 |
| TBD | Multi-company SAP, SSO/SCIM, SAP write-back, container deployment | ⬜ open |

Test suite: **74 tests, green** (SQLite in-memory, mocked SAP/HTTP – no real systems required).

---

## Sprint 001 – SAP Read-only Collector  ✅ Complete

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002` |
| Initial full-load of production orders | ✅ | `OWOR_SNAPSHOT_SQL` on first run / `--full` |
| Periodic polling (60 s) | ✅ | `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | |
| Domain events: ORDER_CREATED / ORDER_RELEASED / QUANTITY_CHANGED / DUE_DATE_CHANGED / ORDER_CLOSED | ✅ | see status-code note below |
| Retry with exponential backoff (tenacity) | ✅ | |
| FastAPI REST API, healthcheck, CLI, structured logs, secrets from env | ✅ | |
| Service Layer client + Dev/Prod mode registry | ✅ | write-back itself **not** implemented |

## Sprint 002 – BDE, machines, incremental reading  ✅ Complete

| Feature | Status | Notes |
|---|---|---|
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value is **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − `INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV: **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is now history-on-change only (was +38 561 rows per cycle) |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only; 10 machines on the floor |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | MACHINE_ONLINE / OFFLINE / STATE_CHANGED / ORDER_STARTED / ORDER_FINISHED / PIECES_REPORTED |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` on events and `/api/v1/machines` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records (start/end/pieces per order & machine) from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing & dashboard  ✅ Complete

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured yet** (`MQTT_ENABLED=false`) |
| Kafka publisher | ⬜ | not needed yet – interface allows adding it |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| Dockerfile + docker-compose.yml | ✅ written, ⬜ **not deployed** | needs SQL login `bdx_readonly` (no Windows auth in Linux containers) |

## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17); SQL login `bdx_readonly` does not exist yet on LDSAP |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| SQL login `bdx_readonly` on LDSAP | prerequisite for container deployment (`docker compose up`) |
| Deploy `docker-compose.yml` on 192.168.82.33 | after the SQL login exists; PG is already there |
| MQTT broker | set `MQTT_ENABLED=true`, `MQTT_HOST`; `pip install -e .[mqtt]` |
| Run against PROD | read-only; enables the machine ↔ SAP link for current orders |
| SAP write-back (release, confirmations via Service Layer) | not started; needs explicit approval |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not** exist in the Leisinger company databases. `queries.py` selects `NULL` placeholders; `u_type`/`u_priority` stay `None`. OWOR has other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags) that may be useful later.
2. **Net delta between cycles**: if two changes happen within one polling interval only the net delta is visible (events are derived from state diffs, not from SAP change logs).
3. **Incremental window**: orders that are closed *and* whose `UpdateDate` is older than the lookback window are only caught because BDX re-reads its known open orders by DocEntry. Orders unknown to BDX (created before the first full load and never open since) are not re-read – run `collect --once --full` after long outages or set `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: there is no BDE terminal system; records are reconstructed from SCADA telemetry (`BDE_GAP_SECONDS` splits segments). Scrap quantities are therefore always 0.
5. **API authentication** is an optional shared key only; do not expose the API outside the LAN without a gateway/mTLS.
6. **Legacy history**: the Sprint 001 migration seeded `order_state` with fingerprint `''`, so the first incremental cycle after upgrading rewrites one history row per open order (observed: 871, 30 s one-off).

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py          # Env-var configuration (SAP, PG, collector, machine, BDE, MQTT, app)
│   ├── db/                # SAP/PG engines + parameterised OWOR/OITM queries
│   ├── models/            # Pydantic WorkOrder + ORM (order_state, order_snapshots, snapshot_runs,
│   │                      #   machine_state, domain_events)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode
│   ├── api/               # FastAPI app, routes, static/dashboard.html
│   └── cli/               # bdx-collect
├── alembic/               # migrations 001, 002
├── tests/                 # 74 pytest tests
├── Dockerfile, docker-compose.yml
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS
```
