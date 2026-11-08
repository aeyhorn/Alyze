# BDX Intelligence – Project Goals

> **Zuletzt aktualisiert:** 2026-11-08 04:35 (UTC+1)
> Stand: `main` = `6850feb`. Detail und Nachweise: `PROJECT_STATUS.md`. Anforderungen: `REQUIREMENTS.md`.

Ziele beschreiben das Ergebnis. Der Status wird hier in place nachgezogen. Neue Ziele bekommen die nächste freie ID und werden nicht umnummeriert.

| ID | Ziel | Status auf `main` |
|---|---|---|
| G1 | SAP-Fertigungsaufträge nur lesend, idempotent und als Domain-Events im PostgreSQL-Event-Store, dazu REST und CLI | ✅ Sprint 001, auf `main` |
| G2 | Inkrementelles Lesen, Maschinenzustand (Mazak XMSK) und daraus abgeleitete BDE-Sätze | ✅ Sprint 002, auf `main` |
| G3 | Events optional per MQTT/Kafka veröffentlichen, Betriebsdashboard, SAP-Write-back über die Service Layer mit Dry-Run und Audit | ✅ Sprint 003, auf `main`. Broker ist nicht konfiguriert. Echte Writes sind keine committete Einstellung |
| G4 | CI, nächtliche Integrationstests, DEV-Deploy, freigabepflichtiges PROD-Deploy, Quality-Gate-Agents, HOTL-Prompts | ✅ Code auf `main`. CI von `6850feb` grün. Ruff und mypy bleiben advisory, Coverage-Gate 68 %. DEV-Deploy dieses SHA war zum Abgleich noch in der Queue. `integration.yml` und `dora.yml` haben noch keinen Actions-Lauf |
| G5 | Schwachstellen aus dem Event-Store sichtbar machen (überfällige und festgefahrene Aufträge, Plankorrekturen, stehende Maschinen, Collector-Fehler) | ✅ auf `main` (#6, Darstellung #12). Feste Schwellen im Code, keine Selbstjustierung |
| G6 | Dieselbe Pipeline als Container auf dem DEV-Host, mit read-only SQL-Login statt Windows-Auth | 🟡 Workflow und SQL-Skripte auf `main`. Letztes erfolgreiches DEV-Deploy: `2f13c3f`. Ob `bdx_readonly` auf LDSAP existiert, wurde hier nicht geprüft |
| G7 | Collector gegen PROD lesen, ohne DEV- und PROD-Zeilen im selben `order_state` zu mischen | ⬜ offen. Nur Einzelauftrags-Probes (2026-11-07) |
| G8 | MQTT- oder Kafka-Broker im Betrieb | ⬜ offen. Publisher sind gebaut |
| G9 | SAP-Write-back im echten Betrieb (Release, Close, Cancel, Rückmeldung) | ⬜ offen. Dry-Run bleibt der committete und der DEV-Deploy-Zustand; Audit über `sl_operations` |
| G10 | Mehrere SAP-Firmen und SSO/SCIM | ⬜ offen |
| G11 | KPI-Engine mit Anomalie-Erkennung und selbstjustierenden Schwellen | ⬜ nicht auf `main`. Offener PR #5 |

## Was dieser Abgleich geändert hat

Der vorherige Statustext führte Sprint 004 noch als uncommitted und `main` als einen Commit vor `origin/main`. Beides stimmt nicht mehr: `origin/main` ist `6850feb`, Sprint 004 liegt dort, und G5 ist seit #6/#12 geliefert. G11 bleibt bewusst offen, solange PR #5 nicht auf `main` ist.
