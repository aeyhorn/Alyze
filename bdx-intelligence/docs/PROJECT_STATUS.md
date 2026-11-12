# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-12 01:38 (CET)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (DEV checks below are the 2026-11-07 snapshot) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (same DEV snapshot) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ on `main` (publishers built, no broker; write-back DRY_RUN-verified 2026-11-07) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ tree on `origin/main`. DEV deploy green through 2026-11-10. Nightly integration red (ODBC install, 2026-11-11). Secrets and branch protection unread this run |
| 005 | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, #39). Migrations through `008`. Q2P grants and Quoter on DEV remain operator steps |
| Analytics | KPI engine, anomalies, weakness dashboard | ✅ merged (#5, #6, #12). Migrations `005` and `006`. UI `/analytics` |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41). Migrations `007` and `008`. Deep-link spec #57. Quoter UI is outside this repo |
| Vorgang | Vorgangsleitstand | ✅ merged (#67). UI `/vorgang` |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test functions on `main`: 120 unit + 8 integration (`def test_` under `bdx-intelligence/tests`). Unit tests use SQLite in-memory. The integration suite skips locally when DEV credentials are absent. The nightly GitHub job is failing before pytest (see Sprint 004).

## Git (abgeglichen 2026-11-12 01:38 CET)

`origin/main` is `cd6440f` (2026-11-10 07:21 +0100), “Update deployment timestamp and SHA for the latest release”. This reconciliation started from a clean worktree at that commit.

`deploy-dev` succeeded for that push (run created 2026-11-10 07:22 CET) and for the `main` pushes on 2026-11-09. No `deploy-prod` runs are recorded. Committed `.runtime/last-deploy-at` and `.runtime/last-deploy-sha` still read `2026-11-07 21:50:15 +01:00` and `6ccc036`.

93 remote branches are not contained in `origin/main`. Most of them are open documentation-sync pull requests; this run does not merge them. `chore/ruff-cleanup-20261108` has no pull request. Its tip is one ruff-format commit touching 47 files and is not on `main`. Older feature-branch tips (`sprint-001`, analytics, Q2P, Promise, Quoter spec, dashboard nav, Vorgangsleitstand) remain after squash-merges of #1, #5, #33, #39, #40, #41, #57, #62, and #67.

GitHub Environments `dev`, `prod`, and `CURSOR_API_KEY` exist. The `prod` environment returned no protection rules. Branch protection and Actions secret names returned HTTP 403, so this run leaves both unverified.

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

## Sprint 003 – Publishing, dashboard & write-back  ✅ Complete

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured yet** (`MQTT_ENABLED=false`) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | alternative to MQTT; key = `source_key` (partition affinity), JSON value; `build_all_publishers()` composes both when both are on |
| Kafka publisher | ✅ | `publish/kafka.py` (confluent-kafka, optional `.[kafka]`); `build_all_publishers()` composes MQTT + Kafka |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay an operator action in the host environment. Committed files keep the dry-run guard on |
| Dockerfile + docker-compose.yml | ✅ on `main`, DEV deploy green through 2026-11-10 | `deploy-dev.yml` recreates `collector` and `api` on the DEV host. SQL login `bdx_readonly` (`docs/sql/create_bdx_readonly.sql`) is still unconfirmed |

## Sprint 005 – Quote-to-Promise Cockpit  ✅ Merged

**Goal**: Replace serial multi-person clarification on inquiries (material, capacity, price, personnel)
with one inquiry case that answers domains in parallel from SAP + shop floor. Humans only see
`open_questions` where the system has no data.

| Feature | Status | Notes |
|---|---|---|
| Inquiry case store `q2p_inquiries` (Alembic `004`) | ✅ | status draft/ready/blocked/decided; decision audit |
| Parallel evaluator `bdx.q2p.service.evaluate_promise` | ✅ | item / material / BOM / capacity / pricing / personnel |
| SAP reads OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ | graceful degrade on missing SELECT |
| Capacity from `machine_state` + open `order_state` | ✅ | idle vs busy + backlog same item |
| REST `/api/v1/q2p/*` + ad-hoc `/q2p/promise` | ✅ | create, list, evaluate, decide |
| Cockpit UI `/q2p` | ✅ | form + case list + domain cards + human questions + decision |
| `bdx-collect serve` attaches SAP engine | ✅ | without engine → SAP domains become open questions |
| SQL grant script `docs/sql/grant_q2p_readonly.sql` | ✅ | run on DEV/PROD for live material/price |
| bdx-quoter HTTP adapter + pricing domain | ✅ | `QUOTER_*` env; datenraum on inquiry; `offen[]` → open_questions |
| Migration `008` (datenraum/kunde/use_llm on q2p_inquiries) | ✅ | renumbered after analytics `005` / promise `007` |

**Deploy notes**: `alembic upgrade head` (through `008`); run `grant_q2p_readonly.sql` on LDSAP;
set `QUOTER_ENABLED=true` + `QUOTER_BASE_URL=http://<docker-host>:8020`; open `http://<host>:8085/q2p`.

**Still human by design**: personnel/shift qualification (no feed yet). Quoter `offen` stays human until resolved in the datenraum. Confirm `/api/run` paths against real `web/server.py` if aliases miss.

## Promise Platform  ✅ Merged (#41)

**Goal**: Living Offer as system of record; Gaps instead of e-mail chains; fulfillment agents
(quote/purchase/capacity/contract); internal `/promise` cockpit + customer `/portal/{token}`.

| Feature | Status | Notes |
|---|---|---|
| Domain + Alembic `007` (offers/gaps/evidence/jobs/contracts) | ✅ | |
| Offer Engine (create / recompute / decide / resolve / publish) | ✅ | `bdx.promise.engine` |
| Agents: quote, purchase, capacity, contract | ✅ | quote delegates pricing to `evaluate_promise` + quoter |
| API `/api/v1/promise/*` + `/api/v1/portal/{token}` | ✅ | portal is token-scoped, no API key |
| UI `/promise` + `/portal/{token}` | ✅ | |
| Vision doc | ✅ | `docs/VISION_PROMISE_PLATFORM.md` |
| Quoter Deep Link Contract | 📝 spezifiziert | Entscheidung: Deep Link + `return_url`; Spec/Prompt: `docs/QUOTER_DEEP_LINK.md` (Quoter-Implementierung + BDX-UI folgen) |

**Deploy notes**: `alembic upgrade head` (`007`+`008`); open `/promise`; publish contract then share portal link.

## Analytics and weakness dashboard  ✅ Merged (#5, #6, #12)

**Goal**: KPI snapshots, anomaly detection, self-tuning thresholds, and a shop-floor weakness view on top of the event store.

| Feature | Status | Notes |
|---|---|---|
| Alembic `005` (kpi snapshots, thresholds, anomalies, shift calendar, machine history) | ✅ | on `main`; revision follows Q2P `004` |
| Alembic `006` diagnosis tables | ✅ | measurement quality, flow segments, lateness cause, bottleneck rank |
| Package `src/bdx/analytics/` | ✅ | KPIs, procurement KPIs, anomalies, flow, causes, bottleneck, thresholds |
| REST `/api/v1/analytics/*` | ✅ | kpis, trends, anomalies, thresholds, quality, flow, causes, bottleneck, weaknesses, `POST /run` |
| UI `/analytics` | ✅ | header label „Schwachstellen“; Betrieb, Vorgänge, Q2P, and Promise stay linked (#62) |

## Vorgangsleitstand  ✅ Merged (#67)

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht. Der Commit auf `main` ist `90a6593`.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ written | push/PR to `main`: ruff (lint + format check), mypy on `src/bdx`, pytest with `--cov-fail-under=80`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/` |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, runs green | push to `main` → build image (`ghcr.io/<repo>/bdx-intelligence:dev` + `:sha-<sha>`), push to GHCR, deploy on the self-hosted runner on the DEV host (no SSH hop), `docker compose pull`, migrations, recreate `collector` + `api`, smoke test `/health/live`. Diagnose is not a hard gate. The job aborts when the host env disables the dry-run guard. Last green run: 2026-11-10 07:22 CET (`cd6440f`) |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; `prod` environment with required reviewers; extra inputs `run_migrations` and `confirm_sl_write` (must be `true`); pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | ✅ written | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml` |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | committed with the Sprint 004 tree. A separate ruff-format branch `chore/ruff-cleanup-20261108` is still unmerged and has no PR |
| **`.github/workflows/lint-cleanup.yml`** | ✅ on `main` | manual lint-cleanup workflow. The cleanup branch itself is not merged |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The Sprint 004 tree is on `origin/main` at `cd6440f`.** Workflows, `src/bdx/agents/`, `scripts/`, `tests/integration/`, `AGENTS.md`, and the Cursor prompts and rules are committed. DEV deploy no longer uses an SSH hop; `deploy-dev.yml` runs on the self-hosted runner on the DEV host.
* **Nightly integration is red.** The scheduled runs on 2026-11-09, 2026-11-10, and 2026-11-11 failed. The latest ([run 43003787661](https://github.com/aeyhorn/Alyze/actions/runs/43003787661)) stopped in “Install ODBC Driver 18” with exit code 2, before pytest.
* **G4 acceptance is still open.** Actions secret names and branch protection returned HTTP 403. Environments `dev`, `prod`, and `CURSOR_API_KEY` exist. `prod` returned no protection rules. `AGENTS.md` still marks ruff and mypy as advisory in CI.
* **SSH deploy secrets in the old note are stale.** Current `deploy-dev.yml` does not use `DEV_SSH_*`. Nightly integration still expects `SAP_DB_*`, `SL_*`, and `POSTGRES_DSN`. Whether those names are populated was not readable.



## Operational status (DEV, verified 2026-11-07)

This coordinator did not re-run `diagnose`, `collect`, or the machine probe. The rows below stay the 2026-11-07 snapshot. Schema head in git is Alembic `008`. The snapshot recorded Postgres schema **002**. Successful `deploy-dev` runs since then execute `docker compose run --rm migrate` on the DEV host; this run did not read the live schema.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17); SQL login `bdx_readonly` does not exist yet on LDSAP |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` and `report-production 38559 -q 5 -w W01` → both blocked by DRY_RUN, audited in `sl_operations` |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Finish G4 gates** | Sprint 004 code is on `main`. Still open: Actions secrets for nightly integration, `ci.yml` required on `main`, required reviewers on `prod`. This run got HTTP 403 for protection and secret names. `prod` returned no protection rules |
| **Repair nightly integration** | Red on 2026-11-09, 2026-11-10, and 2026-11-11. Latest failure is step “Install ODBC Driver 18” (exit code 2) in run 43003787661 |
| **`chore/ruff-cleanup-20261108`** | One ruff-format commit, 47 files, no pull request, not on `main` |
| SQL login `bdx_readonly` on LDSAP | script ready in `docs/sql/create_bdx_readonly.sql`. The 2026-11-07 probe used Windows integrated auth. Login presence was not re-checked |
| DEV compose on 192.168.82.33 | `deploy-dev.yml` deploys there on the self-hosted runner. Last green run 2026-11-10 07:22 CET (`cd6440f`), including `/health/live`. Git’s `.runtime/last-deploy-*` still records 2026-11-07 / `6ccc036` |
| MQTT / Kafka broker | publishers exist; documented config still has MQTT disabled and no broker |
| Run collector against PROD | 2026-11-07 single-order probe only. Needs a separate Postgres database or mode-prefixed `source_key`. No `deploy-prod` runs |
| SAP write-back real use | stays off until an operator disables the dry-run guard in the host environment. Committed files keep the guard on. Recent DEV deploys succeeded, which means the workflow’s host-env check passed |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | 2026-11-07 finding; needs MDE-side configuration. Not re-checked |
| Quoter deep link | spec is on `main` (`docs/QUOTER_DEEP_LINK.md`, #57). The Quoter UI change is outside this repo |
| Open docs-sync pull requests | Many open PRs only refresh these three documents. This run does not merge them |

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
│   │                      #   machine_state, domain_events, sl_operations)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── analytics/         # KPI engine, anomalies, flow, causes, bottleneck
│   ├── q2p/               # inquiry evaluation
│   ├── promise/           # offer engine and fulfillment agents
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI; dashboard, vorgang, analytics, q2p, promise
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008
├── tests/                 # 120 unit test functions + 8 integration tests
├── scripts/               # ci_triage, pr_review, create_pr, dora_metrics, deploy.ps1, prepare-dev-host.sh
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS (+ dora-metrics.md weekly)
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen, sync-coordinator
    ├── rules/             # bdx-conventions.mdc, dev-sync.mdc (alwaysApply)
    └── skills/dev-sync/   # sync coordinator procedure
```
