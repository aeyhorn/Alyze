# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-07 21:40 (CET)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

Abgleich mit Git am 2026-11-07 21:40 CET. Quelle ist `main` @ `6ccc036185b5` (`feat(infra): add prepare-dev-host.sh to install GitHub self-hosted runner`, 2026-11-07 21:28 +0100). Dieser Lauf hat den Baum gelesen und die GitHub-Actions-Liste abgefragt. SAP, PostgreSQL und der DEV-Host wurden nicht erneut gemessen. Die Tabelle „Operational status“ bleibt das letzte protokollierte Messergebnis.

| Sprint | Scope | Status auf `main` |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ im Baum, zuletzt betrieblich am 2026-11-07 protokolliert |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ im Baum |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ im Baum (Publisher gebaut, kein Broker konfiguriert; Write-back-Code vorhanden, Dry-Run siehe Sicherheitslücke unten) |
| 004 | CI/CD, quality-gate agents, integration tests, HOTL prompts, DEV/PROD-Deploy | 🟡 auf `main`. Lint und mypy in CI nur beratend. Coverage-Gate ist 68 %. Der Deploy-to-DEV-Lauf für `6ccc036` war beim Abgleich noch `pending` |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ nicht im Baum |

Testfunktionen im Baum: **112** (104 Unit, 8 Integration). `pyproject.toml` setzt `addopts` auf `-m 'not integration'`, der Default-Lauf ist also die Unit-Suite. CI (`ci.yml`) hängt `--cov-fail-under=68` an. Die Integration-Suite läuft in `integration.yml` (`pytest -m integration`, nightly 03:00 UTC und `workflow_dispatch`).

Ziele mit stabilen IDs: `docs/PROJECT_GOALS.md` (G1–G9). Neue Wünsche: `docs/REQUIREMENTS.md`. Dort stehen keine Zeilen; die nächste ID ist `R001`.

---

## Sprint 001 – SAP Read-only Collector  ✅ auf main

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002`, `003` (`sl_operations`) |
| Initial full-load of production orders | ✅ | `OWOR_SNAPSHOT_SQL` on first run / `--full` |
| Periodic polling (60 s) | ✅ | `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | |
| Domain events: ORDER_CREATED / ORDER_RELEASED / QUANTITY_CHANGED / DUE_DATE_CHANGED / ORDER_CLOSED | ✅ | see status-code note below |
| Retry with exponential backoff (tenacity) | ✅ | |
| FastAPI REST API, healthcheck, CLI, structured logs, secrets from env | ✅ | |
| Service Layer client + Dev/Prod mode registry | ✅ | write-back lives in Sprint 003 |

## Sprint 002 – BDE, machines, incremental reading  ✅ auf main

| Feature | Status | Notes |
|---|---|---|
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value is **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV: **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is now history-on-change only (was +38 561 rows per cycle) |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only; 10 machines on the floor |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | MACHINE_ONLINE / OFFLINE / STATE_CHANGED / ORDER_STARTED / ORDER_FINISHED / PIECES_REPORTED |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` on events and `/api/v1/machines` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records (start/end/pieces per order & machine) from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing, dashboard & write-back  ✅ auf main

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured** (`MqttSettings.enabled` default `False`) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | key = `source_key` (partition affinity), JSON value; `build_all_publishers()` composes MQTT + Kafka when both are on. `KafkaSettings.enabled` default `False` |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ im Code | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. Letztes Protokoll: DRY_RUN hat die DEV-Aufrufe blockiert und `sl_operations` beschrieben. Ob Dry-Run an ist, entscheidet die Laufzeit-Konfiguration, nicht dieser Commit |
| Dockerfile + docker-compose.yml | ✅ im Baum | Deploy-Workflows und `scripts/deploy.ps1` sind ebenfalls auf `main`. Ob der Host dem aktuellen Commit entspricht, sagt das Repo nicht |

## Sprint 004 – CI/CD, quality gates, deploy  🟡 auf main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

Der frühere Satz „nichts davon ist committed“ stimmt nicht mehr. Workflows, Agents, Scripts und Integrationstests liegen auf `main`. Was noch offen ist, steht in der Tabelle und unter „Open items“.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ auf main, Lauf für `6ccc036` grün | push/PR auf `main`: ruff und mypy mit `continue-on-error` (beratend), pytest mit `--cov-fail-under=68`, Docker-Build-Smoke-Test. Der Dateikopf kommentiert noch „>= 80 %“; das ausgeführte Gate ist 68 %. Actions-Lauf `42411199913` ist `success`. Arbeitsverzeichnis `bdx-intelligence/` |
| **`.github/workflows/integration.yml`** | ✅ auf main | nightly `0 3 * * *` + `workflow_dispatch`; `pytest -m integration`. Die Suite überspringt sich, wenn `SAP_DB_*`, `SL_*` und `POSTGRES_DSN` fehlen |
| **`.github/workflows/deploy-dev.yml`** | ✅ auf main, Lauf für `6ccc036` pending | Build auf `ubuntu-latest`, Image `ghcr.io/<repo-lowercase>/bdx-intelligence:dev` und `:sha-<sha>`. Deploy-Job `runs-on: [self-hosted, linux]`. Bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet. Actions-Lauf `42411199922` war beim Abgleich `pending` (keine Conclusion) |
| **`.github/workflows/deploy-prod.yml`** | ✅ auf main | nur `workflow_dispatch`; Deploy-Job ebenfalls `[self-hosted, linux]`; Inputs `run_migrations` und `confirm_sl_write` |
| **`.github/workflows/ci-triage.yml`** | ✅ auf main | `workflow_run` nach fehlgeschlagener CI → `scripts/ci_triage.py`. Ohne `CURSOR_API_KEY` No-Op |
| **`.github/workflows/pr-review.yml`** | ✅ auf main, Lauf für `6ccc036` failed | PR open/sync/reopen → `scripts/pr_review.py`. Actions-Lauf `42411198790` (push von `6ccc036`) ist `failure` nach 0 s. Logs in diesem Abgleich nicht gelesen |
| **`.github/workflows/auto-merge.yml`** | ✅ auf main | Label `trivial`, nur Test/Doku, keine geschützten Pfade (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) |
| **`.github/workflows/dora.yml`** | ✅ auf main | Montag 06:00 UTC → `scripts/dora_metrics.py`. `docs/dora-metrics.md` liegt noch nicht im Baum |
| **`.github/workflows/lint-cleanup.yml`** | ✅ auf main | Sonntag 04:00 UTC und `workflow_dispatch`; ruff-Fix als Aufräum-PR. `continue-on-error` in `ci.yml` bleibt, bis das Landen und das Gate scharf geschaltet wird |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ auf main | `docs.py` verlangt `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `SAP_MAPPING.md` und warnt, wenn der Status älter als 90 Tage ist. `tests.py` / `runner.py` toren bei 80 % Coverage, 50 % pro Modul, höchstens 10 % Skips. Das ist strenger als das CI-Gate von 68 % |
| **CLI `bdx-collect check`** | ✅ auf main | `check`, `check-docs`, `check-tests`, `check-quality`; `--json` für ein CI-Artefakt |
| **Integration tests** (`tests/integration/`) | ✅ auf main | 3 SAP-Lese-Tests + 5 Service-Layer-Contract-Tests. Marker `integration` (SAP-Lesen zusätzlich `sap_read`) |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ auf main | `from-notion-spec.mdc`, `triage-issue.mdc`, `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ auf main | SAP-Sicherheitsregeln, Architektur-Invarianten, Workflow |
| **`scripts/deploy.ps1`** | ✅ auf main | `12fa8cf`, Docker-Context-Deploy Richtung DEV |
| **`scripts/prepare-dev-host.sh`** | ✅ auf main | `6ccc036`. Idempotentes Provisioning eines self-hosted Runners (Labels `self-hosted,linux,dev,lan`) plus Docker. Das Registration-Token kommt nur aus der Umgebung, nie aus dem Skript |
| **PROD migration guard** (`alembic/env.py`) | ✅ auf main | `7d0fb2f`. Migriert nicht gegen die PROD-Event-Store-DSN, solange `ALEMBIC_ALLOW_PROD` nicht gesetzt ist. `deploy-prod.yml` setzt das nur beim freigegebenen Migrations-Input |
| **SQL login script** | ✅ auf main | `docs/sql/create_bdx_readonly.sql`. `DENY CONTROL` ist entfernt (`7d0fb2f`), weil es CONNECT blockiert hat. Ob der Login auf LDSAP existiert, wurde hier nicht geprüft |

### Was seit dem letzten Status-Text auf `main` gelandet ist

Der vorherige Text beschrieb Sprint 004 als untracked und `main` als einen Commit vor `origin/main`. Beides ist überholt. Nach dem Sprint-002/003-Bundle (`936d8c8`) liegen auf `main` zusätzlich:

| Commit | Inhalt |
|---|---|
| `2fcd60d` | konfigurierbarer Image-Name, Integration-Marker |
| `48afa46` | ruff und mypy in CI nur noch beratend |
| `7d0fb2f` | `DENY CONTROL` aus dem Readonly-Login entfernt, PROD-Migrations-Guard |
| `241b535` | Coverage-Gate von 80 % auf 68 % (Ratschen-Notiz, Floor ~69 %) |
| `2646b0d` | ghcr.io-Pfad wird kleingeschrieben (`Alyze` → `alyze`) |
| `1480f5c` | SSH-Deploy-Jobs auf dem self-hosted Runner (LAN) |
| `12fa8cf` | `scripts/deploy.ps1` |
| `1e38a68` | Zeitstempel in diesem Dokument, Hinweis in `AGENTS.md`, Marker `.runtime/last-deploy-*` |
| `6ccc036` | `scripts/prepare-dev-host.sh` |

`.runtime/last-deploy-at` enthält `2026-11-07 19:55:13 +01:00`, `.runtime/last-deploy-sha` enthält `1480f5c972fd`. Das ist ein committer Marker, keine Live-Abfrage des Hosts. `main` ist seitdem bei `6ccc036`.

## Operational status (DEV, protokolliert 2026-11-07, hier nicht erneut gemessen)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17). Ob der SQL-Login `bdx_readonly` inzwischen existiert, ist aus Git nicht ablesbar |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied (Stand des Protokolls; Migration 003 ist im Baum) |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` und `report-production 38559` wurden vom Dry-Run blockiert und in `sl_operations` protokolliert |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Dry-Run-Default widerspricht der Sicherheitsregel** | `ServiceLayerSettings.dry_run` steht im Code auf aus. `.env.example` lässt Dry-Run ebenfalls aus. `AGENTS.md` und der Kommentar in `deploy-dev.yml` verlangen Dry-Run an. Der DEV-Deploy bricht ab, wenn die Host-Datei Dry-Run ausschaltet. Dieser Abgleich ändert das nicht (kein Produktcode) und schreibt die Zuweisung nicht in Git |
| **DEV-Deploy von `6ccc036`** | Actions-Lauf 42411199922 war `pending`. Der Self-hosted-Runner ist die Voraussetzung; `prepare-dev-host.sh` ist das Provisioning-Skript, kein Nachweis, dass der Runner schon registriert ist |
| **Coverage-Ratchet und scharfe Lint/Type-Gates** | CI-Fail-Under ist 68 %. `TestAgent` erwartet 80 %. ruff (~381 Altlasten) und mypy (~48 Altlasten) sind in CI `continue-on-error`. Pfad steht in `AGENTS.md` |
| **`pr-review.yml` schlägt sofort fehl** | Mehrere Push-Läufe am 2026-11-07 mit Conclusion `failure` nach 0 s. Ursache in diesem Abgleich nicht gelesen |
| **SQL login `bdx_readonly` auf LDSAP** | Skript liegt in `docs/sql/create_bdx_readonly.sql`. Existenz auf dem Server hier nicht geprüft. Linux-Container brauchen den Login, weil Windows-Auth dort fehlt |
| **MQTT / Kafka broker** | Beide Publisher default `enabled=False`. Einschalten nur über die Laufzeit-Umgebung plus Extras `.[mqtt]` / `.[kafka]` |
| **Collector gegen PROD** | Read-only, aber mit eigener PostgreSQL-Datenbank oder mode-präfixiertem `source_key`, damit DEV- und PROD-Zeilen in `order_state` nicht mischen. Bisher nur Einzelauftrags-Proben protokolliert |
| **Echte SAP-Schreibvorgänge** | Bleiben eine Operator-Entscheidung ausserhalb von Git. Jeder Schreibpfad läuft durch `sap_sl/operations.py` und die Audit-Tabelle |
| Multi-company SAP, SSO/SCIM | ⬜ nicht auf `main` |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |
| GitHub-Settings | Environments `dev` und `prod` existieren, beide ohne Protection Rules (API, 2026-11-07 21:40 CET). Branch Protection von `main` war nicht lesbar (403). Secret-Werte wurden nicht gelesen. Workflows nennen weiterhin `CURSOR_API_KEY`, `DEV_SSH_*`, `PROD_SSH_*`, `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` |

### Nicht auf `main` (offene PRs, Stand 2026-11-07 21:40 CET)

Diese Zweige sind nicht Teil des abgeglichenen Baums. Titel nur als Lagebild, kein übernommener Scope:

| PR | Titel | Draft |
|---|---|---|
| 2 | docs: update PROJECT_STATUS.md – Sprint 004 complete | nein |
| 3 | Dev-Sync-Agent für Desktop und Cloud | nein |
| 4 | docs: reconcile project status and goals | ja |
| 5 | feat(analytics): Sprint 005 - KPI engine, anomaly detection & self-tuning thresholds | nein |
| 6 | feat: Schwachstellen-Analyse Dashboard | nein |
| 7 | docs: reconcile project status and goals | ja |
| 8 | docs: Projektstatus, Ziele und Anforderungen an main abgleichen | ja |

`.cursor/skills/dev-sync/SKILL.md` und `.cursor/prompts/sync-coordinator.mdc` liegen auf `main` nicht.

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not** exist in the Leisinger company databases. `queries.py` selects `NULL` placeholders; `u_type`/`u_priority` stay `None`. OWOR has other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags) that may be useful later.
2. **Net delta between cycles**: if two changes happen within one polling interval only the net delta is visible (events are derived from state diffs, not from SAP change logs).
3. **Incremental window**: orders that are closed *and* whose `UpdateDate` is older than the lookback window are only caught because BDX re-reads its known open orders by DocEntry. Orders unknown to BDX (created before the first full load and never open since) are not re-read – run `collect --once --full` after long outages or set `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: there is no BDE terminal system; records are reconstructed from SCADA telemetry (`BDE_GAP_SECONDS` splits segments). Scrap quantities are therefore always 0.
5. **API authentication** is an optional shared key only; do not expose the API outside the LAN without a gateway/mTLS.
6. **Legacy history**: the Sprint 001 migration seeded `order_state` with fingerprint `''`, so the first incremental cycle after upgrading rewrites one history row per open order (observed: 871, 30 s one-off).
7. **Dry-Run-Default**: der Code-Default von `ServiceLayerSettings.dry_run` ist aus. Die Agent-Regel „Dry-Run ist der Default“ beschreibt den Soll-Zustand, nicht den Feld-Default.
8. **CI-Kommentar vs. Gate**: `ci.yml` kommentiert 80 %, das Kommando erzwingt 68 %.

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py          # Env-var configuration (SAP, PG, collector, machine, BDE, MQTT, Kafka, SL, app)
│   ├── db/                # SAP/PG engines + parameterised OWOR/OITM queries
│   ├── models/            # Pydantic WorkOrder + ORM (order_state, order_snapshots, snapshot_runs,
│   │                      #   machine_state, domain_events, sl_operations)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry)
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI app, routes, static/dashboard.html
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001, 002, 003 (sl_operations)
├── tests/                 # 104 unit test functions + tests/integration/ (8)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py,
│                          #   deploy.ps1, prepare-dev-host.sh
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen
    └── rules/             # bdx-conventions.mdc (alwaysApply)
```
