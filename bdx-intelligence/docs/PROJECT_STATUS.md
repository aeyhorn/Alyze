# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-11 16:34 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ on DEV. MQTT/Kafka built, no broker. Write-back code is on `main`; the DEV deploy guard passed for `cd6440f` |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main` (`cd6440f`). Push CI `42768023614` and Deploy to DEV `42768023481` green (2026-11-10). Docs-branch CI `43039741341` (`28371cd`, 2026-11-11 14:34 UTC) is green: 179 passed, coverage 73.95%. Still open: nightly `gpg` failure (`43003787661`, 2026-11-11 10:27 UTC), `pr-review.yml` fails before any job (`43039728961`), `prod` without required reviewers, branch protection not readable (HTTP 403) |
| 005 | Analytics KPI engine, anomalies, weakness dashboard | ✅ merged (#5, #6, #12), migrations `005`+`006` |
| Q2P | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, #39) – Q2P SAP grants + optional Quoter on DEV still open |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41) – vision: `docs/VISION_PROMISE_PLATFORM.md`; Quoter deep link specified (#57) |
| Vorgang | Vorgangsleitstand (order window, machine load, reported step) | ✅ merged (#67) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

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
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay an operator change on the host; this tree does not enable them |
| Dockerfile + docker-compose.yml | ✅ deployed on the DEV host | Actions run `42768023481` (2026-11-10 06:24 UTC) recreated `collector` and `api`. `/health/live` returned `{"alive":true}`. Which SQL login the container uses is not printed by `diagnose` |

## Sprint 005 – Analytics  ✅ Merged (#5, #6, #12)

**Goal**: KPI snapshots, anomaly detection, self-tuning thresholds, and a shop-floor weakness view from the event store. Git calls this Sprint 005. The Quote-to-Promise cockpit is a separate feature (see below).

| Feature | Status | Notes |
|---|---|---|
| KPI engine (`bdx.analytics`) | ✅ | order, machine, and procurement metrics |
| Anomalies + threshold tuning | ✅ | `anomalies.py`, `thresholds.py` |
| Flow, lateness causes, bottleneck rank | ✅ | migration `006` |
| REST `/api/v1/analytics/*` | ✅ | KPIs, trends, anomalies, quality, flow, causes, bottleneck, weaknesses, on-demand run |
| Weakness dashboard `/analytics` | ✅ | static `analytics.html` |
| Migrations `005` + `006` | ✅ | analytics tables, then diagnosis tables |

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

## Vorgangsleitstand

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On `main`

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest gate is `--cov-fail-under=68`, Docker build smoke test. Working dir = `bdx-intelligence/`. On `cd6440f`, push run `42768023614` was green. Latest docs-branch run `43039741341` (`28371cd`, 2026-11-11 14:34 UTC) is green: 179 passed, 8 deselected, coverage 73.95% (gate 68% reached). Docker, ruff, and mypy jobs in that run succeeded. The prior green docs-branch run was `43030209016` (`1cf2216`, 2026-11-11 13:33 UTC). `42966672784` (`6c0c6f7`, 2026-11-11 05:34 UTC) failed `test_machine_utilization_with_calendar` on the same product tree |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; SL_DRY_RUN forced `true` by fixture — no real SAP writes possible |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, last run green | push to `main` → build `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` + `:sha-<sha>`, push to GHCR, then on the self-hosted DEV runner: `docker compose pull`, migrate, recreate `collector` + `api`, smoke `/health/live` + `bdx-collect diagnose`. Aborts when the host env enables real Service Layer writes. Run `42768023481` succeeded |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only. The workflow expects a `prod` environment with required reviewers; that environment exists and `protection_rules` is empty. Extra inputs `run_migrations` and `confirm_sl_write`; pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 fails before any job | Intended path: PR open/sync/reopen → `scripts/pr_review.py` posts one advisory comment. The "Fetch PR diff" step has two `env` mappings. Run `42768021714` on `cd6440f` failed in 0s with no jobs and no log. Later pushes of the docs branch fail the same way; latest seen is `43039728961` (2026-11-11 14:34:11 UTC, SHA `28371cd`, no jobs) |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | committed with the Sprint 004 tree. Working tree of `origin/main` at `cd6440f` is clean |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The tree is on `origin/main` at `cd6440f`.** Workflows, agents, integration tests, prompts, and scripts are tracked. Nothing in that tree is uncommitted.
* **CI and DEV deploy of that SHA are green.** CI `42768023614` (lint advisory, tests, docker smoke, mypy advisory) on 2026-11-10 06:22 UTC. Deploy to DEV `42768023481` built `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` and recreated the stack on the self-hosted runner. Deploy no longer uses an SSH hop. Latest docs-branch CI `43039741341` (`28371cd`, docs only on top of `cd6440f`, 2026-11-11 14:34 UTC) is green. `42966672784` (`6c0c6f7`) failed one unit test on the same product tree; see the reconcile note below.
* **`prod` has no required reviewers.** Environment `prod` exists and `protection_rules` is empty.
* **Branch protection on `main` is not confirmed.** The protection API returns HTTP 403 for this token.
* **Nightly integration is red before pytest.** Cron in `integration.yml` is `0 3 * * *` UTC. Scheduled run `43003787661` (2026-11-11 10:27 UTC, SHA `cd6440f`) failed in `gpg --dearmor` because `/dev/tty` is missing, during Install ODBC Driver 18. Pytest did not start. Same failure on `42802489315` (2026-11-10 10:50 UTC), `42605350114` (2026-11-09 10:59 UTC), and `42469243262` (2026-11-08 09:55 UTC). Those scheduled runs start hours after the cron.
* **Action secrets are not listed here.** The secrets API returns HTTP 403. Environments that exist: `dev`, `prod`, and one named `CURSOR_API_KEY`.
* **Lint cleanup is not on `main`.** `origin/chore/ruff-cleanup-20261108` has one commit (`57411b2`) and is 11 commits behind `origin/main`. It has no pull request. Ruff and mypy stay advisory until that lands.
* **PR review does not run.** `pr-review.yml` has two `env` mappings on the "Fetch PR diff" step. Run `42768021714` (push of `cd6440f`) failed in 0s with no jobs and no log. The same 0s failure is on later pushes of the docs branch; latest seen is `43039728961` at 2026-11-11 14:34:11 UTC (SHA `28371cd`, no jobs).
* **This reconcile (2026-11-11 16:34 UTC+1) found no newer product commit.** `origin/main` is still `cd6440f`. There is no newer push CI or DEV deploy on that SHA. Nightly run `43003787661` (2026-11-11 10:27 UTC, SHA `cd6440f`) failed in `gpg --dearmor` because `/dev/tty` is missing, before pytest. Latest docs-branch CI `43039741341` (2026-11-11 14:34 UTC, SHA `28371cd`) is green: 179 passed, 8 deselected, coverage 73.95% (gate 68% reached). Docker, ruff, and mypy in that run succeeded. The prior green docs-branch CI was `43030209016` (`1cf2216`, 2026-11-11 13:33 UTC). `42966672784` (`6c0c6f7`, 2026-11-11 05:34 UTC) failed `test_machine_utilization_with_calendar` (`assert None is not None`) with 178 passed on the same product tree. The two lateness tests that failed on `c798b9e` (`42932824913`) stayed green through `28371cd`. Auto-merge `43039741191` succeeded and skipped (`No 'trivial' label — skipping auto-merge.`), so PR 91 stayed open. `pr-review` `43039728961` on `28371cd` failed with no jobs. `prod` `protection_rules` is still empty. The branch-protection API and the secrets API still return HTTP 403. The ruff-cleanup branch is unchanged (1 ahead, 11 behind, no pull request). Ahead of `origin/main` outside `cursor/*`: `origin/chore/ruff-cleanup-20261108`, `origin/sync/status-20261110`, `origin/sync/status-20261111`. 79 pull requests are open. All of them are documentation. #2 and #8 use older titles; the rest are docs reconciles, including #19. None merged on 2026-11-11.



## Operational status (DEV, diagnose in Deploy to DEV `42768023481`, 2026-11-10 06:24 UTC)

| Check | Result |
|---|---|
| Deploy | ✅ image `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` for push `cd6440f`. `collector` and `api` recreated. Migrate container exited without `Running upgrade` (database already at the image head; repo head is `008`) |
| `/health/live` | ✅ `{"alive":true}` |
| PostgreSQL | ✅ connected. Orders (state) 38575, history rows 39446, events 39612, runs 4782, machines 10 |
| SAP read | ✅ `DEV_SBO_LEISINGER`, 885 open orders (P/R). Diagnose does not print the SQL login name |
| Machine feed | ✅ 10 machines from XMSK. Integrex i500S idle, order `10886`. QT350MY running, order `10886/NEU`. SQT250 MSY `unknown` / `AUS` |
| SCADA telemetry | ✅ reachable |
| MQTT | ⬜ disabled (`MQTT_ENABLED` off or no `MQTT_HOST`) |
| Host write guard | ✅ deploy continued, so the host env does not enable real Service Layer writes |
| `deploy.ps1` stamp | ⬜ `.runtime/last-deploy-sha` is `6ccc036`, `.runtime/last-deploy-at` is `2026-11-07 21:50:15 +01:00`. Actions deploy does not update these files |
| PROD read | ⬜ not repeated in this reconcile. The 2026-11-07 FA 38574 probe stays historical |

### Shop-floor notes from that diagnose

* XMSK `Order` is not always a DocNum. QT350MY still reports `10886/NEU`. Those references stay raw in `order_ref`.
* SQT250 MSY is `unknown` with `exec=AUS` (no piece count).
* This run did not repeat the 2026-11-07 PROD comparison, and it did not run `collect --once`.

## Open items / next steps

| Item | Notes |
|---|---|
| Docs-branch pytest | Latest CI `43039741341` on `28371cd` (2026-11-11 14:34 UTC) is green: 179 passed, 8 deselected, coverage 73.95%. The prior green run was `43030209016` (`1cf2216`, 2026-11-11 13:33 UTC). `42966672784` (`6c0c6f7`, 2026-11-11 05:34 UTC) failed `test_machine_utilization_with_calendar` (`assert None is not None`) with 178 passed. The same single failure was on `42960323976` (`94fb704`), `42953851454` (`d43267d`), `42947342693` (`acc922f`), and `42940214804` (`84232df`). Those runs share the product tree of `cd6440f`. `42932824913` (`c798b9e`) also failed `test_lateness_scrap_when_no_material_context` and `test_lateness_waiting_idle`; those two stayed green on `28371cd`. Last push CI on `main` (`42768023614`, `cd6440f`) remains green |
| Nightly integration | `gpg --dearmor` fails on `/dev/tty` before pytest. Latest is `43003787661` (2026-11-11 10:27 UTC, `cd6440f`). Same failure on `42802489315`, `42605350114`, and `42469243262`. The 2026-11-11 scheduled run started at 10:27 UTC, hours after cron `0 3 * * *` |
| PR review workflow | `pr-review.yml` fails before any job. "Fetch PR diff" has two `env` mappings. Run `42768021714` on `cd6440f` has no jobs and no log. Latest docs-branch failure: `43039728961` (2026-11-11 14:34:11 UTC, SHA `28371cd`, no jobs) |
| `prod` reviewers | environment exists, `protection_rules` empty |
| Branch protection on `main` | not confirmed; API returns HTTP 403 |
| Confirm SQL login name | container reads SAP; `diagnose` does not print the login. Script remains `docs/sql/create_bdx_readonly.sql` |
| Land `chore/ruff-cleanup-20261108` | one lint commit, no PR, 11 commits behind `main`. Until then ruff and mypy stay advisory and the coverage gate stays 68 |
| MQTT / Kafka broker | publisher code is on `main`; diagnose shows MQTT disabled |
| PROD read-only collector | needs a separate Postgres database or a mode-prefixed `source_key`. Not running |
| Real Service Layer writes | stay an operator change on the host. Committed files do not enable them. The DEV deploy guard passed |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User` / `LastProdEnd` | still not part of this reconcile; earlier note was that the feed leaves them empty |

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
├── alembic/               # migrations 001 through 008 (head `008`)
├── tests/                 # 179 selected tests in CI + 8 deselected integration tests
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py
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
