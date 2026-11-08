# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-08 20:37 (CET)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._
>
> **Git-Abgleich:** `origin/main` = `283ee4b` (2026-11-08 17:18 +0100), `feat(analytics): Sprint 005 - KPI engine, anomaly detection & self-tuning thresholds (#5)`. Arbeitsbaum sauber, kein Commit vor `origin/main`. Ziele: [`PROJECT_GOALS.md`](PROJECT_GOALS.md). Anforderungen: [`REQUIREMENTS.md`](REQUIREMENTS.md).

| Sprint / Lieferung | Scope | Status auf `main` |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ auf `main` (`4219156`, #1) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ auf `main` (`60bb34a`, `936d8c8`) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ auf `main` (`936d8c8`). Publisher gebaut, kein Broker konfiguriert. Write-back nur mit Dry-Run-Guard |
| 004 | CI/CD, quality-gate agents, integration tests, HOTL prompts | ✅ Dateien auf `main`. CI und Deploy to DEV für `283ee4b` grün. ruff/mypy bleiben advisory, Coverage-Gate ist 68 %. Nightly-Integration und Lint-Cleanup am 2026-11-08 rot |
| Q2P | Quote-to-Promise cockpit (parallele Anfragebewertung) | ✅ auf `main` (#33, `2796032`, Alembic `004`). Kein Sprint-005-Label in Git |
| 005 | KPI engine, anomaly detection, self-tuning thresholds, Schwachstellen-Dashboard, Diagnose | ✅ auf `main` (#5, #6, #12, Alembic `005`–`006`). CI und Deploy to DEV für `283ee4b` grün. Shop-Floor in diesem Lauf nicht neu gemessen |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ nicht im Baum |

Test suite: 180 `test_`-Funktionen unter `bdx-intelligence/tests` (172 Unit auf SQLite in-memory, 8 Integration). Integration überspringt, wenn DEV-Zugangsdaten fehlen. CI-Gate: `--cov-fail-under=68` (Kommentar im Workflow: Floor ~69 %, nur nach oben ratcheten). `AGENTS.md` nennt noch 80 % als Ziel.

---

## Sprint 001 – SAP Read-only Collector  ✅ auf `main`

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002`; Head im Baum ist `006` |
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
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value on the 2026-11-07 probe was **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV 2026-11-07: **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is history-on-change only (was +38 561 rows per cycle) |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only; 10 machines on the floor (probe 2026-11-07) |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | MACHINE_ONLINE / OFFLINE / STATE_CHANGED / ORDER_STARTED / ORDER_FINISHED / PIECES_REPORTED |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` on events and `/api/v1/machines` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records (start/end/pieces per order & machine) from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing, dashboard & write-back  ✅ auf `main`

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured** (`MQTT_ENABLED=false` in the example config) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | alternative to MQTT; key = `source_key` (partition affinity), JSON value; `build_all_publishers()` composes both when both are on |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | plus `/health/live` |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. Dry-run against DEV verified on 2026-11-07 (no real writes). Real writes are an operator switch in the host environment only; committed files keep the guard |
| Dockerfile + docker-compose.yml | ✅ im Baum | Deploy-to-DEV-Workflow läuft (siehe unten). SQL-Login `bdx_readonly` war am 2026-11-07 noch nicht vorhanden; dieser Lauf hat das nicht erneut geprüft |

## Quote-to-Promise cockpit  ✅ auf `main` (#33)

Git führt Q2P nicht als Sprint 005. Sprint 005 ist die Analytics-Lieferung. Q2P ist `2796032` / PR #33, Migration `004` (`q2p_inquiries`). CI und Deploy to DEV für diesen Commit waren grün (2026-11-08).

**Goal**: Replace serial multi-person clarification on inquiries (material, capacity, price, personnel)
with one inquiry case that answers domains in parallel from SAP + shop floor. Humans only see
`open_questions` where the system has no data.

| Feature | Status | Notes |
|---|---|---|
| Inquiry case store `q2p_inquiries` (Alembic `004`) | ✅ | status draft/ready/blocked/decided; decision audit |
| Parallel evaluator `bdx.q2p.service.evaluate_promise` | ✅ | item / material / BOM / capacity / pricing / personnel |
| SAP reads OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ | graceful degrade on missing SELECT |
| Capacity from `machine_state` + open `order_state` | ✅ | idle vs busy + backlog same item |
| REST `/api/v1/q2p/*` + ad-hoc `/q2p/promise` | ✅ | create, list, get, patch, evaluate, decide |
| Cockpit UI `/q2p` | ✅ | `static/q2p.html` |
| `bdx-collect serve` attaches SAP engine | ✅ | without engine → SAP domains become open questions |
| SQL grant script `docs/sql/grant_q2p_readonly.sql` | ✅ im Baum | zusätzlich Grants in `docs/sql/create_bdx_readonly.sql`. Ob sie auf LDSAP liegen, ist hier nicht geprüft |
| Personnel domain | ⬜ bewusst offen | kein Schicht-/Qualifikations-Feed; Domain bleibt `needs_human` |

**Deploy notes (code, not re-probed):** `alembic upgrade head` includes migration 004; grants are a DBA step; UI is `http://<host>:8085/q2p`.

## Sprint 004 – CI/CD, quality gates, HOTL  ✅ Dateien auf `main`

Die frühere Aussage „nichts committed / untracked“ stimmt nicht mehr. Workflows, `scripts/`, `tests/integration/`, `src/bdx/agents/`, `AGENTS.md` und `.cursor/prompts/` liegen auf `origin/main`.

| Feature | Status | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | ✅ | push/PR to `main`: ruff und mypy **advisory** (`continue-on-error`), pytest `--cov-fail-under=68`, Docker build smoke. Lauf `42499222986` für `283ee4b`: success |
| `.github/workflows/integration.yml` | ✅ geschrieben, 🔴 letzter Lauf | nightly `0 3 * * *`. Lauf `42469243262` (2026-11-08, SHA `6710fdc`): Job „Integration (DEV SAP + SL DRY_RUN)“ exit 2. Die Workflow-Meldung verweist auf die Logs; dieser Abgleich hat die Assertion nicht wiederholt |
| `.github/workflows/deploy-dev.yml` | ✅ | push to `main` → Image `ghcr.io/<repo-lowercase>/bdx-intelligence:dev` + `:sha-<sha>`, Deploy auf dem self-hosted Runner auf dem DEV-Host (kein SSH-Hop), `docker compose run --rm migrate`, recreate `collector` + `api`, `/health/live` muss 200 liefern. Der anschließende `diagnose`-Aufruf darf fehlschlagen, ohne den Job rot zu machen. Der Job bricht ab, wenn die Host-Umgebung Service-Layer-Schreibzugriff erlauben würde. Läufe für `2796032` und `283ee4b`: success |
| `.github/workflows/deploy-prod.yml` | ✅ geschrieben | `workflow_dispatch`, Environment `prod`, Inputs `run_migrations` und `confirm_sl_write`. Kein Prod-Deploy in diesem Abgleich |
| `.github/workflows/ci-triage.yml` | ✅ | `workflow_run` nach fehlgeschlagener CI. Für `283ee4b` skipped, weil CI grün war |
| `.github/workflows/pr-review.yml` | 🔴 letzter Lauf | Lauf `42499221888` für den Push `283ee4b`: conclusion failure. Die Jobs-API lieferte keine Steps; das ist kein Review-Befund aus dem Diff |
| `.github/workflows/auto-merge.yml` | ✅ geschrieben | trivial label + Pfad-Schutz. In diesem Lauf nicht ausgelöst |
| `.github/workflows/dora.yml` | ✅ geschrieben | weekly Mon 06:00 UTC. `docs/dora-metrics.md` liegt nicht im Baum |
| `.github/workflows/lint-cleanup.yml` | 🔴 letzter Lauf | Lauf `42473962358` (2026-11-08, SHA `6710fdc`): ruff meldete 431 Befunde (345 automatisch behoben, 86 übrig), Job rot. Branch `origin/chore/ruff-cleanup-20261108` ist nicht in `main` |
| Quality-gate agents (`src/bdx/agents/`) | ✅ | docs, tests, quality, runner. `bdx-collect check` / `check-docs` / `check-tests` / `check-quality` |
| Integration tests (`tests/integration/`) | ✅ im Baum | 8 Tests. Skip ohne DEV-Creds. Nightly-Lauf siehe oben |
| HOTL prompts (`.cursor/prompts/`) | ✅ | `from-notion-spec`, `triage-issue`, `feature`, `bugfix`, `refactor`, `testgen`. `.cursor/skills/dev-sync/` und `sync-coordinator.mdc` sind **nicht** auf `main` (offen in PR #3) |
| PROD migration guard (`alembic/env.py`) | ✅ | `ALEMBIC_ALLOW_PROD=1` nur, wenn der Prod-Workflow die Freigabe setzt |
| Helper scripts (`scripts/`) | ✅ | `ci_triage.py`, `pr_review.py`, `create_pr.py`, `dora_metrics.py`, `prepare-dev-host.sh`, `deploy.ps1`, Runner-/Secret-Helfer |

## Sprint 005 – Analytics, Anomalien, Diagnose  ✅ auf `main`

Commit `283ee4b` (PR #5) plus Schwachstellen-Dashboard `2f13c3f` (PR #6) und Darstellung `6850feb` (PR #12). Migration `005` wurde beim Merge hinter Q2P-`004` nummeriert; Diagnose ist `006`.

| Feature | Status | Notes |
|---|---|---|
| KPI cycle in `run_polling_loop` | ✅ | Default 600 s. `AnalyticsCollector` / `run_analytics_once` |
| Shop-floor KPIs | ✅ | `cycle_time_hours`, `on_time_delivery_rate`, `backlog_overdue_count`, `rejection_rate_pct`, `release_to_start_hours`, `order_change_frequency`, `machine_utilization_pct`, `setup_ratio_pct`, `mtbf_hours`, `mttr_hours`, `queue_unstarted_count`, `oee_availability_pct` |
| Procurement KPIs | ✅ | aus SAP, wenn eine Engine da ist: `material_coverage_pct`, `critical_items_count`, `po_lead_time_days`, `supplier_otd_rate`, `po_overdue_count`, `gr_delay_days`, `stock_coverage_days` |
| Anomaly detection | ✅ | `detected_anomalies`, Empfehlungstext, resolved/unresolved |
| Self-tuning thresholds | ✅ | Seeds sofort, Perzentil P75/P90 ab 14 Samples über 30 Tage, Tune-Intervall 24 h |
| Diagnosis | ✅ | `measurement_quality` (inkl. Little's Law), `order_flow_segments` (wait/setup/run/post-process), `lateness_causes` (material_gap, overdue_po, waiting_idle, bottleneck, scrap, unstable, unassigned), `bottleneck_rank` |
| REST `/api/v1/analytics/*` | ✅ | `kpis`, `kpis/{metric}`, `trends`, `anomalies`, `thresholds`, `quality`, `flow`, `causes`, `bottleneck`, `weaknesses`, `POST /run` |
| UI `/analytics` | ✅ | `static/analytics.html` |
| Tests | ✅ | `test_analytics.py` (40), `test_diagnosis.py` (10), `test_weaknesses.py` (11) |

Schwächen-Liste (`/weaknesses`): überfällige offene Aufträge, hängende freigegebene Aufträge, Planänderungen, Idle-Maschinen, Offline-Events, Collector-Fehler.

---

## CI- und Deploy-Stand (2026-11-08, nicht der Shop-Floor)

| Lauf | SHA | Ergebnis |
|---|---|---|
| CI | `283ee4b` | success (`42499222986`) |
| Deploy to DEV | `283ee4b` | success (`42499223057`), inklusive `migrate` und `/health/live` |
| CI Failure Triage | `283ee4b` | skipped |
| pr-review workflow | `283ee4b` | failure (`42499221888`), keine Job-Steps in der API |
| CI + Deploy to DEV | `2796032` (Q2P) | success |
| Integration nightly | `6710fdc` | failure (`42469243262`) |
| Lint Cleanup | `6710fdc` | failure (`42473962358`), 86 ruff-Befunde übrig |

Dieser Lauf hat SAP, Postgres und die Maschinen nicht abgefragt. Ein grüner Deploy sagt, dass `migrate` und `/health/live` durchliefen, nicht dass `diagnose` SAP gesehen hat.

## Letzter Hands-on-Probe (DEV, 2026-11-07)

Unverändert als Messpunkt stehen lassen. Schema im Repo ist seitdem von `002` auf `006` gewachsen. Ob die laufende Datenbank genau `006` ist, folgt nur indirekt aus dem grünen `migrate` am 2026-11-08.

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). SQL-Login `bdx_readonly` existierte zu diesem Zeitpunkt nicht auf LDSAP |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** zu diesem Zeitpunkt |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| PROD read probe (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed. DEV lags PROD (FA 38560/38561 were R in PROD, P in DEV) |
| SAP write-back dry-run (DEV) | ✅ `release 38559` and `report-production 38559 -q 5 -w W01` blocked by the dry-run guard and audited in `sl_operations` |
| API + `/dashboard` on :8085 | ✅ endpoints and dashboard rendered |

### Findings from the first real machine cycle (still the last recorded probe)

* **DEV database lags production**: machine *Integrex i500S* ran SAP order **38574**, but `DEV_SBO_LEISINGER` ended at DocNum 38561. The link resolves when the collector reads PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`) into a separate event store.
* XMSK `Order` is not always a DocNum: *QT350MY* reported `10886/NEU`. Those stay raw in `order_ref`.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Offene Punkte

| Item | Ziel | Notes |
|---|---|---|
| Nightly integration wieder grün | G4 | Lauf vom 2026-11-08 rot (exit 2) |
| ruff/mypy von advisory auf blockierend, Coverage-Gate Richtung 80 % | G4 | Gate steht bei 68; Lint-Cleanup 86 Befunde übrig; Branch `chore/ruff-cleanup-20261108` nicht gemergt |
| `pr-review.yml` auf Push nach `main` | G4 | letzter Lauf failure ohne Job-Steps |
| `docs/dora-metrics.md` | G4 | Workflow existiert, Datei fehlt |
| SQL-Login `bdx_readonly` plus Q2P-SELECT auf LDSAP | G7 | Skripte liegen im Baum. Letzter negativer Befund: 2026-11-07. Nicht erneut geprüft |
| MQTT- oder Kafka-Broker | G8 | Publisher-Code da, kein Broker |
| Collector gegen PROD mit eigener PG | G9 | bisher nur Einzelauftrags-Proben (2026-11-07) |
| Q2P Personal / Qualifikation | G11 | Domain fest `needs_human` |
| Multi-company SAP, SSO/SCIM | G10 | nicht im Baum |
| Echte Service-Layer-Schreibvorgänge | G3 | nur als Operator-Schalter auf dem Host, nie in einer committeten Datei |
| Dev-Sync-Skill auf `main` | — | PR #3 offen. Dieser Abgleich folgt dem Automations-Prompt; die Skill-Datei ist nicht auf `main` |

### Branches vor `origin/main` (nicht gemergt)

Produktnah: `cursor/q2p-cockpit-9a6c` (PR #39, bdx-quoter in der Pricing-Domain), `cursor/promise-platform-vision-9a6c` (PR #40, Vision, nicht auf `main`), `cursor/dev-sync-agent-e2dc` (PR #3), `chore/ruff-cleanup-20261108`. Dazu viele offene Doku-PRs `cursor/projekt-dokumenten-abgleich-*` und `cursor/sync-agent-*`, die denselben Abgleich gegen ältere Stände versuchen. Nichts davon ist Teil von `283ee4b`.

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not** exist in the Leisinger company databases. `queries.py` selects `NULL` placeholders. OWOR has other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags) that may be useful later.
2. **Net delta between cycles**: if two changes happen within one polling interval only the net delta is visible.
3. **Incremental window**: orders closed *and* older than the lookback are caught only because BDX re-reads known open orders by DocEntry. Unknown historical orders need `collect --once --full` or `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: records come from SCADA telemetry (`BDE_GAP_SECONDS`). Scrap quantities from that path stay 0.
5. **API authentication** is an optional shared key; do not expose the API outside the LAN without a gateway/mTLS.
6. **Legacy history**: Sprint 001 seeded `order_state` with fingerprint `''`, so the first incremental cycle after that upgrade rewrote one history row per open order (observed 2026-11-07: 871).
7. **Q2P personnel** has no feed. Commercial margin beyond list price is not evaluated.
8. **Analytics reliability** is gated by `measurement_quality` (`utilization_reliable`, `cycle_time_reliable`). A green deploy does not mean those flags are true on DEV.

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py
│   ├── db/                # sap.py, postgres.py, queries.py, queries_sap_extended.py
│   ├── models/            # sap, events, analytics
│   ├── collector/         # polling (SAP + analytics timer), snapshots, change_detector, machines
│   ├── adapters/          # machine.py (XMSK), bde.py
│   ├── analytics/         # kpis, kpis_procurement, anomalies, thresholds, history,
│   │                      #   quality, flow, causes, bottleneck, collector
│   ├── q2p/               # service, store, models
│   ├── publish/           # Null, MQTT, Kafka
│   ├── sap_sl/            # client, mode, audited operations
│   ├── agents/            # docs, tests, quality, runner
│   ├── api/               # routes orders, machines, service_layer, analytics, q2p
│   │                      # static: dashboard.html, analytics.html, q2p.html
│   └── cli/
├── alembic/versions/      # 001 … 006 (head 006)
├── tests/                 # 180 test functions, including tests/integration (8)
├── scripts/
├── Dockerfile, docker-compose.yml
├── AGENTS.md
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS,
                           # PROJECT_GOALS, REQUIREMENTS, sql/
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc
```
