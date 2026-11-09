# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-09 05:37 (UTC+1)
> **Git-Stand dieses Abgleichs:** `main` `723f794` (2026-11-08, `docs: Promise Platform vision … (#40)`)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

Abgleich nur gegen den Git-Baum und die GitHub-Actions-Läufe von `main`. Kein erneuter SAP-, Maschinen- oder Host-Probe. Die Messung vom 2026-11-07 bleibt als historische Beobachtung stehen.

| Lieferumfang | Commit / PR | Status |
|---|---|---|
| Sprint 001 – SAP read-only collector, event store, REST/CLI | `4219156` (#1) | ✅ auf `main` |
| Sprint 002/003 – BDE, Maschinen, inkrementelles Lesen, Dashboard, Publisher, Service-Layer-Schreibwege | `60bb34a`, `936d8c8` | ✅ auf `main` |
| Sprint 004 – CI/CD, Quality-Gate-Agenten, Integrationstests, HOTL-Prompts | Workflows und `src/bdx/agents/` auf `main` | ✅ auf `main`. Ruff/mypy beratend, Coverage-Gate 68 |
| Sprint 005 – KPI-Engine, Anomalien, Schwellen, Schwachstellen-Diagnose | `283ee4b` (#5), `2f13c3f` (#6), `6850feb` (#12); Migrationen `005`, `006` | ✅ auf `main` |
| Quote-to-Promise – parallele Anfragebewertung und Quoter | `2796032` (#33), `0de31a7` (#39); Migrationen `004`, `008` | ✅ auf `main`. Braucht Migration bis `008`, Q2P-Grants und optional den Quoter auf DEV |
| Promise Platform – Offer, Gaps, Agenten, Portal | `1ce5fdf` (#41), Vision `723f794` (#40); Migration `007` | ✅ auf `main`. Phase E und eigenständiges Portal-Auth fehlen, siehe `PROJECT_GOALS.md` G9 |
| Mehrere SAP-Firmen, SSO/SCIM | — | ⬜ offen |

Tests: 190 `test_`-Funktionen in 19 Dateien (17 unter `tests/`, 2 unter `tests/integration/`). Unit-Tests laufen gegen SQLite in-memory. Die Integrationstests überspringen sich, wenn keine DEV-Zugangsdaten gesetzt sind.

`PROJECT_GOALS.md` (`G1`–`G10`) und `REQUIREMENTS.md` (leerer Katalog, nächste ID `R001`) sind Teil dieses Abgleichs. Vorher lagen beide Dateien nicht auf `main`.

---

## Was dieser Abgleich korrigiert

Der Stand vom 2026-11-08 21:06 beschrieb Sprint 004 noch als uncommitted und Sprint 005 als Quote-to-Promise. Beides trifft auf `723f794` nicht zu.

- Sprint 004 (Workflows, `src/bdx/agents/`, `scripts/`, `tests/integration/`, `AGENTS.md`, `.cursor/prompts/`, `.cursor/rules/`) ist auf `main`.
- Sprint 005 im Commit `283ee4b` ist die Analytics-Engine. Quote-to-Promise ist ein eigener Lieferumfang (#33, #39).
- Alembic-Head ist `008` (`001`…`008`), nicht Schema `002`.
- `ci.yml` fordert `--cov-fail-under=68`. Ruff und mypy laufen mit `continue-on-error`. `AGENTS.md` nennt weiterhin 80 und eine mypy-Verschärfung als offen.
- DEV-Deploy läuft auf dem Self-hosted-Runner auf dem DEV-Host, ohne SSH-Sprung (`.github/workflows/deploy-dev.yml`). Image-Pfad wird kleingeschrieben (`ghcr.io/<repo-lowercase>/bdx-intelligence`).
- `docs/ARCHITECTURE.md` schreibt Docker noch als „not deployed“ und den Service Layer noch als „no write operations“. Beides ist älter als der Baum.
- `docs/VISION_PROMISE_PLATFORM.md` §8 nennt Offer/Gap-Tabellen als nächsten Bau-Schritt. Migration `007` ist bereits auf `main`.

---

## Sprint 001 – SAP Read-only Collector  ✅ auf `main`

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002`; Head auf `main` ist `008` |
| Initial full-load of production orders | ✅ | `OWOR_SNAPSHOT_SQL` on first run / `--full` |
| Periodic polling (60 s) | ✅ | `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | |
| Domain events: ORDER_CREATED / ORDER_RELEASED / QUANTITY_CHANGED / DUE_DATE_CHANGED / ORDER_PARTIAL_COMPLETE / ORDER_CLOSED | ✅ | |
| Retry with exponential backoff (tenacity) | ✅ | |
| FastAPI REST API, healthcheck, CLI, structured logs, secrets from env | ✅ | |
| Service Layer client + Dev/Prod mode registry | ✅ | Schreiboperationen selbst liegen in Sprint 003 |

## Sprint 002 – BDE, machines, incremental reading  ✅ auf `main`

| Feature | Status | Notes |
|---|---|---|
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value at the 2026-11-07 probe was **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV at the 2026-11-07 probe: **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is history-on-change only |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | `MACHINE_ONLINE`, `MACHINE_OFFLINE`, `MACHINE_STATE_CHANGED`, `MACHINE_ORDER_STARTED`, `MACHINE_ORDER_FINISHED`, `MACHINE_PIECES_REPORTED` |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing, dashboard & write-back  ✅ auf `main`

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`. Fehler brechen den Collector nicht. Im Repo ist kein Broker hinterlegt (`MQTT_ENABLED` default aus) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | key = `source_key`; `build_all_publishers()` setzt MQTT und Kafka zusammen, wenn beide an sind |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles, events, open orders, runs, BDE; auto-refresh |
| REST orders, events, machines, BDE, runs | ✅ | siehe Repository-Layout |
| Optional API key (`API_KEY`, `X-API-Key` oder `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` und `/health/live` | ✅ | |
| SAP Service Layer write-back (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py`, Audit-Tabelle `sl_operations` (Migration `003`). CLI und `POST /api/v1/service-layer/orders/{doc_entry}/…`. DRY_RUN gegen DEV am 2026-11-07 geprüft. Echte Writes schaltet nur die Host-Umgebung, nie eine committete Datei |
| Dockerfile + docker-compose.yml | ✅ | Deploy-Workflow auf `main`, siehe CI-Abschnitt. `docs/ARCHITECTURE.md` sagt noch „not deployed“ |

## Sprint 004 – CI/CD, quality gates, HOTL  ✅ auf `main`

**Goal**: Lint, Type, Test und Coverage in CI, nächtliche Integration, DEV-Deploy nach grünem Push, PROD nur mit Freigabe, lokale Prüfung über `bdx-collect check`.

| Feature | Status | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | ✅ | push/PR auf `main`. Ruff und mypy beratend. Pytest `--cov-fail-under=68`. Docker-Import-Smoke. Working dir `bdx-intelligence/` |
| `.github/workflows/integration.yml` | ✅ | cron `0 3 * * *` und `workflow_dispatch`; ODBC Driver 18; `pytest -m integration`. Die Fixture erzwingt den Schreibschutz, echte SAP-Writes sind in diesem Lauf nicht vorgesehen |
| `.github/workflows/deploy-dev.yml` | ✅ | push auf `main`: Image bauen, nach ghcr.io pushen (`:dev` und `:sha-<kurz>`), Deploy auf `[self-hosted, linux]` unter `/home/docadm/bdx-intelligence`. `docker compose pull`, `migrate`, recreate `collector` und `api`, Smoke `/health/live`. Der Job bricht ab, wenn die Host-Umgebung Schreibzugriffe erlauben würde. Kein SSH-Hop |
| `.github/workflows/deploy-prod.yml` | ✅ | nur `workflow_dispatch`, Environment `prod`, Eingaben `run_migrations` und Schreib-Bestätigung |
| `.github/workflows/ci-triage.yml` | ✅ | `workflow_run` nach fehlgeschlagener CI. Ohne `CURSOR_API_KEY` kein Agent-Lauf |
| `.github/workflows/pr-review.yml` | ✅ Datei | `pull_request` opened/synchronize/reopened. Der Push von `723f794` hat trotzdem Lauf `42518586380` erzeugt: failure, **keine Jobs** |
| `.github/workflows/auto-merge.yml` | ✅ | nur mit Label `trivial`, nur Test/Doku, keine geschützten Pfade |
| `.github/workflows/dora.yml` | ✅ | Montag 06:00 UTC, schreibt `docs/dora-metrics.md`. Diese Datei liegt auf `723f794` nicht im Baum |
| `.github/workflows/lint-cleanup.yml` | ✅ | manuell, ruff-Fix als Folge-PR |
| Quality-gate agents `src/bdx/agents/` | ✅ | docs, tests, quality, runner. `bdx-collect check`, `check-docs`, `check-tests`, `check-quality` |
| Integrationstests | ✅ | `tests/integration/test_sap_read.py`, `test_sl_contract.py`. Skip ohne `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` |
| HOTL prompts und `AGENTS.md` | ✅ | `.cursor/prompts/` (feature, bugfix, refactor, testgen, from-notion-spec, triage-issue), `.cursor/rules/bdx-conventions.mdc` |
| Helper scripts | ✅ | `scripts/ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `prepare-dev-host.sh`, `deploy.ps1` |
| PROD migration guard | ✅ | `alembic/env.py` verweigert PROD ohne `ALEMBIC_ALLOW_PROD=1` |

### CI-Läufe auf `main` (nicht erneut ausgeführt)

| Lauf | Workflow | Ergebnis |
|---|---|---|
| `42518587593` | CI für `723f794` | success (53 s) |
| `42518587710` | Deploy to DEV für `723f794` | success (Build und Deploy, 1 min 59 s). Der Job führt `docker compose run --rm migrate` aus |
| `42518586380` | `pr-review.yml` beim Push von `723f794` | failure, 0 Jobs |
| `42516285446` | Deploy to DEV für Quoter-Commit `0de31a7` (#39) | Build success, Deploy-Job failure. Spätere Deploys von Analytics-Folge, Promise (`42518204744`) und Vision sind success |

Secrets, die der Baum noch nennt: `CURSOR_API_KEY` (Triage und PR-Review, sonst Skip), SAP/SL/Postgres für die nächtliche Integration. DEV-Deploy braucht keine SSH-Secrets mehr. Environment `prod` mit Required Reviewers steht als Voraussetzung in `deploy-prod.yml` und wurde hier nicht in den Repo-Settings geprüft.

## Sprint 005 – Analytics und Schwachstellen  ✅ auf `main`

**Goal**: KPI-Engine, Anomalie-Erkennung, selbstjustierende Schwellen und eine Diagnose-Schicht über Auftragsdurchlauf und Maschinen.

| Feature | Status | Notes |
|---|---|---|
| Migration `005` | ✅ | `kpi_snapshots`, `metric_thresholds`, `detected_anomalies`, `shift_calendar`, `machine_state_history`. Revision folgt auf Q2P-`004` |
| Auftrags-KPIs | ✅ | `cycle_time_hours`, `on_time_delivery_rate`, `backlog_overdue_count`, `rejection_rate_pct`, `completion_rate_pct`, `release_to_start_hours`, `order_change_frequency` |
| Maschinen-KPIs | ✅ | `machine_utilization_pct`, `setup_ratio_pct`, `mtbf_hours`, `mttr_hours`, `queue_unstarted_hours`, `override_low_pct` |
| Beschaffungs-KPIs | ✅ | `kpis_procurement.py`: `material_coverage_pct`, `critical_items_count`, `po_lead_time_days`, `supplier_otd_rate`, `po_overdue_count`, `gr_delay_days`, `stock_coverage_days`. SAP-Zeilen werden als Dicts übergeben, Tests ohne SAP |
| Anomalien und Schwellen | ✅ | `analytics/anomalies.py`, `thresholds.py` |
| Migration `006` Diagnose | ✅ | `measurement_quality`, Flow, Verspätungsursachen, Bottleneck-Rang |
| REST `/api/v1/analytics/*` | ✅ | `/kpis`, `/kpis/{metric}`, `/trends`, `/anomalies`, `/thresholds`, `/quality`, `/flow`, `/causes`, `/bottleneck`, `POST /run`, `/weaknesses` |
| UI `/analytics` | ✅ | `static/analytics.html` |

## Quote-to-Promise  ✅ auf `main` (#33, #39)

**Goal**: Eine Anfrage beantwortet Material, Kapazität, Preis und Personal parallel. Menschen sehen `open_questions`, wo keine Daten liegen.

| Feature | Status | Notes |
|---|---|---|
| `q2p_inquiries` (Alembic `004`) | ✅ | draft/ready/blocked/decided, Entscheidungs-Audit |
| `bdx.q2p.service.evaluate_promise` | ✅ | item, material, BOM, capacity, pricing, personnel |
| SAP-Lesen OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ | fehlendes SELECT wird zur offenen Frage |
| Kapazität aus `machine_state` und offenen `order_state` | ✅ | |
| REST `/api/v1/q2p/*` und `/q2p/promise` | ✅ | create, list, patch, evaluate, decide, Ad-hoc-Promise |
| Cockpit `/q2p` | ✅ | |
| `bdx-collect serve` hängt die SAP-Engine an | ✅ | ohne Engine werden SAP-Domänen zu offenen Fragen |
| SQL-Grant `docs/sql/grant_q2p_readonly.sql` | ✅ Datei | Ausführung auf LDSAP ist kein Git-Fakt |
| bdx-quoter HTTP-Adapter | ✅ | `QUOTER_*`, Datenraum auf der Anfrage, `offen[]` → `open_questions`. Migration `008` |
| Quoter-Vertrag | 🟡 Annahme | `docs/Q2P_QUOTER.md`: `web/server.py` lag nicht im Baum. Pfade sind überschreibbar |

**Deploy-Hinweis aus dem Code, nicht neu geprüft:** `alembic upgrade head` bis `008`. Personal/Schichtqualifikation hat weiter keinen Feed.

## Promise Platform  ✅ auf `main` (#41)

**Goal**: Lebendiges Angebot als Akte. Gaps statt E-Mail-Ketten. Agenten für Kalkulation, Einkauf, Kapazität und Vertrag. Internes Cockpit `/promise` und token-scoped Portal.

| Feature | Status | Notes |
|---|---|---|
| Migration `007` | ✅ | `promise_offers`, Gaps, Evidence, Agent-Jobs, Contracts |
| Offer Engine | ✅ | `bdx.promise.engine`: create, recompute, decide, resolve, publish, portal accept/reject |
| Konfidenz v0 | ✅ | `bdx.promise.confidence` |
| Agenten quote, purchase, capacity, contract | ✅ | Quote delegiert an `evaluate_promise` und den Quoter. Purchase und Capacity schlagen vor und öffnen Gaps. Contract schreibt einen Entwurf. Kein autonomes Bestellen (Vision Phase E) |
| API | ✅ | `/api/v1/promise/offers` (create, list, get, recompute, decide, gap resolve, contract publish). Portal ohne API-Key: `GET /api/v1/portal/{token}`, accept, reject |
| UI | ✅ | `/promise`, `/portal`, `/portal/{token}` |
| Vision | ✅ Datei | `docs/VISION_PROMISE_PLATFORM.md`. §8 ist gegenüber Migration `007` veraltet |

Phase A bis D sind im Code angelegt, ihre Exit-Kriterien nicht. Phase D im Code ist ein Token-Portal, nicht die eigenständige Auth aus der Vision. Details: `PROJECT_GOALS.md` G7–G9.

---

## Operational status (DEV, verified 2026-11-07)

Diese Tabelle ist die letzte protokollierte Host-Messung. Dieser Abgleich hat sie nicht wiederholt. Der erfolgreiche Deploy-Job von `723f794` sagt nur: Image-Build, `migrate` und `/health/live` im Workflow waren grün.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Ob das SQL-Login `bdx_readonly` inzwischen existiert, sagt der Git-Stand nicht |
| PostgreSQL event store | ✅ zum Messzeitpunkt Container `bdx-intelligence-postgres` auf Docker-Host 192.168.82.33:5437, damals Schema **002**. Code-Head heute ist Migration `008`. Der Deploy von `723f794` hat `migrate` ausgeführt |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| PROD read probe (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed. DEV hinkte PROD hinterher (FA 38560/38561 waren R in PROD, P in DEV) |
| SAP write-back DRY_RUN (DEV) | ✅ `release 38559` und `report-production 38559` wurden vom Schreibschutz blockiert und in `sl_operations` protokolliert |
| API + `/dashboard` on :8085 | ✅ zum Messzeitpunkt |

### Findings from the first real machine cycle (2026-11-07, not re-checked)

* **DEV database lags production**: machine *Integrex i500S* ran SAP order **38574**, while `DEV_SBO_LEISINGER` ended at DocNum 38561. The link stays unresolved on DEV until the collector reads PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`) into a separate event store.
* XMSK `Order` is not always a DocNum: *QT350MY* reported `10886/NEU`. Such refs stay raw in `order_ref`.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| Doku an den Baum ziehen | `ARCHITECTURE.md` (Deploy, „no write operations“, Coverage- und Env-Defaults) und Vision §8 (Offer/Gap als nächster Schritt) hinken `723f794` hinterher. Dieser Abgleich ändert nur Status, Ziele und Anforderungen |
| Coverage- und Typ-Ratchet | Gate steht bei 68. `AGENTS.md` beschreibt den Weg, Ruff und mypy von beratend auf blockierend zu stellen |
| `pr-review.yml` auf Push rot | Lauf `42518586380` zu `723f794`: failure ohne Jobs. Die Datei abonniert nur `pull_request` |
| Quoter-HTTP-Vertrag prüfen | `docs/Q2P_QUOTER.md`: echte Pfade von `web/server.py` gegen die Aliase in `adapters/quoter.py` |
| SQL-Login `bdx_readonly` | Skripte in `docs/sql/`. Ob das Login auf LDSAP existiert, ist nicht im Git belegt. Linux-Container können keine Windows-Integrated-Auth nutzen |
| MQTT / Kafka Broker | Publisher sind gebaut. Defaults lassen beide aus |
| Collector gegen PROD | read-only, aber mit getrenntem Event-Store, damit DEV- und PROD-Zeilen in `order_state` sich nicht mischen. Bisher nur Einzelauftrags-Probes am 2026-11-07 |
| Echte Service-Layer-Writes | bleiben eine Entscheidung auf dem Host. `ServiceLayerSettings.dry_run` defaultet im Code auf aus; `AGENTS.md` verlangt den umgekehrten sicheren Default. Nichts in diesem Abgleich schaltet Writes an |
| Vision-Exit und Phase E | Exit-Kriterien der Phasen A–D sind nicht belegt. Autonomes Bestellen und Slot-Binden (Phase E) ist nicht im Baum. Entscheidungen V-1 bis V-5 sind offen |
| Multi-company SAP, SSO/SCIM | offen (G10) |
| Machine `User` / `LastProdEnd` leer | Befund vom 2026-11-07, MDE-Seite, nicht erneut geprüft |
| `docs/dora-metrics.md` | Workflow ist da, die Datei fehlt auf `723f794` |

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) existieren in den Leisinger-Firmendatenbanken nicht. `queries.py` selektiert `NULL`. OWOR hat andere UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, Arbeitsschritt-Flags).
2. **Net delta between cycles**: zwei Änderungen in einem Poll werden nur als Netto-Differenz sichtbar.
3. **Incremental window**: geschlossene Aufträge außerhalb des Lookbacks fängt BDX nur, weil bekannte offene Aufträge per DocEntry nachgelesen werden. Unbekannte Altaufträge brauchen `collect --once --full` oder `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: kein BDE-Terminal. Ausschuss bleibt 0. Segmente trennt `BDE_GAP_SECONDS`.
5. **API authentication** ist ein optionales Shared Secret. Portal-Routen sind token-scoped und ohne API-Key. Die API nicht ohne Gateway oder mTLS aus dem LAN geben.
6. **Legacy history**: die Sprint-001-Migration hat `order_state` mit Fingerprint `''` befüllt. Der erste inkrementelle Lauf nach dem Upgrade schreibt eine History-Zeile pro offenem Auftrag (beobachtet 2026-11-07: 871, einmalig 30 s).
7. **Schreibschutz-Default**: Code-Default von `dry_run` und die Texte in `AGENTS.md` sowie `ARCHITECTURE.md` widersprechen sich. Der DEV-Workflow erzwingt den Schutz über die Host-Umgebung.

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py
│   ├── db/                 # SAP/PG, queries, queries_sap_extended
│   ├── models/             # sap, events, analytics
│   ├── collector/          # polling, snapshots, change_detector, machines
│   ├── adapters/           # machine (XMSK), bde (SCADA), quoter
│   ├── publish/            # Null, MQTT, Kafka
│   ├── sap_sl/             # client, mode, operations
│   ├── agents/             # Sprint 004 quality gates
│   ├── analytics/          # Sprint 005 KPIs, anomalies, thresholds, diagnosis
│   ├── q2p/                # inquiry store, evaluate_promise
│   ├── promise/            # engine, confidence, agents (quote, purchase, capacity, contract)
│   ├── api/                # routes + static dashboard, analytics, q2p, promise, portal
│   └── cli/                # bdx-collect
├── alembic/                # 001 … 008 (head 008)
├── tests/                  # 17 Unit-Dateien + integration/ (2)
├── scripts/
├── Dockerfile, docker-compose.yml
├── AGENTS.md
└── docs/                   # ARCHITECTURE, SAP_MAPPING, Q2P_QUOTER,
                            #   VISION_PROMISE_PLATFORM, PROJECT_STATUS,
                            #   PROJECT_GOALS, REQUIREMENTS, sql/
```

Repo-root:

```
├── .github/workflows/      # ci, integration, deploy-dev, deploy-prod,
│                           #   ci-triage, pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/            # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/              # bdx-conventions.mdc
```

UI-Routen in `api/main.py`: `/` → `/dashboard`, `/dashboard`, `/analytics`, `/q2p`, `/promise`, `/portal`, `/portal/{token}`. API-Prefix `/api/v1` für orders, machines (inkl. BDE und runs), service-layer, analytics, q2p, promise, portal. Health bleibt ohne Prefix.
