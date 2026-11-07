# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-07 22:40 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Abgleich gegen `origin/main` `2f13c3f`. IDs bleiben stabil. Neue Ziele nur, wenn gelieferte Arbeit keinem bestehenden Ziel entspricht.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** teilweise
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `main`. Ruff und mypy sind in `ci.yml` nur beratend. Das Coverage-Gate ist 68 %, nicht 80 %. Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. Branch Protection war mit diesem Token nicht lesbar (HTTP 403). `pr-review.yml` ist beim Push von `2f13c3f` in 0 s ohne Jobs fehlgeschlagen.
- **Akzeptanz:** Sprint-004-Baum ist committet und auf `main` — erfüllt. Offen: nächtliche Integrations-Secrets, bestätigte Reviewer auf `prod`, Branch Protection mit dem Check aus `ci.yml`, Ruff/mypy wieder blockierend, Coverage-Ratchet.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. Die Publisher-Settings defaulten auf aus. Ein Broker ist im Baum nicht konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574, letzter manueller Check). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL.

## Erledigt

### G5 – SQL-Login `bdx_readonly`

- **Status:** erledigt für den DEV-Container (`12fa8cf`)
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `docs/sql/create_bdx_readonly.sql` verweigert CONTROL nicht mehr (`7d0fb2f`). Der Commit `12fa8cf` hält fest, dass der Login aus dem DEV-Container 871 offene Aufträge gelesen hat. Dieser Abgleich hat LDSAP nicht erneut geprüft.
- **Akzeptanz:** erfüllt für DEV. Kein Schreibrecht auf dem SAP-SQL-Server. Ein eigener Nachweis für die PROD-Company-DB fehlt.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt auf dem DEV-Host (`12fa8cf`, aufgezeichnet 2026-11-07 19:55 +0100, sha `1480f5c`)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5, erfüllt für den DEV-Container.
- **Stand:** `12fa8cf` hält fest, dass collector und api oben waren und der Event-Store verbunden war (38561 Aufträge, 184 Läufe). `.runtime/last-deploy-sha` ist weiterhin `1480f5c`. Seit `232b138` deployt Actions direkt auf dem Self-hosted-Runner. Lauf `42415113477` für `2f13c3f` ist `success` und prüft `/health/live`. Der Host wurde hier nicht erneut inspiziert.
- **Akzeptanz:** erfüllt für den aufgezeichneten `deploy.ps1`-Lauf und für den späteren Actions-Lauf. Das Skript bricht ab, wenn der DEV-Host den Service-Layer-Guard nicht auf dem sicheren Default hält.

### G1 – SAP Read-only Collector

- **Status:** erledigt (Sprint 001, auf DEV in Betrieb)
- **Ziel:** Read-only-Verbindung zu SAP Business One, idempotente Änderungserkennung, REST und CLI.
- **Akzeptanz:** erfüllt. MSSQL-Kanal bleibt read-only.

### G2 – BDE, Maschinen, inkrementelles Lesen

- **Status:** erledigt (Sprint 002, auf DEV in Betrieb)
- **Ziel:** Inkrementeller SAP-Lesen, Maschinenzustand aus XMSK, BDE aus SCADA-Telemetrie.
- **Akzeptanz:** erfüllt. Statuscodes `P`/`R`/`L`/`C` bleiben wie gegen OWOR geprüft.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Broker ist G7, der DEV-Container ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Stand:** Code liegt auf `main` (`sap_sl/operations.py`, Migration 003). Das letzte DEV-Protokoll zeigt blockierte Aufrufe mit Audit in `sl_operations`. `ServiceLayerSettings.dry_run` defaultet im Code auf aus, und `.env.example` lässt Dry-Run ebenfalls aus. Das widerspricht der Akzeptanz unten. Dieser Abgleich ändert den Code nicht und schreibt die Ausschalt-Zuweisung nicht erneut ins Repository.
- **Akzeptanz:** Code und die protokollierte Dry-Run-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Guard in der nicht versionierten Host-Umgebung umstellt. Committete Dateien sollen den Guard nicht abschalten; der Default und die Beispieldatei tun das derzeit doch.

### G10 – Schwachstellen-Analyse

- **Status:** erledigt (PR #6, `2f13c3f`, auf `main`)
- **Ziel:** Prozessschwächen aus dem Event-Store in einem Dashboard zeigen.
- **Stand:** `GET /api/v1/analytics/weaknesses` und `GET /analytics`. Neun Tests in `tests/test_analytics.py`. CI und DEV-Deploy für diesen Commit sind grün.
- **Abgrenzung:** Die KPI-Engine, Anomalien und Migration `004` sind PR #5 und nicht auf `main`. Dafür gibt es noch kein Ziel, solange keine Zeile in `REQUIREMENTS.md` steht.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
