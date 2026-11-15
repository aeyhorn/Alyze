# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-15 04:35 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich hält die Ziele gegen `origin/main` (`cd6440f`, 2026-11-10 07:21 +01:00).

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `main` (`cd6440f`). Der Push-CI dieses Commits ist grün (Actions `42768023614`). Das Branch-Objekt meldet `protected: false`, die Rulesets-Länge ist 0, der Protection-Endpunkt antwortet 403. Die Environments `dev`, `prod` und `CURSOR_API_KEY` existieren ohne Protection-Rules. Die Actions-Secret-Liste ist mit diesem Token nicht lesbar (403). Die nächtliche Integration scheitert vor pytest im Schritt „Install ODBC Driver 18“ (`gpg` kann `/dev/tty` nicht öffnen). Letzter Lauf: Actions `43582578926` (2026-11-14 09:52 UTC) auf `cd6440f`. Ein Lauf vom 2026-11-15 stand um 04:35 CET noch nicht in der Liste. In `pr-review.yml` hat der Schritt „Fetch PR diff“ zwei `env`-Schlüssel; der letzte Push-Lauf (Actions `43668769054`) hat null Jobs.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Davon ist der Baum auf `main` erfüllt. Protection, `prod`-Reviewer und ein grüner Nachtlauf fehlen. Die Secret-Liste ließ sich nicht lesen.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` liegt auf `main`. Dieser Lauf hat LDSAP nicht erneut geprüft. Zuletzt dokumentiert am 2026-11-07: der Login fehlte.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. `.env.example` lässt beide Publisher aus. Ein Broker ist im Git nicht konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Der letzte dokumentierte PROD-Kontakt bleibt die Einzelprobe vom 2026-11-07 (FA 38574). Ein eigener PROD-Event-Store oder ein mode-prefixed `source_key` ist nicht als geliefert geführt.
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

- **Status:** erledigt als Code (Sprint 003). Broker ist G7. Der DEV-Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Trockenlauf in der echten `.env` ausschaltet. `.env.example` schaltet den Trockenlauf aus; das widerspricht der Regel, committete Dateien nicht so zu setzen. Dieser Lauf ändert die Beispieldatei nicht.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev` von `cd6440f` ist grün (Actions `42768023481`, 2026-11-10 07:22 CET), einschließlich „Deploy + smoke test“. Der Lauf ist nicht am Host-Guard abgebrochen. Im Commit stehen `.runtime/last-deploy-sha` `6ccc036` und `.runtime/last-deploy-at` `2026-11-07 21:50:15 +01:00`. Dieser Lauf hat den Host nicht erneut geprüft.
- **Akzeptanz:** erfüllt zum Deploy-Zeitpunkt. `collector` und `api` sind über den erfolgreichen Smoke-Schritt gelaufen. Der Trockenlauf auf dem DEV-Host hat den Abbruch nicht ausgelöst.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
