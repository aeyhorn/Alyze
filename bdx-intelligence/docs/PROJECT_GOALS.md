# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-22 10:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`71e8726`, 2026-11-21 08:25 +01:00, inklusive #188 und #190). Produkt-CI 44880160970 ist grün: 183 passed, 8 deselected, 1 warning in 5,72 s, 6 093 Statements, 1 627 missed, 73,30 %, Gate 68 %. Ruff und mypy bleiben advisory. DEV-Deploy 44880160990 auf demselben SHA ist grün. Docs-CI von `c4d0a13` (PR #192, 45003548761) ist grün auf einem reinen Doku-Diff gegen `71e8726` (183 passed, 5,68 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44998963145 auf `2a26ffd` (183 passed, 7,50 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44994514887 auf `6df703b` (183 passed, 4,30 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44990014977 auf `c1f1daa` (183 passed, 7,94 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44985839360 auf `970c53a` (183 passed, 7,58 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44981374174 auf `9bf9e2f` (183 passed, 4,50 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44976859835 auf `cf8a03f` (183 passed, 7,34 s, 73,30 %). Der vorherige grüne Docs-CI bleibt 44972375698 auf `e6bae14` (183 passed, 6,10 s, 73,30 %). Der vorherige rote Docs-CI bleibt 44967452019 auf `164505f` (2 failed, 181 passed, 7,33 s, 73,05 %). Der grüne Docs-CI davor bleibt 44962787640 auf `89cd6c2` (183 passed, 7,27 s, 73,30 %). Dieser neue Commit auf `sync/status-20261122` hat noch kein CI-Ergebnis. Branch-Ressource `main` meldet `protected: false` (SHA `71e8726`, Antwort 2026-11-22 09:33:01 GMT); Rulesets Länge 0 (Antwort 09:33:02 GMT, Body `[]`); Environments ohne Protection Rules (Antwort 09:33:02 GMT). Branch-Protection-Endpunkt HTTP 403 (2026-11-22 09:32:23 GMT), Secret-Liste HTTP 403 (09:32:24 GMT). Nightly 44895693730 (2026-11-21 10:43 UTC, head `71e8726`) scheitert weiter bei „Install ODBC Driver 18“; der Lauf davor bleibt 44723784538. Beim Abgleich um 10:34 UTC+1 (09:34 UTC), nach dem Slot 03:00 UTC, ist kein neuerer Nightly-Lauf erschienen (`integration.yml` total_count 14). `pr-review.yml` startet auf Push null Jobs; der jüngste ist 45003544572 (`c4d0a13`, 08:35:42 UTC, null Jobs). Davor bleibt 44998958636 (`2a26ffd`, 07:35:48 UTC). Abgleich 2026-11-22 10:34 UTC+1.
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
