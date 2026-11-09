# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-10 00:35 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Der erste Import der Ziele stammt aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1).

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`90a6593`). Ruff und mypy sind in `ci.yml` noch advisory. Das Coverage-Gate steht auf 68 %. Die nächtliche Integration ist am 2026-11-08 und 2026-11-09 beim ODBC-Treiber-Install rot, bevor pytest läuft. Umgebungen `dev`, `prod` und `CURSOR_API_KEY` existieren. `prod` hat keine Protection Rules. Branch Protection auf `main` war mit diesem Token nicht lesbar (HTTP 403). DEV-Deploy läuft ohne SSH über den self-hosted Runner und war am 2026-11-09 15:52 (UTC+1) grün.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. Offen: nächtliche Integration grün, ruff/mypy blockierend, Coverage-Ratchet, erforderliche Reviewer auf `prod`, bestätigte Branch Protection für `ci.yml`.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Der Login hat `DEV_SBO_LEISINGER` bereits angesprochen (Fehler 18456 state 38, solange `DENY CONTROL` im Skript stand). `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` liegen auf `main` (`7d0fb2f`). Ob der Reset danach auf LDSAP gelaufen ist, steht nicht im Git.
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

- **Status:** erledigt als Code (Sprint 003). Broker bleibt G7. Container-Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run-Schutz in der echten Host-Umgebung umstellt. Committete Dateien setzen das Flag nie auf `false`.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt (Deploy to DEV grün, 2026-11-09 15:52 UTC+1, Commit `90a6593`)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev.yml` baut das Image, deployed auf dem self-hosted Runner des DEV-Hosts ohne SSH, zieht Compose hoch und prüft `/health/live`. `bdx-collect diagnose` bricht den Job nicht ab. Der Job bricht ab, wenn die Host-Umgebung den Dry-Run-Schutz ausschaltet. Der letzte grüne Lauf hat diese Sperre nicht ausgelöst.
- **Abhängigkeit:** G5 bleibt offen für den SQL-Login. `/health/live` beweist den Login nicht.
- **Akzeptanz:** `collector` und `api` werden vom Deploy-Workflow neu erzeugt, `/health/live` war grün. Der Dry-Run-Schutz bleibt auf dem DEV-Host an, bis ein Operator ihn außerhalb des Repos umstellt.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
