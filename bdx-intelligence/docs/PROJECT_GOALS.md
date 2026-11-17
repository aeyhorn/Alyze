# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-14 10:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Abgleich 2026-11-14 gegen `origin/main` (`cd6440f`). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`cd6440f`, 2026-11-10). Der Pytest-Gate in `ci.yml` ist 68 %. Ruff und mypy laufen mit `continue-on-error`. Jeder nächtliche Lauf von 2026-11-08 bis 2026-11-13 ist rot. Der letzte, Run 43410708723, scheitert in `Install ODBC Driver 18` (`curl: Failed writing body`, Exit 2); pytest startet nicht. Bis 2026-11-14 10:34 CET gab es keinen neueren Lauf. Environment `prod` hat keine Protection Rules. Repo-Rulesets sind leer. Classic Branch Protection und die Secret-Namen waren mit diesem Token nicht lesbar (HTTP 403).
- **Akzeptanz:** Der Sprint-004-Baum ist auf `main`. Offen bleiben erforderliche Reviewer auf `prod`, ein erzwungener CI-Check auf `main` und ein grüner nächtlicher Integrationslauf.

### G5 – SQL-Login `bdx_readonly`

- **Status:** in Arbeit
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` liegen auf `main` (`7d0fb2f`). Der Commit beschreibt einen fehlgeschlagenen CONNECT (18456, state 38), weil `DENY CONTROL` den Login blockierte. Ob der Login danach auf LDSAP entsperrt wurde, ist in diesem Lauf nicht geprüft. Die Shop-Floor-Notiz vom 2026-11-07 nennt den Login noch als fehlend.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

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

- **Status:** erledigt als Code (Sprint 003). Der Container-Deploy ist G6 (erledigt). Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator das Dry-Run in der echten `.env` bewusst ausschaltet. Committete Dateien schalten es nicht aus.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `Deploy to DEV` war am 2026-11-10 für `cd6440f` grün (Run 42768023481): Image nach ghcr.io, Compose auf dem Self-Hosted-Runner, Migration, `collector` und `api` neu erstellt, `/health/live` grün. Die Marker `.runtime/last-deploy-*` im Baum stehen noch auf 2026-11-07 / `6ccc036`.
- **Akzeptanz:** erfüllt für den DEV-Compose-Stack. Der Workflow bricht ab, wenn die Host-`.env` Dry-Run ausschaltet.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
