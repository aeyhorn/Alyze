# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-18 23:36 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | 🟡 on `origin/main` (`a66b194`). Product CI and DEV deploy are green on `cd6440f` (2026-11-10). Latest completed docs CI on `9e7e31b` (run 44403303298, 2026-11-18 21:36 UTC, PR #184) is green: 179 passed, 8 deselected, 1 warning, coverage 74 % (5 930 statements, 1 545 missed, 73.95 %, gate 68 % reached). The pytest summary is log line 21:37:24.925 (5.44s); the pytest job completed 21:37:28 UTC. Lint completed 21:37:10 UTC, type check 21:37:33 UTC, Docker smoke 21:37:58 UTC. The previous docs CI on `5dac68d` (run 44392917328, pytest log 20:37:32.413, 5.76s) is the same green shape. Greens of that shape run from 06:37 UTC (`8b8ea51`, run 44252602866) through 21:37 UTC. At 00:37 UTC, run 44209285859 on `fc9dae1` failed the calendar test and both lateness tests (3 failed, 176 passed, 1 560 missed, 73.69 %). The same three failed at 00:37 UTC on 2026-11-17 (run 43989085036, `c89c24a`). At 01:35 UTC, run 44216899780 on `f7c81a7` failed only `test_machine_utilization_with_calendar` (178 passed, 1 545 missed, 73.95 %). Run 44245226262 on `3982b2a` (pytest ended 05:35:20 UTC) is that same calendar-only failure. Only documentation commits sit between those SHAs. Ruff and mypy stay advisory. Nightly integration fails in the ODBC install step (latest run 44293106343, 2026-11-18 11:15 UTC, head `a66b194`; prior run 44074958149, 2026-11-17 11:32 UTC, same head). `pr-review.yml` starts no jobs (latest completed push run 44403291333, 21:36:54 UTC, `9e7e31b`, zero jobs; prior push run 44392899746, 20:37:00 UTC, `5dac68d`, zero jobs). `main` reports `protected: false`. The commit this run is about to push is not in CI yet. |
| 005 | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, quoter #39). Migrations through `008` are in the repo. SAP grants and Quoter on the DEV host were not re-checked in this run. |
| Analytics | KPI engine, anomaly detection, weakness dashboard | ✅ merged (#5, #6, #12). Alembic `005` and `006`, REST `/api/v1/analytics/*`. |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41). Alembic `007`+`008`. Vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Auftragsfenster, Belegung, gemeldeter Arbeitsgang (`/vorgang`) | ✅ merged (#67) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open. SQL login script is on `main`. Container deploy is G6. |

Test suite: unit tests on SQLite in-memory + optional integration against DEV SAP/SL. Integration suite skips cleanly when DEV creds are absent.

## Abgleich mit Git (2026-11-18)

Koordinator-Lauf. Nur diese Dokumente. Kein Shopfloor-Probe.

- `origin/main` ist `a66b194` (2026-11-16 14:23 UTC, `docs(dora): weekly metrics snapshot`). Der einzige Commit nach `cd6440f` (2026-11-10 07:21 +01:00) ist dieser DORA-Snapshot. Diese Sitzung startete auf `cursor/bc-773b475f-0890-40a0-891e-ec0d79421d0a-1deb` bei demselben Commit. Der Arbeitsbaum war sauber.
- Der Vortag liegt auf `sync/status-20261117` (Spitze `ca949f2`, PR #182, offen, mergeable, nicht gemergt). Das Datum in Europe/Paris ist weiter der 2026-11-18, deshalb schreibt dieser Lauf auf den bestehenden Branch `sync/status-20261118` (bisherige Spitze `9e7e31b`, PR #184, offen, nicht als Draft, mergeable, merge state CLEAN, nicht gemergt) und öffnet keinen zweiten Doku-PR. PR #183 (`cursor/projekt-dokumenten-abgleich-8589`, `d9d8cee`, offen, mergeable) bleibt offen. Dieser Lauf mergt nicht.
- Sprint 004 liegt auf `origin/main`: Workflows unter `.github/workflows/`, `src/bdx/agents/`, `scripts/`, `tests/integration/`, `.cursor/prompts/`.
- CI auf `cd6440f`: success (Run 42768023614). Deploy to DEV auf demselben Commit: success (Run 42768023481, Jobs „Build & Push Image“ und „Deploy to DEV host“). An `a66b194` hängt kein Produkt-CI- und kein Deploy-Lauf. Die Integration-Schedule-Läufe 44293106343 (2026-11-18 11:15 UTC) und 44074958149 (2026-11-17 11:32 UTC) liegen auf diesem SHA.
- Der Marker `bdx-intelligence/.runtime/last-deploy-sha` enthält `6ccc036`. `bdx-intelligence/.runtime/last-deploy-at` enthält `2026-11-07 21:50:15 +01:00`. Beide Dateien wurden zuletzt in `cd6440f` (2026-11-10 07:21 +01:00) committet.
- Nightly Integration, letzter abgeschlossener Lauf: 2026-11-18 11:16 UTC (Run 44293106343) auf `a66b194`. Im Job „Integration (DEV SAP + SL DRY_RUN)“ sind „Install ODBC Driver 18“ und „Notify on failure“ fehlgeschlagen; „Run integration tests“ ist skipped. Abschluss 11:16 UTC. Der Cron im Workflow ist `0 3 * * *`; GitHub hat den Schedule-Lauf um 11:15 UTC angelegt. Der vorherige Lauf 44074958149 (2026-11-17 11:32 UTC, derselbe Head) scheiterte genauso. Die geplanten Läufe vom 2026-11-12 bis 2026-11-16 sind ebenfalls failure, zuletzt 2026-11-16 10:44 UTC (Run 43851477564) auf `cd6440f`. Kein neuerer Integration-Lauf bis 23:36 UTC+1.
- `pr-review.yml`: der Schritt „Fetch PR diff“ hat zwei `env`-Blöcke (Zeilen 46 und 51). Der nächste Schritt „Run review“ beginnt in Zeile 54, sein `env` in Zeile 55. Der Push-Lauf 44403291333 (2026-11-18 21:36:54 UTC, `9e7e31b` auf `sync/status-20261118`) endet mit null Jobs und `conclusion: failure`. Der Push-Lauf 44392899746 (2026-11-18 20:37:00 UTC, `5dac68d`) endet genauso.
- Docs-CI von `9e7e31b` (Run 44403303298, 2026-11-18 21:36 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Die Pytest-Zusammenfassung steht in Logzeile 21:37:24.925 (5,44 s). Der Pytest-Job endete 21:37:28 UTC. Lint endete 21:37:10 UTC, Type Check 21:37:33 UTC, Docker-Smoke 21:37:58 UTC. Der vorherige Docs-CI von `5dac68d` (Run 44392917328, Pytest-Log 20:37:32.413, 5,76 s) hat dieselbe grüne Form. Dieselbe grüne Form läuft von 06:37 UTC (`8b8ea51`, Run 44252602866) bis 21:37 UTC. Um 00:37 UTC war Run 44209285859 auf `fc9dae1` rot mit drei Tests (176 passed, 1 560 missed, 73,69 %): `test_machine_utilization_with_calendar` plus `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle`. Dieselben drei Tests waren auf `c89c24a` um 00:37 UTC rot (Run 43989085036, 176 passed). Um 01:35 UTC auf `f7c81a7` (Run 44216899780) und um 05:35 UTC auf `3982b2a` (Run 44245226262, Pytest-Ende 05:35:20 UTC) fällt nur der Kalender-Test (178 passed, 1 545 missed, 73,95 %). Um 01:35 UTC auf `cbec5e1` (Run 43996707190) und um 05:39 UTC auf `b69a171` (Run 44025523409) fällt ebenfalls nur der Kalender-Test. Grün mit 179 passed sind Run 44094522392 (13:37 UTC), Run 44191321190 auf `ca949f2` (22:35:09 UTC) und Run 44200811809 auf `61f842b` (Pytest-Ende 23:36:40 UTC). Zwischen diesen SHAs liegen nur Dokumentations-Commits. Der Commit dieses Laufs ist beim Schreiben noch nicht in CI.
- Auto-merge von `9e7e31b` (Run 44403303617, erstellt 2026-11-18 21:36:58 UTC) hat PR #184 übersprungen: Logzeile 21:37:09.463 sagt `No 'trivial' label — skipping auto-merge.` `PR_LABELS` war `[]`. Auto-merge von `5dac68d` (Run 44392917342, Logzeile 20:37:11.343) hat denselben PR genauso übersprungen. Der PR hat keine Labels, ist vor diesem Push mergeable (merge state CLEAN) und bleibt offen.
- Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules (gelesen 2026-11-18 23:35 UTC+1). Die Branch-Ressource von `main` meldet `protected: false` (Commit `a66b194`). Rulesets: 0. Der Branch-Protection-Endpunkt und die Actions-Secret-Liste antworten mit HTTP 403.
- 172 Pull Requests sind offen, alle Dokumentation. Die höchste Nummer ist 184. Vom exakten Abgleichssatz weichen acht Titel ab und bleiben Dokumentation: #2, #8, #19, #30, #38, #54, #60 und #61. Kein offener Produkt-PR. 183 Remote-Branches liegen nicht in `origin/main`. Außerhalb von `cursor/` und `sync/status-*` sind das `origin/chore/ruff-cleanup-20261108` (`57411b2`) und `origin/chore/ruff-cleanup-20261115` (`1c46e17`). Beide haben keinen PR.
- DORA-Schedule Run 43885095274 (erstellt 2026-11-16 14:22 UTC, Abschluss 14:23 UTC, head `cd6440f`) ist success und hat `a66b194` auf `main` gelegt. Die Zahlen stehen in `docs/dora-metrics.md` (Fenster seit 2026-10-17, erzeugt 2026-11-16 14:22 UTC): Deploy-Frequenz 0,77/Tag (23 Deploys, 13 ok), Cycle Time Median 0,6 h, MTTR Median 244,5 min, Change-Failure-Rate 34,8 %, CI-Flakiness 18,4 % (50/272), 12 gemergte PRs.
- Quoter-Deep-Link bleibt Spezifikation (`docs/QUOTER_DEEP_LINK.md`). In `*.py`, `*.html` und `*.js` auf `origin/main` gibt es keinen Treffer auf `return_url`.
- Dieser Lauf schreibt weiter auf `sync/status-20261118` und mergt nicht. PR #182, PR #183 und PR #184 bleiben offen.
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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off until an operator turns the dry-run guard off in the host environment. |
| Dockerfile + docker-compose.yml | ✅ on `main`, DEV deploy green 2026-11-10 | `deploy-dev.yml` succeeded on `cd6440f` (migrate, recreate `collector` + `api`, `/health/live`). The SQL login `bdx_readonly` stays open for a container that does not use Windows integrated auth. |

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

**Deploy notes**: repo head is Alembic `008`. Successful DEV deploys after the Q2P merge run `docker compose run --rm migrate`. Still to confirm on the host: `grant_q2p_readonly.sql` on LDSAP, `QUOTER_ENABLED=true`, `QUOTER_BASE_URL`. Cockpit path: `/q2p`.

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

**Deploy notes**: Alembic `007` and `008` are in the repo. Successful DEV deploys after #41 run the workflow migrate step. This run did not open `/promise` on the host. Publish a contract, then share the portal link.

## Analytics – KPI, anomalies, weakness dashboard  ✅ Merged (#5, #6, #12)

On `origin/main`: package `bdx.analytics`, Alembic `005` (analytics tables) and `006` (diagnosis tables), REST `/api/v1/analytics/*` (KPIs, trends, anomalies, thresholds, quality, flow, causes, bottleneck, weaknesses, `POST /run`), UI `/analytics`. This run did not re-probe the live dashboard.

## Vorgangsleitstand

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  🟡 On origin/main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | 🟡 last product run green, latest docs CI green | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest coverage gate is `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. Last `main` run on `cd6440f` succeeded (Run 42768023614). `a66b194` has no product CI run. Latest completed docs CI on `5dac68d` (run 44392917328, 2026-11-18 20:37 UTC, PR #184) is green: 179 passed, 8 deselected, 1 warning, coverage 74 % (5 930 statements, 1 545 missed, 73.95 %, gate 68 % reached). Pytest summary log line 20:37:32.413 (5.76s); pytest job completed 20:37:36 UTC. Lint completed 20:37:25 UTC, type check 20:37:33 UTC, Docker smoke 20:37:59 UTC. The previous docs CI on `592d416` (run 44383356996, pytest log 19:44:45.969, 4.76s) is the same green shape. Greens of that shape run from 06:37 UTC (`8b8ea51`) through 20:37 UTC. At 00:37 UTC run 44209285859 on `fc9dae1` failed the calendar test and both lateness tests (176 passed, 1 560 missed, 73.69 %). At 05:35 UTC run 44245226262 on `3982b2a` failed only `test_machine_utilization_with_calendar` (178 passed). Only documentation commits sit between those SHAs. The commit this run is about to push is not in CI yet. |
| **`.github/workflows/integration.yml`** | 🟡 on `main`, nightly red | cron `0 3 * * *` + `workflow_dispatch`. Last completed run 2026-11-18 11:16 UTC (44293106343, head `a66b194`) failed in „Install ODBC Driver 18“ and „Notify on failure“; „Run integration tests“ was skipped. GitHub created that schedule run at 11:15 UTC. The prior schedule run 44074958149 (2026-11-17 11:32 UTC, same head) failed the same way. Scheduled runs from 2026-11-12 through 2026-11-16 failed the same way (last of those: 43851477564 at 10:44 UTC on `cd6440f`). The fixture keeps the Service Layer dry-run guard on, so a green run still cannot write to SAP. |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, last run green | push to `main` builds `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` plus a sha tag. The self-hosted runner on the DEV host pulls, migrates, and recreates `collector` + `api`. Smoke: `/health/live`. The job aborts when the host env file turns the dry-run guard off. Last success: 2026-11-10, commit `cd6440f` (Run 42768023481). No deploy run is attached to `a66b194`. |
| **`.github/workflows/deploy-prod.yml`** | ✅ written, reviewers not confirmed | `workflow_dispatch` only. The workflow text expects required reviewers on environment `prod`. The Environments API on 2026-11-18 22:34 UTC+1 reported no protection rules for `prod`. Inputs include `run_migrations` and `confirm_sl_write`. |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 invalid workflow file | Step „Fetch PR diff“ has two `env` blocks (lines 46 and 51). The next step „Run review“ starts at line 54; its `env` is line 55. Push runs finish with zero jobs. Latest completed push run 44392899746 (2026-11-18 20:37:00 UTC, `5dac68d` on `sync/status-20261118`) has conclusion failure and job count 0. Prior push run 44382392414 (19:38 UTC, `592d416`) failed the same way. The intended path is `scripts/pr_review.py` on PR open/sync/reopen. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch`. Run 44392917342 (`5dac68d`, created 2026-11-18 20:37:06 UTC) skipped PR #184: log line 20:37:11.343 says `No 'trivial' label — skipping auto-merge.` `PR_LABELS` was `[]`. Run 44383357080 (`592d416`, 19:44 UTC) skipped the same way. PR #184 has no labels. |
| **`.github/workflows/dora.yml`** | ✅ ran this week | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` commits `docs/dora-metrics.md`. Schedule run 43885095274 (2026-11-16 14:22 UTC, head `cd6440f`) succeeded and pushed `a66b194`. |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | dev extras and compose are in the tree that `origin/main` already has. Lint-only branches `chore/ruff-cleanup-20261108` and `chore/ruff-cleanup-20261115` are not merged and have no open PR. |
| **`.github/workflows/lint-cleanup.yml`** | 🟡 branch pushed, PR step red | Sunday cron `0 4 * * 0` plus `workflow_dispatch`. Run 43710438515 (2026-11-15 11:45 UTC) applied ruff fixes and the suite step passed; „Create trivial PR“ then failed because GitHub Actions may not create pull requests. `chore/ruff-cleanup-20261115` has no PR. CI lint stays advisory. |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The tree is on `origin/main`.** Workflows, agents, scripts, integration tests, prompts and rules are in `a66b194`. The only commit after `cd6440f` is the DORA snapshot. Nothing from Sprint 004 is only local.
* **DEV deploy runs on the self-hosted runner.** `deploy-dev.yml` does not read `DEV_SSH_*`. PROD still documents `PROD_SSH_*`.
* **The Actions secret list was not readable** in this run (HTTP 403). Names the workflows still mention: `CURSOR_API_KEY` (triage and PR review, no-op without it), `PROD_SSH_*`, and the nightly SAP, Service Layer, and Postgres secrets. The nightly job fails in the ODBC install step, before those secrets are used.
* **Repo settings read this run (2026-11-18 22:34 UTC+1):** environments `dev`, `prod`, and `CURSOR_API_KEY` have empty protection-rule lists. The `main` branch resource reports `protected: false`. Repository rulesets: length 0. The branch-protection endpoint and the Actions secret list returned HTTP 403.
* **`pr-review.yml` starts zero jobs** because „Fetch PR diff“ has two `env` keys (lines 46 and 51). Latest completed push run 44392899746 (2026-11-18 20:37:00 UTC, `5dac68d`, conclusion failure, job count 0). Prior push run 44382392414 (19:38 UTC, `592d416`) ended the same way.
* **Docs CI on `5dac68d` is green.** Run 44392917328 (2026-11-18 20:37 UTC, PR #184) passed lint, type check, Docker smoke, and the tests job: 179 passed, 8 deselected, 1 warning, 74 % (5 930 statements, 1 545 missed, 73.95 %, gate 68 % reached). Pytest summary log line 20:37:32.413 (5.76s); the pytest job completed 20:37:36 UTC. Lint completed 20:37:25 UTC, type check 20:37:33 UTC, Docker smoke 20:37:59 UTC. The previous docs CI on `592d416` (run 44383356996, pytest log 19:44:45.969, 4.76s) is the same green shape. Greens of that shape run from 06:37 UTC through 20:37 UTC. At 00:37 UTC run 44209285859 on `fc9dae1` failed the calendar test and both lateness tests (3 failed, 176 passed, 1 560 missed, 73.69 %). Run 44245226262 on `3982b2a` (pytest ended 05:35:20 UTC) failed only the calendar test. Only documentation commits sit between those SHAs. The commit this run is about to push is not in CI yet.
* **Landing Sprint 004 in git is done.** Still open: the nightly ODBC install, the invalid PR-review workflow, reviewers and branch protection, and a lint-cleanup PR that Actions is not allowed to open. Latest completed docs CI is `5dac68d` (run 44392917328, pytest summary 20:37:32.413, 5.76s, 179 passed, 8 deselected, 1 warning, 1 545 missed, 73.95 %, gate 68 % reached).

## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth that day (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Commit `7d0fb2f` the same day records that SQL login `bdx_readonly` already existed and could not open `DEV_SBO_LEISINGER` because `DENY CONTROL` blocked CONNECT. Not re-checked in this run. |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` and `report-production 38559 -q 5 -w W01` → both blocked by the dry-run guard, audited in `sl_operations` |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

This probe is from 2026-11-07. Later commits added Alembic `003`–`008`. Successful DEV deploys since then run `docker compose run --rm migrate`. This coordinator run did not query the live database, so the schema row above stays the last direct observation (schema 002 on that day).

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Docs CI on `5dac68d`** | Run 44392917328 (2026-11-18 20:37 UTC, PR #184) is green. Lint, type check, Docker smoke, and the tests job succeeded: 179 passed, 8 deselected, 1 warning. Coverage is 74 % (5 930 statements, 1 545 missed, 73.95 %). The 68 % gate was reached. Pytest summary log line 20:37:32.413 (5.76s); the pytest job completed 20:37:36 UTC. Lint completed 20:37:25 UTC, type check 20:37:33 UTC, Docker smoke 20:37:59 UTC. The previous run 44383356996 on `592d416` (pytest log 19:44:45.969, 4.76s) is the same green shape. Greens of that shape run from 06:37 UTC (`8b8ea51`) through 20:37 UTC. At 00:37 UTC run 44209285859 on `fc9dae1` failed the calendar test and both lateness tests (176 passed, 1 560 missed, 73.69 %). At 05:35:20 UTC run 44245226262 on `3982b2a` failed only `test_machine_utilization_with_calendar`. The same three tests failed at 00:37 UTC on 2026-11-17 (run 43989085036, `c89c24a`). Only documentation commits sit between those SHAs. The commit this run is about to push is not in CI yet. |
| **Nightly integration** | Last completed run 2026-11-18 11:16 UTC (44293106343, head `a66b194`) fails in „Install ODBC Driver 18“ and „Notify on failure“. „Run integration tests“ was skipped. The workflow cron is `0 3 * * *`; GitHub created this schedule run at 11:15 UTC. The prior run 44074958149 (2026-11-17 11:32 UTC, same head) failed the same way. Scheduled runs from 2026-11-12 through 2026-11-16 failed the same way, last of those 43851477564 at 10:44 UTC on `cd6440f`. No newer integration run as of 2026-11-18 22:34 UTC+1. |
| **PR review workflow** | `pr-review.yml` has two `env` blocks on „Fetch PR diff“ (lines 46 and 51). The next step „Run review“ starts at line 54; its `env` is line 55. Push run 44392899746 (2026-11-18 20:37:00 UTC, `5dac68d`) finished with zero jobs and conclusion failure. Push run 44382392414 (19:38 UTC, `592d416`) finished the same way. |
| **`prod` reviewers and branch protection** | Environments `dev`, `prod`, and `CURSOR_API_KEY` have empty protection-rule lists (read 2026-11-18 22:34 UTC+1). The `main` branch resource reports `protected: false`. Rulesets length is 0. The protection endpoint and the Actions secret list returned HTTP 403. |
| **DORA weekly** | Cron `0 6 * * 1` created schedule run 43885095274 on 2026-11-16 at 14:22 UTC (finished 14:23 UTC, head `cd6440f`). The job committed `a66b194`. Snapshot: deploy frequency 0.77/day, cycle time median 0.6 h, MTTR median 244.5 min, change failure rate 34.8 %, CI flakiness 18.4 % (50/272), 12 merged PRs. No product CI or deploy-dev run is attached to `a66b194`. Integration schedule runs 44293106343 (2026-11-18 11:15 UTC) and 44074958149 (2026-11-17 11:32 UTC) are. |
| SQL login `bdx_readonly` on LDSAP | `create_bdx_readonly.sql` and `reset_bdx_readonly.sql` are on `main`. Commit `7d0fb2f` records that the login existed on 2026-11-07 and could not open `DEV_SBO_LEISINGER` (`DENY CONTROL` blocked CONNECT). Not re-checked against LDSAP in this run. |
| Plaintext password in git | `docs/sql/reset_bdx_readonly.sql` contains a quoted password literal for the SQL login. It does not belong in the repo. This row does not repeat the value. |
| DEV compose on the Docker host | `deploy-dev.yml` last succeeded 2026-11-10 on `cd6440f` (Run 42768023481: migrate, recreate `collector` + `api`, `/health/live`). `.runtime/last-deploy-sha` contains `6ccc036`. `.runtime/last-deploy-at` contains `2026-11-07 21:50:15 +01:00`. Both files were last committed in `cd6440f`. `origin/main` is `a66b194`; no deploy run is attached to that SHA. |
| MQTT / Kafka broker | Publishers are implemented. `MQTT_ENABLED=false`, no broker configured in the tree. |
| Run collector against PROD | Read-only; needs a separate Postgres database or a mode-prefixed `source_key`. Only single-order probes are recorded (2026-11-07). |
| SAP write-back for real | Stays on the dry-run guard until an operator opens that guard in the host env. `.env.example` in git turns the guard off; this run leaves the file as it is. The 2026-11-10 DEV deploy did not trip the host-env abort. Operations: release, close, cancel, report-production. |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |
| Ruff cleanup branches | `origin/chore/ruff-cleanup-20261108` (`57411b2`) and `origin/chore/ruff-cleanup-20261115` (`1c46e17`, 2026-11-15 11:45 UTC) are each one commit ahead of their base and have no open PR. Run 43710438515 pushed the newer branch, then „Create trivial PR“ failed because Actions may not create pull requests. CI lint stays advisory. |
| Open sync PRs | 172 open pull requests, all documentation. Highest number is 184 (`sync/status-20261118`, tip before this commit `5dac68d`, open, mergeable, merge state CLEAN, not merged). Eight titles differ from the exact reconcile sentence and are still documentation: #2, #8, #19, #30, #38, #54, #60, and #61. No product PR is open. This run continues that branch and does not open a second PR. PR #182 (`ca949f2`) and PR #183 (`d9d8cee`) stay open. This run does not merge. |

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
│   ├── analytics/         # Sprint 005 analytics: KPIs, anomalies, weakness dashboard
│   ├── api/               # FastAPI app, routes, static/dashboard.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008
├── tests/                 # unit tests on SQLite; tests/integration/ skips without DEV creds.
│                          # Docs CI 44326694238 (2026-11-18 14:39 UTC): 179 passed, 8 deselected, 74 % coverage
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
