# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-09 13:36 (CET, UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `origin/main`. Ruff and mypy are advisory; CI coverage gate is 68 %. DEV deploy runs on a self-hosted runner. Environment `prod` lists no protection rules. Actions secrets and branch protection were not readable in this sync (HTTP 403). |
| 005 | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged – needs migration + Q2P SAP grants + optional Quoter on DEV |
| Analytics | KPI engine, anomalies, diagnosis, weakness dashboard | ✅ merged (#5, #6, #12). Migrations `005`+`006`. UI `/analytics`. The commits call this Sprint 005 as well; Q2P above is a separate body of work (migration `004`). |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41) – deploy migrations `007`+`008`; vision: `docs/VISION_PROMISE_PLATFORM.md`. Quoter deep link is specified (#57), not implemented in BDX or the Quoter UI. |
| TBD | Multi-company SAP, SSO/SCIM, container deployment | ⬜ open (SQL login script ready) |

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
| Kafka publisher | ✅ | `publish/kafka.py` (confluent-kafka, optional `.[kafka]`); `build_all_publishers()` composes MQTT + Kafka |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh. Header nav on Betrieb, Schwachstellen, Q2P, and Promise stays visible (#62). |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay an operator switch in the host env; committed files keep the dry-run default. |
| Dockerfile + docker-compose.yml | ✅ on `origin/main` | `deploy-dev.yml` targets the self-hosted runner on 192.168.82.33. Whether the stack is up was not re-checked after the 2026-11-07 snapshot. SQL login script: `docs/sql/create_bdx_readonly.sql`. |

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

## Analytics – KPI, diagnosis, weakness dashboard  ✅ Merged (#5, #6, #12)

**Goal**: Compute shop-floor KPIs, flag anomalies, explain lateness, and show weaknesses on `/analytics`.

| Feature | Status | Notes |
|---|---|---|
| KPI snapshots, trends, anomalies, thresholds | ✅ on `origin/main` | `bdx.analytics`, Alembic `005`, `GET /api/v1/analytics/kpis`, `/trends`, `/anomalies`, `/thresholds` |
| Procurement and inventory KPIs | ✅ on `origin/main` | `kpis_procurement.py` (stock, purchase orders, goods receipts) |
| Diagnosis: flow, causes, bottleneck | ✅ on `origin/main` | Alembic `006`; `/flow`, `/causes`, `/bottleneck` |
| Weakness dashboard | ✅ on `origin/main` | `/analytics` and `/api/v1/analytics/weaknesses`; header link „Schwachstellen“ (#62) |
| On-demand cycle | ✅ on `origin/main` | `POST /api/v1/analytics/run` |

**Deploy notes**: `alembic upgrade head` includes `005` and `006`. The 2026-11-07 DEV snapshot was still on schema `002`; this sync did not re-check the host.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On origin/main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `origin/main` | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest coverage gate is 68 % (ratchet; do not lower), Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. `bdx-collect check` still defaults its coverage gate to 80 %. |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `origin/main` | push to `main` builds `ghcr.io/<lowercase-repo>/bdx-intelligence:dev` and `:sha-<sha>` on a GitHub-hosted runner, then deploys on the self-hosted runner on the DEV host (no SSH hop): `docker compose pull`, migrations, recreate `collector` + `api`, smoke `/health/live`. The job aborts if the host `.env` would allow real Service Layer writes. |
| **`.github/workflows/deploy-prod.yml`** | ✅ on `origin/main` | `workflow_dispatch` only; job environment `prod`; self-hosted runner, then SSH to the PROD host. `confirm_sl_write` must be `true` or the approval job exits. Migrations only when `run_migrations` is set. The workflow text asks for required reviewers; the environments API currently lists no protection rules on `prod`. |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | ✅ written | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml` |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ on `origin/main` | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **`.github/workflows/lint-cleanup.yml`** | ✅ on `origin/main` | `workflow_dispatch` and Sundays 04:00 UTC: `ruff check --fix` + `ruff format`, then a trivial PR. Path to make the ruff job blocking. |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `origin/main` | committed with the Sprint 004 tree |
| **PROD migration guard** (`alembic/env.py`) | ✅ on `origin/main` | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when `run_migrations` is checked |

### Sprint 004 — status & open items

* The Sprint 004 tree is on `origin/main` at `bbdfc8f` (2026-11-09). This sync
  started from a clean worktree that matches `origin/main`. Nothing in that
  tree is uncommitted, and local `main` is not ahead of `origin/main`.
  DEV deploy no longer needs `DEV_SSH_*` (the runner is on the DEV host).
  PROD deploy still expects `PROD_SSH_*`. Nightly integration still expects
  `SAP_DB_*`, `SL_*`, and `POSTGRES_DSN`. Triage and PR review still expect
  `CURSOR_API_KEY`. This sync could not list Actions secrets or branch
  protection (HTTP 403).
* GitHub environments `dev`, `prod`, and `CURSOR_API_KEY` exist. `prod` has
  no protection rules, so required reviewers are not configured there.
  Branch protection on `main` was not readable.
* Git: 54 open PRs. One is non-draft, [#2](https://github.com/aeyhorn/Alyze/pull/2)
  (`cursor/update-project-status-05e2`, Sprint 004 status only, behind later
  `main` work). The other 53 are draft reconcile PRs. This run does not merge
  them. `origin/chore/ruff-cleanup-20261108` has one lint-format commit, no
  open PR, and is behind current `main`.
* Still open for goal G4: confirm Actions secrets, required reviewers on
  `prod`, and branch protection that requires the `ci.yml` checks.



## Operational status (DEV, verified 2026-11-07)

This coordinator run did not re-probe DEV, PROD, or LDSAP. The table below is that snapshot. The repo now contains Alembic revisions `001` through `008`.

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
| **G4 acceptance** | Sprint 004 code is on `origin/main`. Actions secrets and branch protection were not readable (HTTP 403). Environment `prod` exists and lists no protection rules. DEV deploy no longer needs `DEV_SSH_*`. PROD still expects `PROD_SSH_*`. Nightly integration still expects `SAP_DB_*`, `SL_*`, `POSTGRES_DSN`. Triage and PR review still expect `CURSOR_API_KEY`. |
| Apply migrations `004`–`008` on the DEV event store | 2026-11-07 snapshot was schema `002`. Repo head is `008` (Q2P, analytics, diagnosis, promise, quoter fields). Not re-checked this sync. |
| SQL login `bdx_readonly` on LDSAP | Script on `main` grants SELECT and does not `DENY CONTROL` (that denial blocked CONNECT, `7d0fb2f`). The 2026-11-07 check recorded the login as missing. This sync did not re-check LDSAP. |
| Deploy `docker-compose.yml` on 192.168.82.33 | `deploy-dev.yml` is on `main` and expects the self-hosted runner. Stack health was not re-checked after 2026-11-07. Container SQL auth still depends on the login above. |
| MQTT / Kafka broker | set `MQTT_ENABLED=true`+`MQTT_HOST` or `KAFKA_ENABLED=true`+`KAFKA_BOOTSTRAP_SERVERS`; `pip install -e .[mqtt]` / `.[kafka]` |
| Run collector against PROD | read-only; but **needs a separate PG database** (or mode-prefixed `source_key`) to avoid mixing DEV/PROD data in `order_state`. Currently only single-order probes done |
| SAP write-back real use | Real writes stay an operator decision in the host env. Committed files keep the dry-run default. The 2026-11-07 DEV check saw the guarded calls blocked and audited. This sync did not read the host env. |
| Quoter deep link | Spec is on `main` (`docs/QUOTER_DEEP_LINK.md`, #57). Quoter UI and the BDX return path are not in this repo yet. |
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
│   │                      #   machine_state, domain_events, sl_operations)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry), quoter.py
│   ├── analytics/         # KPIs, anomalies, diagnosis, procurement KPIs
│   ├── q2p/               # inquiry evaluation
│   ├── promise/           # offer engine, fulfillment agents
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI; routes; static dashboard, analytics, q2p, promise, portal
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008
├── tests/                 # unit tests on SQLite + tests/integration/ (8 DEV SAP/SL tests)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py,
│                          #   deploy.ps1, prepare-dev-host.sh, runner setup scripts
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
