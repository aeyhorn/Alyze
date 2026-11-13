# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-13 05:37 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (operational on DEV) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (operational on DEV) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (MQTT/Kafka built, no broker yet; write-back DRY_RUN-verified) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | 🟡 on `main` (`cd6440f`). Coverage-Gate 68 %. ruff und mypy advisory. `prod` ohne Protection Rules; Branch Protection nicht lesbar (403). Nächtliche Integration bricht vor pytest ab |
| Analytics | Sprint 005: KPI engine, anomalies, diagnosis, procurement KPIs | ✅ merged (#5, #6, #12). Migrationen `005`+`006`. UI `/analytics` |
| Q2P | Quote-to-Promise cockpit (parallel inquiry evaluation) | ✅ merged (#33, #39). Migrationen `004`+`008` |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41) – Migrationen `007`+`008`; vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Vorgangsleitstand (`/vorgang`) | ✅ merged (#67) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open. DEV-Compose-Deploy ist G6 |

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
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Echte Schreibvorgänge nur, wenn ein Operator den Dry-Run in der Host-Umgebung abschaltet. Committete Dateien tun das nicht. |
| Dockerfile + docker-compose.yml | ✅ DEV-Deploy läuft | `deploy-dev.yml` auf dem Self-hosted-Runner des Hosts 192.168.82.33. Letzter grüner Lauf: 2026-11-10 07:22 (UTC+1), `cd6440f`, inkl. Migration und `/health/live`. Committete Stempel `.runtime/last-deploy-at` / `last-deploy-sha` stehen auf 2026-11-07 21:50 und `6ccc036`. Die Kopfzeile von `docker-compose.yml` sagt weiterhin „NOT yet deployed“. |

## Analytics (Sprint 005)  ✅ Merged (#5, #6, #12)

KPI-Engine, Anomalien und selbstjustierende Schwellen (`bdx.analytics`), Diagnose (Durchlauf, Ursachen, Engpass) und Beschaffungs-KPIs (Bestand, Bestellungen, Wareneingang). Alembic `005` und `006`. REST unter `/api/v1/analytics/*`, UI `/analytics`.

Der grüne DEV-Deploy von `cd6440f` hat `docker compose run --rm migrate` ausgeführt. Eine eigene Schema-Abfrage gegen Postgres gab es in diesem Lauf nicht.

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

## Vorgangsleitstand  ✅ Merged (#67)

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht. Auf `main` seit `90a6593`.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  🟡 On main, Abnahme offen

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on main | push/PR to `main`: ruff (lint + format check), mypy on `src/bdx`, pytest with `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). ruff und mypy sind `continue-on-error`. Working dir = `bdx-intelligence/` |
| **`.github/workflows/integration.yml`** | 🟡 on main, Läufe brechen vor pytest ab | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; die Fixture erzwingt Dry-Run, echte SAP-Schreibvorgänge sind daraus nicht möglich. Geplante Läufe 2026-11-08 bis 2026-11-12 sind rot. Der letzte, Actions `43202844646` (2026-11-12 11:43 UTC+1), stirbt in „Install ODBC Driver 18“: `gpg` kann `/dev/tty` nicht öffnen, danach `curl: Failed writing body`, Exit 2. Pytest startet nicht. Derselbe Abbruch steht im Lauf `43003787661` (2026-11-11). Der Cron-Lauf 2026-11-13 04:00 UTC+1 war zum Abgleich 05:37 (UTC+1) noch nicht gestartet. |
| **`.github/workflows/deploy-dev.yml`** | ✅ on main, letzter DEV-Lauf grün | push to `main` → Image `ghcr.io/<repo>/bdx-intelligence:dev` + `:sha-<sha>`, Deploy auf dem Self-hosted-Runner des DEV-Hosts (kein SSH-Hop), `docker compose pull`, Migration, `collector` + `api` neu, Smoke `/health/live`. Der Lauf bricht ab, wenn die Host-`.env` den Dry-Run abschaltet. Letzter grüner Lauf: 2026-11-10 07:22 (UTC+1), `cd6440f`. |
| **`.github/workflows/deploy-prod.yml`** | ✅ written, keine Läufe | `workflow_dispatch` only. Die Workflow-Datei erwartet Reviewer auf Environment `prod`; die API zeigt für `prod` leere Protection Rules. Inputs `run_migrations` und `confirm_sl_write`. Kein Lauf bisher. |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 written, Push-Läufe ohne Jobs | on PR open/sync/reopen → `scripts/pr_review.py` runs two Cursor cloud agents (bug review + security review) on the diff, posts ONE combined comment. Advisory only — branch protection does the blocking via `ci.yml`. Der Schritt „Fetch PR diff“ hat zwei `env`-Schlüssel. Push-Läufe enden deshalb ohne Jobs. Letztes Beispiel: Actions `43360034754` (2026-11-13 04:36 UTC+1, `7a326da`), Abschluss failure, Jobliste leer. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ written | `base.py` (Severity/Status/Finding/CheckResult), `docs.py` (DocumentationAgent: README, required docs, status freshness ≤90 d, module + public-symbol docstrings, API routes vs `ARCHITECTURE.md`, env vars vs `ARCHITECTURE.md`), `tests.py` (TestAgent: shells out to pytest, parses JUnit XML + coverage.json, gates ≥80 % overall / ≥50 % per module / ≤10 % skipped), `quality.py` (QualityAgent: ruff JSON, mypy, smell scan — TODO without owner, `print()` in prod, empty `except:`), `runner.py` (AgentRunner + RunnerReport, JSON serialisable, exit 0/1/2). Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml` tweaks** | ✅ on main | ruff/format und Dev-Extras sind im Baum. Das Coverage-Gate in `ci.yml` steht auf 68 % (Ratchet; Floor damals ~69 %). |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **Code liegt auf `origin/main`.** HEAD ist `cd6440f` (2026-11-10 07:21 UTC+1). Arbeitsbaum sauber, nichts nur lokal. Workflows, `scripts/`, `tests/integration/`, `src/bdx/agents/`, `AGENTS.md` und die Cursor-Regeln sind im Baum.
* **CI:** `ci.yml` verlangt pytest mit `--cov-fail-under=68`. ruff und mypy laufen mit `continue-on-error`. Der Push-Lauf auf `main` für `cd6440f` war grün (2026-11-10 07:22 UTC+1, Actions `42768023614`). Docs-PRs auf demselben Produktstand sind am 2026-11-13 rot. Der neueste Lauf `43360054629` (04:36 UTC+1, `7a326da`, PR #120) hat einen Test rot: `test_machine_utilization_with_calendar` (`assert None is not None`); 178 passed, 8 deselected; die TOTAL-Zeile zeigt 74 % (1545 von 5930 Anweisungen ohne Coverage). Der Test legt eine Schicht für `datetime.now(UTC).weekday()` an. Lauf `43338394984` (01:36 UTC+1) hatte zusätzlich `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle` rot.
* **DEV-Deploy:** siehe `deploy-dev.yml`. `deploy-prod.yml` hat keine Läufe. SSH-Secrets sind für DEV nicht mehr der Weg; der Runner steht auf dem Host.
* **Abnahme offen (G4):** Environments `dev`, `prod` und `CURSOR_API_KEY` existieren, die Protection Rules sind leer. Repository-Rulesets: 0. Branch Protection für `main` antwortete 403. Die Secret-Liste antwortete 403; Werte wurden nicht gelesen. Die Workflows nennen weiterhin `CURSOR_API_KEY`, `PROD_SSH_*` und die nächtlichen Integrations-Secrets.
* **Erledigt als Git-Schritt:** den Sprint-004-Baum committen und mergen. Der Baum ist auf `main`.



## Operational status (DEV, verified 2026-11-07)

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

Nachtrag 2026-11-13: Die Tabelle ist der Probe-Stand vom 2026-11-07 (damals Schema **002**). `origin/main` ist `cd6440f`. Deploy-to-DEV dieses Commits war am 2026-11-10 07:22 (UTC+1) grün, inklusive `migrate` und `/health/live`. Ob `bdx_readonly` auf LDSAP benutzt wird, steht nicht im Git. Das Skript `docs/sql/create_bdx_readonly.sql` enthält kein DENY CONTROL mehr; ein früheres DENY hat CONNECT blockiert (18456, state 38).

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **G4 Abnahme** | Code ist auf `main`. Offen: Protection Rules für `prod` (API: leer), Rulesets 0, Branch Protection und Secret-Liste nicht lesbar (403). Coverage-Gate ist 68 %. |
| **Nächtliche Integration** | Läufe 2026-11-08 bis 2026-11-12 scheitern in „Install ODBC Driver 18“, vor pytest. Letzter Lauf `43202844646` (2026-11-12 11:43 UTC+1): `gpg` ohne `/dev/tty`, danach `curl: Failed writing body`, Exit 2. Cron ist `0 3 * * *`. Am 2026-11-13 05:37 (UTC+1) gibt es noch keinen Lauf; die Vortage sind erst gegen 11:30–12:00 (UTC+1) gestartet. |
| **Unit-Tests, Re-Run** | Der Push-CI von `cd6440f` (2026-11-10) bleibt grün. Docs-PR `43360054629` (2026-11-13 04:36 UTC+1, PR #120) hat einen Test rot (`test_machine_utilization_with_calendar`); TOTAL 74 % liegt über dem Gate 68 %. Lauf `43338394984` (01:36 UTC+1) hatte drei Tests rot. |
| **PR-Review-Workflow** | `pr-review.yml`, Schritt „Fetch PR diff“, hat zwei `env`-Schlüssel. Push-Läufe enden ohne Jobs. Letztes Beispiel: Actions `43360034754` (2026-11-13 04:36 UTC+1), Jobliste leer. |
| **Doku-Abgleich** | `PROJECT_STATUS` auf `main` beschreibt Sprint 004 noch als uncommitted. Offene Abgleich-PRs (Tagesbranch `sync/status-20261113` ist #118, neuester #120) sind nicht gemergt. |
| **Lint-Cleanup-Branch** | `chore/ruff-cleanup-20261108` liegt einen Commit vor `main` und hat keinen Pull Request. |
| SQL-Login `bdx_readonly` auf LDSAP | Skript liegt im Repo und verweigert kein CONTROL mehr (das DENY hat CONNECT blockiert, 18456 state 38). Ob der Login existiert und der Collector ihn nutzt, ist aus Git nicht sichtbar. |
| DEV-Compose | läuft über `deploy-dev.yml`. Letzter grüner Lauf 2026-11-10 07:22 (UTC+1) für `cd6440f`. Committete Runtime-Stempel hinken hinterher (2026-11-07, `6ccc036`). |
| MQTT / Kafka broker | set `MQTT_ENABLED=true`+`MQTT_HOST` or `KAFKA_ENABLED=true`+`KAFKA_BOOTSTRAP_SERVERS`; `pip install -e .[mqtt]` / `.[kafka]` |
| Run collector against PROD | read-only; but **needs a separate PG database** (or mode-prefixed `source_key`) to avoid mixing DEV/PROD data in `order_state`. `deploy-prod.yml` hat keine Läufe. |
| SAP write-back real use | Dry-Run bleibt der Default. Echte Schreibvorgänge nur, wenn ein Operator das in der Host-Umgebung bewusst abschaltet. Committete Dateien schalten das nicht ab. Grüne DEV-Deploys haben den Abbruchpfad des Workflows nicht ausgelöst. |
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
├── alembic/               # migrations 001–008 (state, machines, sl_operations, q2p, analytics, diagnosis, promise, quoter)
├── tests/                 # unit tests on SQLite + tests/integration/ (DEV SAP/SL, skip without creds)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS (+ dora-metrics.md weekly)
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen, sync-coordinator
    ├── rules/             # bdx-conventions.mdc, dev-sync.mdc (alwaysApply)
    └── skills/dev-sync/   # sync coordinator procedure
```
