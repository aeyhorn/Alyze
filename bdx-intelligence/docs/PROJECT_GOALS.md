# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-13 07:33 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil. Der Abgleich 2026-11-13 prüft die Ziele gegen `origin/main` (`cd6440f`). Neue Ziel-IDs gibt es nicht: `REQUIREMENTS.md` hat keine Zeile ohne Ziel.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`cd6440f`). In `ci.yml` sind ruff und mypy advisory, das Coverage-Gate ist 68 %. `deploy-dev.yml` läuft auf dem self-hosted Runner, ohne SSH; der Deploy von `cd6440f` ist grün (Actions `42768023481`). Environments `dev`, `prod` und `CURSOR_API_KEY` existieren, jeweils mit leerer `protection_rules`-Liste (gelesen 2026-11-13 07:33 UTC+1). Rulesets-Länge 0. Branch Protection und die Secret-Liste antworten 403. Die nächtliche Integration scheitert vor pytest in „Install ODBC Driver 18“ (letzter Lauf Actions `43202844646`, 2026-11-12). `chore/ruff-cleanup-20261108` ist nicht gemergt. `pr-review.yml` hat im Schritt „Fetch PR diff“ zwei `env`-Blöcke; Push-Läufe enden ohne Jobs.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum ist auf `main`. Die übrigen Akzeptanzpunkte sind offen. `prod` hat in der Environments-API keine Reviewer.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` liegt auf `main`, mit SELECT auf OWOR/OITM und den Q2P-Tabellen, ohne `DENY CONTROL`. Die Betriebsnotiz vom 2026-11-07 sagt, der Login existierte da noch nicht. Dieser Abgleich hat LDSAP nicht geprüft.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. `.env.example` setzt `MQTT_ENABLED=false` und `KAFKA_ENABLED=false`. Ein Broker ist im Repo nicht konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574, Notiz 2026-11-07). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge. Seitdem zeigt Git keinen PROD-Sammellauf.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. `SL_DRY_RUN` bleibt unberührt.

## Erledigt

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 für den SQL-Login im Container. Der grüne Deploy beweist den Login nicht.
- **Stand:** `deploy-dev.yml` von `cd6440f` ist grün (Actions `42768023481`, 2026-11-10 07:22 UTC+1): Image-Build und Deploy auf dem self-hosted Runner, inklusive `/health/live`. Der Job bricht ab, wenn die Host-Umgebung echte Service-Layer-Schreibvorgänge erlauben würde. Der committete Stempel `.runtime/last-deploy-sha` bleibt `6ccc036` (2026-11-07 21:50 UTC+1). Der Commit hinter dem Stempel enthält Migrationen `004`–`008` nicht. Dieser Abgleich hat den Host nicht erneut geprüft. Seit `cd6440f` gibt es keinen neueren `main`.
- **Akzeptanz:** erfüllt durch den grünen Deploy-Lauf von `origin/main`. Auf dem DEV-Host bleibt der Schreibschutz an, bis ein Operator ihn bewusst umstellt.

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
