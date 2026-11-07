# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-07 20:36 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main` (`2fcd60d`–`1e38a68`). CI green at a 68 % coverage floor. DEV containers up via `deploy.ps1`. Actions SSH deploy still pending. `prod` has no required reviewers |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open. DEV container deploy is recorded (see operational status) |

Test suite: **111 tests** (103 unit on SQLite in-memory + 8 integration against DEV SAP/SL). Unit suite green; integration suite skips cleanly when DEV creds are absent.

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off until an operator turns the Service Layer guard off in the host env |
| Dockerfile + docker-compose.yml | ✅ deployed on DEV | `scripts/deploy.ps1` (Docker context `remote-prod` → 192.168.82.33). Recorded 2026-11-07 19:55 (UTC+1), sha `1480f5c`: collector + api up. App code on `main` matches that sha; later commits are the script, docs, and runtime stamps |

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ live | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest `--cov-fail-under=68` (measured floor ~69.35 % in `241b535`; ratchet up, do not lower), Docker build smoke test. Working dir = `bdx-intelligence/`. Latest `main` push `1e38a68` was green |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; the fixture keeps the Service Layer dry-run guard on — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ live, SSH job not finishing | build on `ubuntu-latest` pushes `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` and `:sha-<sha>` (path must be lowercase, `2646b0d`). Deploy job `runs-on: [self-hosted, linux]` (`1480f5c`). Run [42405166649](https://github.com/aeyhorn/Alyze/actions/runs/42405166649) for `1e38a68` is still pending. The workflow aborts when the DEV host env does not keep the dry-run guard. Working DEV path today is `scripts/deploy.ps1` |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; deploy job on a self-hosted runner; inputs `run_migrations` and `confirm_sl_write`. The `prod` environment exists and has **no protection rules** (required reviewers are not configured) |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | ✅ written | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml` |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ committed | `ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `deploy.ps1` (local Docker-context deploy onto `remote-prod`, `12fa8cf`) |
| **`.github/workflows/lint-cleanup.yml`** | ✅ committed | manual workflow: `ruff check --fix` + `ruff format`, opens a trivial PR for the legacy findings. After that lands, drop `continue-on-error` on the `lint` job |
| **`pyproject.toml` / `docker-compose.yml` tweaks** | ✅ committed | ruff/dev-extras wiring landed with `2fcd60d` |
| **PROD migration guard** (`alembic/env.py`) | ✅ committed | refuses to migrate against the PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets that only when the human checks `run_migrations` (`7d0fb2f`) |

### Sprint 004 — status & open items

* **Sprint 004 code is on `origin/main`.** Workflows, agents, scripts, integration tests, HOTL prompts, `AGENTS.md`, and `.cursor/rules/bdx-conventions.mdc` are committed (`2fcd60d` through `1e38a68`). Follow-ups on `main`: coverage floor 68 % (`241b535`), lowercase ghcr.io path (`2646b0d`), deploy jobs on a self-hosted runner (`1480f5c`), `deploy.ps1` (`12fa8cf`).
* **`TestAgent.min_coverage` is still 80 %.** The CI workflow floor is 68 %. Those two gates do not match.
* **Repo settings still open.** Secret names were not readable (API 403). Environments `dev` and `prod` exist; `prod.protection_rules` is empty. Branch protection on `main` was not readable (API 403).
* **Actions SSH deploy has not completed.** Run 42405166649 (`1e38a68`) is pending. DEV itself was deployed with `deploy.ps1` (see operational status).



## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth on the Windows host (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). The DEV container uses SQL login `bdx_readonly`; `12fa8cf` records 871 open orders from inside the container. The login script no longer denies CONTROL (`7d0fb2f`) |
| DEV containers (`deploy.ps1`) | ✅ 2026-11-07 19:55 (UTC+1), sha `1480f5c`, host 192.168.82.33: collector + api up, event store connected (38561 orders, 184 runs). Actions deploy of `1e38a68` still pending |
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
| **Self-hosted runner for Actions deploy** | Deploy-to-DEV run 42405166649 (`1e38a68`) is still pending. GitHub-hosted runners cannot reach 192.168.82.33. The host that is actually up was deployed with `scripts/deploy.ps1` |
| **`prod` reviewers and branch protection** | `prod` environment has no protection rules. Branch protection and the secret-name list were not readable (API 403). Nightly integration still needs its SAP/Postgres secrets before it can do more than skip |
| **Ratchet the CI coverage floor** | Workflow floor is 68 % (~69.35 % measured). `TestAgent.min_coverage` is still 80. Do not lower the workflow floor |
| MQTT / Kafka broker | set `MQTT_ENABLED=true`+`MQTT_HOST` or `KAFKA_ENABLED=true`+`KAFKA_BOOTSTRAP_SERVERS`; `pip install -e .[mqtt]` / `.[kafka]` |
| Run collector against PROD | read-only; needs a separate Postgres database (or a mode-prefixed `source_key`) so DEV and PROD rows do not mix in `order_state`. Only single-order probes so far |
| SAP write-back for real use | stays off until an operator changes the Service Layer guard in the host env. `deploy.ps1` and `deploy-dev.yml` refuse a DEV deploy when that guard is off. Committed files do not turn the guard off |
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
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI app, routes, static/dashboard.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001, 002, 003 (sl_operations)
├── tests/                 # 103 unit tests + tests/integration/ (8 DEV SAP/SL tests)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py, deploy.ps1
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc (alwaysApply)
```

## Git-Stand (abgeglichen 2026-11-07 20:36 UTC+1)

`origin/main` is `1e38a68`. This reconciliation only touches the three docs below; it does not merge anything.

| Remote branch | Ahead of `main` | What it is |
|---|---|---|
| `cursor/update-project-status-05e2` | PR [#2](https://github.com/aeyhorn/Alyze/pull/2) | Older `PROJECT_STATUS` refresh. Stops at `1480f5c` and still treats the SQL login and the compose deploy as open. Superseded by this file |
| `cursor/dev-sync-agent-e2dc` | PR [#3](https://github.com/aeyhorn/Alyze/pull/3) | Dev-sync rule, skill, and prompt, plus `DocumentationAgent.required_docs`. Also edits product code (`docs.py`, `tests/test_agents.py`). Not merged. This run does not take that code change |
| `cursor/bdx-intelligence-sprint-001-2e0e` | leftover from merged PR [#1](https://github.com/aeyhorn/Alyze/pull/1) | Pre-squash commits `574c4eb` and `a479b94`. No new work |

`PROJECT_GOALS.md` and `REQUIREMENTS.md` were missing on `main`. They are added here. `REQUIREMENTS.md` has no rows; the next id is `R001`.
