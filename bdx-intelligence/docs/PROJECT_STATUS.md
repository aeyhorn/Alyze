# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-07 22:40 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._
> Git-Abgleich gegen `origin/main` `2f13c3f` (2026-11-07 21:17 UTC). Ziele: `docs/PROJECT_GOALS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main` (ruff/mypy advisory, coverage gate 68 %) |
| — | Schwachstellen-Analyse (`/analytics`, PR #6) | ✅ on `main` (`2f13c3f`) |
| 005 | KPI engine, anomaly detection, self-tuning thresholds | 🟡 open PR #5, not on `main` |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test suite on `main`: **120 tests** (112 unit on SQLite in-memory, including one parametrized case, + 8 integration against DEV SAP/SL). Counted from `def test_` in `bdx-intelligence/tests` (fixtures named `test_*` excluded). CI run [42415113307](https://github.com/aeyhorn/Alyze/actions/runs/42415113307) for `2f13c3f` succeeded. Integration suite skips when DEV creds are absent.

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Gap: `ServiceLayerSettings.dry_run` defaults to off, and `.env.example` does the same. `deploy.ps1` and `deploy-dev.yml` still refuse a DEV deploy unless the host env keeps dry-run enabled. This sync does not change that code. |
| Dockerfile + docker-compose.yml | ✅ written, ⬜ **not deployed** | needs SQL login `bdx_readonly` (script in `docs/sql/create_bdx_readonly.sql`) |

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff and mypy are **advisory** (`continue-on-error`), pytest `--cov-fail-under=68` (floor ~69 %, ratchet up only), Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. Header comment still says 80 %; the job does not. |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main` | push to `main`: build `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` + `:sha-<sha>` (repo name lowercased), push to GHCR. Deploy job runs **on the self-hosted runner on the DEV host** (`runs-on: [self-hosted, linux]`, `environment: dev`, path `/home/docadm/bdx-intelligence`) — no SSH hop and no `DEV_SSH_*` secrets (`232b138`). Refreshes `docker-compose.yml` from the repo, keeps the host `.env` in place, `docker compose pull`, migrate, recreate `collector` + `api`, smoke `/health/live`. Aborts when the host env disables dry-run. `bdx-collect diagnose` does not fail the job. |
| **`.github/workflows/deploy-prod.yml`** | ✅ on `main` | `workflow_dispatch` only; uses the `prod` environment; inputs `run_migrations` and `confirm_sl_write`. This sync could not read whether required reviewers are configured (branch-protection API 403; environment protection rules came back empty). |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 on `main`, failing to start | Declared for PR open/sync/reopen. The push of `2f13c3f` recorded run [42415112307](https://github.com/aeyhorn/Alyze/actions/runs/42415112307) as **failure in 0s with no jobs**. The "Fetch PR diff" step has two `env:` keys. Advisory only when it runs. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ on `main` | `ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `deploy.ps1` (Docker context `remote-prod`), `prepare-dev-host.sh` (Linux runner on the DEV host), `setup-github-runner.ps1`, `set-github-secrets.ps1` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | committed with the Sprint 002–004 tree; not a dirty worktree |
| **PROD migration guard** (`alembic/env.py`) | ✅ on `main` | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |
| **`.github/workflows/lint-cleanup.yml`** | ✅ on `main` | manual ruff auto-fix PR; ruff stays advisory until that lands |

### Sprint 004 — status & open items

* **Landed on `origin/main`.** Workflows, agents, prompts, and scripts are in the tree at `2f13c3f`. This sync's worktree matches that commit; nothing in those paths is untracked.
* **DEV deploy no longer uses SSH secrets.** `set-github-secrets.ps1` still writes `DEV_SSH_HOST/USER/KEY/DEPLOY_PATH`, which `deploy-dev.yml` does not read after `232b138`.
* **GitHub environments** `dev`, `prod`, and `CURSOR_API_KEY` exist. This token cannot read branch protection (HTTP 403). Do not treat empty protection-rule payloads as proof that reviewers are set.
* **Nightly integration** still needs `SAP_DB_*`, `SL_*`, and `POSTGRES_DSN` as repo secrets before that workflow can do more than skip.



## Schwachstellen-Analyse  ✅ On main (PR #6)

Landed in `2f13c3f`. Not part of Sprint 005 (that PR is still open).

| Feature | Status | Notes |
|---|---|---|
| `GET /api/v1/analytics/weaknesses` | ✅ | overdue orders, stuck released orders (<10 % done, unchanged ≥ 3 days), plan changes (7 days), idle machines, `MACHINE_OFFLINE` (24 h), collector errors (7 days), last 20 runs |
| `GET /analytics` | ✅ | `src/bdx/api/static/analytics.html`, auto-refresh 30 s |
| Tests | ✅ | 9 tests in `tests/test_analytics.py` |
| CI + DEV deploy for this commit | ✅ | CI [42415113307](https://github.com/aeyhorn/Alyze/actions/runs/42415113307), Deploy to DEV [42415113477](https://github.com/aeyhorn/Alyze/actions/runs/42415113477) |

The committed marker `bdx-intelligence/.runtime/last-deploy-sha` is still `1480f5c` (2026-11-07 19:55 +01). The successful deploy run did not update that file. This sync did not probe the host again.

## Operational status (DEV, last manual check 2026-11-07)

These rows are the last hands-on check recorded in this file. This sync did not re-run `bdx-collect`.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth on the workstation (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Superseded for the container by `12fa8cf`: `bdx_readonly` read 871 open orders from inside the DEV container. Not re-checked in this sync. |
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
| **Sprint 005 (PR #5)** | `cursor/sprint-005-analytics-kpi-engine-1e2b` is open, not merged. KPI engine, anomalies, migration `004`. Do not describe it as landed. |
| **Fix `pr-review.yml` startup** | push of `2f13c3f` failed the workflow in 0s with no jobs; duplicate `env:` on the diff step |
| **Branch protection** | not readable with this token. `ci.yml` is the intended required check; confirm in repo settings. |
| **Ruff / mypy / coverage ratchet** | both linters advisory; coverage gate is 68 %, not 80 %. `AGENTS.md` still tells operators to pass `--cov-fail-under=80`. |
| SQL login `bdx_readonly` on LDSAP | `docs/sql/create_bdx_readonly.sql` no longer denies CONTROL (`7d0fb2f`). `12fa8cf` records that the login worked from the DEV container (871 open orders). PROD company DB was not shown. Not re-checked this sync. |
| DEV compose on 192.168.82.33 | `12fa8cf` records collector + api up at sha `1480f5c` (2026-11-07 19:55 +0100). Actions deploy [42415113477](https://github.com/aeyhorn/Alyze/actions/runs/42415113477) for `2f13c3f` is `success` (`/health/live`). The committed marker is still `1480f5c`. Host env was not opened in this sync. |
| MQTT / Kafka broker | publishers exist; `MQTT_ENABLED=false`; no broker recorded |
| Run collector against PROD | read-only; needs a separate Postgres database or a mode-prefixed `source_key`. Only single-order probes at the last manual check. |
| SAP write-back guard | `ServiceLayerSettings.dry_run` defaults to off, and `.env.example` matches that. DEV deploy scripts refuse to roll out unless the host env keeps dry-run enabled. Code was not changed in this sync. |
| Multi-company SAP, SSO/SCIM | TBD (goal G9) |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |
| **Dev-sync skill** | `.cursor/skills/dev-sync/SKILL.md` is not on `main`. It lives on open PR #3. |

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
│   ├── api/               # FastAPI app, routes (incl. analytics), static/dashboard.html, analytics.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001, 002, 003 (sl_operations). 004 is only on PR #5
├── tests/                 # 112 unit + tests/integration/ (8 DEV SAP/SL tests)
├── scripts/               # ci_triage, pr_review, create_pr, dora_metrics, deploy.ps1,
│                          #   prepare-dev-host.sh, setup-github-runner.ps1, set-github-secrets.ps1
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

## Git snapshot (this sync)

`HEAD` and `origin/main`: `2f13c3f` feat: Schwachstellen-Analyse Dashboard (#6).

Remote branches not contained in `origin/main` (product or agent work, not the draft doc-sync branches):

| Branch | PR | On main? |
|---|---|---|
| `cursor/sprint-005-analytics-kpi-engine-1e2b` | #5 open | no |
| `cursor/dev-sync-agent-e2dc` | #3 open | no |
| `cursor/update-project-status-05e2` | #2 open | no |

Draft doc-sync PRs #4, #7, #8, #9, #10 are also unmerged. They are not the source of truth; this file is reconciled to `main` directly.
