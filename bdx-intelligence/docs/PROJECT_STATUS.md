# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-08 04:35 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._
>
> Abgleich dieser Sitzung gegen `main` = `origin/main` = `6850feb` (`feat(analytics): sharpen dashboard visualization (#12)`, 2026-11-07 23:27 +0100). Ziele: `PROJECT_GOALS.md`. Anforderungen: `REQUIREMENTS.md`.

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV, last probe 2026-11-07) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV, last probe 2026-11-07) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (publishers built, no broker configured; write-back dry-run verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main` (CI green on `6850feb`; ruff/mypy advisory; coverage gate 68 %; DEV deploy of HEAD still queued) |
| — | Schwachstellen-Analyse (`/analytics`) | ✅ on `main` (#6, Darstellung #12) |
| — | KPI engine, anomaly detection, self-tuning thresholds | ⬜ not on `main` (open PR #5) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test suite: **123 test functions** (115 unit on SQLite in-memory + 8 integration against DEV SAP/SL), counted as `def test_*` in `bdx-intelligence/tests`. CI runs the unit suite with `--cov-fail-under=68` and was green on `6850feb` (Actions run 42420693051). The integration suite skips when DEV credentials are absent. This sync did not re-run pytest (pytest is not installed in the sync environment).

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
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured yet** (MQTT stays disabled) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | `publish/kafka.py`; key = `source_key` (partition affinity), JSON value; `build_all_publishers()` composes MQTT + Kafka when both are on. **No broker configured yet** |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **Dry-run verified against DEV** (no real writes). Committed files keep dry-run on; only the host environment may turn real writes on |
| Dockerfile + docker-compose.yml | ✅ on `main`, DEV deploy partial | Image build and GHCR push run in `deploy-dev.yml`. Last **successful** DEV deploy in Actions is `2f13c3f` (#6, run 42415113477). Deploy of HEAD `6850feb` built the image and is **queued** on the self-hosted runner (run 42420693125). SQL login script: `docs/sql/create_bdx_readonly.sql` (plus `reset_bdx_readonly.sql`) |

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On `main`

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main`, green on `6850feb` | push/PR to `main`: ruff and mypy are **advisory** (`continue-on-error`), pytest with `--cov-fail-under=68` (floor ~69 %, ratchet up only), Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. Actions run 42420693051 succeeded |
| **`.github/workflows/integration.yml`** | ✅ on `main`, no Actions run yet | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; the fixture forces dry-run on — no real SAP writes possible. `gh run list` showed no runs for this workflow at sync time |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main` | push to `main` → build image (`ghcr.io/<lowercase-repo>/bdx-intelligence:dev` + `:sha-<sha>`), push to GHCR, then the **self-hosted runner on the DEV host** (no SSH hop) copies `docker-compose.yml`, pulls, migrates, recreates `collector` + `api`, smoke-tests `/health/live`. **Aborts if the host env turns dry-run off.** Last success: `2f13c3f` (run 42415113477). HEAD `6850feb`: image built, deploy job still queued (run 42420693125) |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; `prod` environment with required reviewers; extra inputs `run_migrations` and `confirm_sl_write` (must be `true`); pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | ✅ on `main` | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml`. Pushes to `main` also show failed runs of this file with **zero jobs** (for example run 42421319257 on `6850feb`); CI itself stayed green |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ on `main`, no Actions run yet | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md`. No `dora-metrics.md` in the tree; `gh run list` showed no runs |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | ruff/mypy config is permissive on purpose; dev extras wired. See `AGENTS.md` for the tightening path |
| **Lint cleanup** (`.github/workflows/lint-cleanup.yml`) | ✅ on `main` | `workflow_dispatch` + Sundays 04:00 UTC: `ruff check --fix` and `ruff format`, then a trivial PR. Path to make the ruff job blocking |
| **DEV host runner** | ✅ on `main` | `scripts/prepare-dev-host.sh`, `scripts/setup-github-runner.ps1`, `scripts/set-github-secrets.ps1`, `scripts/deploy.ps1`. Deploy job `runs-on: [self-hosted, linux]` |
| **PROD migration guard** (`alembic/env.py`) | ✅ on `main` | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status on `main`

* **Landed.** Workflows, `src/bdx/agents/`, `tests/integration/`, `tests/test_agents.py`, `scripts/`, `AGENTS.md`, `.cursor/prompts/*` and `.cursor/rules/*` are on `origin/main` at `6850feb`. This sync branch started clean and equal to `main`.
* **CI** on that SHA succeeded. **DEV deploy** of that SHA has not finished: the image job succeeded and the self-hosted deploy job was still queued at 2026-11-08 04:35 (UTC+1).
* **SSH deploy secrets are no longer the DEV path.** `deploy-dev.yml` runs compose on the self-hosted runner. A successful DEV deploy already happened for `2f13c3f` and, via `workflow_dispatch`, for `232b138` (run 42414445157).
* **Still required before nightly integration and advisory review do useful work:** repo secrets `CURSOR_API_KEY` (triage + PR review; both no-op without it), `SAP_DB_*`, `SL_*`, `POSTGRES_DSN`. PROD deploy still needs the `prod` environment with required reviewers. Branch protection requiring `ci.yml` was not re-checked in this sync.
* **Not in this tree:** `docs/dora-metrics.md` (workflow has not run). `.runtime/last-deploy-sha` in git is still `1480f5c` (recorded 2026-11-07 19:55 +0100) and is older than the successful Actions deploy of `2f13c3f`.



## Schwachstellen-Analyse  ✅ On `main`

Merged after the previous status text (`1e38a68`). Not the open Sprint-005 KPI engine (PR #5).

| Feature | Status | Notes |
|---|---|---|
| `GET /api/v1/analytics/weaknesses` | ✅ | `src/bdx/api/routes/analytics.py`. One payload: overdue open orders, stuck released orders (status `R`, completion under 10 %, unchanged ≥ 3 days), plan changes (`QUANTITY_CHANGED` / `DUE_DATE_CHANGED`, 7 days), idle online machines, `MACHINE_OFFLINE` in 24 h, collector errors in 7 days, last 20 `snapshot_runs` as `run_trend` |
| Page `/analytics` | ✅ | `src/bdx/api/static/analytics.html`, linked from the app. KPI bar, tabs, machine and run charts. #12 only changed this file (sharper visualisation) |
| Tests | ✅ | `tests/test_analytics.py` — 11 test functions |
| Thresholds | fixed in code | `_STUCK_THRESHOLD_DAYS=3`, `_STUCK_COMPLETION_THRESHOLD=0.10`, `_PLAN_CHANGE_WINDOW_DAYS=7`, `_OFFLINE_WINDOW_HOURS=24`. No self-tuning. That work is PR #5 and is **not** on `main` |

## Operational status (DEV)

Shop-floor numbers below are the last recorded probe (**2026-11-07**). This sync did not log in to SAP, Postgres, or the DEV host.

### Git and Actions (checked 2026-11-08 04:35 UTC+1)

| Check | Result |
|---|---|
| `main` / `origin/main` | `6850feb` — analytics visualisation #12 |
| Commits since the previous status commit `1e38a68` | `6ccc036` runner install script, `232b138` deploy without SSH, `2f13c3f` Schwachstellen-Dashboard #6, `6850feb` visualisation #12 |
| CI on `6850feb` | ✅ success, run 42420693051 |
| Deploy to DEV on `6850feb` | 🟡 run 42420693125: image build succeeded, **deploy job queued** on `[self-hosted, linux]` |
| Last successful Deploy to DEV | ✅ `2f13c3f` (#6), run 42415113477, 2026-11-07 21:17 UTC. Also `workflow_dispatch` of `232b138`, run 42414445157 |
| `integration.yml` / `dora.yml` | no Actions runs recorded |
| Open, not on `main` | PR #5 KPI engine; PR #3 Dev-Sync agent; PR #2 older status update. Several draft docs PRs from earlier sync runs are also open and are not the git baseline |

### Last shop-floor probe (2026-11-07)

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

The probe recorded event-store schema **002**. Migration `003` (`sl_operations`) is on `main`, and later DEV deploys run `docker compose run --rm migrate`, so the host schema may be ahead of that probe. `/analytics` did not exist at probe time (merged later the same day as #6).

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Finish DEV deploy of `6850feb`** | image is in GHCR; self-hosted deploy job 42420693125 was still queued. Until it runs, DEV is at the last successful deploy (`2f13c3f`, dashboard #6) |
| **Nightly integration secrets** | `integration.yml` has never run. It needs `SAP_DB_*`, `SL_*`, `POSTGRES_DSN`. The fixture keeps dry-run on |
| **Advisory review + triage** | `CURSOR_API_KEY` if those workflows should do more than no-op. `pr-review.yml` failures on `main` pushes have zero jobs and did not fail CI |
| **Ruff / mypy still advisory** | `continue-on-error` in `ci.yml`. Cleanup path is `lint-cleanup.yml`, then remove `continue-on-error`. Coverage gate stays at 68 % until tests raise the floor |
| SQL login `bdx_readonly` on LDSAP | scripts `docs/sql/create_bdx_readonly.sql` and `reset_bdx_readonly.sql` are on `main` (`7d0fb2f` removed `DENY CONTROL`, which had blocked `CONNECT`). Whether the login exists on the server was **not** re-checked |
| MQTT / Kafka broker | publishers are in the tree; no broker is configured in committed config |
| Run collector against PROD | read-only; **needs a separate PG database** (or mode-prefixed `source_key`) so DEV and PROD rows do not mix in `order_state`. Only single-order probes are recorded |
| SAP write-back in real use | committed code and DEV deploys keep dry-run on. Real writes are an operator decision in the host environment, audited in `sl_operations` |
| Multi-company SAP, SSO/SCIM | TBD |
| KPI engine (PR #5) | open, not merged. Do not treat it as delivered |
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
│   ├── api/               # FastAPI app, routes (incl. analytics.py),
│   │                      #   static/dashboard.html, static/analytics.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001, 002, 003 (sl_operations). No 004 on main
├── tests/                 # 115 unit test functions + tests/integration/ (8)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py,
│                          #   deploy.ps1, prepare-dev-host.sh,
│                          #   set-github-secrets.ps1, setup-github-runner.ps1
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS,
                           #   PROJECT_GOALS, REQUIREMENTS
                           #   (dora-metrics.md is produced by dora.yml; not in git yet)
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc (alwaysApply)
```
