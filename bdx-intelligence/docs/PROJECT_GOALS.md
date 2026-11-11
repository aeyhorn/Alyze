# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-11 21:40 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`cd6440f`). Nichts davon ist uncommitted. CI `42768023614` und Deploy to DEV `42768023481` waren am 2026-11-10 grün. Ruff und mypy sind in `ci.yml` noch advisory, das Coverage-Gate steht auf 68. `prod` existiert ohne Protection Rules. Die Branch-Protection-API antwortet mit HTTP 403. Nightly `43003787661` (2026-11-11 10:27 UTC, SHA `cd6440f`) ist nach etwa 8 Sekunden rot; das Job-Log war in diesem Abgleich nicht lesbar. Derselbe Workflow ist auch `42802489315` (2026-11-10) und `42605350114` (2026-11-09) fehlgeschlagen. `pr-review.yml` hat auf dem Schritt „Fetch PR diff“ zwei `env`-Blöcke; Lauf `42768021714` (`cd6440f`) endet in 0s, ebenso `43088715108` (2026-11-11 19:36 UTC, SHA `9fd62e3`, ohne Jobs). Abgleich 2026-11-11 21:40 UTC+1: kein neuer Commit auf `origin/main`, kein neuer Deploy. CI `43088728363` auf dem Doku-Stand `9fd62e3` ist grün. Auto-merge `43088728203` ist durchgelaufen; PR #91 hat kein `trivial`-Label und bleibt offen. `origin/chore/ruff-cleanup-20261108` ist 1 Commit voraus und 11 zurück, ohne Pull Request.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Ob der Login auf LDSAP `bdx_readonly` heißt, ist in diesem Abgleich nicht geprüft. Der DEV-Deploy vom 2026-11-10 ist grün; der Workflow nennt den SQL-Login nicht.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Nicht gestartet. Die PROD-Einzelprobe vom 2026-11-07 (FA 38574) ist historisch und wurde in diesem Abgleich nicht wiederholt.
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

- **Status:** erledigt als Code (Sprint 003). Deploy ist G6. Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator das Schreibflag in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 war als Voraussetzung notiert. Der Stack-Deploy ist grün; der Login-Name bleibt unter G5 offen.
- **Stand:** Deploy to DEV `42768023481` für `cd6440f` (2026-11-10 06:22 UTC) ist erfolgreich. Der Job verlangt `/health/live` mit Status 200 und bricht ab, wenn die Host-Umgebung echte Service-Layer-Schreibvorgänge freigibt. `.runtime/last-deploy-sha` ist weiterhin `6ccc036` (`2026-11-07 21:50:15 +01:00`), geschrieben von `deploy.ps1`, nicht von Actions.
- **Akzeptanz:** erfüllt für den grünen Deploy-Lauf. Echte SL-Schreibvorgänge bleiben eine bewusste Änderung auf dem Host.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
