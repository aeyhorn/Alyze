# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-09 08:32 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._
>
> **Git-Stand dieser Fassung:** `main` `723f794` (2026-11-08, „docs: Promise Platform vision… (#40)“). Abgleich 2026-11-09 08:32 (UTC+1): `origin/main` unverändert, Arbeitsbaum sauber, keine Commits vor `origin/main`. Einziger Produktzweig mit Inhalt außerhalb von `main`: `chore/ruff-cleanup-20261108` (`57411b2`, kein PR). Abgleich nur gegen den Repository-Inhalt. Der DEV-Lauf vom 2026-11-07 wurde nicht wiederholt.

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main`. Ruff and mypy are advisory (`continue-on-error`). Pytest coverage floor is 68 % (`241b535`) |
| 005 | KPI engine, anomaly detection, self-tuning thresholds, diagnosis / weakness dashboard | ✅ merged (#5, #6, #12) – migrations `005` and `006` |
| Q2P | Quote-to-Promise cockpit + bdx-quoter pricing domain | ✅ merged (#33, #39) – migrations `004` and `008`; Q2P SAP grants and optional Quoter still operator steps |
| Promise | Promise Platform (Offer/Gaps/Agents/token portal) | ✅ code merged (#41); vision #40. Phase A–C objects are in git. Standalone portal auth (Phase D) and autonomous ordering (Phase E) are not |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open. SQL login script and `docker-compose.yml` exist; no SSO/SCIM code |

Test suite: unit tests on SQLite in-memory + optional integration against DEV SAP/SL. Integration suite skips cleanly when DEV creds are absent.

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
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off unless an operator enables them outside the repository |
| Dockerfile + docker-compose.yml | ✅ written, ⬜ **not deployed** | needs SQL login `bdx_readonly` (script in `docs/sql/create_bdx_readonly.sql`) |

## Sprint 005 – Analytics, diagnosis, weakness dashboard  ✅ Merged

**Goal**: KPI engine over the event store, anomaly detection with self-tuning
thresholds, and a shop-floor weakness view. Git calls this Sprint 005
(`283ee4b`, #5). The diagnosis layer is migration `006` (`2f13c3f`, #6;
dashboard sharpening #12).

| Feature | Status | Notes |
|---|---|---|
| Alembic `005` analytics tables | ✅ | KPI snapshots, anomalies, thresholds, machine-state history, shift calendar |
| Alembic `006` diagnosis tables | ✅ | measurement quality, flow segments, lateness causes, bottleneck rank |
| `AnalyticsCollector` | ✅ | KPI cycle default 600 s; threshold tune default 24 h (`bdx.analytics.collector`) |
| Order and machine KPIs | ✅ | cycle time, OTD, backlog, rejection/completion, utilization, setup, MTBF/MTTR, queue, override |
| Anomaly detection + threshold tuning | ✅ | `analytics/anomalies.py`, `analytics/thresholds.py` |
| REST `/api/v1/analytics/*` | ✅ | kpis, trends, anomalies, thresholds, quality, flow, causes, bottleneck, weaknesses, `POST /run` |
| UI `/analytics` | ✅ | `static/analytics.html` |
| Procurement KPIs | ✅ | `analytics/kpis_procurement.py` (in tree with #5) |

Exit criteria such as “thresholds trusted on DEV” are not evidenced by git. This sync did not run the analytics cycle.

## Quote-to-Promise Cockpit  ✅ Merged (#33, #39)

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

## Promise Platform  ✅ Code merged (#41); vision phases not all met

**Goal**: Living Offer as system of record; Gaps instead of e-mail chains; fulfillment agents
(quote/purchase/capacity/contract); internal `/promise` cockpit + customer `/portal/{token}`.

| Feature | Status | Notes |
|---|---|---|
| Domain + Alembic `007` (offers/gaps/evidence/jobs/contracts) | ✅ | |
| Offer Engine (create / recompute / decide / resolve / publish) | ✅ | `bdx.promise.engine` |
| Agents: quote, purchase, capacity, contract | ✅ | quote delegates pricing to `evaluate_promise` + quoter; purchase and capacity propose; contract drafts a body |
| API `/api/v1/promise/*` + `/api/v1/portal/{token}` | ✅ | portal is token-scoped, no API key; accept and reject exist |
| UI `/promise` + `/portal/{token}` | ✅ | |
| Vision doc | ✅ | `docs/VISION_PROMISE_PLATFORM.md` (#40) |

**Git vs vision:** `VISION_PROMISE_PLATFORM.md` §8 still names “Offer + Gap as first-class tables” as the next build step. That step is the code in #41 (same evening, four minutes earlier). Phase A–C objects are in the tree. Phase D in the vision is a separate portal (own auth, branding, domain); git has a token projection on the same app. Phase E (ordering and slot binding inside policy limits) is not implemented. Exit criteria (sales uses only the file, mail-free gap closure, pilot customer) are not evidenced by git.

**Deploy notes**: `alembic upgrade head` (head is `008`); open `/promise`; publish contract then share portal link. Whether DEV has applied `007`/`008` was not checked in this sync.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On `main`

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff (lint + format check) and mypy on `src/bdx` are advisory (`continue-on-error`, `48afa46`); pytest `--cov-fail-under=68` (`241b535`, do not lower); Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/` |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main` | push to `main` → build image (`ghcr.io/<lowercase-repo>/bdx-intelligence`, `2646b0d`) tagged `dev` and `sha-<sha>`, push to GHCR. Deploy job runs on the self-hosted runner on the DEV host (`232b138`, no SSH hop): pull, migrations, recreate `collector` + `api`, smoke `/health/live`. The job aborts if the host environment would allow real Service Layer writes |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; `prod` environment with required reviewers; extra inputs `run_migrations` and `confirm_sl_write` (must be `true`); pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | ✅ written | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml` |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **`.github/workflows/lint-cleanup.yml`** | ✅ on `main` | `workflow_dispatch` and Sundays 04:00 UTC. In `bdx-intelligence/` it runs `ruff check --fix` and `ruff format`, then opens a trivial PR on `chore/ruff-cleanup-<date>` when the tree changes |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | image name is configurable (`2fcd60d`); the earlier “uncommitted tweaks” note does not match `723f794` |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status against git (`723f794`)

* Workflows, `src/bdx/agents/`, `bdx-intelligence/scripts/`, `tests/integration/`,
  `AGENTS.md`, `.cursor/prompts/` and `.cursor/rules/` are on `main`. This sync
  saw a clean tree at the same commit as `origin/main`.
* CI coverage floor is 68 %. The local `bdx-collect check` agent still defaults
  its own gate to 80 % (`agents/runner.py`, `agents/tests.py`).
* DEV deploy uses a self-hosted runner (`scripts/prepare-dev-host.sh`) plus an
  optional `scripts/deploy.ps1` Docker-context path. Git does not show whether
  the runner, `prod` environment, or branch protection are configured.
* Nightly integration still expects `SAP_DB_*`, `SL_*`, and `POSTGRES_DSN`.
  Triage and PR-review workflows still no-op without `CURSOR_API_KEY`. SSH
  deploy secrets are no longer the path in `deploy-dev.yml`.
* `lint-cleanup.yml` is on `main`. Branch `chore/ruff-cleanup-20261108` is one
  commit ahead (`57411b2`, ruff --fix and format, 2026-11-08). It has no open
  pull request and is not in `723f794`.



## Operational status (DEV, verified 2026-11-07)

This table is the last recorded probe. This sync did not re-run it. Alembic head in git is `008`; the probe below reported schema `002`.

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
| **Apply migrations through `008` on DEV** | git head is `008` (q2p quoter fields). The 2026-11-07 probe reported schema `002`. Not re-checked here |
| **Q2P grants + optional Quoter** | `docs/sql/grant_q2p_readonly.sql`; `QUOTER_*` documented in `docs/Q2P_QUOTER.md`. Not evidenced as applied |
| **Raise coverage from 68 %** | CI floor fixed in `241b535` with an explicit “do not lower” note. `bdx-collect check` still gates at 80 % |
| **Make ruff and mypy blocking** | both jobs are `continue-on-error` (`48afa46`). `AGENTS.md` describes the ratchet. `lint-cleanup.yml` is the intended cleanup path; `chore/ruff-cleanup-20261108` (`57411b2`) is still unmerged and has no PR |
| **Repo settings outside git** | `CURSOR_API_KEY` for triage/review, integration secrets, `prod` environment with reviewers, branch protection. Not visible in the tree. DEV deploy no longer uses `DEV_SSH_*` |
| SQL login `bdx_readonly` on LDSAP | script ready in `docs/sql/create_bdx_readonly.sql` (`7d0fb2f` removed a DENY that blocked CONNECT). Whether the login exists was not re-checked |
| Deploy compose on the DEV host | `deploy-dev.yml` targets a self-hosted runner; actual rollout is not in git |
| MQTT / Kafka broker | publishers exist; status doc still records no broker (`MQTT_ENABLED` left off at the last probe) |
| Run collector against PROD | read-only; needs a separate PG database (or mode-prefixed `source_key`) so DEV and PROD rows do not share `order_state`. Only single-order probes are recorded |
| SAP write-back for real use | operations exist and were DRY_RUN-verified on 2026-11-07. Keep real writes disabled until an operator turns them on outside the repository |
| Promise Phase D and E | token portal is in git; separate customer auth and autonomous purchase/capacity binding are only in the vision |
| Multi-company SAP, SSO/SCIM | no code on `main` |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration (finding from 2026-11-07) |

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
│   ├── db/                # SAP/PG engines + parameterised SAP queries (incl. Q2P reads)
│   ├── models/            # Work orders, events, machines, analytics ORM
│   ├── collector/         # polling, snapshots, change_detector, machines
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA), quoter.py
│   ├── analytics/         # Sprint 005 KPIs, anomalies, thresholds, diagnosis helpers
│   ├── q2p/               # inquiry store + parallel promise evaluation
│   ├── promise/           # Offer engine, models, fulfillment agents
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI; static dashboard, analytics, q2p, promise, portal
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008 (head `008`)
├── tests/                 # 189 test_* functions, including tests/integration/
├── scripts/               # ci_triage, pr_review, create_pr, dora_metrics, deploy.ps1, prepare-dev-host.sh
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, Q2P_QUOTER,
                           #   VISION_PROMISE_PLATFORM, PROJECT_GOALS, REQUIREMENTS
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc (alwaysApply)
```
