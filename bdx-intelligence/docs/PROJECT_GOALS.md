# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-12 14:36 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich hält den Stand gegen `origin/main` (`cd6440f`).

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (Workflows, Agents, Skripte, Prompts). Coverage-Gate ist 68 %. Ruff und mypy laufen mit `continue-on-error`. Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. `prod` hat keine `protection_rules` (erneut gelesen 2026-11-12 14:36 UTC+1). Die Ruleset-Liste war leer. Klassische Branch Protection und die Actions-Secrets waren mit diesem Token nicht lesbar (403). `origin/chore/ruff-cleanup-20261108` (`57411b2`) ist nicht gemergt, liegt 11 Commits hinter `main` und hat keinen offenen PR. Der Push-CI-Lauf von `cd6440f` am 2026-11-10 war grün. PR-CI am 2026-11-12 ist gespalten: Läufe bis 05:33 UTC scheitern an `tests/test_analytics.py::test_machine_utilization_with_calendar` (`assert None is not None`; 1 fehlgeschlagen, 178 bestanden, 8 abgewählt). Grün danach, zuletzt 12:37 UTC auf `cursor/projekt-dokumente-abgleich-76f7` (Actions `43219558353`: 179 bestanden, 8 abgewählt, Coverage 73,95 % bei 5930 Anweisungen und 1545 verfehlt, Gate 68 %). Dieselben Zahlen lagen um 11:37 UTC auf `sync/status-20261112` (Actions `43210723137`) und um 09:36 UTC (Actions `43192961156`). Der Test hängt den Schichtkalender an den aktuellen UTC-Wochentag und eine Schicht 06:00–14:00. Die nächtlichen Integration-Läufe vom 2026-11-08 bis 2026-11-12 scheitern in `Install ODBC Driver 18` (`gpg` kann `/dev/tty` nicht öffnen, Exit 2), bevor pytest startet. Der Lauf vom 2026-11-12 ist Actions `43202844646` (10:43 UTC). Pushes zeichnen einen fehlgeschlagenen Actions-Lauf `.github/workflows/pr-review.yml` ohne Jobs auf, weil der Schritt „Fetch PR diff“ zwei `env`-Schlüssel hat. Vor diesem Lauf 94 offene PRs gegen `main` (25 bereit, 69 Draft), alles Dokumentation, darunter #99 und #106. Dieser Lauf liegt auf `cursor/projekt-dokumenten-abgleich-ce27` und öffnet einen weiteren Doku-PR, ohne zu mergen. 104 Remote-Branches liegen vor diesem Push nicht in `origin/main`.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum-Teil ist erfüllt. Reviewer, Branch Protection und die Secrets sind offen bzw. nicht geprüft.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` liegen im Repo. Commit `7d0fb2f` hat `DENY CONTROL` entfernt, weil dieser Deny CONNECT blockiert hat. Die frühere Behauptung „Login existiert nicht“ trägt der Fix nicht mehr. Dieser Abgleich hat LDSAP nicht angefragt.
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

- **Status:** erledigt als Code (Sprint 003). Broker bleibt G7. DEV-Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator das Flag in der echten `.env` umstellt. Committete Dateien schalten Schreibvorgänge nicht ein.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt auf DEV (Actions)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev.yml` läuft auf dem Self-hosted-Runner des DEV-Hosts, ohne SSH-Hop. Erfolgreiche Läufe bis einschließlich `cd6440f` (2026-11-10 07:22 UTC+1) ziehen das Image, migrieren, erzeugen `collector` und `api` neu und bestehen `/health/live`. Die Stempeldatei `.runtime/last-deploy-*` im Repo steht noch auf 2026-11-07 21:50 +01:00 und SHA `6ccc036`.
- **Abhängigkeit:** G5 bleibt für den SQL-Login offen. Der laufende Deploy nutzt die Host-`.env`, die nicht im Repo liegt.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist in den erfolgreichen Actions-Läufen grün. Der Workflow bricht ab, wenn die DEV-Host-Umgebung Schreibvorgänge erlauben würde. Dieser Abgleich hat den Host nicht selbst geprüft.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
