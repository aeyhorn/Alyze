# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-09 00:32 (CET)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._
> Git-Abgleich gegen `origin/main` `723f794` (2026-11-08 21:08 +0100), `docs: Promise Platform vision toward portal, purchasing agents, contracts (#40)`. Parent `1ce5fdf` ist `feat(promise): Alyze Promise Platform engine, agents, API, portal (#41)`. Ziele: `docs/PROJECT_GOALS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main` (ruff/mypy advisory, coverage gate 68 %) |
| — | Schwachstellen-Analyse (`/analytics`, PR #6) plus Darstellung (PR #12) | ✅ on `main` (`6850feb`) |
| — | Quote-to-Promise cockpit (PR #33, `2796032`) plus bdx-quoter pricing (PR #39, `0de31a7`) | ✅ code on `main`. DEV deploy of `1ce5fdf` applied the quoter columns as Alembic `008`. No goal id |
| 005 | KPI engine, anomaly detection, self-tuning thresholds, procurement KPIs, diagnosis | ✅ on `main` (`283ee4b`, PR #5). DEV has `005_analytics_tables` and `006_diagnosis_tables`. Revision `005` is unique again. No goal id |
| — | Promise Platform (PR #41, `1ce5fdf`) plus vision (PR #40, `723f794`) | ✅ on `main`. DEV deploy applied Alembic `007` and `008`. No goal id |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test suite on `main`: **185 test functions** (177 unit on SQLite in-memory + 8 integration against DEV SAP/SL). Counted from `def test_` in `bdx-intelligence/tests` (189 matches; 4 fixtures named `test_engine` / `test_session_factory` excluded). `1ce5fdf` adds 5 tests in `tests/test_promise.py`. `723f794` adds none. CI [42518204806](https://github.com/aeyhorn/Alyze/actions/runs/42518204806) on `1ce5fdf` succeeded. CI [42518587593](https://github.com/aeyhorn/Alyze/actions/runs/42518587593) on `723f794` succeeded. Deploy to DEV [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) for `1ce5fdf` succeeded and logged Alembic `006 -> 007` and `007 -> 008`, then `/health/live`. Deploy to DEV [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) for `723f794` succeeded; migrate found nothing further to apply. `pr-review.yml` runs [42518203439](https://github.com/aeyhorn/Alyze/actions/runs/42518203439) and [42518586380](https://github.com/aeyhorn/Alyze/actions/runs/42518586380) failed in 0s with no jobs. The same 0s failure happened on the docs-branch push of open PR #44 ([42519013954](https://github.com/aeyhorn/Alyze/actions/runs/42519013954), 21:13 CET), of open PR #45 ([42520953516](https://github.com/aeyhorn/Alyze/actions/runs/42520953516), 21:36 CET), and of open PR #46 ([42525833457](https://github.com/aeyhorn/Alyze/actions/runs/42525833457), 22:33 CET). CI for those docs PRs succeeded ([42519027712](https://github.com/aeyhorn/Alyze/actions/runs/42519027712), [42520964589](https://github.com/aeyhorn/Alyze/actions/runs/42520964589), [42525846129](https://github.com/aeyhorn/Alyze/actions/runs/42525846129)). Auto-merge on PR #46 ([42525846092](https://github.com/aeyhorn/Alyze/actions/runs/42525846092)) exited 0 and skipped the merge because the label `trivial` is absent. This sync did not re-run pytest. Integration suite skips when DEV creds are absent. `origin/main` is still `723f794` at 00:32 CET on 2026-11-09. The docs-branch push of open PR #47 failed `pr-review.yml` in 0s with no jobs ([42530945036](https://github.com/aeyhorn/Alyze/actions/runs/42530945036), 23:34 CET). CI for that PR succeeded ([42530960050](https://github.com/aeyhorn/Alyze/actions/runs/42530960050)). Auto-merge ([42530960057](https://github.com/aeyhorn/Alyze/actions/runs/42530960057)) exited 0 and skipped the merge because the label `trivial` is absent. The `def test_` count was rechecked on this tree: still 189 matches, 185 functions (177 unit + 8 integration).

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
| Dockerfile + docker-compose.yml | ✅ on DEV | SQL login `bdx_readonly` recorded working from the DEV container (`12fa8cf`). Actions deploys for `2f13c3f`, `6850feb`, `6710fdc` and `2796032` succeeded. The `2796032` host job applied Alembic `003 -> 004`. Deploy [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) for `283ee4b` succeeded at 17:21 (CET) and logged Alembic `004 -> 005` and `005 -> 006`, then `/health/live`. Deploy [42516285446](https://github.com/aeyhorn/Alyze/actions/runs/42516285446) for `0de31a7` pushed the image and stopped in migrate (revision `005` present more than once). Containers were not recreated. Deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) for `1ce5fdf` succeeded and logged Alembic `006 -> 007` and `007 -> 008`, then `/health/live`. Deploy [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) for `723f794` succeeded with no further upgrade. The committed marker file remains `1480f5c`. |

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
| **`.github/workflows/integration.yml`** | ✅ on `main`, last run failed before pytest | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible. Run [42469243262](https://github.com/aeyhorn/Alyze/actions/runs/42469243262) (2026-11-08 09:55 UTC, `6710fdc`) failed in the ODBC install: `gpg --dearmor` exited 2 (`can't open '/dev/tty'`). Pytest did not start. |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main` | push to `main`: build `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` + `:sha-<sha>` (repo name lowercased), push to GHCR. Deploy job runs **on the self-hosted runner on the DEV host** (`runs-on: [self-hosted, linux]`, `environment: dev`, path `/home/docadm/bdx-intelligence`) — no SSH hop and no `DEV_SSH_*` secrets (`232b138`). Refreshes `docker-compose.yml` from the repo, keeps the host `.env` in place, `docker compose pull`, migrate, recreate `collector` + `api`, smoke `/health/live`. Aborts when the host env disables dry-run. `bdx-collect diagnose` does not fail the job. |
| **`.github/workflows/deploy-prod.yml`** | ✅ on `main` | `workflow_dispatch` only; uses the `prod` environment; inputs `run_migrations` and `confirm_sl_write`. This sync could not read whether required reviewers are configured (branch-protection API 403; environment protection rules came back empty). |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 on `main`, failing to start | Declared for PR open/sync/reopen. Push of `0de31a7` recorded run [42516284484](https://github.com/aeyhorn/Alyze/actions/runs/42516284484) as **failure in 0s with no jobs**, same as [42518586380](https://github.com/aeyhorn/Alyze/actions/runs/42518586380) for `723f794`, [42518203439](https://github.com/aeyhorn/Alyze/actions/runs/42518203439) for `1ce5fdf`, [42519013954](https://github.com/aeyhorn/Alyze/actions/runs/42519013954) for the docs branch of PR #44, [42499221888](https://github.com/aeyhorn/Alyze/actions/runs/42499221888) for `283ee4b`, [42498523815](https://github.com/aeyhorn/Alyze/actions/runs/42498523815) for `2796032`, [42464603622](https://github.com/aeyhorn/Alyze/actions/runs/42464603622) for `6710fdc`, [42420692054](https://github.com/aeyhorn/Alyze/actions/runs/42420692054) for `6850feb` and [42415112307](https://github.com/aeyhorn/Alyze/actions/runs/42415112307) for `2f13c3f`. The "Fetch PR diff" step has two `env:` keys. The docs-branch push of open PR #45 failed the same way ([42520953516](https://github.com/aeyhorn/Alyze/actions/runs/42520953516), 21:36 CET), and so did open PR #46 ([42525833457](https://github.com/aeyhorn/Alyze/actions/runs/42525833457), 22:33 CET) and open PR #47 ([42530945036](https://github.com/aeyhorn/Alyze/actions/runs/42530945036), 23:34 CET). Advisory only when it runs. This sync does not change the workflow. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ on `main`, no Actions run yet | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md`. `gh run list` showed no runs |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ on `main` | `ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `deploy.ps1` (Docker context `remote-prod`), `prepare-dev-host.sh` (Linux runner on the DEV host), `setup-github-runner.ps1`, `set-github-secrets.ps1` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | committed with the Sprint 002–004 tree; not a dirty worktree |
| **PROD migration guard** (`alembic/env.py`) | ✅ on `main` | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |
| **`.github/workflows/lint-cleanup.yml`** | 🟡 ran, no PR | `workflow_dispatch` + Sundays 04:00 UTC: `ruff check --fix` and `ruff format`, then a trivial PR. Run [42473962358](https://github.com/aeyhorn/Alyze/actions/runs/42473962358) (2026-11-08 11:02 UTC) pushed `chore/ruff-cleanup-20261108` (`57411b2`, 47 files) and then failed: `could not add label: 'trivial' not found`. No pull request exists for that branch. Ruff stays advisory. This sync does not create the label. |

### Sprint 004 — status & open items

* **Landed on `origin/main`.** Workflows, agents, prompts, and scripts are in the tree at `723f794`. Nothing in those paths is untracked. CI for `1ce5fdf` and `723f794` succeeded. The DEV deploy of `723f794` succeeded. The earlier failure on `0de31a7` was the duplicate Alembic revision, which `1ce5fdf` removed by renaming the quoter migration to `008`.
* **DEV deploy no longer uses SSH secrets.** `set-github-secrets.ps1` still writes `DEV_SSH_HOST/USER/KEY/DEPLOY_PATH`, which `deploy-dev.yml` does not read after `232b138`.
* **GitHub environments** `dev`, `prod`, and `CURSOR_API_KEY` exist. This token cannot read branch protection (HTTP 403). Do not treat empty protection-rule payloads as proof that reviewers are set.
* **Nightly integration** reached the ODBC install and stopped there (run 42469243262). Pytest did not start, so the secrets were not the failure this time.



## Schwachstellen-Analyse  ✅ On main (PR #6, Darstellung PR #12)

API landed in `2f13c3f`. Darstellung landed in `6850feb` (`feat(analytics): sharpen dashboard visualization (#12)`). This is goal G10, not the Sprint 005 KPI engine. `6850feb` changes only `src/bdx/api/static/analytics.html`. `283ee4b` does not replace that page.

| Feature | Status | Notes |
|---|---|---|
| `GET /api/v1/analytics/weaknesses` | ✅ | overdue orders, stuck released orders (<10 % done, unchanged ≥ 3 days), plan changes (7 days), idle machines, `MACHINE_OFFLINE` (24 h), collector errors (7 days), last 20 runs |
| `GET /analytics` | ✅ | `src/bdx/api/static/analytics.html`, auto-refresh 30 s |
| Darstellung (`6850feb`) | ✅ | Plan-Änderungen als Delta-Chips (Menge, Termin). Verzug und Festgefahren als Balken (gelb ≤7 T, orange 8–30 T, rot >30 T). KPI-Kontext: Summe Verzugstage und längste Stagnation. Maschinenkachel: „seit X min/h/T“ aus `last_changed_at`. Fortschrittsbalken 8 px mit Beschriftung. Event-Codes als deutsche Labels. Laufstatus als Pills. |
| Tests | ✅ | 9 tests in `tests/test_weaknesses.py` (the `test_engine` and `test_session_factory` defs there are fixtures). `6850feb` added no tests. `283ee4b` moved these tests out of `tests/test_analytics.py`. |
| CI + DEV deploy | ✅ | PR #6: CI [42415113307](https://github.com/aeyhorn/Alyze/actions/runs/42415113307) and Deploy to DEV [42415113477](https://github.com/aeyhorn/Alyze/actions/runs/42415113477) succeeded. PR #12: CI [42420693051](https://github.com/aeyhorn/Alyze/actions/runs/42420693051) succeeded. Deploy to DEV [42420693125](https://github.com/aeyhorn/Alyze/actions/runs/42420693125) for `6850feb` succeeded; the host job had been queued since 2026-11-07 23:36 (UTC+1) and finished 2026-11-08 09:39 (UTC+1). `6710fdc`: CI [42464604714](https://github.com/aeyhorn/Alyze/actions/runs/42464604714) and Deploy to DEV [42464604728](https://github.com/aeyhorn/Alyze/actions/runs/42464604728) succeeded (host job 09:52 UTC+1). HEAD was `2796032`: CI [42498525145](https://github.com/aeyhorn/Alyze/actions/runs/42498525145) and Deploy to DEV [42498525158](https://github.com/aeyhorn/Alyze/actions/runs/42498525158) succeeded (host job 17:13 UTC+1). Current `main` `723f794`: CI [42518587593](https://github.com/aeyhorn/Alyze/actions/runs/42518587593) succeeded. Deploy to DEV [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) succeeded, so the host is on that image. The earlier deploy of `0de31a7` ([42516285446](https://github.com/aeyhorn/Alyze/actions/runs/42516285446)) failed before recreate; `1ce5fdf` ([42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744)) then deployed successfully. |

The committed marker `bdx-intelligence/.runtime/last-deploy-sha` is still `1480f5c` (2026-11-07 19:55 +01). The successful Actions deploys did not change that file in git. This sync did not probe the host again.

## Quote-to-Promise  ✅ On main (PR #33, quoter wiring PR #39)

The merge message for `2796032` calls this a cockpit that answers material, BOM, capacity, price and personnel in parallel. Earlier feature text labeled that cockpit Sprint 005. This file keeps Sprint 005 for the KPI engine at `283ee4b`. Quote-to-Promise stays the delivery at `2796032`, extended on `main` by `0de31a7` (PR #39), which wires the Docker bdx-quoter into the pricing domain. `1ce5fdf` (PR #41) renamed that migration from a second revision `005` to `008_q2p_quoter_fields` (revises `007`). It has no goal id: `REQUIREMENTS.md` has no row, and G7 stays the broker. The quoter wiring is not a new goal. The Promise Platform at `1ce5fdf` is a separate delivery and also has no goal id.

| Feature | Status | Notes |
|---|---|---|
| Inquiry case store `q2p_inquiries` (Alembic `004_q2p_inquiries`) | ✅ on `main` and applied on DEV | statuses draft / ready / blocked / decided, with a decision audit. Deploy [42498525158](https://github.com/aeyhorn/Alyze/actions/runs/42498525158) logged `Running upgrade 003 -> 004` |
| Parallel evaluator `bdx.q2p.service.evaluate_promise` | ✅ | item, material, BOM, capacity, pricing, personnel. Pricing calls the quoter when a datenraum is set |
| bdx-quoter HTTP adapter | ✅ in the deployed image | `src/bdx/adapters/quoter.py` and `QUOTER_*` in config. `.env.example` leaves `QUOTER_ENABLED` off. `kalkulation.offen` maps to `open_questions`. Without a datenraum, pricing falls back to SAP ITM1. `docs/Q2P_QUOTER.md` is on `main`. PR #39 records the `/api/run` paths as assumptions until they are checked against `web/server.py`. This sync did not read the host env, so it does not claim the quoter is enabled on DEV |
| Inquiry columns `datenraum` / `kunde` / `use_llm` | ✅ on `main` and applied on DEV | `008_q2p_quoter_fields.py` revises `007`. Deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) logged `Running upgrade 007 -> 008` for the quoter datenraum link |
| SAP reads OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ in code | a missing SELECT turns that domain into an open question instead of failing the case. `docs/sql/grant_q2p_readonly.sql` is in the repo. The deploy log does not show that script running on LDSAP |
| Capacity from `machine_state` plus open `order_state` | ✅ | idle versus busy, plus backlog of the same item |
| REST under `/api/v1/q2p` | ✅ | `POST/GET /inquiries`, `GET/PATCH /inquiries/{id}`, `POST .../evaluate`, `POST .../decide`, `GET /promise` |
| Cockpit UI `/q2p` | ✅ | `src/bdx/api/static/q2p.html`, including the datenraum, kunde and use_llm fields from `0de31a7` |
| `bdx-collect serve` attaches the SAP engine | ✅ | without an engine the SAP domains become open questions |
| Tests | ✅ counted, not re-run | 7 `def test_` in `tests/test_q2p.py` and 4 in `tests/test_quoter.py`. CI [42518587593](https://github.com/aeyhorn/Alyze/actions/runs/42518587593) on current `main` succeeded |

Personnel and shift qualification stay human: there is no feed. Quoter `offen` stays human until it is resolved in the datenraum.

## Promise Platform  ✅ On main (PR #41, vision PR #40)

Squash-merged as `1ce5fdf` (2026-11-08 21:04 +0100). The vision doc landed next as `723f794` (PR #40, 21:08 +0100). Branch tips `bc09b62` and `3ffbeef` are not ancestors of `main` because both merges were squashes. There is no goal id. `REQUIREMENTS.md` has no row. This is not G7 and not G10.

| Feature | Status | Notes |
|---|---|---|
| Domain + Alembic `007_promise_platform` | ✅ on `main` and applied on DEV | offers, gaps, evidence, agent jobs, contracts. Revises `006`. Deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) logged `Running upgrade 006 -> 007` |
| Offer engine | ✅ | `bdx.promise.engine`: create, recompute, decide, resolve, publish |
| Agents quote, purchase, capacity, contract | ✅ | quote delegates pricing to `evaluate_promise` plus the quoter |
| API `/api/v1/promise/*` and `/api/v1/portal/{token}` | ✅ | portal is token-scoped and does not use the API key |
| UI `/promise` and `/portal/{token}` | ✅ | `promise.html`, `portal.html` |
| Vision | ✅ | `docs/VISION_PROMISE_PLATFORM.md` on `main` via `723f794` |
| Tests | ✅ counted, not re-run | 5 `def test_` in `tests/test_promise.py`. CI [42518204806](https://github.com/aeyhorn/Alyze/actions/runs/42518204806) succeeded |

This sync did not open `/promise` or a portal link. Publishing a contract and sharing the portal stay operator steps.

## Sprint 005 – KPI engine, anomalies, procurement, diagnosis  ✅ On main (PR #5)

Squash-merged as `283ee4b` (2026-11-08 17:18 +0100). The feature branch tip `ebad8ee` is not an ancestor of `main` because the merge was a squash. `005_analytics_tables` revises `004`, and `006` revises `005`. `1ce5fdf` moved the quoter columns off revision `005` onto `008`, which revises `007`. Revision `005` is only the analytics migration. DEV is at `008` after deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744). Deploy [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) logged no further upgrade. There is no goal id. `REQUIREMENTS.md` has no row, and G10 stays the weakness dashboard.

| Feature | Status | Notes |
|---|---|---|
| Alembic `005_analytics_tables` | ✅ on `main` and applied on DEV | `kpi_snapshots`, `metric_thresholds`, `detected_anomalies`, `shift_calendar`, `machine_state_history`. Revises `004`. Deploy [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) logged `Running upgrade 004 -> 005` |
| Alembic `006_diagnosis_tables` | ✅ on `main` and applied on DEV | `measurement_quality`, `order_flow_segments`, `lateness_causes`, `bottleneck_rank`. Same deploy logged `Running upgrade 005 -> 006` |
| Event-store KPIs (`bdx.analytics.kpis`) | ✅ | cycle time, on-time delivery, backlog aging, rejection rate, release-to-start, order-change frequency, utilization, setup ratio, MTBF/MTTR, queue unstarted, OEE components |
| Procurement KPIs (`bdx.analytics.kpis_procurement`) | ✅ | material coverage, PO lead time, supplier on-time rate, overdue PO lines, stock coverage days. Live SAP reads are skipped when no SAP engine is attached |
| Thresholds and anomalies | ✅ | fixed seeds, then rolling percentile tune; German recommendations; anomalies resolve when the KPI returns inside the band |
| Diagnosis | ✅ | flow split into wait / setup / run / post-process; one lateness cause per late order; machines ranked by utilization times waiting hours |
| SAP reads (`queries_sap_extended.py`) | ✅ | WOR1, OITW, ORDR/RDR1, OPOR/POR1, OPDN/PDN1, goods-receipt lead time, supplier OTD, OIVL consumption. No INSERT/UPDATE/DELETE in that module |
| REST `/api/v1/analytics` | ✅ | `GET /kpis`, `/kpis/{metric}`, `/trends`, `/anomalies`, `/thresholds`, `/quality`, `/flow`, `/causes`, `/bottleneck`, `POST /run`, plus the existing `GET /weaknesses` |
| Scheduler | ✅ in code | `run_analytics_once` from the polling loop: KPI cycle default 600 s, threshold tune default 24 h |
| Tests | ✅ counted, not re-run | 40 `def test_` in `tests/test_analytics.py`, 10 in `tests/test_diagnosis.py`. CI [42499222986](https://github.com/aeyhorn/Alyze/actions/runs/42499222986) succeeded |

`GET /analytics` remains the weakness page from G10. Sprint 005 does not add a second dashboard file.

## Operational status (DEV, last manual check 2026-11-07)

These rows are the last hands-on check recorded in this file (2026-11-07). This sync did not re-run `bdx-collect`. After that check, Deploy to DEV [42498525158](https://github.com/aeyhorn/Alyze/actions/runs/42498525158) for `2796032` logged Alembic `003 -> 004` and the host job succeeded, including `/health/live`. Deploy [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) for `283ee4b` logged Alembic `004 -> 005`, `005 -> 006` and `/health/live`. Deploy [42516285446](https://github.com/aeyhorn/Alyze/actions/runs/42516285446) for `0de31a7` stopped in migrate. Deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) for `1ce5fdf` then applied `006 -> 007` and `007 -> 008` and passed `/health/live`. Deploy [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) for `723f794` succeeded with the schema already at `008`. The shopfloor counts below were not remeasured.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth on the workstation (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Superseded for the container by `12fa8cf`: `bdx_readonly` read 871 open orders from inside the DEV container. Not re-checked in this sync. |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437. The 2026-11-07 check saw schema **002**. Later Actions deploys applied through `008` (`42518204744`). `723f794` did not migrate further |
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
| **Promise Platform** | Code and the vision doc are on `main` (`1ce5fdf` PR #41, `723f794` PR #40). DEV has Alembic `007` and `008`. No goal id until a requirement row exists. This sync did not open `/promise` or a portal link. |
| **Sprint 005 goal** | Code is on `main` and DEV has migrations `005_analytics_tables` and `006`. No goal id until a requirement row exists. Shopfloor KPI values were not remeasured. |
| **Quote-to-Promise grants and quoter enablement** | Code, migration `004`, migration `008`, and the quoter adapter are on `main`. DEV has the quoter columns after `007 -> 008`. `docs/sql/grant_q2p_readonly.sql` was not shown in the deploy log. `.env.example` leaves the quoter off; the host env was not read. Personnel and quoter `offen` stay human questions. No goal id until a requirement row exists. |
| **Fix `pr-review.yml` startup** | pushes of `2f13c3f`, `6850feb`, `6710fdc`, `2796032` (run 42498523815), `283ee4b` (run 42499221888), `0de31a7` (run 42516284484), `1ce5fdf` (run 42518203439) and `723f794` (run 42518586380) failed the workflow in 0s with no jobs; duplicate `env:` on the diff step. The docs-branch pushes of open PR #44 (run 42519013954, 21:13 CET), open PR #45 (run 42520953516, 21:36 CET), open PR #46 (run 42525833457, 22:33 CET) and open PR #47 (run 42530945036, 23:34 CET) failed the same way. Auto-merge on PR #46 (run 42525846092) and on PR #47 (run 42530960057) skipped because the label `trivial` is absent. CI for PR #47 (run 42530960050) succeeded. Not changed in this sync. |
| **Branch protection** | not readable with this token. `ci.yml` is the intended required check; confirm in repo settings. |
| **Ruff / mypy / coverage ratchet** | both linters advisory; coverage gate is 68 %, not 80 %. `AGENTS.md` still tells operators to pass `--cov-fail-under=80`. Lint-cleanup run 42473962358 pushed `chore/ruff-cleanup-20261108` and stopped because the label `trivial` does not exist. No pull request. |
| SQL login `bdx_readonly` on LDSAP | `docs/sql/create_bdx_readonly.sql` no longer denies CONTROL (`7d0fb2f`). `12fa8cf` records that the login worked from the DEV container (871 open orders). PROD company DB was not shown. Not re-checked this sync. |
| DEV compose on 192.168.82.33 | `12fa8cf` records collector + api up at sha `1480f5c` (2026-11-07 19:55 +0100). Actions deploy [42415113477](https://github.com/aeyhorn/Alyze/actions/runs/42415113477) for `2f13c3f` is `success` (`/health/live`). Deploy [42420693125](https://github.com/aeyhorn/Alyze/actions/runs/42420693125) for `6850feb` succeeded 2026-11-08 09:39 (UTC+1) after a long queue. Deploy [42464604728](https://github.com/aeyhorn/Alyze/actions/runs/42464604728) for `6710fdc` succeeded 09:52 (UTC+1). Deploy [42498525158](https://github.com/aeyhorn/Alyze/actions/runs/42498525158) for `2796032` succeeded 17:13 (UTC+1), including Alembic `003 -> 004` and `/health/live`. Deploy [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) for `283ee4b` succeeded 17:21 (CET), including Alembic `004 -> 005`, `005 -> 006` and `/health/live`. Deploy [42516285446](https://github.com/aeyhorn/Alyze/actions/runs/42516285446) for `0de31a7` failed in migrate at 20:43 (CET) and did not recreate collector or api. Deploy [42518204744](https://github.com/aeyhorn/Alyze/actions/runs/42518204744) for `1ce5fdf` succeeded at 21:06 (CET), including Alembic `006 -> 007`, `007 -> 008` and `/health/live`. Deploy [42518587710](https://github.com/aeyhorn/Alyze/actions/runs/42518587710) for `723f794` succeeded at 21:10 (CET) with no further upgrade. The committed marker is still `1480f5c`. Host env was not opened in this sync. |
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
│   ├── db/                # SAP/PG engines + parameterised OWOR/OITM and extended SAP reads
│   ├── models/            # Pydantic WorkOrder + ORM (order_state, order_snapshots, snapshot_runs,
│   │                      #   machine_state, domain_events, sl_operations, analytics)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry), quoter.py (bdx-quoter HTTP)
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── analytics/         # Sprint 005: KPIs, procurement, thresholds, anomalies, diagnosis
│   ├── q2p/               # Quote-to-Promise evaluator, models, inquiry store (PR #33, quoter wiring PR #39)
│   ├── promise/           # Promise Platform engine, agents, models (PR #41)
│   ├── api/               # FastAPI app, routes (analytics, q2p, promise, portal), static UI
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # 001–008 linear: 004 q2p, 005 analytics, 006 diagnosis, 007 promise, 008 quoter fields
├── tests/                 # 177 unit + tests/integration/ (8 DEV SAP/SL tests)
├── scripts/               # ci_triage, pr_review, create_pr, dora_metrics, deploy.ps1,
│                          #   prepare-dev-host.sh, setup-github-runner.ps1, set-github-secrets.ps1
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, Q2P_QUOTER, VISION_PROMISE_PLATFORM, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS
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

`HEAD` of this sync and `origin/main`: `723f794` docs: Promise Platform vision toward portal, purchasing agents, contracts (#40). Parent `1ce5fdf` feat(promise): Alyze Promise Platform engine, agents, API, portal (#41).

Remote branches whose tips are not contained in `origin/main` (product or agent work, not the draft doc-sync branches):

| Branch | PR | On main? |
|---|---|---|
| `cursor/q2p-cockpit-9a6c` | #39 merged (squash `0de31a7`); tip `4342119` is not an ancestor | yes, as `0de31a7` |
| `cursor/sprint-005-analytics-kpi-engine-1e2b` | #5 merged (squash `283ee4b`); tip `ebad8ee` is not an ancestor | yes, as `283ee4b` |
| `cursor/promise-platform-engine-9a6c` | #41 merged (squash `1ce5fdf`); tip `bc09b62` is not an ancestor | yes, as `1ce5fdf` |
| `cursor/promise-platform-vision-9a6c` | #40 merged (squash `723f794`); tip `3ffbeef` is not an ancestor | yes, as `723f794` |
| `cursor/dev-sync-agent-e2dc` | #3 open (`ac652b1`) | no |
| `cursor/update-project-status-05e2` | #2 open (`7781c7c`) | no |
| `chore/ruff-cleanup-20261108` | no PR (`57411b2`) | no |

Draft doc-sync PRs #4, #7–#11, #13–#32, #34–#38 and #42–#47 are unmerged. They are not the source of truth; this file is reconciled to `main` directly. The previous reconcile from this coordinator was #47 against `723f794` (23:34 CET). Its push failed `pr-review.yml` in 0s with no jobs (run 42530945036, 23:34 CET); its CI run 42530960050 succeeded. Auto-merge run 42530960057 finished green and skipped the merge because the label `trivial` is absent, so #47 stayed a draft. `origin/main` has not moved since #47. The `PROJECT_STATUS.md` on `origin/main` still marks Sprint 004 as uncommitted; that claim does not match the tree at `723f794`. Goal IDs stay `G1`–`G10`. Later hourly drafts renumbered `G7`–`G10` and invented `R001`–`R020`. This sync does not adopt that numbering. PR #3 still holds `.cursor/skills/dev-sync/SKILL.md`; it is not on `main`. Test count remains 185 functions (177 unit + 8 integration). This sync did not re-run pytest.
