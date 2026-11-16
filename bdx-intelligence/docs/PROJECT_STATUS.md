# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-16 12:38 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | 🟡 on `origin/main` — CI and DEV deploy green on `cd6440f` (2026-11-10); ruff/mypy advisory; coverage gate 68 %; nightly 2026-11-16 10:44 UTC (Run 43851477564) fails in the ODBC install step, same as 2026-11-15; `pr-review.yml` starts zero jobs (latest Run 43850636733 on `031e040`); docs CI of `031e040` (PR #178, Run 43850646182) is green with 179 passed, 8 deselected, and 74 %; the Monday DORA cron due 06:00 UTC still has no run at 12:38 UTC+1 |
| 005 | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, quoter #39) — DEV deploy runs migrations; SAP grants and Quoter on DEV not re-checked 2026-11-15 |
| Analytics | KPI engine, anomaly detection, weakness dashboard | ✅ merged (#5, #6, #12) — Alembic `005` and `006`, REST `/api/v1/analytics/*` |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41) — Alembic `007`+`008`; vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Auftragsfenster, Belegung, gemeldeter Arbeitsgang (`/vorgang`) | ✅ merged (#67) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open (SQL login script ready; container deploy is G6) |

Test suite: unit tests on SQLite in-memory + optional integration against DEV SAP/SL. Integration suite skips cleanly when DEV creds are absent.

## Abgleich mit Git (2026-11-16)

Koordinator-Lauf, nur diese Dokumente. Kein Shopfloor-Probe (SAP, Maschinen, Postgres live).

- Abgleichsbasis ist `origin/main` bei `cd6440f` (2026-11-10 07:21 +01:00, „Update deployment timestamp and SHA for the latest release“). Diese Sitzung startete auf `cursor/projekt-dokumenten-abgleich-4b74`, der auf denselben Commit zeigte. Der Arbeitsbaum war sauber. Seit `031e040` (2026-11-16 10:38 UTC auf `sync/status-20261116`, PR #178) hat `origin/main` keinen neuen Commit. Dieser Lauf schreibt denselben Branch fort und öffnet keinen weiteren Doku-PR. PR #178 bleibt offen und wird nicht gemergt.
- Sprint 004 liegt auf `origin/main`: Workflows unter `.github/workflows/`, `src/bdx/agents/`, `scripts/`, `tests/integration/`, `.cursor/prompts/`.
- CI auf `cd6440f`: success (Run 42768023614). Deploy to DEV auf demselben Commit: success (Run 42768023481, Jobs „Build & Push Image“ und „Deploy to DEV host“, Abschluss 2026-11-10 06:24 UTC). Der Deploy läuft auf dem Self-hosted-Runner des DEV-Hosts, ohne SSH-Hop, und führt `docker compose run --rm migrate` plus `/health/live` aus.
- Der committete Marker `bdx-intelligence/.runtime/last-deploy-sha` zeigt noch `6ccc036` vom 2026-11-07 21:50 +01:00 und hinkt hinter dem grünen Actions-Lauf her.
- Nightly Integration: der letzte abgeschlossene Lauf ist 2026-11-16 10:44 UTC (Run 43851477564) auf `cd6440f`, Abschluss 10:44:17 UTC. Fehlgeschlagen sind die Schritte „Install ODBC Driver 18“ und „Notify on failure“; ein pytest-Schritt ist nicht unter den fehlgeschlagenen Schritten. Der Cron ist `0 3 * * *`; der Lauf startete um 10:44 UTC. Der vorherige Lauf 2026-11-15 10:28 UTC (Run 43704248636) ist an denselben Schritten fehlgeschlagen. Die geplanten Läufe vom 2026-11-08 bis 2026-11-14 sind ebenfalls failure (2026-11-14: Run 43582578926). Die Abfrage nach Integration-Läufen mit Erstelldatum 2026-11-16 liefert genau Run 43851477564. Zwei ältere Actions-Läufe stehen seit 2026-11-11 20:41 UTC auf queued: CI 43097537658 und Auto-merge 43097537724 (Branch `cursor/projekt-dokumente-abgleich-a8a9`, Commit `f89c817`). Sie gehören nicht zu diesem Cron.
- `.github/workflows/pr-review.yml` hat auf dem Schritt „Fetch PR diff“ zwei `env`-Blöcke. Push-Läufe enden ohne Job. Letzter Lauf: 2026-11-16 10:38 UTC, Run 43850636733, Commit `031e040` auf `sync/status-20261116`, conclusion failure, null Jobs. Der Lauf davor (43841169727, 2026-11-16 09:35 UTC, `dc20523`) endete gleich, ebenso 43832477042 (2026-11-16 08:35 UTC, `a79ab84`), 43825406548 (2026-11-16 07:39 UTC, `50039ba`), 43818061702 (2026-11-16 06:37 UTC, `08c3f6b`), 43811254306 (2026-11-16 05:35 UTC, `71c5a03`) und 43805165533 (2026-11-16 04:36 UTC, `cc87d72`).
- GitHub-Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. Die Environments-API meldet für alle drei keine Protection Rules (in diesem Lauf um 12:35 UTC+1 am 2026-11-16 gelesen). `deploy-prod.yml` beschreibt erforderliche Reviewer. Die Branch-Ressource von `main` meldet `protected: false`. Die Ruleset-Liste hat die Länge 0. GET `/branches/main/protection` und die Actions-Secret-Liste antworten mit HTTP 403.
- 168 offene PRs, sämtlich Dokumentation: 160 mit dem Titel „docs: reconcile project status and goals“, fünf mit „docs: reconcile project status, goals and requirements“, dazu drei einzelne Doku-Titel. Kein offener Produkt-PR. Höchste Nummer ist 180. 179 Remote-Branches liegen nicht in `origin/main`. Außerhalb von `cursor/` und `sync/status-*` sind das `origin/chore/ruff-cleanup-20261108` (`57411b2`, 2026-11-08) und `origin/chore/ruff-cleanup-20261115` (`1c46e17`, 2026-11-15 11:45 UTC). Beide haben keinen PR. Dieser Lauf hängt den Commit an `sync/status-20261116` (PR #178). Der bisherige Tip dieses Branches ist `031e040` (2026-11-16 10:38 UTC). Seit 05:35 UTC (PR #180) ist kein neuer PR hinzugekommen. PR #179 und PR #180 bleiben offen.
- Lint Cleanup (Cron `0 4 * * 0`): der Lauf 2026-11-15 11:45 UTC (Run 43710438515) hat `ruff --fix`, Format und „Verify suite still green“ bestanden. Der Schritt „Create trivial PR“ ist fehlgeschlagen, weil GitHub Actions keine Pull Requests anlegen darf. Deshalb liegt `origin/chore/ruff-cleanup-20261115` ohne PR. Der Lauf vom 2026-11-08 (Run 42473962358) ist ebenfalls failure.
- Der Docs-CI auf `sync/status-20261116` für Commit `cc87d72` (Run 43805169716, 2026-11-16 04:36 UTC, PR #178) scheitert im Job Tests: 1 failed, 178 passed, 8 deselected. Die TOTAL-Zeile zeigt 74 % bei Gate 68 % (5 930 Statements, 1 545 missed). Fehlgeschlagen ist `test_machine_utilization_with_calendar` (`assert None is not None`). Lint, Type Check und Docker-Smoke dieses Laufs sind success. Derselbe Test scheitert im Docs-CI von `ecc180b` (Run 43799221206), von `a22c5d6` (Run 43793408407, 74 %) und von `98c607f` (Run 43787512471, 73,95 %). Der Docs-CI von PR #180 (Run 43811268796, 2026-11-16 05:35 UTC, Commit `71c5a03`) scheitert am selben Test (1 failed, 178 passed, 74 %). Der ältere Docs-CI desselben Branches (Run 43775742168, 2026-11-15 23:36 UTC, Commit `058466c`) ist success. Der Docs-CI von PR #179 (Run 43781268705, 2026-11-16 00:35 UTC, Commit `69b15ca`, nur `PROJECT_STATUS.md` und `PROJECT_GOALS.md` auf dem Produktbaum `cd6440f`) scheitert mit 3 failed und 176 passed bei 73,69 % Coverage: `test_machine_utilization_with_calendar`, `test_lateness_scrap_when_no_material_context`, `test_lateness_waiting_idle`. Der Push-CI von `cd6440f` bleibt der Erfolg vom 2026-11-10 (Run 42768023614). Auto-merge auf PR #178 für `cc87d72` (Run 43805169727) ist success und hat nicht gemergt: das Log sagt „No 'trivial' label — skipping auto-merge.“ Die Läufe 43799221191 (`ecc180b`) und 43793408393 (`a22c5d6`) haben denselben Sprung gemacht. Der Docs-CI von `08c3f6b` (Run 43818069462, 2026-11-16 06:37 UTC, PR #178) ist success: Tests 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed, Gate 68 %). `test_machine_utilization_with_calendar`, `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle` sind in diesem Lauf passed. Lint, Type Check und Docker-Smoke sind success. Auto-merge (Run 43818069370) hat PR #178 für `08c3f6b` übersprungen, weil das Label `trivial` fehlt. Der Docs-CI von `50039ba` (Run 43825413067, 2026-11-16 07:40 UTC, PR #178) ist success: Tests 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed, Gate 68 %). Lint, Type Check und Docker-Smoke sind success. Auto-merge (Run 43825413115) hat PR #178 für `50039ba` übersprungen, das Log sagt „No 'trivial' label — skipping auto-merge.“ Der Docs-CI von `a79ab84` (Run 43832485591, 2026-11-16 08:35 UTC, PR #178) ist success: 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed; die Coverage-Zeile nennt 73,95 %, Gate 68 %). Lint, Type Check und Docker-Smoke sind success. Auto-merge (Run 43832485594) hat PR #178 für `a79ab84` übersprungen, das Log sagt „No 'trivial' label — skipping auto-merge.“ Der Docs-CI von `dc20523` (Run 43841180628, 2026-11-16 09:36 UTC, PR #178) ist success: 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed; die Coverage-Zeile nennt 73,95 %, Gate 68 %). Lint, Type Check und Docker-Smoke sind success. Auto-merge (Run 43841180693) hat PR #178 für `dc20523` übersprungen, das Log sagt „No 'trivial' label — skipping auto-merge.“ Der Docs-CI von `031e040` (Run 43850646182, 2026-11-16 10:38 UTC, PR #178) ist success: 179 passed, 8 deselected, 1 warning, TOTAL-Zeile 74 % (5 930 Statements, 1 545 missed, Gate 68 %). Lint, Type Check und Docker-Smoke sind success. Auto-merge (Run 43850646194) hat PR #178 für `031e040` übersprungen, das Log sagt „No 'trivial' label — skipping auto-merge.“ Dieser Lauf ändert keinen Produktcode und mergt nicht.
- SQL-Login: Commit `7d0fb2f` (2026-11-07) hält fest, dass `bdx_readonly` auf LDSAP existierte und `DEV_SBO_LEISINGER` nicht öffnen konnte, weil `DENY CONTROL` CONNECT blockierte. `docs/sql/reset_bdx_readonly.sql` auf `main` enthält ein Klartext-Passwort für diesen Login. Dieser Lauf hat LDSAP nicht verbunden und wiederholt das Passwort nicht.
- `.env.example` schaltet den Service-Layer-Dry-Run aus. Die Datei bleibt in diesem Lauf unverändert. Die Host-`.env` liegt nicht im Git. Der grüne Deploy vom 2026-11-10 ist am Guard nicht abgebrochen.
- DORA-Snapshot in `docs/dora-metrics.md`: erzeugt 2026-11-09 14:47 UTC (Run 42638115770, success, Commit `bbdfc8f`). Der Wochen-Cron `0 6 * * 1` war am 2026-11-16 um 06:00 UTC fällig. Stand 2026-11-16 12:38 UTC+1 hat er weder einen abgeschlossenen noch einen wartenden oder laufenden Lauf. Die Abfrage nach Läufen mit Erstelldatum 2026-11-16 ist leer.
- Quoter-Deep-Link bleibt Spezifikation (`docs/QUOTER_DEEP_LINK.md`). Im Produktcode gibt es keinen Treffer auf `return_url`.

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes stay off until an operator turns the dry-run guard off in the uncommitted host environment. |
| Dockerfile + docker-compose.yml | ✅ on `main`, DEV deploy green 2026-11-10 | `deploy-dev.yml` succeeded on `cd6440f` (migrate, recreate `collector` + `api`, `/health/live`). SQL login `bdx_readonly` remains open for a container that does not use Windows integrated auth. |

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
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest coverage gate is `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/`. Last `main` run on `cd6440f` succeeded. |
| **`.github/workflows/integration.yml`** | 🟡 on `main`, nightly red | cron `0 3 * * *` + `workflow_dispatch`. Last completed run 2026-11-16 10:44 UTC (43851477564, finished 10:44:17 UTC) failed in „Install ODBC Driver 18“ and „Notify on failure“; pytest is not among the failed steps. The cron is `0 3 * * *`; this run started at 10:44 UTC. The previous run 2026-11-15 10:28 UTC (43704248636) failed on the same steps. Scheduled runs from 2026-11-08 through 2026-11-14 also failed (2026-11-14 is 43582578926). A query for integration runs created on 2026-11-16 returns exactly 43851477564. Two older Actions runs have stayed queued since 2026-11-11 20:41 UTC: CI 43097537658 and auto-merge 43097537724 (branch `cursor/projekt-dokumente-abgleich-a8a9`, commit `f89c817`). They are not this cron. The fixture keeps the Service Layer dry-run guard on, so a green run still cannot write to SAP. |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, last run green | push to `main` builds `ghcr.io/aeyhorn/alyze/bdx-intelligence:dev` plus a sha tag, then the self-hosted runner on the DEV host pulls, migrates, and recreates `collector` + `api`. Smoke: `/health/live`. No SSH hop. The job aborts when the host env file turns the dry-run guard off. Last success: 2026-11-10, commit `cd6440f`. |
| **`.github/workflows/deploy-prod.yml`** | ✅ written, reviewers not confirmed | `workflow_dispatch` only. The workflow text expects required reviewers on environment `prod`. The Environments API on 2026-11-16 12:35 UTC+1 reported no protection rules for `prod`. Inputs include `run_migrations` and `confirm_sl_write`. |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 invalid workflow file | Step „Fetch PR diff“ has two `env` blocks, so push runs finish with zero jobs (latest 43850636733, 2026-11-16 10:38 UTC, `031e040` on `sync/status-20261116`, failure; the run before that is 43841169727, 2026-11-16 09:35 UTC, `dc20523`). The intended path is `scripts/pr_review.py` on PR open/sync/reopen. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | 🟡 written, this week's cron has no run yet | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md`. Last success is 42638115770 (2026-11-09 14:47 UTC, `bbdfc8f`). As of 2026-11-16 12:38 UTC+1 the cron due 06:00 UTC has no completed, queued, or in-progress run. A query for runs created on 2026-11-16 is empty. |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | dev extras and compose are in the tree that `origin/main` already has. Lint-only branches `chore/ruff-cleanup-20261108` and `chore/ruff-cleanup-20261115` are not merged and have no open PR. |
| **`.github/workflows/lint-cleanup.yml`** | 🟡 branch pushed, PR step red | Sunday cron `0 4 * * 0` plus `workflow_dispatch`. Run 43710438515 (2026-11-15 11:45 UTC) applied ruff fixes and the suite step passed; „Create trivial PR“ then failed because GitHub Actions may not create pull requests. `chore/ruff-cleanup-20261115` has no PR. The 2026-11-08 run (42473962358) failed as well. CI lint stays advisory. |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **The tree is on `origin/main`.** Workflows, agents, scripts, integration tests, prompts and rules are in the commit history of `cd6440f`. This branch only adds the status documents on top of that commit. There is nothing local-only from Sprint 004.
* **DEV deploy no longer uses SSH.** `deploy-dev.yml` runs on the self-hosted runner. `DEV_SSH_*` is not what that workflow reads. PROD still documents `PROD_SSH_*`.
* **Secret list was not readable** in this run (HTTP 403). Names the workflows still mention: `CURSOR_API_KEY` (triage and PR review, no-op without it), `PROD_SSH_*`, and the nightly SAP/SL/Postgres secrets. The nightly job is red in the ODBC install step, before those secrets are used.
* **Repo settings read this run (2026-11-16 12:35 UTC+1):** environments `dev`, `prod`, and `CURSOR_API_KEY` have empty protection-rule lists. The `main` branch resource reports `protected: false`. Repository rulesets: length 0. The branch-protection endpoint and the Actions secret list returned HTTP 403.
* **`pr-review.yml` starts zero jobs** because „Fetch PR diff“ has two `env` keys (latest run 43850636733, 2026-11-16 10:38 UTC, `031e040` on `sync/status-20261116`; the run before that is 43841169727, 2026-11-16 09:35 UTC, `dc20523`).
* **Landing Sprint 004 in git is done.** What is left is the nightly ODBC install, the invalid PR-review workflow, reviewers and branch protection, and a lint-cleanup PR that Actions is not allowed to open.



## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth that day (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Commit `7d0fb2f` the same day records that SQL login `bdx_readonly` already existed and could not open `DEV_SBO_LEISINGER` because `DENY CONTROL` blocked CONNECT. Not re-checked 2026-11-15. |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` and `report-production 38559 -q 5 -w W01` → both blocked by DRY_RUN, audited in `sl_operations` |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

This probe is from 2026-11-07. Later commits added Alembic `003`–`008`. Successful DEV deploys since then run `docker compose run --rm migrate`. This coordinator run did not query the live database, so the schema row above stays the last direct observation (schema 002 on that day).

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Nightly integration** | last completed run 2026-11-16 10:44 UTC (43851477564, finished 10:44:17 UTC) fails in „Install ODBC Driver 18“ and „Notify on failure“; pytest is not among the failed steps. Cron `0 3 * * *` started this run at 10:44 UTC. The previous run 2026-11-15 10:28 UTC (43704248636) failed on the same steps. Scheduled runs from 2026-11-08 through 2026-11-14 also failed (2026-11-14 is 43582578926). A query for integration runs created on 2026-11-16 returns exactly 43851477564. Two older Actions runs have stayed queued since 2026-11-11 20:41 UTC: CI 43097537658 and auto-merge 43097537724 (branch `cursor/projekt-dokumente-abgleich-a8a9`, commit `f89c817`). They are not this cron. |
| **Unit tests on the current tree** | Docs CI of `031e040` (43850646182, 2026-11-16 10:38 UTC, PR #178) passed on product tree `cd6440f`: 179 passed, 8 deselected, 1 warning, TOTAL line 74 % (5 930 statements, 1 545 missed) at a 68 % gate. Docs CI of `dc20523` (43841180628, 2026-11-16 09:36 UTC, PR #178) passed the same counts (coverage line there printed 73.95 %). Docs CI of `a79ab84` (43832485591, 2026-11-16 08:35 UTC), `50039ba` (43825413067, 2026-11-16 07:40 UTC), and `08c3f6b` (43818069462, 2026-11-16 06:37 UTC) passed the same counts. Docs CI of `cc87d72` (43805169716, 2026-11-16 04:36 UTC) failed `test_machine_utilization_with_calendar` (1 failed, 178 passed, 74 %). Docs CI of `ecc180b` (43799221206), `a22c5d6` (43793408407), and PR #180 (43811268796, `71c5a03`) failed the same test at 74 %. Docs CI of `98c607f` (43787512471) failed it at 73.95 %. Docs CI of PR #179 (43781268705, `69b15ca`) failed three tests including that one (3 failed, 176 passed, coverage 73.69 %). Docs CI of `058466c` (43775742168) passed. Push CI of `cd6440f` remains the 2026-11-10 success (42768023614). |
| **PR review workflow** | `pr-review.yml` has two `env` blocks on „Fetch PR diff“. Push run 43850636733 (2026-11-16 10:38 UTC, `031e040` on `sync/status-20261116`) finished with zero jobs, as did 43841169727 (2026-11-16 09:35 UTC, `dc20523`) and 43832477042 (2026-11-16 08:35 UTC, `a79ab84`), 43825406548 (2026-11-16 07:39 UTC, `50039ba`), 43818061702 (2026-11-16 06:37 UTC, `08c3f6b`), 43811254306 (2026-11-16 05:35 UTC, `71c5a03`) and 43805165533 (2026-11-16 04:36 UTC, `cc87d72`). |
| **`prod` reviewers and branch protection** | environments `dev`, `prod`, and `CURSOR_API_KEY` have empty protection-rule lists (re-read 2026-11-16 12:35 UTC+1). The `main` branch resource reports `protected: false`. Rulesets length is 0. The protection endpoint and the Actions secret list returned HTTP 403. |
| **DORA weekly** | cron `0 6 * * 1` was due 2026-11-16 06:00 UTC. As of 12:38 UTC+1 there is no completed, queued, or in-progress run, and no run created on 2026-11-16. Last success remains 42638115770 (2026-11-09 14:47 UTC, `bbdfc8f`). |
| SQL login `bdx_readonly` on LDSAP | `create_bdx_readonly.sql` and `reset_bdx_readonly.sql` are on `main`. Commit `7d0fb2f` records that the login existed on 2026-11-07 and could not open `DEV_SBO_LEISINGER` (`DENY CONTROL` blocked CONNECT, error 18456 state 38). Not re-checked against LDSAP on 2026-11-15. Compose deploy does not wait on this anymore. |
| Plaintext password in git | `docs/sql/reset_bdx_readonly.sql` contains a plaintext password for the SQL login. It does not belong in the repo. This row does not repeat the value. |
| DEV compose on the Docker host | `deploy-dev.yml` last succeeded 2026-11-10 on `cd6440f` (migrate, recreate `collector` + `api`, `/health/live`). Repo marker `.runtime/last-deploy-sha` still says `6ccc036`. |
| MQTT / Kafka broker | publishers are implemented. `MQTT_ENABLED=false`, no broker configured in the tree. |
| Run collector against PROD | read-only; needs a separate Postgres database or a mode-prefixed `source_key`. Only single-order probes are recorded (2026-11-07). |
| SAP write-back for real | stays dry-run until an operator opens the guard in the host env. `.env.example` in git turns that guard off; this run leaves the file as it is. The 2026-11-10 DEV deploy did not trip the host-env abort. Operations: release, close, cancel, report-production. |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |
| Ruff cleanup branches | `origin/chore/ruff-cleanup-20261108` (`57411b2`) and `origin/chore/ruff-cleanup-20261115` (`1c46e17`, 2026-11-15 11:45 UTC) are each one commit ahead of `main` and have no open PR. Run 43710438515 pushed the newer branch, then „Create trivial PR“ failed because Actions may not create pull requests. CI lint stays advisory until one lands and `continue-on-error` is removed. |
| Open sync PRs | 168 open pull requests, all documentation (160 titled „docs: reconcile project status and goals“). Highest number is 180. No pull request opened after 2026-11-16 05:35 UTC (PR #180). The tip on `sync/status-20261116` before this push is `031e040` (2026-11-16 10:38 UTC), PR #178. Auto-merge run 43850646194 skipped PR #178 for that commit because it has no `trivial` label. PR #179 and PR #180 remain open. This run appends to `sync/status-20261116` and does not merge anything. |

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
│   ├── analytics/         # KPI engine, anomalies, flow, bottleneck, weaknesses
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── q2p/               # Quote-to-Promise evaluator and store
│   ├── promise/           # Offer engine and fulfillment agents
│   ├── api/               # FastAPI app, routes, static/dashboard.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008 (through q2p quoter fields)
├── tests/                 # unit tests plus tests/integration/ (DEV SAP/SL)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py,
│                          #   deploy.ps1, prepare-dev-host.sh
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
