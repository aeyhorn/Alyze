# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-23 06:36 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`71e8726`, 2026-11-21 08:25 +01:00, inklusive #188 und #190). Produkt-CI 44880160970 ist grün: 183 passed, 8 deselected, 1 warning in 5,72 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 %. Ruff und mypy bleiben advisory. DEV-Deploy 44880160990 auf demselben SHA ist grün. Docs-CI von `a89c163` (PR #193, 45113132923, erstellt 04:39:10 UTC, aktualisiert 04:40:08 UTC) ist grün (183 passed, 8 deselected, 1 warning in 5,83 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 % erreicht, Pytest-Logzeile 04:39:44.7067778, Pytest-Job 04:39:50 UTC, Pytest-Step 04:39:37–04:39:44 UTC, Lint 04:39:31 UTC, Type Check 04:39:42 UTC, Docker 04:40:07 UTC). Docs-CI von `ef78e0a` (PR #193, 45106941548, erstellt 03:36:08 UTC, aktualisiert 03:37:05 UTC) ist grün (183 passed, 8 deselected, 1 warning in 5,34 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 % erreicht, Pytest-Logzeile 03:36:50.4848064, Pytest-Job 03:36:53 UTC, Pytest-Step 03:36:43–03:36:50 UTC, Lint 03:36:18 UTC, Type Check 03:36:31 UTC, Docker 03:37:04 UTC). Docs-CI von `4a49d1c` (PR #193, 45101618170, erstellt 02:41:11 UTC, aktualisiert 02:42:07 UTC) ist grün (183 passed, 8 deselected, 1 warning in 5,43 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 % erreicht, Pytest-Logzeile 02:41:48.3026901, Pytest-Job 02:41:53 UTC, Pytest-Step 02:41:41–02:41:48 UTC, Lint 02:41:24 UTC, Type Check 02:41:39 UTC, Docker 02:42:07 UTC). Docs-CI von `3f99b2b` (PR #193, 45095574240, aktualisiert 01:38:05 UTC) bleibt grün (183 passed, 8 deselected, 1 warning in 8,18 s, 6 093 Statements, 1 627 missed, 73,30 %). Docs-CI von `81f0a53` (PR #193, 45084445382) ist grün auf einem reinen Doku-Diff gegen `71e8726` (183 passed, 8 deselected, 1 warning in 6,56 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 % erreicht, Pytest-Logzeile 23:40:18.9701192, Pytest-Job 23:40:21 UTC, Pytest-Step 23:40:10–23:40:19 UTC, Lint 23:40:00 UTC, Type Check 23:40:18 UTC, Docker 23:40:38 UTC, aktualisiert 23:40:39 UTC). Docs-CI von `8741ea2` (PR #193, 45089709348, erstellt 00:35:57 UTC, aktualisiert 00:36:49 UTC) ist rot auf einem reinen Doku-Diff gegen `71e8726` (2 failed, 181 passed, 8 deselected, 1 warning in 5,33 s, 6 093 Statements, 1 642 missed, 73,05 %, Gate 68 % erreicht, Pytest-Logzeile 00:36:35.8665963, Pytest-Job 00:36:40 UTC, Pytest-Step 00:36:28–00:36:36 UTC, Lint 00:36:13 UTC, Type Check 00:36:37 UTC, Docker 00:36:48 UTC). Fehlschläge: `tests/test_diagnosis.py::test_lateness_scrap_when_no_material_context` und `tests/test_diagnosis.py::test_lateness_waiting_idle` (`AttributeError`, `session.get(LatenessCause, …)` ist `None`; Log `causes.classified` count=0, 00:36:32.627375Z und 00:36:32.682556Z). Dieselben zwei Tests scheiterten in Run 44967452019 auf `164505f`. PR #193 ist offen, kein Entwurf, MERGEABLE, merge state CLEAN, Kopf `a89c163`, 6 Commits. Auto-merge 45101618218 (erstellt 02:41:11 UTC, aktualisiert 02:41:19 UTC, conclusion success) hat übersprungen (Logzeile 02:41:16.2621098, `PR_LABELS` `[]`). Docs-CI von `4a49d1c` (45101618170) ist grün: Pytest-Logzeile 02:41:48.3026901, Pytest-Job 02:41:53 UTC, Pytest-Step 02:41:41–02:41:48 UTC, Lint 02:41:24 UTC, Type Check 02:41:39 UTC, Docker 02:42:07 UTC. Der vorherige Kopf `3f99b2b` (3 Commits) bleibt mit grünem Docs-CI 45095574240 (Pytest-Logzeile 01:37:45.2439987, Pytest-Job 01:37:50 UTC, Pytest-Step 01:37:35–01:37:45 UTC, Lint 01:37:21 UTC, Type Check 01:37:36 UTC, Docker 01:38:05 UTC). Auto-merge 45095574242 (erstellt 01:37:10 UTC, aktualisiert 01:37:18 UTC, conclusion success) hat übersprungen (Logzeile 01:37:15.6479123, `PR_LABELS` `[]`). Der Commit `8741ea2` (2 Commits) war UNSTABLE. Auto-merge 45089709349 (erstellt 00:35:57 UTC, aktualisiert 00:36:09 UTC, conclusion success) hat übersprungen (Logzeile 00:36:07.0701887, `PR_LABELS` `[]`). Docs-CI von `ef78e0a` (45106941548) ist grün: 183 passed, 8 deselected, 1 warning in 5,34 s, 73,30 %, Pytest-Logzeile 03:36:50.4848064, Pytest-Job 03:36:53 UTC, Pytest-Step 03:36:43–03:36:50 UTC, Lint 03:36:18 UTC, Type Check 03:36:31 UTC, Docker 03:37:04 UTC. Auto-merge 45106941566 (erstellt 03:36:08 UTC, aktualisiert 03:36:15 UTC, conclusion success) hat übersprungen (Logzeile 03:36:12.9854411, `PR_LABELS` `[]`). Docs-CI von `a89c163` (45113132923) ist grün: 183 passed, 8 deselected, 1 warning in 5,83 s, 73,30 %, Pytest-Logzeile 04:39:44.7067778, Pytest-Job 04:39:50 UTC, Pytest-Step 04:39:37–04:39:44 UTC, Lint 04:39:31 UTC, Type Check 04:39:42 UTC, Docker 04:40:07 UTC. Auto-merge 45113133067 (erstellt 04:39:10 UTC, aktualisiert 04:39:16 UTC, conclusion success) hat übersprungen (Logzeile 04:39:14.6382885, `PR_LABELS` `[]`). Dieser neue Commit hat noch kein CI-Ergebnis. Der vorherige grüne Docs-CI bleibt 45078862527 auf `85748d3` (183 passed, 5,36 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45072976850 auf `7761308` (183 passed, 7,43 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45067485516 auf `f2b7f69` (183 passed, 6,62 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45061564611 auf `d35d55f` (183 passed, 7,46 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45056276373 auf `dd31a58` (183 passed, 7,52 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45050197471 auf `01d473b` (183 passed, 5,30 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45044578028 auf `15a1ba6` (183 passed, 7,35 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45039256504 auf `a1443a7` (183 passed, 5,64 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45033910031 auf `e703736` (183 passed, 7,28 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45028444731 auf `bf46b32` (183 passed, 5,55 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45023065025 auf `8d3cd87` (183 passed, 6,13 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45018280931 auf `23cdaca` (183 passed, 7,13 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45013418859 auf `99346f1` (183 passed, 5,34 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45008212758 auf `d184821` (183 passed, 4,27 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 45003548761 auf `c4d0a13` (183 passed, 5,68 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44998963145 auf `2a26ffd` (183 passed, 7,50 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44994514887 auf `6df703b` (183 passed, 4,30 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44990014977 auf `c1f1daa` (183 passed, 7,94 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44985839360 auf `970c53a` (183 passed, 7,58 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44981374174 auf `9bf9e2f` (183 passed, 4,50 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44976859835 auf `cf8a03f` (183 passed, 7,34 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44972375698 auf `e6bae14` (183 passed, 6,10 s, 73,30 %). Der vorherige rote Docs-CI bleibt 44967452019 auf `164505f` (2 failed, 181 passed, 7,33 s, 73,05 %). Der grüne Docs-CI davor bleibt 44962787640 auf `89cd6c2` (183 passed, 7,27 s, 73,30 %). Branch-Ressource `main` meldet `protected: false` (SHA `71e8726`, Antwort 2026-11-23 05:33:19 GMT); Rulesets Länge 0 (Antwort 2026-11-23 05:33:20 GMT, Content-Length 2, Body `[]`); Environments ohne Protection Rules (Antwort 2026-11-23 05:34:31 GMT). Branch-Protection-Endpunkt HTTP 403 (2026-11-23 05:33:20 GMT), Secret-Liste HTTP 403 (2026-11-23 05:33:20 GMT). Nightly 45014291592 (2026-11-22 10:49 UTC, head `71e8726`, erstellt 10:49:30 UTC, aktualisiert 10:49:42 UTC) scheitert bei „Install ODBC Driver 18“ und „Notify on failure“; „Run integration tests“ ist übersprungen. Der vorherige Schedule-Lauf bleibt 44895693730 (2026-11-21 10:43 UTC). Der Lauf davor bleibt 44723784538. Beim Abgleich um 2026-11-23 06:36 UTC+1 (2026-11-23 05:36 UTC) ist 45014291592 weiter der jüngste (`integration.yml` total_count 15, Workflow aktiv). Der Cron 03:00 UTC desselben Tages ist verstrichen; ein neuerer Lauf fehlt. `pr-review.yml` startet auf Push null Jobs; der jüngste ist 45113130259 (`a89c163`, 04:39:09 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45106935642 (`ef78e0a`, 03:36:05 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45101612732 (`4a49d1c`, 02:41:08 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45095568044 (`3f99b2b`, 01:37:07 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45089703665 (`8741ea2`, 00:35:54 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45084285026 (`81f0a53`, 23:37:52 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45078857961 (`85748d3`, 22:38:31 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45072969343 (`7761308`, 21:35:36 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45067480759 (`f2b7f69`, 20:37:27 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45061558126 (`d35d55f`, 19:34:49 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45056272361 (`dd31a58`, 18:38:52 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45050191728 (`01d473b`, 17:34:17 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45044573031 (`15a1ba6`, 16:34:13 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45039251033 (`a1443a7`, 15:36:26 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45033903920 (`e703736`, 14:38:19 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45028439913 (`bf46b32`, 13:37:16 UTC, null Jobs, `created_at` gleich `updated_at`). Davor bleibt 45023059499 (`8d3cd87`, 12:35:19 UTC). Davor bleibt 45018276873 (`23cdaca`, 11:38:00 UTC). Davor bleibt 45013414144 (`99346f1`, 10:38:19 UTC). Davor bleibt 45008209075 (`d184821`, 09:34:32 UTC). Lint Cleanup 45021479034 (2026-11-22 12:17:09 UTC, aktualisiert 12:17:38 UTC, head `71e8726`) ist nach grüner Suite (183 passed, 8 deselected, 1 warning in 2,19 s) bei „Create trivial PR“ rot, weil GitHub Actions keine Pull Requests anlegen darf. `origin/chore/ruff-cleanup-20261122` (`1981d31`) ist gepusht und hat keinen offenen PR. Abgleich 2026-11-23 06:36 UTC+1.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skripte `create_bdx_readonly.sql`, `reset_bdx_readonly.sql` und `scripts/Fix-DevSapAccess.ps1` liegen auf `main` (R006, Code geliefert). Das Reset-Template nutzt den Platzhalter `__SAP_DB_PASSWORD__`. Die Deploy-Diagnose von `71e8726` (2026-11-21 07:26:56 UTC) kann `DEV_SBO_LEISINGER` weiter nicht öffnen (ODBC 4060). Dieser Lauf hat LDSAP nicht verbunden und das Reset nicht ausgeführt.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** in Arbeit
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 ist nicht mehr Voraussetzung für den laufenden DEV-Deploy.
- **Stand:** Deploy to DEV für `71e8726` ist grün (Run 44880160990, aktualisiert 2026-11-21 07:27:01 UTC, `/health/live` um 07:26:54 UTC). Die Diagnose meldete Alembic-Revision `008`. Q2P-Grants und `QUOTER_ENABLED` sind nicht bestätigt, R005 bleibt offen. `.runtime/last-deploy-sha` auf `main` bleibt `6ccc036` und hinkt Actions hinterher. `.env.example` lässt den Dry-Run-Guard offen; der Deploy ist am Host-Guard nicht abgebrochen. Dieser Lauf hat die Host-Datei nicht gelesen.
- **Akzeptanz:** `collector` und `api` laufen im Compose-Stack, `/health/live` ist grün, `SL_DRY_RUN` bleibt auf dem DEV-Host `true`, bis ein Operator es bewusst umstellt.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher`, `KafkaPublisher` und `RecordingPublisher` liegen auf `origin/main` (R002, #188). `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Letzter erfolgreicher PROD-Leseprobe bleibt FA 38574 vom 2026-11-07. R001 (Health/Diagnose für `POSTGRES_DSN_PROD` und Alembic-Revision) ist seit #188 auf `main`. Eigene PG-DB bzw. Mode-Prefix auf dem Host bleiben offen. Kein neuer PROD-Leselauf in diesem Abgleich.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. `SL_DRY_RUN` bleibt unberührt.

### G10 – Quoter Deep-Link in Promise

- **Status:** in Arbeit (BDX-Seite geliefert)
- **Ziel:** Aus der Promise-Akte fehlende Technik/Kalkulation im Quoter klären und mit `return_url` zurückkehren → Recompute.
- **Stand:** R003 ist auf `origin/main` (#188): `QUOTER_UI_URL`, `build_quoter_work_url`, API `POST …/quoter-link`, Promise-UI. Das Quoter-Repo muss `/work` und den Fertig-Redirect noch liefern (`docs/QUOTER_DEEP_LINK.md`).
- **Akzeptanz:** Gap „Im Quoter klären“ öffnet Deep Link; nach Save kehrt der Browser zur Akte zurück und Gaps/Evidence aktualisieren sich.

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
- **Akzeptanz:** Code und die Dry-Run-Prüfung auf DEV sind da. Echte Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run-Guard in der Host-Umgebung öffnet. `.env.example` lässt diesen Guard offen. Dieser Lauf lässt die Datei unverändert.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
