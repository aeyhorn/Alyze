# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-09 15:37 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Q2P (#33, #39), Analytics/Schwachstellen (#5, #6, #12), Promise (#41) und die Header-Navigation (#62) sind auf `main` und im Status beschrieben. Dafür gibt es keine Zeile in `REQUIREMENTS.md`, deshalb keine neue Ziel-ID. PR #67 (Vorgangsleitstand) ist offen und nicht Teil von `main`.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`bbdfc8f`), nicht uncommitted. Ruff und mypy sind in `ci.yml` beratend. Das Coverage-Gate der CI ist 68; `bdx-collect check` prüft weiter gegen 80. `deploy-dev.yml` läuft auf dem Self-hosted-Runner des DEV-Hosts, ohne SSH-Hop, und bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet. Aus Git nicht belegbar und deshalb offen: Reviewer auf `prod`, Branch Protection für `ci.yml`, Integrations-Secrets, optionales `CURSOR_API_KEY`.
- **Akzeptanz:** Sprint-004-Baum ist auf `main`. Offen bleibt, dass `CURSOR_API_KEY`, die nächtlichen Integrations-Secrets und der Self-hosted-Runner gesetzt sind, `prod` erforderliche Reviewer hat und `main` den Check aus `ci.yml` verlangt.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Beim DEV-Check am 2026-11-07 existierte der Login auf LDSAP noch nicht. Ein neuerer Nachweis liegt im Git nicht.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** offen
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres lief dort beim Check am 2026-11-07 bereits.
- **Stand:** `deploy-dev.yml` ist auf `main` und zielt auf diesen Host. Ob der Stack läuft und ob die Alembic-Revisionen `003`–`008` dort angewendet sind, steht nicht im Git.
- **Abhängigkeit:** G5 für den SAP-Zugriff aus dem Container.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, Dry-Run bleibt auf dem DEV-Host an, bis ein Operator es bewusst umstellt.

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
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator `SL_DRY_RUN` in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
