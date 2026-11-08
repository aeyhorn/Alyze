# BDX Intelligence – Requirements

> **Zuletzt aktualisiert:** 2026-11-08 19:40 (UTC+1)
> Abgleich mit `main` @ `283ee4b`. Status heißt hier: im Git belegt, nicht „auf dem Shop-Floor neu gemessen“. Der letzte Hands-on-Probe steht in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) unter 2026-11-07. Ziele: [`PROJECT_GOALS.md`](PROJECT_GOALS.md).

Legende: **erfüllt** = Code und Tests auf `main`. **teilweise** = geliefert, mit einer im Git sichtbaren Lücke. **offen** = nicht implementiert. **Betrieb** = Workflow oder Probe, kein reiner Code-Nachweis.

## Sicherheit

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| SR-01 | MSSQL-Kanal ist read-only. Kein INSERT/UPDATE/DELETE/DDL aus der Anwendung | erfüllt | `src/bdx/db/sap.py`, `AGENTS.md` |
| SR-02 | SQL nur mit gebundenen Parametern | erfüllt | `src/bdx/db/queries.py`, `queries_sap_extended.py` |
| SR-03 | Secrets nur aus der Umgebung. `.env` nicht im Git | erfüllt | `.gitignore`, `AGENTS.md` |
| SR-04 | Service-Layer-Schreibaufrufe laufen durch `sap_sl/operations.py` und landen in `sl_operations` | erfüllt | Migration `003`, CLI und REST |
| SR-05 | Committete Beispiele lassen den Dry-Run-Schalter auf Blockieren | offen | `ServiceLayerSettings.dry_run` defaultet auf aus. `.env.example` lässt Schreiben zu. Der DEV-Deploy-Workflow bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet |
| SR-06 | Prod-Migrationen nur mit explizitem Opt-in | erfüllt | `alembic/env.py` verlangt `ALEMBIC_ALLOW_PROD=1`, wenn `SAP_MODE=prod` und `POSTGRES_DSN_PROD` gesetzt sind |
| SR-07 | Prod-Deploy nur mit manueller Freigabe | erfüllt im Workflow | `deploy-prod.yml` ist `workflow_dispatch` mit Environment `prod` |
| SR-08 | API außerhalb des LAN nur mit Schlüssel oder Gateway | teilweise | `API_KEY` optional. Leer heißt offen |

## SAP-Lesen und Event-Store

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| FR-01 | Fertigungsaufträge aus OWOR/OITM lesen | erfüllt | Sprint 001 |
| FR-02 | Statuscodes `P` geplant, `R` freigegeben, `L` geschlossen, `C` storniert | erfüllt | Sprint 002, `docs/SAP_MAPPING.md` |
| FR-03 | Eine Zeile `order_state` pro Auftrag, Historie nur bei Änderung | erfüllt | Migration `002` |
| FR-04 | Inkrementelles Fenster plus Nachlesen verschwundener offener Aufträge per DocEntry | erfüllt | `collector/polling.py` |
| FR-05 | Ereignisse `ORDER_CREATED`, `ORDER_RELEASED`, `QUANTITY_CHANGED`, `DUE_DATE_CHANGED`, `ORDER_PARTIAL_COMPLETE`, `ORDER_CLOSED` | erfüllt | `EventType` |
| FR-06 | `event_id` idempotent, Duplikate werden verworfen | erfüllt | `persist_events()` |
| FR-07 | `source_key` = `<company_db>:<doc_entry>` | erfüllt | |
| FR-08 | Custom-UDFs `U_Type`, `U_Priority`, `U_BDX_Machine` nicht voraussetzen | erfüllt | Queries selektieren NULL |
| FR-09 | Mehrere Buchungskreise | offen | TBD |

## Shop-Floor

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| FR-10 | Maschinenzustand read-only aus der XMSK-XML | erfüllt | `adapters/machine.py` |
| FR-11 | Ereignisse ONLINE, OFFLINE, STATE_CHANGED, ORDER_STARTED, ORDER_FINISHED, PIECES_REPORTED | erfüllt | `EventType` |
| FR-12 | Numerische XMSK-Order an SAP-`DocNum` binden. Freitext bleibt `order_ref` | erfüllt | Sprint 002 |
| FR-13 | BDE aus SCADA-Telemetrie ableiten, kein Terminal-System | erfüllt | `adapters/bde.py`. Ausschuss dadurch 0 |
| FR-14 | Maschinen nicht steuern | erfüllt | nur HTTP GET |

## API, UI, CLI

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| FR-15 | REST für Orders, Events, Machines, BDE, Runs, Health | erfüllt | `api/routes/` |
| FR-16 | Dashboard `/dashboard` | erfüllt | `static/dashboard.html` |
| FR-17 | CLI `diagnose`, `collect`, `machines`, `runs`, `serve`, Service-Layer-Kommandos, `check*` | erfüllt | `cli/report.py` |
| FR-18 | Optional MQTT und Kafka, Collector läuft ohne Broker weiter | erfüllt | Defaults `enabled=false` |

## Quote-to-Promise

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| FR-19 | Anfrage als Fall speichern und entscheiden (accept, reject, counter) | erfüllt | Migration `004`, `/api/v1/q2p/inquiries` |
| FR-20 | Domänen Artikel, Material, Stückliste, Kapazität, Preis parallel prüfen | erfüllt | `q2p/service.py` |
| FR-21 | Fehlende Daten als `open_questions`, nicht als stille Annahme | erfüllt | `needs_human` |
| FR-22 | Personal/Qualifikation aus einem Schichtfeed | offen | Domain `personnel` ist fest `UNKNOWN` |
| FR-23 | Cockpit unter `/q2p` | erfüllt | `static/q2p.html` |
| FR-24 | SAP-SELECT für die Q2P-Tabellen auf dem Login | Betrieb | Skript `docs/sql/grant_q2p_readonly.sql`. Ausführung nicht im Git |

## Analytics

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| FR-25 | Auftrags- und Maschinen-KPIs zyklisch persistieren | erfüllt | `analytics/kpis.py`, Intervall 600 s, `kpi_snapshots` |
| FR-26 | Beschaffungs-KPIs, wenn eine SAP-Engine da ist | erfüllt | `kpis_procurement.py`. Ohne Engine übersprungen |
| FR-27 | Anomalien gegen Schwellen, mit Empfehlung, und Schließen bei Entwarnung | erfüllt | `analytics/anomalies.py` |
| FR-28 | Schwellen seeden und aus der Historie nachziehen | erfüllt | `analytics/thresholds.py`, Intervall 24 h |
| FR-29 | Messgüte, Flusssegmente, eine Verspätungsursache pro verspätetem Auftrag, Engpass-Rang | erfüllt | Migration `006` |
| FR-30 | REST für KPIs, Trends, Anomalien, Schwellen, Qualität, Fluss, Ursachen, Engpass und einen Lauf auf Abruf | erfüllt | `api/routes/analytics.py` |
| FR-31 | Schwachstellenliste: überfällig, festgefahren (<10 % Fortschritt und 3 Tage unverändert), Plänänderung 7 Tage, Leerlauf, Ausfälle 24 h, Collector-Fehler | erfüllt | `GET /analytics/weaknesses`, UI `/analytics` |
| FR-32 | Dieselbe UI zeigt KPI-Zeitreihen und Anomalien | offen | `/analytics` liest die Schwachstellen-Aggregation, nicht `/kpis` oder `/anomalies` |

## Lieferung und Qualität

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| NR-01 | CI auf push/PR nach `main`: Test, Coverage, Docker-Import | erfüllt | `ci.yml`. Lauf `42499222986` auf `283ee4b` grün |
| NR-02 | Coverage-Gate mindestens 80 % | offen | pytest-Zeile erzwingt 68. `AGENTS.md` nennt 80 |
| NR-03 | Ruff und mypy blockieren die Pipeline | offen | `continue-on-error: true` |
| NR-04 | Jeder neue Pfad in collector, adapters, sap_sl, db, publish hat einen Test | teilweise | Agents und `AGENTS.md` fordern das. Dieser Abgleich hat die Abdeckung pro Modul nicht neu gemessen |
| NR-05 | DEV-Deploy bei Push auf `main`, mit Migration und Smoke, ohne SSH-Hop | erfüllt | `deploy-dev.yml`. Lauf `42499223057` auf `283ee4b` grün |
| NR-06 | Nächtliche Integration gegen DEV, Dry-Run erzwungen | teilweise | Workflow und 8 Tests existieren. Lauf `42469243262` (2026-11-08, SHA `6710fdc`) fehlgeschlagen |
| NR-07 | Alembic-Head ist die Kette `001`→`006` | erfüllt | `004` Q2P, `005` Analytics, `006` Diagnose |
| NR-08 | Wöchentlicher DORA-Bericht im Repo | offen | `dora.yml` vorhanden, `docs/dora-metrics.md` fehlt |
| NR-09 | `PROJECT_STATUS.md` trägt bei jeder Bearbeitung einen aktuellen Zeitstempel | erfüllt | diese drei Dokumente, 2026-11-08 19:40 (UTC+1) |
