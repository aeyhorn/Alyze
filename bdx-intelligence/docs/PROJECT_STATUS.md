# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-12 21:37 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `origin/main` (`cd6440f`). Push CI of that SHA is green. Ruff and mypy stay advisory; pytest coverage gate is 68 %. Nightly integration fails in the ODBC install (2026-11-08 through 2026-11-12). `prod` has no protection rules. Branch protection and the Actions secret list were not readable in this run (403) |
| 005 | Analytics: KPI engine, anomalies, diagnosis | ✅ merged (#5, #6, #12) — migrations `005`+`006`, API `/api/v1/analytics`, UI `/analytics` |
| Q2P | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, #39) – needs Q2P SAP grants + optional Quoter on DEV. Migrations run on DEV deploy (`alembic upgrade head`) |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41) – migrations `007`+`008` are in head; vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Vorgangsleitstand (`/vorgang`) | ✅ merged (#67). DEV deploy of that commit succeeded |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

**Git-Abgleich 2026-11-12 21:37 (UTC+1):** Checkout `cursor/bc-6982bc1d-4f28-4f7d-b45b-00807a91b734-2ab0` matches `origin/main` `cd6440f` (2026-11-10 07:21 +0100, “Update deployment timestamp and SHA for the latest release”). Working tree was clean and not ahead of `origin`. Latest successful DEV deploy of that SHA: 2026-11-10 07:22 (UTC+1), Actions `42768023481` (`deploy-dev.yml`; smoke `/health/live` is required to pass). Push CI of the same SHA succeeded (Actions `42768023614`). The in-repo stamp `.runtime/last-deploy-at` / `.runtime/last-deploy-sha` is still 2026-11-07 21:50 +01:00 / `6ccc036`. `cd6440f` only moved that stamp from 2026-11-07 19:55 +01:00 / `1480f5c`.

100 open pull requests (31 ready, 69 draft), all documentation. 92 use the title `docs: reconcile project status and goals`. Five use `docs: reconcile project status, goals and requirements`. One each: `docs: Projektstatus, Ziele und Anforderungen an main abgleichen`, `docs: reconcile project status, goals and requirements with main`, and `docs: update PROJECT_STATUS.md – Sprint 004 complete`. This run does not merge them. 110 remote branches are not contained in `origin/main`. The only one outside `cursor/` and `sync/status-*` is `origin/chore/ruff-cleanup-20261108` (`57411b2`, 11 commits behind, 1 ahead, no pull request). Named feature branches (Sprint 001, dashboard nav, Q2P, Promise, analytics, Quoter deep link, Vorgangsleitstand) are leftovers after squash merges and sit behind `main`. The repository ruleset list is empty (re-read 2026-11-12 21:37 UTC+1). Classic branch protection on `main` returned 403. Environments `dev`, `prod`, and `CURSOR_API_KEY` exist and have no protection rules (same read).

The newest documentation PR (#112) passed pytest at 19:38 UTC (Actions `43292212808`). Nightly integration failed on 2026-11-08, 2026-11-09, 2026-11-10, 2026-11-11, and 2026-11-12 in `Install ODBC Driver 18`. The 2026-11-12 run is Actions `43202844646` (10:43 UTC): `gpg` could not open `/dev/tty`, step exit 2, before pytest. The 2026-11-08 run `42469243262` failed on the same step. Pushes record a failed Actions run named `.github/workflows/pr-review.yml` with duration 0s (latest seen 2026-11-12 19:38 UTC, Actions `43292190062`, the push of #112). In that file the step `Fetch PR diff` has two `env` keys. Shop-floor figures below are still the 2026-11-07 check; this run did not re-probe SAP or the machines.

Test suite: 120 `def test_` functions in unit modules and 8 in `tests/integration/` (128 total), SQLite in-memory. The integration suite skips cleanly when DEV creds are absent.

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off until an operator turns dry-run off in the host `.env` outside git |
| Dockerfile + docker-compose.yml | ✅ deployed on DEV | `deploy-dev.yml` recreates `collector` and `api` on the DEV host. Latest success is `cd6440f` (2026-11-10 07:22 UTC+1). SQL login script: `docs/sql/create_bdx_readonly.sql` |

## Quote-to-Promise Cockpit  ✅ Merged (#33, #39)

Git names **Sprint 005** as the analytics work (`#5`), not this cockpit. Q2P landed separately.

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

## Analytics (Sprint 005)  ✅ Merged (#5, #6, #12)

KPI engine, anomaly detection, procurement metrics, and the diagnosis layer (measurement quality, flow, one lateness cause per late order, bottleneck rank). Migrations `005` and `006`. API `/api/v1/analytics/*`, UI `/analytics`. The DEV deploy of `#5` succeeded on 2026-11-08. This sync did not re-run the analytics cycle against SAP.

## Vorgangsleitstand  ✅ Merged (#67)

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht. Der DEV-Deploy von `#67` war erfolgreich.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On `origin/main`

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff (lint + format check), mypy on `src/bdx`, pytest with `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. Ruff and mypy jobs are `continue-on-error`. Latest `main` run (`cd6440f`) succeeded |
| **`.github/workflows/integration.yml`** | ✅ on `main`, nightly red | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`. The fixture forces dry-run on, so the job cannot write to SAP. Runs from 2026-11-08 through 2026-11-12 fail in `Install ODBC Driver 18` before pytest. Latest: Actions `43202844646` (2026-11-12 10:43 UTC), `gpg` cannot open `/dev/tty`, exit 2 |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, deploying | push to `main` → build image (`ghcr.io/<repo>/bdx-intelligence:dev`), push to GHCR, deploy on the self-hosted runner on the DEV host (no SSH hop): `docker compose pull`, `alembic upgrade head`, recreate `collector` + `api`, smoke `/health/live`. Diagnose is best-effort. The job aborts when the host `.env` turns dry-run off |
| **`.github/workflows/deploy-prod.yml`** | ✅ on `main` | `workflow_dispatch` only; uses environment `prod`. The workflow comment expects required reviewers; the environments API on 2026-11-12 shows no protection rules on `prod`. Inputs `run_migrations` and `confirm_sl_write`; pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 on `main`, push parse fails | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only. Branch protection is what would block via `ci.yml`. The step `Fetch PR diff` contains two `env` keys. Push events record a failed run of this workflow file with duration 0s. Latest: Actions `43292190062` (2026-11-12 19:38 UTC) |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml` tweaks** | ✅ on `main` | advisory lint/typecheck config and compose image override are in the tree (`48afa46` and later). `origin/chore/ruff-cleanup-20261108` is a separate unmerged format pass with no PR |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The tree is on `origin/main`.** Workflows, `scripts/`, `tests/integration/`,
  `src/bdx/agents/`, `AGENTS.md`, and `.cursor/prompts` are tracked. This
  checkout matches `origin/main` (`cd6440f`); it is not one commit ahead.
* **DEV deploy no longer needs `DEV_SSH_*`.** The self-hosted runner on the
  DEV host runs compose directly. `CURSOR_API_KEY` is still the opt-in for
  triage and PR review. Nightly integration still needs `SAP_DB_*`, `SL_*`,
  and `POSTGRES_DSN`. This run could not list Actions secrets (403).
* **`prod` exists and has no protection rules** (environments API,
  re-read 2026-11-12 21:37 UTC+1). Branch protection on `main` was not
  readable (403), so the “required `ci.yml` check” acceptance point stays
  open. The ruleset list is empty.
* **Not a landing task anymore.** Remaining work is the ops acceptance in G4,
  not a first commit of the Sprint 004 tree.



## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17) on the 2026-11-07 check. Commit `7d0fb2f` records that SQL login `bdx_readonly` existed and could not CONNECT until `DENY CONTROL` was removed from the script. Whether `docs/sql/reset_bdx_readonly.sql` was applied on LDSAP is not in git |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437. The 2026-11-07 check saw schema **002**. Later successful DEV deploys run `alembic upgrade head` (head on `cd6440f` is `008`). This run did not query the live database |
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
| **G4 ops acceptance** | Sprint 004 code is on `main`. Still open: required reviewers on `prod` (none today), branch protection requiring `ci.yml` (not readable, 403), confirmation that triage/review and nightly integration secrets are set (secret list 403). Nightly integration is red before pytest |
| In-repo deploy stamp | `.runtime/last-deploy-*` is 2026-11-07 21:50 +01:00 / `6ccc036`. Actions deploy of `cd6440f` succeeded on 2026-11-10 07:22 (UTC+1) and is not that stamp |
| SQL login `bdx_readonly` on LDSAP | scripts `docs/sql/create_bdx_readonly.sql` and `docs/sql/reset_bdx_readonly.sql`. Login existed on 2026-11-07 (`7d0fb2f`). Acceptance — collector connects with it, read-only — is not re-checked here |
| Example env dry-run | `bdx-intelligence/.env.example` line 24 turns dry-run off. The rule is that committed files keep dry-run on. This run does not edit that file |
| DEV compose on 192.168.82.33 | done for `cd6440f`: `deploy-dev.yml` success 2026-11-10 07:22 (UTC+1), `/health/live` required. Postgres was already on that host |
| MQTT / Kafka broker | set `MQTT_ENABLED=true`+`MQTT_HOST` or `KAFKA_ENABLED=true`+`KAFKA_BOOTSTRAP_SERVERS`; `pip install -e .[mqtt]` / `.[kafka]` |
| Run collector against PROD | read-only; but **needs a separate PG database** (or mode-prefixed `source_key`) to avoid mixing DEV/PROD data in `order_state`. Currently only single-order probes done |
| SAP write-back real use | dry-run stays on unless an operator changes the host `.env` outside git. DEV deploy aborts if that file turns dry-run off. Operations: release/close/cancel/report-production. The committed example env currently turns dry-run off (see row above) |
| Multi-company SAP, SSO/SCIM | TBD |
| Ruff cleanup branch | `origin/chore/ruff-cleanup-20261108` is ahead of `main` and has no PR |
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
│   ├── analytics/         # Sprint 005: KPIs, anomalies, diagnosis
│   ├── promise/           # Promise Platform engine and agents
│   ├── q2p/               # Quote-to-Promise evaluator
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI app, routes, static dashboard / analytics / vorgang / q2p / promise
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008 (head `008`)
├── tests/                 # 120 `test_` functions in unit modules + 8 in tests/integration/
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
