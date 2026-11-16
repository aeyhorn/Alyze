# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-16 11:37 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`cd6440f`). CI (Run 42768023614) und der DEV-Deploy (Run 42768023481) dieses Commits sind grün. Ruff und mypy sind in `ci.yml` advisory, das Coverage-Gate steht auf 68 %. Der letzte abgeschlossene Nightly-Lauf (2026-11-15 10:28 UTC, Run 43704248636) scheitert in „Install ODBC Driver 18“ und „Notify on failure“; pytest ist nicht unter den fehlgeschlagenen Schritten. Die geplanten Läufe vom 2026-11-08 bis 2026-11-14 sind ebenfalls failure. Stand 2026-11-16 11:37 UTC+1 hat der Cron `0 3 * * *` für diesen Tag (fällig 03:00 UTC) weder einen abgeschlossenen noch einen wartenden oder laufenden Lauf. Die Abfrage nach Integration-Läufen mit Erstelldatum 2026-11-16 ist leer. Zwei ältere Actions-Läufe stehen seit 2026-11-11 20:41 UTC auf queued: CI 43097537658 und Auto-merge 43097537724 (Branch `cursor/projekt-dokumente-abgleich-a8a9`, Commit `f89c817`). Sie gehören nicht zu diesem Cron. `pr-review.yml` hat zwei `env`-Blöcke im Schritt „Fetch PR diff“; der letzte Push-Lauf 43841169727 (2026-11-16 09:35 UTC, `dc20523` auf `sync/status-20261116`) endet ohne Job, ebenso 43832477042 (2026-11-16 08:35 UTC, `a79ab84`), 43825406548 (2026-11-16 07:39 UTC, `50039ba`), 43818061702 (2026-11-16 06:37 UTC, `08c3f6b`), 43811254306 (2026-11-16 05:35 UTC, `71c5a03`) und 43805165533 (2026-11-16 04:36 UTC, `cc87d72`). Der Docs-CI von `dc20523` (Run 43841180628, 2026-11-16 09:36 UTC, PR #178) ist success: 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed; Coverage-Zeile 73,95 %). Der Docs-CI von `a79ab84` (Run 43832485591, 2026-11-16 08:35 UTC, PR #178) ist success: 179 passed, 8 deselected, TOTAL 74 % (5 930 Statements, 1 545 missed; Coverage-Zeile 73,95 %). Der Docs-CI von `50039ba` (Run 43825413067, 2026-11-16 07:40 UTC, PR #178) ist success mit denselben Zählern. Der Docs-CI von `08c3f6b` (Run 43818069462) hat dieselben Zahlen. Der Docs-CI von `cc87d72` (Run 43805169716) scheitert mit 1 failed und 178 passed an `test_machine_utilization_with_calendar`. Dieselbe Zahl haben die Docs-CI-Läufe von `ecc180b` (Run 43799221206), `a22c5d6` (Run 43793408407) und PR #180 (Run 43811268796, `71c5a03`). Der Docs-CI von `98c607f` (Run 43787512471) scheitert am selben Test bei 73,95 %. Der Docs-CI von `058466c` (Run 43775742168) ist success. Der Docs-CI von PR #179 (Run 43781268705, `69b15ca`) scheitert mit 3 failed und 176 passed bei 73,69 % Coverage. Auto-merge (Run 43841180693) hat PR #178 für `dc20523` übersprungen, weil das Label `trivial` fehlt. Run 43832485594 hat dasselbe für `a79ab84` getan, Run 43825413115 für `50039ba`, Run 43818069370 für `08c3f6b`, Run 43805169727 für `cc87d72`. Der Sonntags-Lint-Cleanup (Run 43710438515, 2026-11-15 11:45 UTC) hat die Suite grün; der Schritt „Create trivial PR“ endet mit Exit 1, weil Actions keine Pull Requests anlegen darf, und `chore/ruff-cleanup-20261115` hat keinen PR. Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules (erneut um 11:37 UTC+1 am 2026-11-16 gelesen). Die Branch-Ressource von `main` meldet `protected: false`, die Ruleset-Liste ist leer. Der Branch-Protection-Endpunkt und die Secret-Liste antworten mit HTTP 403. Der DORA-Wochenlauf `0 6 * * 1` war am 2026-11-16 um 06:00 UTC fällig und hat um 11:37 UTC+1 weder einen abgeschlossenen noch einen wartenden oder laufenden Lauf. Die Abfrage nach DORA-Läufen mit Erstelldatum 2026-11-16 ist leer. Der letzte Erfolg bleibt Run 42638115770 vom 2026-11-09 14:47 UTC.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Der Baum auf `main` ist erfüllt. Secrets, Reviewer und der Pflichtcheck bleiben in diesem Lauf offen.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `create_bdx_readonly.sql` und `reset_bdx_readonly.sql` liegen auf `main`. Commit `7d0fb2f` (2026-11-07) hält fest, dass der Login `bdx_readonly` auf LDSAP existierte und `DEV_SBO_LEISINGER` nicht öffnen konnte, weil `DENY CONTROL` CONNECT blockierte (Fehler 18456, State 38). Das Reset-Skript enthält ein Klartext-Passwort und gehört so nicht ins Repo. Dieser Lauf hat LDSAP nicht erneut verbunden, deshalb ist nicht belegt, dass der Login heute funktioniert.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 ist nicht mehr die Voraussetzung für den laufenden DEV-Deploy. Der SQL-Login bleibt offen für den Betrieb ohne Windows-Integrated-Auth.
- **Stand:** `deploy-dev.yml` auf dem Self-hosted-Runner war am 2026-11-10 für `cd6440f` grün (Run 42768023481: Build, Migrate, Recreate von `collector` und `api`, `/health/live`). Der Marker `.runtime/last-deploy-sha` im Repo zeigt noch `6ccc036` (2026-11-07 21:50 +01:00). Ein frischer Shopfloor-Probe fehlt in diesem Lauf. `.env.example` schaltet den Dry-Run-Guard aus und ist nicht die Host-Datei.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, der Dry-Run-Guard bleibt auf dem DEV-Host an, bis ein Operator ihn bewusst öffnet. Der letzte grüne Deploy belegt die ersten beiden Punkte darüber, dass der Deploy-Job durchgelaufen ist und der Host-Guard den Lauf nicht abgebrochen hat.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574, 2026-11-07). DEV hinkte dabei PROD hinterher, deshalb fehlte auf DEV die Maschinen-Verknüpfung für laufende Aufträge. Kein neuer PROD-Leselauf in diesem Abgleich.
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
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run-Guard in der Host-`.env` öffnet. `.env.example` im Repo schaltet diesen Guard aus.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
