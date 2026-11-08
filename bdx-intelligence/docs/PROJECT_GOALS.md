# BDX Intelligence – Project Goals

> **Zuletzt abgeglichen:** 2026-11-08 08:37 (UTC+1)
> Stand: `main` = `6850feb`. Detail und Nachweise: `PROJECT_STATUS.md`. Anforderungen: `REQUIREMENTS.md`.

Ziele beschreiben das Ergebnis. Der Status wird hier in place nachgezogen. Neue Ziele bekommen die nächste freie ID und werden nicht umnummeriert.

| ID | Ziel | Status auf `main` |
|---|---|---|
| G1 | SAP-Fertigungsaufträge nur lesend, idempotent und als Domain-Events im PostgreSQL-Event-Store, dazu REST und CLI | ✅ Sprint 001, auf `main` |
| G2 | Inkrementelles Lesen, Maschinenzustand (Mazak XMSK) und daraus abgeleitete BDE-Sätze | ✅ Sprint 002, auf `main` |
| G3 | Events optional per MQTT/Kafka veröffentlichen, Betriebsdashboard, SAP-Write-back über die Service Layer mit Dry-Run und Audit | ✅ Sprint 003, auf `main`. Broker ist nicht konfiguriert. Echte Writes sind keine committete Einstellung |
| G4 | CI, nächtliche Integrationstests, DEV-Deploy, freigabepflichtiges PROD-Deploy, Quality-Gate-Agents, HOTL-Prompts | ✅ Code auf `main`. CI von `6850feb` grün. Ruff und mypy bleiben advisory, Coverage-Gate 68 %. DEV-Deploy dieses SHA (run 42420693125) ist seit 2026-11-07 23:36 (UTC+1) in der Queue; der Self-hosted-Job hatte um 08:37 (~9 h) nicht gestartet. Letztes erfolgreiches Deploy bleibt `2f13c3f`. `integration.yml`, `dora.yml` und `lint-cleanup.yml` haben noch keinen Actions-Lauf |
| G5 | Schwachstellen aus dem Event-Store sichtbar machen (überfällige und festgefahrene Aufträge, Plankorrekturen, stehende Maschinen, Collector-Fehler) | ✅ auf `main` (#6, Darstellung #12). Feste Schwellen im Code, keine Selbstjustierung |
| G6 | Dieselbe Pipeline als Container auf dem DEV-Host, mit read-only SQL-Login statt Windows-Auth | 🟡 Workflow und SQL-Skripte auf `main`. Letztes erfolgreiches DEV-Deploy: `2f13c3f`. Ob `bdx_readonly` auf LDSAP existiert, wurde hier nicht geprüft |
| G7 | Collector gegen PROD lesen, ohne DEV- und PROD-Zeilen im selben `order_state` zu mischen | ⬜ offen. Nur Einzelauftrags-Probes (2026-11-07) |
| G8 | MQTT- oder Kafka-Broker im Betrieb | ⬜ offen. Publisher sind gebaut |
| G9 | SAP-Write-back im echten Betrieb (Release, Close, Cancel, Rückmeldung) | ⬜ offen. Dry-Run bleibt der committete und der DEV-Deploy-Zustand; Audit über `sl_operations` |
| G10 | Mehrere SAP-Firmen und SSO/SCIM | ⬜ offen |
| G11 | KPI-Engine mit Anomalie-Erkennung und selbstjustierenden Schwellen | ⬜ nicht auf `main`. Offener PR #5, konfliktiert mit `main` |

## Was dieser Abgleich geändert hat

`origin/main` ist weiter `6850feb`. Seit dem Abgleich um 07:35 (UTC+1) ist kein Commit auf `main` dazugekommen. Sprint 004 und G5 liegen dort; `PROJECT_STATUS.md` auf `main` beschrieb Sprint 004 noch als uncommitted. G11 bleibt offen: PR #5 ist nicht gemergt und konfliktiert mit `main`. Der DEV-Deploy von `6850feb` hat das Image gebaut; der Self-hosted-Job ist seit 2026-11-07 23:36 (UTC+1) in der Queue und war um 08:37 noch nicht gestartet (etwa 9 Stunden, `updatedAt` weiter 2026-11-07T22:36:22Z). Letztes erfolgreiches DEV-Deploy bleibt `2f13c3f`. `integration.yml`, `dora.yml` und `lint-cleanup.yml` haben weiterhin keinen Actions-Lauf. Draft-Doku-PRs #4, #7–#11 und #13–#22 sind offen und nicht die Basis. `PROJECT_GOALS.md` und `REQUIREMENTS.md` fehlen auf `main` und werden hier mitgeführt.
