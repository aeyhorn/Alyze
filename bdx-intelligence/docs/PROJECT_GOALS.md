# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-16 15:28 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`a66b194`). Die Push-CI für `cd6440f` ist grün (Run 42768023614, 2026-11-10), ebenso der DEV-Deploy (Run 42768023481). Ruff und mypy sind in `ci.yml` advisory, das Coverage-Gate steht auf 68 %. Der DORA-Wochenlauf 43885095274 ist am 2026-11-16 14:22 UTC grün und hat den Snapshot `a66b194` committet. Der nächtliche Integrationstest scheitert in „Install ODBC Driver 18“ (Run 43851477564, 2026-11-16 10:44 UTC); pytest startet nicht. `main` meldet `protected: false`, die Ruleset-Liste ist leer. Die Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules. Branch-Protection-Endpunkt und Secret-Liste antworten mit HTTP 403.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum auf `main` ist erfüllt. Secrets, Reviewer und der Pflichtcheck bleiben in diesem Lauf offen.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` liegen auf `main`. Commit `7d0fb2f` (2026-11-07) hält fest, dass `DENY CONTROL` den Login `bdx_readonly` am CONNECT gehindert hat. Dieser Lauf hat LDSAP nicht verbunden, deshalb ist nicht belegt, dass der Login heute funktioniert.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 bleibt offen für den Betrieb ohne Windows-Integrated-Auth. Der DEV-Deploy-Workflow ist davon unabhängig gelaufen.
- **Stand:** `deploy-dev.yml` war am 2026-11-10 für `cd6440f` grün (Run 42768023481: Build, Deploy auf den Host, Smoke-Test). Der Marker `.runtime/last-deploy-sha` zeigt noch `6ccc036` (2026-11-07 21:50 +01:00). Ein frischer Shopfloor-Probe fehlt in diesem Lauf. Die Host-`.env` wurde nicht gelesen.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, der Dry-Run-Guard bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst öffnet. Der Deploy-Job vom 2026-11-10 ist durchgelaufen. Der Host wurde in diesem Lauf nicht erneut geprüft, deshalb bleibt G6 in Arbeit.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. `SL_DRY_RUN` bleibt unberührt.

## Erledigt

### G1 – SAP Read-only Collector

- **Status:** erledigt (Sprint 001, auf DEV in Betrieb)
- **Ziel:** Read-only-Verbindung zu SAP Business One, idempotente Änderungserkennung, REST und CLI.
- **Akzeptanz:** erfüllt. MSSQL-Kanal bleibt read-only.

### G2 – BDE, Maschinen, inkrementelles Lesen

- **Status:** erledigt (Sprint 002, auf DEV in Betrieb)
- **Ziel:** Inkrementeller SAP-Lesen, Maschinenzustand aus XMSK, BDE aus SCADA-Telemetrie.
- **Akzeptanz:** erfüllt. Statuscodes `P`/`R`/`L`/`C` bleiben wie gegen OWOR geprüft.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Broker und Deploy sind G6 und G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run-Guard in der Host-`.env` öffnet. `.env.example` im Repo schaltet diesen Guard aus; das bleibt ein Verstoß gegen die Regel, committete Dateien lassen den Guard an.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
