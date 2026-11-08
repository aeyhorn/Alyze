# BDX Intelligence – Anforderungen

> **Zuletzt abgeglichen:** 2026-11-08 20:37 (CET)
>
> Append-only. Zeilen nicht löschen und nicht umsortieren. Nächste freie ID: **R022**.
>
> Neue Zeile vor der Umsetzung: `ID`, `Quelle` (`desktop` oder `cloud`), `Aufgenommen` (`YYYY-MM-DD`), `Ziel` (`G#` oder leer), `Status` (`open`), `Text` (ein Satz). Bei Lieferung nur `Status` auf `in-progress` oder `done` setzen.
>
> Die Zeilen R001–R021 sind ein Rückstand aus `origin/main` `283ee4b`, nicht aus einer Sitzung diktiert. Ihre Quelle ist `git`.

| ID | Quelle | Aufgenommen | Ziel | Status | Text |
|---|---|---|---|---|---|
| R001 | git | 2026-11-07 | G1 | done | SAP Business One lesend (OWOR/OITM), parametrisierte Queries, Read-only-Guard, Event-Store und REST/CLI. |
| R002 | git | 2026-11-07 | G2 | done | Inkrementelles Lesen, `order_state` pro Auftrag, History nur bei Änderung, Schließungen über DocEntry nachlesen. |
| R003 | git | 2026-11-07 | G2 | done | Mazak-XMSK-Maschinenzustand und aus SCADA-Telemetrie abgeleitete BDE-Sätze. |
| R004 | git | 2026-11-07 | G3 | done | Domain-Events über MQTT- und Kafka-Publisher schicken können, ohne den Collector bei Publisher-Fehlern zu stoppen. |
| R005 | git | 2026-11-07 | G3 | done | Dashboard unter `/dashboard` für Aufträge, Maschinen, Events, Läufe und BDE. |
| R006 | git | 2026-11-07 | G3 | done | Service-Layer release/close/cancel/report-production mit Audit in `sl_operations` und Dry-Run-Guard; der Schreibschalter bleibt auf dem Host. |
| R007 | git | 2026-11-07 | G4 | done | CI auf Push und PR nach `main` (Tests blockierend, ruff und mypy vorerst advisory). |
| R008 | git | 2026-11-07 | G7 | done | DEV-Deploy auf dem self-hosted Runner: Image nach ghcr.io, `migrate`, Collector und API neu, `/health/live`. |
| R009 | git | 2026-11-07 | G9 | done | Prod-Deploy nur per `workflow_dispatch` mit Freigabe und getrenntem Migrations-Opt-in. |
| R010 | git | 2026-11-07 | G4 | done | Quality-Gate-Agents und `bdx-collect check` ohne SAP und ohne Datenbank. |
| R011 | git | 2026-11-08 | G5 | done | Quote-to-Promise: eine Anfrage, parallele Domänen item/material/BOM/capacity/pricing, UI `/q2p`, Migration `004`. |
| R012 | git | 2026-11-08 | G6 | done | KPI-Engine, Anomalie-Erkennung und selbst justierende Schwellen im Collector-Takt, Migration `005`. |
| R013 | git | 2026-11-07 | G6 | done | Schwachstellen-Dashboard unter `/analytics` inklusive `/api/v1/analytics/weaknesses`. |
| R014 | git | 2026-11-08 | G6 | done | Diagnose: Messgüte, Durchlaufsegmente, eine Verspätungsursache pro Auftrag, Engpass-Rang, Migration `006`. |
| R015 | git | 2026-11-07 | G7 | open | SQL-Login `bdx_readonly` und die Q2P-SELECT-Grants auf LDSAP anlegen (Skripte liegen unter `docs/sql/`). |
| R016 | git | 2026-11-07 | G8 | open | Einen MQTT- oder Kafka-Broker an die vorhandenen Publisher anbinden. |
| R017 | git | 2026-11-07 | G9 | open | Den Collector lesend gegen PROD laufen lassen, mit einem von DEV getrennten Event-Store. |
| R018 | git | 2026-11-08 | G11 | open | Einen Schicht- oder Qualifikations-Feed an die Q2P-Personal-Domäne anbinden. |
| R019 | git | 2026-11-07 | G10 | open | Mehrere SAP-Firmenmandanten und SSO/SCIM unterstützen. |
| R020 | git | 2026-11-07 | G4 | open | Coverage-Gate von 68 % in Richtung 80 % anheben und ruff sowie mypy blockierend schalten. |
| R021 | git | 2026-11-08 | G4 | open | Den nächtlichen Integration-Lauf gegen DEV wieder grün bekommen (letzter Lauf 2026-11-08, exit 2). |
