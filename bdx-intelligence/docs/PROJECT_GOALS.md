# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-18 23:36 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`a66b194`, 2026-11-16 14:23 UTC). Der einzige Commit seit `cd6440f` ist der DORA-Snapshot. CI (Run 42768023614) und der DEV-Deploy (Run 42768023481) von `cd6440f` sind grün. An `a66b194` hängt kein Produkt-CI- und kein Deploy-Lauf. Die Integration-Schedule-Läufe 44293106343 (2026-11-18 11:15 UTC) und 44074958149 (2026-11-17 11:32 UTC) liegen auf diesem SHA. Ruff und mypy sind in `ci.yml` advisory, das Coverage-Gate steht auf 68 %. Docs-CI von `9e7e31b` (Run 44403303298, 2026-11-18 21:36 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Die Pytest-Zusammenfassung steht in Logzeile 21:37:24.925 (5,44 s). Der Pytest-Job endete 21:37:28 UTC. Lint endete 21:37:10 UTC, Type Check 21:37:33 UTC, Docker-Smoke 21:37:58 UTC. Der vorherige Docs-CI von `5dac68d` (Run 44392917328, Pytest-Log 20:37:32.413, 5,76 s) hat dieselbe grüne Form. Dieselbe grüne Form läuft von 06:37 UTC (`8b8ea51`, Run 44252602866) bis 21:37 UTC. Um 00:37 UTC war Run 44209285859 auf `fc9dae1` rot mit dem Kalender-Test plus `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle` (3 failed, 176 passed, 1 560 missed, 73,69 %). Dieselben drei Tests waren auf `c89c24a` um 00:37 UTC rot (Run 43989085036). Um 01:35 UTC fiel auf `f7c81a7` (Run 44216899780) nur der Kalender-Test (178 passed, 1 545 missed, 73,95 %). Run 44245226262 auf `3982b2a` (Pytest-Ende 05:35:20 UTC) ist dieselbe Kalender-Form. Zwischen diesen SHAs liegen nur Dokumentations-Commits. Der Docs-Commit dieses Laufs ist beim Schreiben noch nicht in CI. Auto-merge (Run 44403303617 auf `9e7e31b`, Logzeile 21:37:09.463) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge 44392917342 auf `5dac68d` tat dasselbe. Der letzte Nightly-Lauf (2026-11-18 11:16 UTC, Run 44293106343, head `a66b194`) scheitert in „Install ODBC Driver 18“ und „Notify on failure“; „Run integration tests“ ist skipped. Der Workflow-Cron ist `0 3 * * *`; GitHub hat den Lauf um 11:15 UTC angelegt. Der vorherige Lauf 44074958149 (2026-11-17 11:32 UTC, derselbe Head) scheiterte genauso. `pr-review.yml` hat im Schritt „Fetch PR diff“ zwei `env`-Blöcke (Zeilen 46 und 51). Der nächste Schritt „Run review“ beginnt in Zeile 54, sein `env` in Zeile 55. Push-Lauf 44403291333 (2026-11-18 21:36:54 UTC, `9e7e31b`) endet ohne Job. Push-Lauf 44392899746 (20:37:00 UTC, `5dac68d`) endet ohne Job. Der Lint-Cleanup vom 2026-11-15 (Run 43710438515) hat die Suite grün und „Create trivial PR“ rot, weil Actions keine Pull Requests anlegen darf. Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules (gelesen 2026-11-18 23:35 UTC+1). `main` meldet `protected: false`, die Ruleset-Liste ist leer. Der Branch-Protection-Endpunkt und die Secret-Liste antworten mit HTTP 403. Der DORA-Lauf 43885095274 hat `a66b194` gelegt.
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
