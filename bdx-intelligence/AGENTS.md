# BDX-Intelligence – Agent Guide

This file is the canonical guide for AI agents (and humans) working on the
`bdx-intelligence/` project. The same rules are mirrored in
`../.cursor/rules/bdx-conventions.mdc` for Cursor.

## Project at a glance

BDX-Intelligence connects SAP Business One and the shop floor to a local
PostgreSQL event store and exposes the result as REST API, dashboard, CLI and
(optionally) MQTT/Kafka events.

- **Read channels**: SAP B1 SQL Server (MSSQL, read-only), Mazak XmskSvr
  (HTTP/XML via SCADA proxy), SCADA telemetry REST (BDE derivation).
- **Write channel**: SAP Service Layer (OData v4), guarded by `SL_DRY_RUN`.
- **Storage**: PostgreSQL event store (`order_state`, `order_snapshots`,
  `snapshot_runs`, `machine_state`, `domain_events`, `sl_operations`,
  `app_setting`).
- **Exposure**: FastAPI (`/api/v1/*`), static dashboard (`/dashboard`),
  CLI (`bdx-collect`).

See `docs/ARCHITECTURE.md` and `docs/PROJECT_STATUS.md` for details.

## SAP Safety (hard rules)

1. **MSSQL channel is read-only.** Never add INSERT/UPDATE/DELETE/DDL against
   the SAP SQL Server. The SQLAlchemy event listener in `src/bdx/db/sap.py`
   blocks these at the Python layer — do not weaken it. The DB account must
   also be read-only.
2. **Service Layer writes are guarded by `SL_DRY_RUN`.** Default is `true`
   (blocks all writes). Never set `SL_DRY_RUN=false` in code or in
   `.env.example`. Only operators flip it in the real `.env`. Every SL call
   goes through `sap_sl/operations.py::_exec` which audits to `sl_operations`.
   Do not bypass the audit.
3. **No string interpolation in SQL.** Use parameterized `text()` with
   `:param` binds, as in `src/bdx/db/queries.py`. Never f-string/format SQL.
4. **Secrets only from env.** No credentials in code, tests, or docs. `.env`
   is gitignored. `.env.example` contains only placeholders.
5. **Custom SAP UDFs** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not**
   exist in Leisinger company DBs — `queries.py` selects `NULL` placeholders.
   Do not assume they are populated.
6. **PROD migrations require explicit opt-in.** `alembic/env.py` refuses to
   run against the PROD event store (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`
   set) unless `ALEMBIC_ALLOW_PROD=1` is also set. `deploy-prod.yml` sets it
   only when the human has checked the `run_migrations` approval input. Never
   set `ALEMBIC_ALLOW_PROD=1` in a committed file or in DEV `.env`.

## Architecture invariants (do not break without a migration)

- `order_state` is one row per order, upserted by fingerprint.
  `order_snapshots` is history-on-change only. Do not change this to
  history-on-every-cycle (Sprint 001 did that and produced +38 561 rows/cycle).
- `source_key` is the PK of `order_state` and the join key for events.
  Format: `<company_db>:<doc_entry>`.
- Events are idempotent by `event_id` (UUID). `persist_events()` skips
  duplicates. Never reuse event_ids.
- Machine ↔ SAP link: numeric XMSK `Order` = SAP `DocNum` →
  `order_state.doc_num` → `doc_entry`. Free-text refs (e.g. `10886/NEU`)
  stay raw in `order_ref`, no link.
- SAP status codes: `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled.
  (Sprint 001 had these wrong — do not reintroduce the old mapping.)
- Incremental read window:
  `since = max(sap_update_date) − INCREMENTAL_LOOKBACK_DAYS`. Open orders
  are always re-read; vanished open orders are re-read by DocEntry so
  closures are never missed.

## Event naming

- Order events: `ORDER_CREATED`, `ORDER_RELEASED`, `QUANTITY_CHANGED`,
  `DUE_DATE_CHANGED`, `ORDER_PARTIAL_COMPLETE`, `ORDER_CLOSED`.
- Machine events: `MACHINE_ONLINE`, `MACHINE_OFFLINE`,
  `MACHINE_STATE_CHANGED`, `MACHINE_ORDER_STARTED`,
  `MACHINE_ORDER_FINISHED`, `MACHINE_PIECES_REPORTED`.
- New event types go in the `EventType` enum in `src/bdx/models/events.py`
  and are added to `ORDER_EVENT_TYPES` or `MACHINE_EVENT_TYPES`.
- Payloads are JSON, decimals as strings (`str(qty)`), dates as ISO strings.

## Test pattern (mandatory)

- Every new code path in `collector/`, `adapters/`, `sap_sl/`, `db/`,
  `publish/` gets a pytest test.
- Tests run on SQLite in-memory (`conftest.py` sets
  `POSTGRES_DSN=sqlite:///:memory:`). No real Postgres/SAP required.
- Use `respx` for HTTP mocks (SCADA, SL), `fakeredis` only if needed. SAP
  rows are mocked as dicts (see `mock_sap_rows` fixture).
- Quantity comparisons use `Decimal` with `_QTY_EPSILON` tolerance — mirror
  this in tests.
- Target: keep coverage ≥ 80 % (CI gate). Aim for 90 % on `sap_sl/` and
  `collector/`.

## Code style

- Python 3.11+, `from __future__ import annotations` at top of every module.
- `structlog` for logging (`logger = structlog.get_logger(__name__)`),
  structured kwargs not f-strings.
- Pydantic v2 for DTOs, SQLAlchemy 2.0 typed mappings (`Mapped[...]`).
- `tenacity` for retries on external calls (SAP, SL, SCADA).
- Type hints required on all public functions in `sap_sl/`, `db/`,
  `collector/` (mypy strict in CI).
- `ruff check` and `ruff format --check` must pass (CI + pre-commit).

> **ruff status:** currently advisory (`continue-on-error` in CI) because the
> legacy codebase has ~381 ruff findings (import sorting, format) from before
> ruff was added. New files already pass. Run the `Lint Cleanup` workflow
> (`.github/workflows/lint-cleanup.yml`, manual trigger) to auto-fix the
> codebase as a trivial PR; once that lands, remove `continue-on-error` from
> the `lint` job in `.github/workflows/ci.yml`.

> **mypy status:** currently advisory (`continue-on-error` in CI) because the
> legacy code has ~48 errors (pydantic-settings `call-arg` friction + untyped
> functions in `collector/polling.py`). The config in `pyproject.toml` is
> permissive on purpose so CI is green on day 1. Tightening path:
> 1. Annotate the untyped functions in `collector/polling.py`, `snapshots.py`,
>    `change_detector.py`.
> 2. Add `# type: ignore[call-arg]` (or a pydantic mypy plugin) for the
>    `*Settings()` calls in `config.py`.
> 3. Flip `check_untyped_defs` to `true` and re-enable
>    `disallow_untyped_defs` in the `[[tool.mypy.overrides]]` block.
> 4. Remove `continue-on-error` from the `typecheck` job in
>    `.github/workflows/ci.yml`.

## Workflow (human-out-of-the-loop)

1. **Spec** (Notion or GitHub Issue) → auto-branch `feat/<slug>` or
   `fix/<slug>`.
2. **Implement**: `explore` subagent (quick) finds patterns; write code +
   test.
3. **Local gates**: `ruff check . && ruff format --check . && mypy src/bdx
   && pytest`. Pre-commit runs the same on commit.
4. **PR**: auto-created with a diff-based description. `bugbot` and
   `security-review` subagents run automatically.
5. **Review tier**:
   - Trivial (tests/docs/refactor, no behavior change) → auto-merge on green.
   - Touches `src/bdx/sap_sl/`, `src/bdx/db/`, `alembic/versions/`,
     `pyproject.toml` major deps, `docker-compose.yml` → CODEOWNER review.
6. **Deploy**: merge to `main` → Docker build → auto-deploy to DEV
   (`SL_DRY_RUN=true`) + smoke test (`bdx-collect diagnose`, `/health`).
   Prod-deploy needs manual approval and a `SL_DRY_RUN` pre-check.

## Documentation

- `docs/PROJECT_STATUS.md` ist das living-Dokument zum Projektstand. Die
  erste Zeile nach der Überschrift enthält ein Blockquote mit
  **Zuletzt aktualisiert:** <YYYY-MM-DD HH:MM (TZ)>. **Bei jeder Bearbeitung
  dieses Dokuments muss dieser Zeitstempel auf den aktuellen Zeitpunkt
  gesetzt werden** — egal wie klein die Änderung ist. Veralteter Zeitstempel
  = veraltetes Dokument.
- Die `DocumentationAgent` (`bdx-collect check-docs`) warnt, wenn
  `PROJECT_STATUS.md` älter als 90 Tage ist (`DOC.STATUS_STALE`).
- Neue Endpunkte, Env-Vars und Events werden zusätzlich in
  `docs/ARCHITECTURE.md` bzw. `docs/SAP_MAPPING.md` gepflegt (die Agents
  prüfen Konsistenz automatisch).
- `docs/PROJECT_GOALS.md` und `docs/REQUIREMENTS.md` sind Pflicht-Dokumente
  (`DocumentationAgent`, `required_docs`).

## Dev-Sync

Desktop und mobile Cloud-Entwicklung sehen denselben Stand nur über Git.
Jede Sitzung folgt `.cursor/rules/dev-sync.mdc`:

1. Zu Beginn `git fetch` und die drei Dokumente lesen. Einen zurückliegenden
   Branch integrieren, bevor etwas geändert wird.
2. Neue Anforderungen, ob vom Desktop oder aus der Cloud, als neue Zeile in
   `docs/REQUIREMENTS.md` anhängen.
3. Den betroffenen Abschnitt in `PROJECT_STATUS.md` und den Zielstatus in
   `PROJECT_GOALS.md` im selben Commit nachziehen. Beide Zeitstempel setzen.
4. Committen und `git push -u origin HEAD`. Ohne Push ist die Arbeit auf dem
   anderen Gerät nicht da.

Der Koordinator-Lauf (`.cursor/skills/dev-sync/SKILL.md`, Prompt
`.cursor/prompts/sync-coordinator.mdc`) ändert keinen Produktcode. Er gleicht
die drei Dokumente mit Git ab, pusht, und öffnet von `main` aus einen
Doku-PR `sync/status-<datum>`. Diesen PR mergt er nicht.

## Never

- Commit `.env` or real credentials.
- Set `SL_DRY_RUN=false` in any committed file.
- Add a write method to the MSSQL channel.
- Change SAP status code mappings without verifying against OWOR.
- Bypass the `sl_operations` audit for SL writes.
- Reuse `event_id`s (events must stay idempotent).

## Useful commands

```bash
# Install dev deps + pre-commit
pip install -e ".[dev]"
pre-commit install

# Local gates (mirror CI)
ruff check .
ruff format --check .
mypy src/bdx
pytest -v --cov=bdx --cov-fail-under=80

# Run app locally
bdx-collect diagnose
bdx-collect collect --once
bdx-collect serve

# Docker
docker compose --env-file .env up -d --build
docker compose run --rm migrate
```
