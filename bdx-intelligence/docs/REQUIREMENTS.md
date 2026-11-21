# BDX Intelligence – Anforderungen

Eingang für neue Anforderungen. Desktop und Cloud (einschließlich mobiler Cloud Agents) hängen Zeilen nur an. Bestehende Zeilen bleiben stehen; geliefert wird über die Spalte `Status`.

Offene Punkte, die schon in `docs/PROJECT_GOALS.md` stehen, werden hier nicht wiederholt.

| ID | Quelle | Aufgenommen | Ziel | Status | Text |
|---|---|---|---|---|---|
| R001 | cloud | 2026-11-21 | G8 | done | Diagnose und `/health` prüfen PROD-Trennung (`POSTGRES_DSN_PROD` bei `SAP_MODE=prod`) und melden die Alembic-Revision. |
| R002 | cloud | 2026-11-21 | G7 | done | Publisher lokal prüfbar machen (`RecordingPublisher`, Kafka/MQTT-Exports, Diagnose über `build_all_publishers`); echter Broker bleibt Host-Arbeit. |
| R003 | cloud | 2026-11-21 | G10 | done | Quoter Deep-Link mit `QUOTER_UI_URL`/`return_url` in Promise-API und Promise-UI (Im Quoter klären / Return→Recompute). |
| R004 | cloud | 2026-11-21 | G4 | done | Analytics nutzbarer machen: zeitstabiler Kalender-Test und CLI `seed-shift-calendar` für geplante Schichten. |
| R005 | cloud | 2026-11-21 | G6 | open | Auf dem DEV-Host Alembic auf head (`008`), `grant_q2p_readonly.sql` und `QUOTER_ENABLED=true` bestätigen. |

Quellen: `desktop` oder `cloud`. Status: `open`, `in-progress`, `done`.

Nächste freie ID: `R006`.
