# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-17 19:37 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`a66b194`, 2026-11-16 14:23 UTC). Der einzige Commit seit `cd6440f` ist der DORA-Snapshot. CI (Run 42768023614) und der DEV-Deploy (Run 42768023481) von `cd6440f` sind grün. An `a66b194` hängt kein CI- und kein Deploy-Lauf. Ruff und mypy sind in `ci.yml` advisory, das Coverage-Gate steht auf 68 %. Docs-CI von `cca6abe` (Run 44139092716, 2026-11-17 17:37 UTC, PR #182) ist grün: 179 passed, 8 deselected, 74 % (1 545 missed, 73,95 %) bei Gate 68 %. Der Pytest-Schritt endete 17:38:24 UTC, nach `shift_end` 14:00; `test_machine_utilization_with_calendar` ist PASSED. Docs-CI von `a32b017` (Run 44127681394, Pytest-Ende 16:37:03 UTC) hatte dieselben Zahlen. Docs-CI von `90c508c` (Run 44116051241, Pytest-Ende 15:35:45 UTC) hatte dieselben Zahlen. Docs-CI von `00ba5f7` (Run 44105277181, Pytest-Ende 14:38 UTC) hatte dieselben Zahlen. Docs-CI von `cdb311f` (Run 44094522392, Pytest-Ende 13:37 UTC) hatte dieselben Zahlen. Docs-CI von `8c3fe28` (Run 44084752663, Pytest-Ende 12:37 UTC) hatte dieselben Zahlen. Docs-CI von `f5b822a` (Run 44075816944, Pytest-Ende 11:38 UTC), von `f8b6e80` (Run 44066363337, Pytest-Ende 10:36 UTC), von `2eed0bd` (Run 44057049653, Pytest-Ende 09:36 UTC) und von `bc3b7a2` (Run 44048407839, Pytest-Ende 08:38 UTC) hatte dieselben Zahlen. Docs-CI von `b69a171` (Run 44025523409, 05:38 UTC) war rot: 1 failed, 178 passed. Fehlgeschlagen war nur `test_machine_utilization_with_calendar`. Dieselbe einzelne Fehlstelle lag auf `6c85cfa` (Run 44018364452), `d90d1da` (Run 44011713279), `754e4e1` (Run 44004330779) und `cbec5e1` (Run 43996707190). Auf `c89c24a` (Run 43989085036) waren zusätzlich `test_lateness_scrap_when_no_material_context` und `test_lateness_waiting_idle` rot; beide sind seit `cbec5e1` wieder grün. Auf `1e3d1e5` (Run 43981065146) waren 179 passed. Dazwischen liegen nur Dokumentations-Commits. Die Schicht im Test ist 06:00–14:00 UTC; 05:39 UTC liegt davor, 13:37 UTC darin, 17:38 UTC danach, und der Kalender-Test ist um 17:38 trotzdem grün. Auto-merge (Run 44139092744 auf `cca6abe`) hat PR #182 übersprungen, weil das Label `trivial` fehlt. Der Lauf 44127681386 auf `a32b017` ebenso. Der Lauf 44116050891 auf `90c508c` ebenso. Der Lauf 44105277196 auf `00ba5f7` ebenso. Der Lauf 44094522647 auf `cdb311f` ebenso. Der letzte Nightly-Lauf (2026-11-17 11:32 UTC, Run 44074958149, head `a66b194`) scheitert in „Install ODBC Driver 18“ und „Notify on failure“; „Run integration tests“ ist skipped. Der Workflow-Cron ist `0 3 * * *`; GitHub hat den Lauf um 11:32 UTC angelegt. `pr-review.yml` hat im Schritt „Fetch PR diff“ zwei `env`-Blöcke; Push-Lauf 44139080511 (2026-11-17 17:37 UTC, `cca6abe`) endet ohne Job. Der Lauf 44127663539 (`a32b017`, 16:36 UTC) ebenso. Der Lauf 44116030124 (`90c508c`, 15:35 UTC) ebenso. Der Lauf 44094511412 (`cdb311f`, 13:37 UTC) ebenso. Der Lint-Cleanup vom 2026-11-15 (Run 43710438515) hat die Suite grün und keinen PR erzeugt. Environments `dev`, `prod` und `CURSOR_API_KEY` haben keine Protection Rules (gelesen 2026-11-17 19:37 UTC+1). `main` meldet `protected: false`, die Ruleset-Liste ist leer. Der Branch-Protection-Endpunkt und die Secret-Liste antworten mit HTTP 403. Der DORA-Lauf 43885095274 hat `a66b194` gelegt.
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
