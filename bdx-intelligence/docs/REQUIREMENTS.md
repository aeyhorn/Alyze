# BDX Intelligence – Requirements

> **Zuletzt aktualisiert:** 2026-11-08 08:37 (UTC+1)
> Stand: `main` = `6850feb`. Nachweis im Code und in `PROJECT_STATUS.md`. Ziele: `PROJECT_GOALS.md`.

Regeln für die nächste Pflege:

- Neue Anforderungen werden angehängt. Die nächste freie ID ist **R027**.
- IDs werden nicht wiederverwendet und nicht umsortiert.
- Der Status einer Zeile wird in place geändert, wenn sich der Git-Stand ändert.
- Eine Anforderung gilt erst als erfüllt, wenn sie auf `main` liegt. Offene Pull Requests bleiben `open`.

| ID | Anforderung | Status | Wo |
|---|---|---|---|
| R001 | MSSQL-Kanal zu SAP Business One ist read-only. INSERT/UPDATE/DELETE/DDL werden in der Engine abgewiesen | met | `src/bdx/db/sap.py` |
| R002 | Fertigungsaufträge aus OWOR/OITM über parametrisierte Abfragen, mit Full-Load und inkrementellem Fenster | met | `src/bdx/db/queries.py`, `collector/polling.py` |
| R003 | Eine Zeile pro Auftrag in `order_state` (Fingerprint-Upsert); `order_snapshots` nur bei Änderung; `snapshot_runs` pro Zyklus | met | `collector/snapshots.py`, Alembic 001–002 |
| R004 | Domain-Events idempotent über `event_id`: Auftrag (created, released, quantity, due date, partial, closed) und Maschine (online, offline, state, order start/finish, pieces) | met | `models/events.py`, `collector/change_detector.py`, `collector/machines.py` |
| R005 | SAP-Statuscodes `P` Planned, `R` Released, `L` Closed, `C` Cancelled | met | `models/sap.py` |
| R006 | Maschinenfeed Mazak XMSK über den SCADA-Proxy, read-only, eigener Poll, Offline-Erkennung | met | `adapters/machine.py`, `collector/machines.py` |
| R007 | Numerische XMSK-`Order` wird als SAP-`DocNum` verknüpft. Freitext bleibt `order_ref` ohne Link | met | `collector/machines.py` |
| R008 | BDE-Sätze werden aus der SCADA-Telemetrie abgeleitet, nicht aus einem BDE-Terminal. Ausschuss bleibt 0 | met | `adapters/bde.py` |
| R009 | Jedes neue Event kann an MQTT und/oder Kafka. Fehler beim Publish brechen den Collector nicht. Ohne Broker bleibt der Null-Publisher | met (broker open) | `publish/mqtt.py`, `publish/kafka.py` |
| R010 | REST unter `/api/v1` für Orders, Events, Machines, BDE, Runs, Health inklusive `/health/live`, optionales API-Key | met | `api/routes/` |
| R011 | Betriebsdashboard unter `/dashboard` | met | `api/static/dashboard.html` |
| R012 | Service-Layer-Write-back: Release, Close, Cancel, Report-Production. Jeder Aufruf landet in `sl_operations`. Dry-Run ist der committete Default | met (real writes open) | `sap_sl/operations.py`, Alembic 003 |
| R013 | CLI `bdx-collect` für Diagnose, Collect, Machines, Runs, Reports, Service-Layer und die Check-Agents | met | `cli/report.py` |
| R014 | CI auf Push und PR nach `main`: pytest mit Coverage-Untergrenze 68 %, Docker-Smoke. Ruff und mypy laufen advisory | met | `.github/workflows/ci.yml`. Grün auf `6850feb` (run 42420693051) |
| R015 | Nächtliche Integrationstests gegen DEV. Ohne Credentials wird geskippt. Die Fixture lässt keine echten SAP-Writes zu | partial | `.github/workflows/integration.yml`, `tests/integration/`. Workflow liegt auf `main`, Actions-Lauf: keiner |
| R016 | DEV-Deploy bei Push auf `main`: Image nach GHCR, Deploy auf dem Self-hosted-Runner des DEV-Hosts, Migration, Smoke `/health/live`. Abbruch, wenn die Host-Umgebung Dry-Run ausschaltet | partial | `.github/workflows/deploy-dev.yml`. Letztes erfolgreiches Deploy `2f13c3f` (run 42415113477). Deploy von `6850feb` (run 42420693125): Image gebaut, Self-hosted-Job seit 2026-11-07 23:36 (UTC+1) queued, um 08:37 (~9 h) nicht gestartet |
| R017 | PROD-Deploy nur per `workflow_dispatch`, mit Reviewern. Migrationen nur nach explizitem Opt-in | met (workflow) | `.github/workflows/deploy-prod.yml`, `alembic/env.py` |
| R018 | Quality-Gate-Agents (Docs, Tests, Quality) und `bdx-collect check`, ohne Datenbank und ohne SAP | met | `src/bdx/agents/` |
| R019 | HOTL-Prompts und Agent-Regeln im Repo | met | `.cursor/prompts/`, `.cursor/rules/bdx-conventions.mdc`, `AGENTS.md` |
| R020 | Schwachstellen-Endpunkt und Seite: überfällige Aufträge, festgefahrene freigegebene Aufträge (unter 10 % und mindestens 3 Tage unverändert), Planänderungen über 7 Tage, idle Maschinen, Offline-Events über 24 Stunden, Collector-Fehler über 7 Tage, Run-Trend | met | `api/routes/analytics.py`, `api/static/analytics.html`, #6 und #12. 11 Tests in `tests/test_analytics.py` |
| R021 | Read-only SQL-Login für den Container, weil Windows-Auth im Linux-Image nicht zur Verfügung steht | partial | `docs/sql/create_bdx_readonly.sql`, `docs/sql/reset_bdx_readonly.sql`. Serverstand nicht erneut geprüft |
| R022 | Eigenes PostgreSQL für einen PROD-Lese-Collector, damit `order_state` nicht DEV und PROD mischt | open | nur Probe einzelner Aufträge, siehe `PROJECT_STATUS.md` |
| R023 | MQTT- oder Kafka-Broker ist konfiguriert und nimmt Events an | open | Publisher vorhanden, kein Broker in der committeten Konfiguration |
| R024 | Mehrere SAP-Buchungskreise | open | — |
| R025 | SSO/SCIM für die API | open | heute nur optionales Shared-Key |
| R026 | KPI-Snapshots, Anomalie-Erkennung und selbstjustierende Schwellen | open | nicht auf `main`. PR #5, konfliktiert mit `main` |

Nächste freie ID nach dieser Liste: **R027**.
