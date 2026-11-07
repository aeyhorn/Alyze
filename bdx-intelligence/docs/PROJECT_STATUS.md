# BDX Intelligence – Project Status

## Sprint 001 – SAP Read-only Collector  ✅ Complete

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

### Delivered

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | `order_snapshots`, `domain_events` tables |
| Initial full-load of open production orders | ✅ | `OWOR_OPEN_ORDERS_SQL` |
| Periodic snapshot polling (60 s) | ✅ | Configurable via `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | All 5 event types |
| Domain events: ORDER_CREATED | ✅ | First appearance in snapshot |
| Domain events: ORDER_RELEASED | ✅ | Status L→R |
| Domain events: QUANTITY_CHANGED | ✅ | PlannedQty delta |
| Domain events: DUE_DATE_CHANGED | ✅ | DueDate delta |
| Domain events: ORDER_CLOSED | ✅ | Status →C/X |
| Retry with exponential backoff (tenacity) | ✅ | Configurable max attempts |
| FastAPI REST API | ✅ | /health, /api/v1/orders, /api/v1/events |
| Healthcheck endpoint | ✅ | Checks SAP + PostgreSQL |
| CLI: report, events, diagnose, collect | ✅ | Rich table output |
| Diagnostic mode (one-shot) | ✅ | `bdx-collect diagnose` |
| Structured logs (structlog) | ✅ | JSON or console format |
| Secrets exclusively from env vars | ✅ | pydantic-settings, .env.example only |
| BDE adapter stub | ✅ | Abstract interface, NullAdapter |
| Machine adapter stub | ✅ | Abstract interface, NullAdapter (read-only) |
| pytest test suite with mock data | ✅ | No real SAP/Postgres required |
| docs/ARCHITECTURE.md | ✅ | |
| docs/SAP_MAPPING.md | ✅ | |
| README.md | ✅ | |

### Not in Sprint 001 (Planned)

| Feature | Sprint |
|---|---|
| BDE adapter implementation | 002 |
| Machine adapter (OPC-UA / MTConnect) | 002 |
| Kafka / MQTT event publishing | 003 |
| Dashboard UI | 003 |
| Multi-company SAP support | TBD |
| ORDER_PARTIAL_COMPLETE event | TBD |
| SCIM / SSO for API | TBD |

## Known Limitations (Sprint 001)

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) must exist in the SAP company database; otherwise queries fail.  Workaround: remove those columns from the query in `queries.py`.

2. **Clock drift**: Change detection uses SAP's `UpdateDate`/`UpdateTS` only for display; the authoritative signal is the BDX snapshot diff.  If two changes happen between polling cycles only the net delta is visible.

3. **Full-table snapshot**: The collector reads *all* production orders every 60 s.  For companies with tens of thousands of orders this may be slow.  Incremental reading (using `UpdateDate`) is planned for Sprint 002.

4. **No authentication on the API**: The REST API is currently unauthenticated.  It must not be exposed on a public network without an API gateway or mTLS.

## Repository Layout

```
bdx-intelligence/
├── src/bdx/          # Main Python package
│   ├── config.py     # Env-var configuration
│   ├── logging_config.py
│   ├── db/           # DB connection + queries
│   ├── models/       # Pydantic + ORM models
│   ├── collector/    # Polling, snapshots, change detection
│   ├── api/          # FastAPI application
│   ├── adapters/     # BDE + machine stubs
│   └── cli/          # CLI entry-points
├── alembic/          # Database migrations
├── tests/            # pytest tests (SQLite-based, no real SAP)
└── docs/             # Architecture, mapping, status
```
