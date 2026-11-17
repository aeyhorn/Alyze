# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-09 21:38 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Analytics, Q2P, Promise und Vorgangsleitstand liegen auf `origin/main` und haben keine eigene `G#`, weil `REQUIREMENTS.md` dafür keine Zeile hat.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand laut PROJECT_STATUS:** Der Baum (Workflows, Agents, Skripte, Integrationstests, Prompts) liegt auf `origin/main` (`90a6593`, unverändert seit 15:49 UTC+1). CI `42638402851` (pytest, Coverage-Untergrenze 68; Ruff und mypy advisory) und Deploy to DEV `42638402840` sind für diesen Commit grün. DEV-Deploy läuft auf dem Self-hosted-Runner des DEV-Hosts, ohne SSH. Der nächtliche Integrationslauf `42605350114` (Commit `184a6bd`) ist vor pytest gescheitert: `gpg` konnte beim Installieren von ODBC Driver 18 kein TTY öffnen. Zwei Push-Läufe von `pr-review.yml` für `90a6593` (`42638400656`, `42638911861`) endeten ohne Jobs als Fehler; der Workflow startet nur bei `pull_request`. DORA-Lauf `42638115770` (Schedule, Basis `bbdfc8f`) ist grün und hat `465b1fb` auf `main` committet. Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. `prod` hat keine Protection Rules. Actions-Secrets und Branch Protection waren per API nicht lesbar (403).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. Secrets, Reviewer auf `prod` und der erzwungene CI-Check auf `main` sind noch offen. Der Baum ist erfüllt.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` liegt auf `origin/main`. Es erlaubt nur SELECT und verweigert INSERT, UPDATE, DELETE und ALTER, ohne CONTROL zu verbieten. Ob der Login auf LDSAP existiert, ist seit der DEV-Prüfung vom 2026-11-07 nicht erneut geprüft; damals fehlte er.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 für den SQL-Login im Linux-Container. Der Deploy-Workflow selbst hängt nicht an diesem Login.
- **Stand:** Deploy to DEV `42638402840` für `90a6593` ist grün: Image pull, Migration, Neustart von `collector` und `api`, `/health/live` antwortet. Die Probe prüft nur, dass der Prozess läuft. `bdx-collect diagnose` bricht den Job nicht ab. Ob SAP aus dem Container erreichbar ist und ob `bdx_readonly` existiert, ist seit 2026-11-07 nicht erneut geprüft.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, und der Dry-Run-Guard bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst umstellt. Liveness ist erfüllt. SAP aus dem Container und der SQL-Login bleiben offen.

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
