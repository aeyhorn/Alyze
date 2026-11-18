# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-18 18:37 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`a66b194`, 2026-11-16 14:23 UTC). Der einzige Commit seit `cd6440f` ist der DORA-Snapshot. CI (Run 42768023614) und der DEV-Deploy (Run 42768023481) von `cd6440f` sind grün. An `a66b194` hängt kein Produkt-CI- und kein Deploy-Lauf. Die Integration-Schedule-Läufe 44293106343 (2026-11-18 11:15 UTC) und 44074958149 (2026-11-17 11:32 UTC) liegen auf diesem SHA. Ruff und mypy sind in `ci.yml` advisory, das Coverage-Gate steht auf 68 %. Docs-CI von `f565a5b` (Run 44349282362, 2026-11-18 16:37 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 16:37:33 UTC (7,93 s). Lint, Type Check und Docker-Smoke sind success. Der Docs-Commit dieses Laufs ist beim Schreiben noch nicht in CI. Der vorherige Docs-CI von `4930574` (Run 44338308174, 2026-11-18 15:40 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 15:40:45 UTC (5,54 s). Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `7fec286` (Run 44326694238, 2026-11-18 14:39 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 14:40:21 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `bfd2542` (Run 44315355504, 2026-11-18 13:36 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 13:36:33 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `af1e8d5` (Run 44305401711, 2026-11-18 12:35 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 12:36:01 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `2b635c0` (Run 44296187746, 2026-11-18 11:36 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 11:36:55 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `2961d0b` (Run 44286887798, 2026-11-18 10:35 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 10:36:21 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `4f1c8e3` (Run 44278007929, 2026-11-18 09:39 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 09:40:07 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `c3aa2e9` (Run 44268180313, 2026-11-18 08:34 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 08:35:08 UTC. Lint, Type Check und Docker-Smoke sind success. Der Docs-CI von `fe43873` (Run 44260337407, 2026-11-18 07:37 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 07:37:58 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `8b8ea51` (Run 44252602866, 2026-11-18 06:36 UTC, PR #184) ist grün: 179 passed, 8 deselected, 1 warning, 74 % (5 930 Statements, 1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 06:37:06 UTC. Lint, Type Check und Docker-Smoke sind success. Der vorherige Docs-CI von `3982b2a` (Run 44245226262, 2026-11-18 05:34 UTC, PR #184) ist rot: 1 failed, 178 passed, 8 deselected, 74 % (1 545 missed, 73,95 %) bei Gate 68 %, Pytest-Exit 1. Der Pytest-Schritt endete 05:35:20 UTC. Rot ist `test_machine_utilization_with_calendar` (`assert None is not None`). Die beiden Lateness-Tests sind in diesem Lauf grün. Der vorherige Docs-CI von `45a5e6c` (Run 44238704263, Pytest-Ende 04:38:58 UTC) hatte dieselbe Form. Der Docs-CI von `67c0bb2` (Run 44231377596, Pytest-Ende 03:35:02 UTC, Kurzfassung 03:34:59 UTC) hatte dieselbe Form. Der Docs-CI von `de52f27` (Run 44224593755, Pytest-Ende 02:37:47 UTC) hatte dieselbe Form. Um 01:35 UTC war Run 44216899780 auf `f7c81a7` genauso (nur der Kalender-Test, 178 passed, 1 545 missed, 73,95 %). Um 00:37 UTC am selben Tag war Run 44209285859 auf `fc9dae1` rot mit dem Kalender-Test plus `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle` (3 failed, 176 passed, 1 560 missed, 73,69 %). Dieselben drei Tests waren auf `c89c24a` um 00:37 UTC rot (Run 43989085036, 176 passed). Um 01:35 UTC (`cbec5e1`, Run 43996707190) und um 05:39 UTC (`b69a171`, Run 44025523409) fällt nur der Kalender-Test (178 passed). Grün mit 179 passed sind Run 44094522392 (13:37 UTC), Run 44191321190 auf `ca949f2` (22:35:09 UTC) und Run 44200811809 auf `61f842b` (23:36:40 UTC, 1 545 missed, 73,95 %). Zwischen diesen SHAs liegen nur Dokumentations-Commits. Auto-merge (Run 44349282282 auf `f565a5b`, 2026-11-18 16:37 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44338308308 auf `4930574`, 2026-11-18 15:40 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44326694231 auf `7fec286`, 2026-11-18 14:39 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44315355535 auf `bfd2542`, 2026-11-18 13:36 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44305401801 auf `af1e8d5`, 2026-11-18 12:35 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44296187585 auf `2b635c0`, 2026-11-18 11:36 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44286887650 auf `2961d0b`, 2026-11-18 10:35 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Auto-merge (Run 44278008274 auf `4f1c8e3`, 2026-11-18 09:39 UTC) hat PR #184 übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Run 44268180254 auf `c3aa2e9` (2026-11-18 08:34 UTC) hat denselben PR genauso übersprungen, weil das Label `trivial` fehlt. `PR_LABELS` war `[]`. Run 44260337427 auf `fe43873` (2026-11-18 07:37 UTC) hat denselben PR genauso übersprungen. Run 44252602999 auf `8b8ea51` (2026-11-18 06:36 UTC) hat denselben PR genauso übersprungen. Run 44245226360 auf `3982b2a` hat denselben PR genauso übersprungen. Run 44238704329 (`45a5e6c`), Run 44231377595 (`67c0bb2`), Run 44224593845 (`de52f27`) und Run 44216899736 (`f7c81a7`) haben denselben PR genauso übersprungen. Der letzte Nightly-Lauf (2026-11-18 11:16 UTC, Run 44293106343, head `a66b194`) scheitert in „Install ODBC Driver 18“ und „Notify on failure“; „Run integration tests“ ist skipped. Der Workflow-Cron ist `0 3 * * *`; GitHub hat den Lauf um 11:15 UTC angelegt. Der vorherige Lauf 44074958149 (2026-11-17 11:32 UTC, derselbe Head) scheiterte genauso. `pr-review.yml` hat im Schritt „Fetch PR diff“ zwei `env`-Blöcke; Push-Lauf 44349268204 (2026-11-18 16:36 UTC, `f565a5b`) endet ohne Job. Push-Lauf 44338291253 (2026-11-18 15:40 UTC, `4930574`) endet ohne Job. Push-Lauf 44326679721 (2026-11-18 14:39 UTC, `7fec286`) endet ohne Job. Push-Lauf 44315344389 (2026-11-18 13:36 UTC, `bfd2542`) endet ohne Job. Push-Lauf 44305390511 (2026-11-18 12:35 UTC, `af1e8d5`) endet ohne Job. Push-Lauf 44296179125 (2026-11-18 11:36 UTC, `2b635c0`) endet ohne Job. Push-Lauf 44286880175 (2026-11-18 10:35 UTC, `2961d0b`) endet ohne Job. Push-Lauf 44277998822 (2026-11-18 09:39 UTC, `4f1c8e3`) endete genauso. Push-Lauf 44268172418 (2026-11-18 08:34 UTC, `c3aa2e9`) endete genauso. Push-Lauf 44260327426 (2026-11-18 07:37 UTC, `fe43873`) endete genauso. Push-Lauf 44252596006 (2026-11-18 06:36 UTC, `8b8ea51`) endete genauso. Push-Lauf 44245217457 (2026-11-18 05:34 UTC, `3982b2a`) endete genauso. Push-Lauf 44238698375 (2026-11-18 04:38 UTC, `45a5e6c`) endete genauso. Push-Lauf 44231369372 (03:34 UTC, `67c0bb2`), Push-Lauf 44224585706 (02:37 UTC, `de52f27`) und Push-Lauf 44216893967 (01:34 UTC, `f7c81a7`) endeten genauso. Der Lint-Cleanup vom 2026-11-15 (Run 43710438515) hat die Suite grün und keinen PR erzeugt. Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules (gelesen 2026-11-18 18:37 UTC+1). `main` meldet `protected: false`, die Ruleset-Liste ist leer. Der Branch-Protection-Endpunkt und die Secret-Liste antworten mit HTTP 403. Der DORA-Lauf 43885095274 hat `a66b194` gelegt.
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
