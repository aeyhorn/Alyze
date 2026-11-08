# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-08 19:40 (UTC+1)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

Abgleich mit `main` @ `283ee4b` (2026-11-08). Quellen: Git-Historie, Baum auf diesem Commit, GitHub Actions auf `main`. Kein neuer Shop-Floor-Probe in diesem Lauf. Ziele: [`PROJECT_GOALS.md`](PROJECT_GOALS.md). Anforderungen: [`REQUIREMENTS.md`](REQUIREMENTS.md).

| Sprint / Lieferung | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ auf `main` (PR #1) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ auf `main` |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ auf `main`. Broker standardmäßig aus. Write-Pfad vorhanden und auditiert |
| 004 | CI/CD, quality-gate agents, integration tests, HOTL prompts | ✅ Workflows auf `main`. Ruff und mypy bleiben advisory. Coverage-Gate in `ci.yml` ist 68 % |
| Q2P | Quote-to-Promise cockpit (parallele Anfragebewertung) | ✅ gemergt (#33, Migration `004`). UI `/q2p` |
| 005 | KPI engine, anomaly detection, self-tuning thresholds, diagnosis layer, Schwachstellen-Dashboard | ✅ gemergt (#5, #6, #12; Migrationen `005` und `006`) |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ kein Code |

Test suite: `181` Funktionen `def test_` unter `bdx-intelligence/tests/` (davon 8 Integration). CI auf `283ee4b` ist grün mit `--cov-fail-under=68`. Integrationstests überspringen ohne DEV-Credentials. Der nächtliche Integration-Lauf am 2026-11-08 ist fehlgeschlagen (älterer SHA, siehe unten).

---

## Sprint 001 – SAP Read-only Collector  ✅ auf `main`

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002`; Head auf `main` ist `006` |
| Initial full-load of production orders | ✅ | `OWOR_SNAPSHOT_SQL` on first run / `--full` |
| Periodic polling (60 s) | ✅ | `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | |
| Domain events: ORDER_CREATED / ORDER_RELEASED / QUANTITY_CHANGED / DUE_DATE_CHANGED / ORDER_CLOSED | ✅ | see status-code note below |
| Retry with exponential backoff (tenacity) | ✅ | |
| FastAPI REST API, healthcheck, CLI, structured logs, secrets from env | ✅ | |
| Service Layer client + Dev/Prod mode registry | ✅ | write operations live in Sprint 003 |

## Sprint 002 – BDE, machines, incremental reading  ✅ auf `main`

| Feature | Status | Notes |
|---|---|---|
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value at the 2026-11-07 probe was **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV (2026-11-07): **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is history-on-change only (was +38 561 rows per cycle) |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only; 10 machines on the floor at the 2026-11-07 probe |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | MACHINE_ONLINE / OFFLINE / STATE_CHANGED / ORDER_STARTED / ORDER_FINISHED / PIECES_REPORTED |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` on events and `/api/v1/machines` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records (start/end/pieces per order & machine) from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing, dashboard & write-back  ✅ auf `main`

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. Default `enabled=false` |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | key = `source_key`; `build_all_publishers()` composes MQTT + Kafka when both are on. Default `enabled=false` |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; link to `/analytics` |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | plus `/health/live` used by the deploy smoke test |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ Code | `sap_sl/operations.py` with `sl_operations` audit (migration `003`); CLI and `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}`. Code default of `ServiceLayerSettings.dry_run` is off, and `.env.example` ships the switch in the write-enabled position. The DEV deploy workflow aborts when the host environment file does the same. See open items |
| Dockerfile + docker-compose.yml | ✅ Deploy-Pfad aktiv | `deploy-dev.yml` baut das Image, pusht nach GHCR (lowercase), deployed auf dem self-hosted Runner ohne SSH-Hop. Job für `283ee4b` erfolgreich |

## Quote-to-Promise  ✅ gemergt (#33)

Nicht Sprint 005. Migration `004` (`q2p_inquiries`) liegt vor den Analytics-Migrationen. Commit `2796032`, gemergt 2026-11-08.

**Goal**: Eine Anfrage bewertet Material, Kapazität, Preis und Personal parallel aus SAP und Shop-Floor. Menschen sehen `open_questions`, wo keine Daten liegen.

| Feature | Status | Notes |
|---|---|---|
| Inquiry case store `q2p_inquiries` (Alembic `004`) | ✅ | Status draft/evaluating/ready/blocked/decided/cancelled; Decision accept/reject/counter |
| Parallel evaluator `bdx.q2p.service.evaluate_promise` | ✅ | item / material / BOM / capacity / pricing / personnel |
| SAP reads OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ | graceful degrade on missing SELECT |
| Capacity from `machine_state` + open `order_state` | ✅ | idle vs busy + backlog same item |
| REST `/api/v1/q2p/*` | ✅ | create, list, get, patch, evaluate, decide, ad-hoc `GET /q2p/promise` |
| Cockpit UI `/q2p` | ✅ | `static/q2p.html` |
| `bdx-collect serve` attaches SAP engine | ✅ | without engine, SAP domains become open questions |
| SQL grant script `docs/sql/grant_q2p_readonly.sql` | ✅ im Repo | separates Operator-Skript, keine Alembic-Migration. Ob es auf LDSAP gelaufen ist, steht nicht im Git |

**Still human by design**: Personal/Schichtqualifikation hat keinen Feed (`DomainStatus.UNKNOWN`). Kommerzielle Marge jenseits Listenpreis ist kein Systemergebnis.

Deploy von `2796032` nach DEV war grün, bevor Analytics darauf landete.

## Sprint 004 – CI/CD, quality gates, HOTL  ✅ auf `main`

Die frühere Aussage „built (uncommitted)“ ist überholt. Workflows, Agents, Scripts und Prompts sind auf `main`.

| Feature | Status | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | ✅ läuft | push/PR `main`: ruff, mypy, pytest `--cov-fail-under=68`, Docker import smoke. Working dir `bdx-intelligence/` |
| Ruff und mypy | 🟡 advisory | `continue-on-error: true`. Der Kopfkommentar von `ci.yml` spricht noch von einem 80-%-Gate; die pytest-Zeile erzwingt 68 |
| `.github/workflows/integration.yml` | 🟡 Workflow da, letzter Nachtlauf rot | 2026-11-08 09:55 UTC, SHA `6710fdc`, Run `42469243262`, Exit 2. Das war vor Q2P und Analytics. Dieser Abgleich hat den Lauf nicht wiederholt |
| `.github/workflows/deploy-dev.yml` | ✅ grün auf HEAD | self-hosted Runner, kein SSH. Image `ghcr.io/<repo>/bdx-intelligence`. Run `42499223057` (Build & Push + Deploy to DEV host) für `283ee4b` erfolgreich. Der Job bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet |
| `.github/workflows/deploy-prod.yml` | ✅ geschrieben | `workflow_dispatch`, Environment `prod`, Inputs für Migrationen und Schreibfreigabe. Kein erfolgreicher Prod-Lauf in diesem Abgleich geprüft |
| `.github/workflows/ci-triage.yml` | ✅ geschrieben | `workflow_run` nach CI. Auf `283ee4b` skipped, weil CI grün war |
| `.github/workflows/pr-review.yml` | 🟡 | Datei ist pull_request-only und soll ohne `CURSOR_API_KEY` grün skippen. Run `42499221888` an `283ee4b` endete failed ohne Jobs |
| `.github/workflows/auto-merge.yml` | ✅ geschrieben | Label `trivial` und keine geschützten Pfade |
| `.github/workflows/dora.yml` | ✅ geschrieben | weekly; committet `docs/dora-metrics.md`. Die Datei liegt auf diesem Stand nicht im Baum |
| `.github/workflows/lint-cleanup.yml` | 🟡 letzter Lauf rot | Run `42473962358` (2026-11-08, schedule) Exit 1 |
| Quality-gate agents (`src/bdx/agents/`) | ✅ | docs, tests, quality, runner. CLI `bdx-collect check`, `check-docs`, `check-tests`, `check-quality` |
| Integration tests (`tests/integration/`) | ✅ im Baum | 8 Tests. Skip ohne DEV-Credentials. Der nächtliche Lauf ist zuletzt fehlgeschlagen |
| HOTL prompts (`.cursor/prompts/`) | ✅ | `from-notion-spec`, `triage-issue`, `feature`, `bugfix`, `refactor`, `testgen` |
| `AGENTS.md` + `.cursor/rules/bdx-conventions.mdc` | ✅ | |
| Helper scripts | ✅ | `ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `deploy.ps1`, `prepare-dev-host.sh`, `set-github-secrets.ps1`, `setup-github-runner.ps1` |
| PROD migration guard (`alembic/env.py`) | ✅ | verweigert PROD-DSN ohne `ALEMBIC_ALLOW_PROD=1` |

## Sprint 005 – Analytics und Schwachstellen  ✅ gemergt

Code und Migrationen nennen dies Sprint 005. Q2P ist die eigene Lieferung #33 davor.

| Lieferung | Commit / PR | Inhalt |
|---|---|---|
| Schwachstellen-Dashboard | #6, `2f13c3f` | `GET /api/v1/analytics/weaknesses`, Seite `/analytics` |
| Dashboard-Darstellung | #12, `6850feb` | dieselbe Schwachstellen-Seite geschärft |
| KPI engine, Anomalien, Schwellen, Diagnose | #5, `283ee4b` | Migrationen `005` und `006`. Gemergt 2026-11-08 16:18 UTC, nach Q2P |

Analytics-Zyklus (`bdx.analytics.collector`): alle 600 s KPIs, Maschinenhistorie, Anomalien; Schwellen-Tuning alle 24 h. Einhängung in `run_polling_loop`. Procurement-KPIs laufen nur mit SAP-Engine.

| Fläche | Status | Notes |
|---|---|---|
| Order-KPIs | ✅ | cycle time, on-time delivery, backlog overdue, rejection, completion, release-to-start, order-change frequency |
| Machine-KPIs | ✅ | utilization, setup ratio, MTBF, MTTR, queue unstarted, low override |
| Procurement-KPIs | ✅ Code | material coverage, critical items, PO lead time, supplier OTD, overdue PO, GR delay, stock coverage days. SAP-Zeilen werden zur Laufzeit gelesen; ohne Engine übersprungen |
| Anomalien | ✅ | warn/crit gegen `metric_thresholds`, Empfehlungstexte, `resolved_at` wenn die Schwelle wieder hält |
| Threshold tuning | ✅ | Seed plus Perzentil aus 30 Tagen Snapshots |
| Diagnose | ✅ | `measurement_quality` (link rate, history depth, Little's Law), `order_flow_segments` (wait/setup/run/post-process), `lateness_causes` (material_gap, overdue_po, waiting_idle, bottleneck, scrap, unstable, sonst unassigned), `bottleneck_rank` |
| REST `/api/v1/analytics/*` | ✅ | `/kpis`, `/kpis/{metric}`, `/trends`, `/anomalies`, `/thresholds`, `/quality`, `/flow`, `/causes`, `/bottleneck`, `/weaknesses`, `POST /run` |
| UI `/analytics` | ✅ für Schwachstellen | Die statische Seite liest `/analytics/weaknesses` plus Maschinen und Event-Summary: überfällige Aufträge, festgefahrene Freigaben, Plänänderungen (7 Tage), Leerlauf, Ausfälle 24 h, Collector-Trend. Sie ruft die KPI-/Anomalie-Endpunkte nicht auf |
| Tabellen | ✅ | `005`: `kpi_snapshots`, `metric_thresholds`, `detected_anomalies`, `shift_calendar`, `machine_state_history`. `006`: `measurement_quality`, `order_flow_segments`, `lateness_causes`, `bottleneck_rank` |

Deploy von `283ee4b` nach DEV ist grün (Run `42499223057`). Der Job führt Migrationen aus. Dieser Abgleich hat das Schema auf dem Host nicht abgefragt. Der manuelle Probe vom 2026-11-07 sah noch Schema `002`.

---

## GitHub Actions auf `main` (Stand dieses Abgleichs)

| Lauf | Ergebnis |
|---|---|
| CI `283ee4b` (`42499222986`) | ✅ pytest, ruff (advisory), mypy (advisory), Docker smoke |
| Deploy to DEV `283ee4b` (`42499223057`) | ✅ Build & Push und Deploy to DEV host |
| CI und Deploy für Q2P `2796032` | ✅ |
| Integration nightly `6710fdc` (`42469243262`, 2026-11-08 09:55 UTC) | ❌ Exit 2, vor Q2P/Analytics |
| Lint Cleanup schedule (`42473962358`) | ❌ Exit 1 |
| PR Review run `42499221888` an `283ee4b` | ❌ keine Jobs |
| CI Failure Triage an `283ee4b` | skipped (CI grün) |

## Operational status (letzter manueller DEV-Probe, 2026-11-07)

Diese Tabelle ist der letzte im Dokument festgehaltene Hands-on-Probe. Sie ist kein Beleg für den Zustand nach den Deploys vom 2026-11-08.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Zum Probe-Zeitpunkt existierte das SQL-Login `bdx_readonly` auf LDSAP nicht. Das Skript wurde danach korrigiert (`7d0fb2f`, `DENY CONTROL` entfernt). Ob das Login inzwischen angelegt ist, steht nicht im Git |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** zum Probe-Zeitpunkt. Alembic-Head im Git ist jetzt `006` |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` and `report-production 38559` wurden vom Dry-Run blockiert und in `sl_operations` auditiert |
| API + `/dashboard` on :8085 | ✅ zum Probe-Zeitpunkt. `/analytics` und `/q2p` kamen danach |

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| Dry-Run-Default im Commit | `ServiceLayerSettings.dry_run` defaultet auf aus. `.env.example` setzt den Schalter auf Schreiben. `AGENTS.md` verlangt den Schalter in committeten Beispielen auf Blockieren. Dieser Lauf ändert keinen Produktcode |
| Nächtliche Integration | Lauf vom 2026-11-08 auf `6710fdc` rot. Nach Q2P und Analytics erneut ausführen |
| PR-Review- und Lint-Cleanup-Workflows | letzte Läufe rot; Ursache in diesem Abgleich nicht weiter zerlegt |
| Coverage-Ratchet | Gate ist 68 %. `AGENTS.md` und der Kopf von `ci.yml` nennen weiter 80 %. Ruff/mypy bleiben advisory |
| Q2P-Grants | `docs/sql/grant_q2p_readonly.sql` ist nicht Teil von Alembic. Anwendung auf LDSAP ist ein Operator-Schritt |
| SQL-Login `bdx_readonly` | Skript `docs/sql/create_bdx_readonly.sql` ist korrigiert. Anlage auf LDSAP seit dem Probe vom 2026-11-07 nicht im Git belegt |
| MQTT / Kafka Broker | Publisher existieren, Defaults sind aus |
| Collector gegen PROD | read-only, braucht eine getrennte PG-Datenbank oder mode-prefixed `source_key`. Bisher nur Einzelauftrags-Probes |
| `docs/dora-metrics.md` | Workflow existiert, Datei fehlt auf `main` |
| Sync-Skill | `.cursor/skills/dev-sync/SKILL.md` und `.cursor/prompts/sync-coordinator.mdc` sind nicht im Repo. Dieser Abgleich folgt dem Automations-Prompt und `AGENTS.md` |
| Multi-company SAP, SSO/SCIM | kein Code |
| Machine `User`/operator and `LastProdEnd` | im ersten Probe leer; MDE-Seite |

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not** exist in the Leisinger company databases. `queries.py` selects `NULL` placeholders; `u_type`/`u_priority` stay `None`. OWOR has other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags) that may be useful later.
2. **Net delta between cycles**: if two changes happen within one polling interval only the net delta is visible (events are derived from state diffs, not from SAP change logs).
3. **Incremental window**: orders that are closed *and* whose `UpdateDate` is older than the lookback window are only caught because BDX re-reads its known open orders by DocEntry. Orders unknown to BDX (created before the first full load and never open since) are not re-read – run `collect --once --full` after long outages or set `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: there is no BDE terminal system; records are reconstructed from SCADA telemetry (`BDE_GAP_SECONDS` splits segments). Scrap quantities are therefore always 0.
5. **API authentication** is an optional shared key only; do not expose the API outside the LAN without a gateway/mTLS.
6. **Legacy history**: the Sprint 001 migration seeded `order_state` with fingerprint `''`, so the first incremental cycle after upgrading rewrites one history row per open order (observed at the 2026-11-07 probe: 871, 30 s one-off).
7. **Schwachstellen-UI und KPI-API** sind zwei Flächen. `/analytics` zeigt die Aggregat-Signale. Zeitreihen, Anomalien und Diagnose liegen auf den REST-Endpunkten.
8. **Q2P Personal** bleibt eine explizite offene Frage.

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py          # Env-var configuration
│   ├── db/                # SAP/PG engines, OWOR/OITM, queries_sap_extended.py
│   ├── models/            # events, sap, analytics
│   ├── collector/         # polling, snapshots, change_detector, machines
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── publish/           # Null, MQTT, Kafka
│   ├── sap_sl/            # Service Layer client, mode, audited operations
│   ├── agents/            # Sprint 004 quality-gate agents
│   ├── analytics/         # Sprint 005 KPIs, anomalies, thresholds, diagnosis
│   ├── q2p/               # Quote-to-Promise evaluator, store, models
│   ├── api/               # FastAPI, routes, static dashboard/analytics/q2p
│   └── cli/               # bdx-collect
├── alembic/               # 001 … 006 (head 006)
├── tests/                 # 181 test functions, including tests/integration/ (8)
├── scripts/               # triage, review, dora, deploy.ps1, prepare-dev-host.sh
├── Dockerfile, docker-compose.yml
├── AGENTS.md
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS,
                           # REQUIREMENTS, sql/
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc
```
