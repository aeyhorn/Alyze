# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-10 08:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `main` (`cd6440f`, geprüft 2026-11-10 08:34 UTC+1). CI-Lauf `42768023614` ist grün; ruff und mypy bleiben advisory, das Coverage-Gate ist 68. Deploy-to-DEV `42768023481` ist grün. Die nächtliche Integration ist am 2026-11-08 und 2026-11-09 vor pytest an `gpg`/`/dev/tty` gescheitert; für 2026-11-10 gab es bis 08:34 CET keinen Lauf (Cron 03:00 UTC). Environment `prod` hat leere `protection_rules`. Branch Protection auf `main` war mit diesem Token nicht lesbar (HTTP 403).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. Deploy-Secrets reichen für den DEV-Deploy. Offen: erforderliche Reviewer auf `prod`, ein lesbarer Pflicht-Check aus `ci.yml` auf `main`, und ein nächtlicher Integrationslauf, der pytest erreicht.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Die Diagnose im DEV-Container am 2026-11-10 hat SAP gelesen (885 offene Aufträge in `DEV_SBO_LEISINGER`). Der Kontoname steht im Log nicht; `bdx_readonly` ist damit nicht bestätigt.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. Die DEV-Diagnose am 2026-11-10 meldet MQTT disabled, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. `SL_DRY_RUN` bleibt unberührt.

## Erledigt

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** Deploy-to-DEV für `cd6440f` (Lauf `42768023481`, 2026-11-10) hat den Migrate-Container ohne `Running upgrade` beendet (Schema schon auf head, Migrationen bis `008`) und `collector` sowie `api` neu erzeugt. `/health/live` war grün. Die Diagnose im Collector war vollständig (Postgres 38575 Auftragszeilen, SAP 885 offene Aufträge, 10 Maschinen, SCADA, MQTT aus). Der Lauf bricht ab, wenn die Host-`.env` Live-Schreibvorgänge einschaltet; dieser Lauf ist nicht abgebrochen. Die Marker `.runtime/last-deploy-sha` und `.runtime/last-deploy-at` schreibt `deploy.ps1`; sie stehen noch auf `6ccc036` / 2026-11-07 21:50.
- **Abhängigkeit:** G5 bleibt offen, blockiert den laufenden Stack aber nicht mehr: der Container liest SAP.
- **Akzeptanz:** erfüllt für den Actions-Deploy von `cd6440f`. Live-Schreibvorgänge bleiben aus, bis ein Operator sie in der echten Host-`.env` einschaltet.

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
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator `SL_DRY_RUN` in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
