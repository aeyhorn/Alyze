# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-13 08:38 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand laut PROJECT_STATUS:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`cd6440f`). Coverage-Gate ist 68 %. Ruff und mypy sind in CI noch advisory. Secrets und Branch Protection waren in diesem Lauf nicht lesbar (API 403).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Zuletzt dokumentiert: der Login existiert auf LDSAP noch nicht. Dieser Lauf hat LDSAP nicht geprüft.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 für einen Container ohne Windows-Integrated-Auth. Der aktuelle DEV-Deploy läuft mit der Host-Umgebung.
- **Stand:** `deploy-dev.yml` baut das Image, spielt es auf dem Self-Hosted-Runner des DEV-Hosts aus und prüft `/health/live`. GitHub Actions meldet Erfolg auf `main` bis 2026-11-10 06:22 UTC (`cd6440f`). Der im Repo gespeicherte Stempel `.runtime/last-deploy-at` ist 2026-11-07 21:50 +01:00 (`6ccc036`). Dieser Lauf hat den Host nicht selbst abgefragt.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, der Service-Layer-Trockenlauf bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst ausstellt.

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
- **Akzeptanz:** Code und die Trockenlauf-Prüfung auf DEV sind da. Echte Service-Layer-Schreibvorgänge bleiben aus, bis ein Operator den Trockenlauf in der Host-Umgebung ausstellt. `.env.example` stellt den Trockenlauf derzeit aus; das widerspricht der Sicherheitsregel und bleibt offen.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
