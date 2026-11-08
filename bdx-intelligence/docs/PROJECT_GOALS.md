# BDX Intelligence – Project Goals

> **Zuletzt aktualisiert:** 2026-11-08 19:40 (UTC+1)
> Abgleich mit `main` @ `283ee4b`. Stand der Lieferung: [`PROJECT_STATUS.md`](PROJECT_STATUS.md). Prüfbare Anforderungen: [`REQUIREMENTS.md`](REQUIREMENTS.md).

BDX-Intelligence verbindet SAP Business One und den Shop-Floor mit einem lokalen PostgreSQL-Event-Store und macht den Stand über REST, Dashboard und CLI sichtbar. Schreiben nach SAP bleibt ein gesonderter, auditierter Kanal.

## Geliefert (Code auf `main`)

| Ziel | Beleg |
|---|---|
| Fertigungsaufträge read-only, idempotent und inkrementell aus SAP lesen und als Domain-Events halten | Sprints 001–002, PR #1, Migrationen `001`–`002` |
| Maschinenzustand der Mazak-XMSK-Quelle lesen und an SAP-`DocNum` hängen, wo die Order numerisch ist | Sprint 002, `XmskMachineAdapter` |
| BDE-Sätze aus SCADA-Telemetrie ableiten | Sprint 002, `ScadaTelemetryBDEAdapter` |
| Ereignisse optional per MQTT oder Kafka veröffentlichen, ohne den Collector zu stoppen, wenn der Broker fehlt | Sprint 003. Defaults aus |
| Shop-Floor über `/dashboard`, REST und `bdx-collect` bedienen | Sprints 002–003 |
| SAP-Schreibvorgänge (release, close, cancel, report-production) nur über den Service Layer und mit Audit in `sl_operations` | Sprint 003, Migration `003` |
| Qualität und Auslieferung automatisieren: CI, DEV-Deploy, Prod-Workflow mit Freigabe, Doku-/Test-Agents | Sprint 004, Workflows auf `main`. CI und DEV-Deploy für `283ee4b` grün |
| Eine Kundenanfrage parallel über Artikel, Material, Stückliste, Kapazität und Preis bewerten und Lücken als `open_questions` zeigen | Q2P #33, Migration `004`, UI `/q2p` |
| Kennzahlen, Anomalien mit Selbstheilung, nachjustierte Schwellen und eine Diagnoseschicht (Fluss, Verspätungsursache, Engpass, Messgüte) rechnen | Sprint 005 #5, Migrationen `005`–`006` |
| Prozessschwächen (überfällig, festgefahren, Plänänderung, Leerlauf, Ausfall, Collector-Fehler) in einer Seite zeigen | #6 und #12, UI `/analytics` |

## Teilweise

| Ziel | Was fehlt |
|---|---|
| DEV dauerhaft aus `main` betreiben | Deploy-Job für HEAD ist grün und migriert. Der letzte Hands-on-Probe (2026-11-07) sah Schema `002`. Nächtliche Integration auf `6710fdc` ist rot. Q2P-Grants und das SQL-Login `bdx_readonly` sind Skripte, keine belegte Ausführung |
| Schreiben nach SAP im Alltag blockiert lassen | Der DEV-Deploy bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet. Im Git defaultet `ServiceLayerSettings.dry_run` auf aus, und `.env.example` lässt Schreiben zu. `AGENTS.md` verlangt das Gegenteil für committete Beispiele |
| Qualitätsziele aus dem Agent-Guide | Coverage-Gate ist 68 %, nicht 80 %. Ruff und mypy sind advisory. PR-Review- und Lint-Cleanup-Läufe vom 2026-11-08 sind rot |
| KPI-Arbeit im UI | Die API liefert Zeitreihen, Anomalien, Schwellen und Diagnose. Die Seite `/analytics` zeigt nur das Schwachstellen-Aggregat |
| Broker-Betrieb | Publisher sind gebaut. Ein Broker ist kein Bestandteil der Default-Konfiguration |
| DORA-Bericht | Workflow `dora.yml` ist da. `docs/dora-metrics.md` liegt nicht auf `main` |

## Offen

| Ziel | Stand |
|---|---|
| Mehrere SAP-Buchungskreise | kein Code (TBD) |
| SSO / SCIM | kein Code (TBD) |
| Personal- und Qualifikationsfeed für Q2P | bewusst offen, Domain `personnel` ist `UNKNOWN` |
| Collector gegen PROD mit getrenntem Event-Store | nur Einzelauftrags-Probes, Stand 2026-11-07 |
| Sync-Koordinator als Repo-Skill | `.cursor/skills/dev-sync/SKILL.md` und `.cursor/prompts/sync-coordinator.mdc` fehlen |

## Nicht das Ziel

- Kein Schreiben auf dem MSSQL-Kanal. Der SQLAlchemy-Guard bleibt.
- Keine Maschinensteuerung. XMSK und BDE sind lesend.
- Keine Secrets im Git.
- Prod-Deploy bleibt manuell freigegeben.
