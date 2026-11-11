# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-11 20:35 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`cd6440f`). CI `42768023614` und Deploy to DEV `42768023481` waren am 2026-11-10 grün. Ruff und mypy sind in `ci.yml` noch advisory, das Coverage-Gate steht auf 68. `prod` existiert ohne Protection Rules. Branch Protection für `main` antwortet mit HTTP 403, Secrets ebenfalls. Die nächtlichen Läufe `42469243262` (2026-11-08 09:55 UTC), `42605350114` (2026-11-09 10:59 UTC), `42802489315` (2026-11-10 10:50 UTC) und `43003787661` (2026-11-11 10:27 UTC, SHA `cd6440f`) scheitern in `gpg --dearmor` an fehlendem `/dev/tty`, bevor pytest startet. `pr-review.yml` hat auf dem Schritt „Fetch PR diff“ zwei `env`-Blöcke; Lauf `42768021714` (`cd6440f`) endet in 0s ohne Jobs und ohne Log, ebenso spätere Pushes des Doku-Branches (zuletzt `43079578457`, 2026-11-11 18:37:43 UTC, SHA `09714dc`, ohne Jobs). Abgleich 2026-11-11 20:35 UTC+1: kein neuer Commit auf `origin/main`, kein neuer Deploy. Der Nightly-Lauf für 2026-11-11 ist `43003787661` (10:27 UTC), wieder vor pytest rot. CI des Doku-Branches `43079587870` (2026-11-11 18:37 UTC, `09714dc`) ist grün: 179 passed, 8 deselected, Coverage 73.95%. Docker, ruff und mypy in dem Lauf sind grün. Der vorherige grüne Lauf war `43069381987` (`58c2e62`, 2026-11-11 17:33 UTC). `42966672784` (`6c0c6f7`, 2026-11-11 05:34 UTC) war auf demselben Produktbaum rot (`test_machine_utilization_with_calendar`, 178 passed). Die zwei Lateness-Tests, die auf `c798b9e` (`42932824913`) fehlschlugen, bleiben grün. Auto-merge `43079587968` ist grün und hat nicht gemergt (Log: `No 'trivial' label — skipping auto-merge.`). `prod` weiter ohne Protection Rules, Branch Protection und Secrets weiter HTTP 403.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Der Collector-Container liest `DEV_SBO_LEISINGER` (885 offene Aufträge, Diagnose im Deploy-Lauf `42768023481`, 2026-11-10 06:24 UTC). Die Diagnose nennt den Login-Namen nicht, deshalb ist nicht belegt, dass es `bdx_readonly` ist.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Nicht gestartet. Die Diagnose vom 2026-11-10 liest nur `DEV_SBO_LEISINGER`. Die PROD-Einzelprobe vom 2026-11-07 (FA 38574) ist historisch und wurde nicht wiederholt.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. `SL_DRY_RUN` bleibt unberührt.

## Erledigt

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 war als Voraussetzung notiert. Der Stack läuft; der Login-Name bleibt unter G5 offen.
- **Stand:** Deploy to DEV `42768023481` für `cd6440f` (2026-11-10 06:24 UTC) hat `collector` und `api` neu erstellt. `/health/live` antwortete `{"alive":true}`. `bdx-collect diagnose` lief im Collector. Die Migration endete ohne `Running upgrade` (Schema schon auf dem Head des Images, im Repo `008`). `.runtime/last-deploy-sha` ist weiterhin `6ccc036` und `.runtime/last-deploy-at` `2026-11-07 21:50:15 +01:00`, geschrieben von `deploy.ps1`, nicht von Actions. Der DEV-Deploy bricht ab, wenn die Host-Umgebung echte Service-Layer-Schreibvorgänge freigibt; dieser Lauf hat die Prüfung bestanden.
- **Akzeptanz:** erfüllt für den laufenden Compose-Stack und den grünen Healthcheck. Echte SL-Schreibvorgänge bleiben eine bewusste Änderung auf dem Host.

### G1 – SAP Read-only Collector

- **Status:** erledigt (Sprint 001, auf DEV in Betrieb)
- **Ziel:** Read-only-Verbindung zu SAP Business One, idempotente Änderungserkennung, REST und CLI.
- **Akzeptanz:** erfüllt. MSSQL-Kanal bleibt read-only.

### G2 – BDE, Maschinen, inkrementelles Lesen

- **Status:** erledigt (Sprint 002, auf DEV in Betrieb)
- **Ziel:** Inkrementeller SAP-Lesen, Maschinenzustand aus XMSK, BDE aus SCADA-Telemetrie.
- **Akzeptanz:** erfüllt. Statuscodes `P`/`R`/`L`/`C` bleiben wie gegen OWOR geprüft.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Deploy ist G6. Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator `SL_DRY_RUN` in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
