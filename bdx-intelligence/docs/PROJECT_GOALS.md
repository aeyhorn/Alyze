# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-10 02:37 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand laut PROJECT_STATUS:** Der Sprint-004-Baum liegt auf `origin/main` (`90a6593`). CI für diesen Commit ist grün (Run `42638402851`). Ruff und mypy sind noch advisory, das Coverage-Gate steht auf 68. Die nächtliche Integration ist am 2026-11-08 und 2026-11-09 rot, bevor pytest startet (`gpg` öffnet `/dev/tty` nicht; Runs `42469243262`, `42605350114`). `pr-review.yml` hat auf dem Push von `90a6593` zwei Läufe ohne Jobs mit Ergebnis failure (`42638400656`, `42638911861`). Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. `prod` zeigt über die lesbare API keine Protection-Rules. Branch Protection auf `main` war mit diesem Token nicht lesbar (403). Der Dry-Run-Guard auf dem DEV-Host hat den Deploy von `90a6593` durchgelassen. `chore/ruff-cleanup-20261108` ist nicht gemergt und hat keinen PR.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum-Teil ist erfüllt. Secrets, Reviewer und Branch Protection sind nicht bestätigt.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` liegt im Repo. Die Prüfung vom 2026-11-07 fand den Login auf LDSAP nicht. Dieser Abgleich hat LDSAP nicht erneut geprüft; in Git ist die Anlage nicht nachgewiesen.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 für den SQL-Login. Der Deploy-Workflow auf `main` läuft unabhängig davon auf dem Self-hosted-Runner des DEV-Hosts.
- **Stand:** Deploy-to-DEV für `origin/main` `90a6593` war erfolgreich (Actions-Run `42638402840`, 2026-11-09 15:52 CET), inklusive Smoke auf `/health/live`. Ob der SQL-Login existiert, steht nicht im Repo.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, der Dry-Run-Schutz bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst umstellt. Der letzte grüne Deploy spricht für den Stack zum Zeitpunkt des Laufs. Der Host-Schutz ist nur darüber belegt, dass der Workflow nicht abgebrochen ist.

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
