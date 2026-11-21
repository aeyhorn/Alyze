# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-21 07:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`a66b194`, 2026-11-16 14:23 UTC). Der einzige Commit seit `cd6440f` ist der DORA-Snapshot. CI (Run 42768023614) und der DEV-Deploy (Run 42768023481) von `cd6440f` sind grün. An `a66b194` hängt kein Produkt-CI-/Deploy-Lauf. Docs-CI auf `b2abaff` (Run 44874580557, aktualisiert 2026-11-21 06:15:05 UTC) ist grün: 179 passed, 8 deselected, 1 warning in 5,64 s, 1 545 missed, 73,95 %, Gate 68 % erreicht. Der vorherige grüne Docs-CI bleibt Run 44838149396 auf `216e259`. Dazwischen ist Run 44871642825 auf `1195682` rot, nur `test_machine_utilization_with_calendar`. Environments ohne Protection Rules; `main` ohne Branch Protection. Abgleich 2026-11-21 07:34 UTC+1.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum auf `main` ist erfüllt. Secrets, Reviewer und der Pflichtcheck sind in diesem Lauf offen: die Secret-Liste antwortet mit HTTP 403, Protection Rules sind leer.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `create_bdx_readonly.sql` und `reset_bdx_readonly.sql` liegen auf `main`. Commit `7d0fb2f` (2026-11-07) hält fest, dass der Login `bdx_readonly` auf LDSAP existierte und `DEV_SBO_LEISINGER` nicht öffnen konnte, weil `DENY CONTROL` CONNECT blockierte. Das Reset-Skript enthält ein Passwort im Klartext und gehört so nicht ins Repo. Dieser Lauf hat LDSAP nicht erneut verbunden.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 ist nicht mehr die Voraussetzung für den laufenden DEV-Deploy. Der SQL-Login bleibt offen für den Betrieb ohne Windows-Integrated-Auth.
- **Stand:** `deploy-dev.yml` auf dem Self-hosted-Runner war am 2026-11-10 für `cd6440f` grün (Run 42768023481: Build, Migrate, Recreate von `collector` und `api`, `/health/live`). `.runtime/last-deploy-sha` enthält `6ccc036`. `.runtime/last-deploy-at` enthält `2026-11-07 21:50:15 +01:00`. Beide Dateien wurden zuletzt in `cd6440f` committet. `origin/main` ist `a66b194`; ein Deploy-Lauf für diesen SHA existiert nicht. Ein frischer Shopfloor-Probe fehlt in diesem Lauf. `.env.example` schaltet den Dry-Run-Guard aus und ist nicht die Host-Datei. Der Deploy vom 2026-11-10 ist am Host-Guard nicht abgebrochen.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, der Dry-Run-Guard bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst öffnet. Der grüne Deploy-Job vom 2026-11-10 belegt den Lauf bis `/health/live`. Dieser Lauf hat den Host nicht erneut geprüft.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574, 2026-11-07). DEV hinkte dabei PROD hinterher, deshalb fehlte auf DEV die Maschinen-Verknüpfung für laufende Aufträge. Kein neuer PROD-Leselauf in diesem Abgleich.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. Der Dry-Run-Guard bleibt unberührt.

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
- **Akzeptanz:** Code und die Dry-Run-Prüfung auf DEV sind da. Echte Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run-Guard in der Host-Umgebung öffnet. `.env.example` im Repo schaltet diesen Guard aus. Dieser Lauf lässt die Datei unverändert.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
