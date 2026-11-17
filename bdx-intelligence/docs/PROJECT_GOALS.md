# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-14 08:36 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`cd6440f`, 2026-11-10). Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. Die Environments-API zeigt für `prod` keine Protection Rules. Branch Protection auf `main` antwortete mit HTTP 403, deshalb ist der Pflicht-Check aus `ci.yml` hier unbelegt. Ruff und mypy laufen in CI mit `continue-on-error`, das Coverage-Gate liegt bei 68 %.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der erste Punkt ist erfüllt, die Reviewer- und Protection-Punkte sind offen.

### G5 – SQL-Login `bdx_readonly`

- **Status:** in Arbeit
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Der Login `bdx_readonly` wurde angelegt. `DENY CONTROL` hat CONNECT blockiert (Fehler 18456, State 38). `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` verweigern CONTROL nicht mehr (Commit `7d0fb2f`). Ein neuer SQL-Probe in diesem Lauf fehlt.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server. Der Login ist angelegt; die dauerhafte Read-only-Verbindung des Collectors ist seit dem Fix nicht erneut geprüft.

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

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 für den SQL-Login im Container. Der Deploy-Workflow selbst läuft.
- **Stand:** `deploy-dev.yml` baut das Image und startet auf dem Self-hosted-Runner des DEV-Hosts Compose neu. Letzter grüner Lauf: 2026-11-10 07:22 (UTC+1) für `cd6440f`. Der Job bricht ab, wenn die Host-`.env` den Dry-Run-Schutz abschaltet, führt `migrate` aus und verlangt HTTP 200 von `GET /health/live`. Die Marker `.runtime/last-deploy-at` und `.runtime/last-deploy-sha` im Baum nennen noch 2026-11-07 21:50 und `6ccc036`.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, `SL_DRY_RUN` bleibt auf dem DEV-Host `true`, bis ein Operator es bewusst umstellt. Erfüllt für den Lauf vom 2026-11-10.

### G1 – SAP Read-only Collector

- **Status:** erledigt (Sprint 001, auf DEV in Betrieb)
- **Ziel:** Read-only-Verbindung zu SAP Business One, idempotente Änderungserkennung, REST und CLI.
- **Akzeptanz:** erfüllt. MSSQL-Kanal bleibt read-only.

### G2 – BDE, Maschinen, inkrementelles Lesen

- **Status:** erledigt (Sprint 002, auf DEV in Betrieb)
- **Ziel:** Inkrementeller SAP-Lesen, Maschinenzustand aus XMSK, BDE aus SCADA-Telemetrie.
- **Akzeptanz:** erfüllt. Statuscodes `P`/`R`/`L`/`C` bleiben wie gegen OWOR geprüft.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Der Container-Deploy ist G6 und erledigt. Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator `SL_DRY_RUN` in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
