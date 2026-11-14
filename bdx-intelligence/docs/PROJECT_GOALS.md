# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-14 07:35 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich folgt `origin/main` = `cd6440f`.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main`. Der Arbeitsbaum ist sauber. Ruff und mypy sind in CI nur beratend. Das Coverage-Gate in CI liegt bei 68 %, der lokale Check-Agent weiter bei 80 %. Das Environment `prod` hat keine Protection Rules. Branch Protection auf `main` war in diesem Lauf nicht lesbar (API 403). Die nächtliche Integration scheitert seit 2026-11-09 im Schritt „Install ODBC Driver 18“, bevor pytest startet. Der jüngste aufgezeichnete Lauf ist 2026-11-13 10:39 UTC; um 06:33 UTC lag noch kein Lauf vom 2026-11-14 vor.
- **Akzeptanz:** Der Sprint-004-Baum ist committet und gemergt. Offen bleiben erforderliche Reviewer auf `prod` und ein bestätigter Pflicht-Check aus `ci.yml` auf `main`.

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

- **Status:** erledigt als Code (Sprint 003). Deploy ist G6. Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator das auf dem Host bewusst umstellt. Committete Dateien schalten Schreibvorgänge nicht frei.

### G5 – SQL-Login `bdx_readonly`

- **Status:** erledigt
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `7d0fb2f` hat `DENY CONTROL` aus dem Skript genommen, nachdem der Login die Datenbank nicht öffnen konnte. `docs/sql/reset_bdx_readonly.sql` liegt im Repo. Spätere Container-Deploys waren grün, einschließlich des Health-Checks auf `/health/live`.
- **Akzeptanz:** erfüllt, soweit der erfolgreiche DEV-Deploy das zeigt. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5.
- **Stand:** `deploy-dev` für den aktuellen `main`-Stand `cd6440f` war am 2026-11-10 07:22 CET grün (Image-Build, Deploy, Smoke auf `/health/live`). Der Workflow bricht ab, wenn die Host-Umgebung echte Schreibvorgänge zulässt. Der committete Stempel `.runtime/last-deploy-sha` steht noch auf `6ccc036` (2026-11-07 21:50 +01:00).
- **Akzeptanz:** erfüllt für den letzten grünen Lauf. Der Compose-Kopfkommentar „NOT yet deployed“ hinkt hinterher.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
