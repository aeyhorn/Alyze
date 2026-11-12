# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-12 14:36 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (publishers built, no broker; write-back DRY_RUN-verified; DEV compose deploy is running) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | ✅ on `main`. Coverage gate 68 %. Ruff and mypy are advisory. Nightly integration fails in the ODBC install. `prod` has no protection rules. Branch protection and Actions secrets were not readable |
| 005 | Analytics KPI engine, anomalies, self-tuning thresholds, Schwachstellen | ✅ merged (#5, #6, #12). Migrations `005` and `006`. UI `/analytics` |
| Q2P | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, #39). Migrations `004` and `008`. SAP grants and optional Quoter remain operator work |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41). Migrations `007`+`008`. Vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Vorgangsleitstand `/vorgang` | ✅ merged (#67). Order window, machine load, reported operation |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test suite: 191 `def test_` functions under `bdx-intelligence/tests/` (183 outside `integration/`, 8 in `tests/integration/`) on SQLite in-memory. The integration suite skips cleanly when DEV creds are absent.

**Git (this sync):** Reconciled against `origin/main` `cd6440f` (2026-11-10 07:21 +01:00). `deploy-dev` succeeded for that SHA (run 2026-11-10 07:22 +01:00, Actions `42768023481`). 94 open pull requests against `main` (25 ready, 69 draft), all documentation: 93 reconciliations and #2 (`docs: update PROJECT_STATUS.md – Sprint 004 complete`, conflicting). This run starts on `cursor/projekt-dokumenten-abgleich-ce27`, which matches `origin/main`, and opens a new documentation pull request. It does not merge. PR #99 and PR #106 stay open. Pull-request CI on 2026-11-12 is split. Runs through 05:33 UTC failed `tests/test_analytics.py::test_machine_utilization_with_calendar` (`assert None is not None`; 1 failed, 178 passed, 8 deselected). Later runs passed that test, including 06:35 UTC on `cursor/projekt-dokumente-sync-cf11`, 07:39 UTC on `sync/status-20261112` (Actions `43176820152`), 08:36 UTC on `cursor/projekt-dokumenten-abgleich-bb30` (Actions `43184320869`), 09:36 UTC on `cursor/projekt-dokumenten-abgleich-7c70` (Actions `43192961156`), 10:34 UTC on `cursor/projekt-dokumenten-abgleich-c555` (Actions `43201569835`), 11:37 UTC on `sync/status-20261112` (Actions `43210723137`), and 12:37 UTC on `cursor/projekt-dokumente-abgleich-76f7` (Actions `43219558353`). The 12:37 UTC run reported 179 passed, 8 deselected, coverage total 73.95 % (5930 statements, 1545 missed, displayed as 74 %) against a 68 % gate. The 09:36 UTC and 11:37 UTC runs reported the same totals. The test uses `datetime.now(UTC).weekday()` and a 06:00–14:00 shift. Push CI for `cd6440f` on 2026-11-10 succeeded. Nightly integration on 2026-11-08, 2026-11-09, 2026-11-10, 2026-11-11 and 2026-11-12 failed in `Install ODBC Driver 18` (`gpg` could not open `/dev/tty`, step exit 2) before pytest. The 2026-11-12 run is Actions `43202844646` (started 10:43 UTC). The cron is 03:00 UTC; the 2026-11-08 run started at 09:55 UTC and the 2026-11-11 run at 10:27 UTC. Checked 2026-11-12 14:36 +01:00. 104 remote branches are not contained in `origin/main` before this branch is pushed, mostly earlier doc-sync branches that are behind. One product commit is not in `main`: `57411b2` on `origin/chore/ruff-cleanup-20261108` (ruff format). That branch is 11 commits behind `main` and has no pull request. The tree of `origin/cursor/vorgangsleitstand-b8e4` (`3f3cac6`) differs from `origin/main` only in `.runtime/last-deploy-*` and a missing `docs/dora-metrics.md`; `vorgang.html` is the same in both trees. The branch is still not contained in `main` because #67 was squash-merged. Other named feature branches (Sprint 001, dashboard nav, Q2P, Promise, analytics, Quoter deep link) are leftovers after squash merges and are behind `main`. The repository rulesets list was empty. Classic branch protection on `main` returned 403. `prod` `protection_rules` was empty on a re-read at 2026-11-12 14:36 +01:00. Pushes of these branches also record a failed Actions run named `.github/workflows/pr-review.yml` with no jobs. The Fetch PR diff step in that file has two `env` keys.

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off until an operator enables them in the host env. Committed files do not enable them |
| Dockerfile + docker-compose.yml | ✅ deployed on DEV by `deploy-dev` | Self-hosted runner on the DEV host recreates `collector` and `api` and requires `/health/live`. The in-repo stamp `.runtime/last-deploy-*` was last committed in `cd6440f` and still reads 2026-11-07 21:50 +01:00 / `6ccc036`, which lags the later successful Actions runs |

## Sprint 005 – Quote-to-Promise Cockpit  ✅ Merged

The analytics engine also shipped under the name Sprint 005 (#5, migrations `005`/`006`). This section is the Quote-to-Promise cockpit (#33, #39), migrations `004` and `008`.

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

## Vorgangsleitstand  ✅ Merged (#67)

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht. Der Header hält Betrieb, Q2P und Promise sichtbar (#62). Die statischen Header-Dateien auf `origin/cursor/vorgangsleitstand-b8e4` stimmen mit `main` überein. Commit `3f3cac6` ist kein Ancestor; der Branch-Tip hängt nur bei den Deploy-Stempeln und bei `docs/dora-metrics.md` hinterher.

## Analytics and Schwachstellen  ✅ Merged (#5, #6, #12)

`bdx.analytics` computes KPIs, detects anomalies, and tunes thresholds. Migration `006` adds the diagnosis layer: measurement quality, flow segments, lateness causes, and bottleneck rank. The UI is `/analytics`. REST lives under `/api/v1/analytics/` (`kpis`, `trends`, `anomalies`, `thresholds`, `quality`, `flow`, `causes`, `bottleneck`, `weaknesses`, and `POST /run`).

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  ✅ On main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest with `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. `lint-cleanup.yml` exists for a later ruff format PR |
| **`.github/workflows/integration.yml`** | ✅ written, nightly red | cron `0 3 * * *` + `workflow_dispatch`. Scheduled runs 2026-11-08 through 2026-11-12 failed in `Install ODBC Driver 18` before pytest. The 2026-11-12 run is Actions `43202844646` (10:43 UTC). The test fixture keeps Service Layer writes off |
| **`.github/workflows/deploy-dev.yml`** | ✅ running | push to `main` builds `ghcr.io/<repo>/bdx-intelligence:dev` plus a SHA tag, pushes to GHCR, then deploys on the self-hosted runner on the DEV host (no SSH hop): `docker compose pull`, migrations, recreate `collector` + `api`, smoke test `/health/live`. The job aborts if the host env would allow Service Layer writes. Latest success seen this sync: `cd6440f`, 2026-11-10 07:22 (UTC+1) |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; uses the `prod` environment. The workflow comments expect required reviewers, but the environment API returned no protection rules (re-read 2026-11-12 14:36 +01:00). Inputs include `run_migrations` and `confirm_sl_write` (that input must be `true`); pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live` |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 on `main`, invalid | Intended: PR open/sync/reopen runs `scripts/pr_review.py` (bug + security, one comment, advisory). The Fetch PR diff step has two `env` keys, so pushes record a failed Actions run with no jobs |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml` tweaks** | ✅ on `main` | advisory lint/typecheck and image-name wiring landed with the CI commits. A separate ruff-format branch (`origin/chore/ruff-cleanup-20261108`) is still unmerged |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The tree is on `origin/main`.** Workflows, `scripts/`, `tests/integration/`,
  `src/bdx/agents/`, `AGENTS.md`, `.cursor/prompts/`, and `.cursor/rules/`
  are committed. This sync started from a clean tree matching `origin/main`
  at `cd6440f`. DEV deploy no longer uses the SSH secrets; it runs on the
  self-hosted runner (`scripts/prepare-dev-host.sh`).
* **Settings this token could read:** GitHub environments `dev`, `prod`, and
  `CURSOR_API_KEY` exist. Re-read 2026-11-12 14:36 +01:00: `prod` still
  returned an empty `protection_rules` list, so required reviewers are not
  configured there. The repository rulesets list was empty. Classic branch
  protection and the Actions secrets list returned 403, so this sync does
  not claim those are set or missing.
* **Still open for the original acceptance:** required reviewers on `prod`,
  branch protection that requires `ci.yml`, and confirmation that
  `CURSOR_API_KEY` plus the nightly integration secrets exist. Ruff cleanup
  on `origin/chore/ruff-cleanup-20261108` is not merged, which is why ruff
  stays advisory.
* **PR CI on 2026-11-12 is split.** Docs PRs based on `cd6440f` failed
  through 05:33 UTC in `tests/test_analytics.py::test_machine_utilization_with_calendar`
  (`assert None is not None`; 1 failed, 178 passed, 8 deselected).
  The 06:35 UTC run, the 07:39 UTC run (Actions `43176820152`), the
  08:36 UTC run (Actions `43184320869`), the 09:36 UTC run
  (Actions `43192961156`), the 10:34 UTC run (Actions `43201569835`), the
  11:37 UTC run (Actions `43210723137`), and the 12:37 UTC run
  (Actions `43219558353`, PR #106) passed. The 12:37 UTC run reported
  179 passed, 8 deselected, coverage total 73.95 % (5930 statements,
  1545 missed, displayed as 74 %) against a 68 % gate. The 09:36 UTC and
  11:37 UTC runs reported the same totals. The test keys the shift calendar
  to the current UTC weekday and a 06:00–14:00 shift. Push CI for the same SHA succeeded on 2026-11-10. This sync does
  not change product code.
* **Nightly integration does not reach SAP.** The scheduled runs on
  2026-11-08, 2026-11-09, 2026-11-10, 2026-11-11 and 2026-11-12 failed in
  `Install ODBC Driver 18` (`gpg` could not open `/dev/tty`, step exit 2).
  Pytest did not start. The 2026-11-12 run is Actions `43202844646`
  (started 10:43 UTC). The failure notice still says to investigate the
  DEV SAP contract. That notice does not match the failed step.
* **`pr-review.yml` fails before any job.** Pushes record a failed Actions
  run whose name is the workflow path and whose job list is empty. The
  Fetch PR diff step has two `env` keys. This sync leaves the workflow
  file unchanged.



## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ probed 2026-11-07 with Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Commit `7d0fb2f` removed `DENY CONTROL` from the `bdx_readonly` script because that deny blocked CONNECT, and added `docs/sql/reset_bdx_readonly.sql`. This sync did not probe LDSAP, so it does not claim the login is usable today |
| PostgreSQL event store | ✅ probed 2026-11-07: container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002**. Later successful `deploy-dev` runs execute `migrate`. This sync did not query Postgres, so the live schema is not re-confirmed |
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
| **`prod` reviewers and branch protection** | `prod` exists with no protection rules (re-read 2026-11-12 14:36 +01:00). Repository rulesets list was empty. Classic branch protection and Actions secrets were not readable (403). Ruff stays advisory until `origin/chore/ruff-cleanup-20261108` lands and `continue-on-error` is removed |
| **Doc-sync PR pile** | 94 open pull requests against `main` before this run (25 ready, 69 draft), all documentation (93 reconciliations plus #2). PR #99 and PR #106 stay open. This run opens one more from `cursor/projekt-dokumenten-abgleich-ce27` and does not merge |
| **Analytics calendar test** | PR CI on 2026-11-12 failed `test_machine_utilization_with_calendar` through 05:33 UTC (`assert None is not None`; 1 failed, 178 passed). Green from 06:35 UTC through 12:37 UTC (Actions `43219558353`: 179 passed, 8 deselected, coverage total 73.95 % against a 68 % gate). Push CI for `cd6440f` on 2026-11-10 was green |
| **Nightly ODBC install** | Integration runs on 2026-11-08 through 2026-11-12 fail in `Install ODBC Driver 18` before pytest. The 2026-11-12 run is Actions `43202844646` (10:43 UTC). That does not show a SAP contract break |
| **`pr-review.yml`** | Pushes record a failed Actions run with no jobs. The Fetch PR diff step has two `env` keys. Workflows stay untouched in this sync |
| SQL login `bdx_readonly` on LDSAP | create and reset scripts are in `docs/sql/`. The 2026-11-07 fix assumes the login already existed and could not CONNECT. Not re-probed this sync. DEV deploy itself is already running on the host `.env` |
| DEV deploy stamp in git | Actions has succeeded through `cd6440f`. `.runtime/last-deploy-at` / `last-deploy-sha` in the repo still say 2026-11-07 21:50 +01:00 / `6ccc036` |
| MQTT / Kafka broker | publishers are implemented. No broker is configured in git (`MQTT_ENABLED` stays off until an operator sets a host) |
| Run collector against PROD | read-only; needs a separate Postgres database (or mode-prefixed `source_key`) so DEV and PROD rows do not share `order_state`. Only single-order probes are recorded |
| SAP write-back real use | release/close/cancel/report-production exist and were DRY_RUN-verified on DEV. Real writes stay off until an operator changes the host env. Committed files do not turn writes on. `deploy-dev` aborts if the DEV host env would allow them |
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
│   ├── analytics/         # Sprint 005 KPI engine, anomalies, diagnosis
│   ├── q2p/               # Quote-to-Promise inquiry evaluation
│   ├── promise/           # Offer engine, fulfillment agents, portal
│   ├── api/               # FastAPI app, routes, static dashboard/q2p/promise/analytics/vorgang
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008 (through promise + quoter fields)
├── tests/                 # 191 test functions (183 + 8 integration; DEV SAP/SL skipped without creds)
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
