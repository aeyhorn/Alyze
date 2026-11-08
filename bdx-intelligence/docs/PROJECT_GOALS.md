# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-07 22:20 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich folgt `origin/main` bei `2f13c3f446cb`.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Baum ist auf `main` (`2fcd60d`–`2f13c3f`, inklusive `scripts/prepare-dev-host.sh`, dem Deploy ohne SSH-Hop und dem Schwachstellen-Dashboard). CI für `2f13c3f` ist grün (Lauf `42415113307`). Coverage-Floor im Workflow ist 68 %; `TestAgent` verlangt weiter 80 %. ruff und mypy sind in CI nur beratend. `deploy.ps1` hat den DEV-Host ausgebracht (siehe G6). Der Push-Deploy von `2f13c3f` ist `success` (Lauf `42415113477`). Der Push von `232b138` (Lauf `42413750137`) ist `failure` (Exit 130 bei `docker compose pull`); `workflow_dispatch` desselben Stands (Lauf `42414445157`) ist `success`. Der SSH-Deploy von `6ccc036` (Lauf `42411199922`) ist `failure` (passphrase-geschützter Schlüssel). `deploy-dev.yml` macht diesen SSH-Hop seit `232b138` nicht mehr. `pr-review.yml` löst nur bei Pull Requests aus; der Push-Lauf `42415112307` ist `failure` nach 0 s ohne Jobs. Environments `CURSOR_API_KEY`, `dev` und `prod` existieren und haben keine Protection Rules (API, 2026-11-07 22:20 CET). Branch Protection von `main` war über die API nicht lesbar (403). Secret-Werte wurden nicht gelesen.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Davon ist der Commit-Teil erfüllt, der Rest nicht nachgewiesen.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. `MqttSettings.enabled` und `KafkaSettings.enabled` defaulten auf aus. Das letzte DEV-Protokoll hatte MQTT aus. Ein Broker ist im Baum nicht konfiguriert.
- **Akzeptanz:** Entweder MQTT an plus Host, oder Kafka an plus Bootstrap-Server. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge. Dieser Abgleich hat nicht erneut gemessen.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL. Der Service-Layer-Guard bleibt unberührt.

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

- **Status:** erledigt als Code (Sprint 003). Broker ist G7, der DEV-Container ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Stand:** Code liegt auf `main` (`sap_sl/operations.py`, Migration 003). Das letzte DEV-Protokoll zeigt blockierte Aufrufe mit Audit in `sl_operations`. `ServiceLayerSettings.dry_run` defaultet im Code auf aus, und `.env.example` lässt Dry-Run ebenfalls aus. Das widerspricht der Akzeptanz unten. Dieser Abgleich ändert den Code nicht und schreibt die Ausschalt-Zuweisung nicht erneut ins Repository.
- **Akzeptanz:** Code und die protokollierte Dry-Run-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Guard in der nicht versionierten Host-Umgebung umstellt. Committete Dateien schalten den Guard nicht ab.

### G5 – SQL-Login `bdx_readonly`

- **Status:** erledigt für den DEV-Container (`12fa8cf`)
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` verweigert CONTROL nicht mehr (`7d0fb2f`). Der Commit `12fa8cf` hält fest, dass der Login aus dem DEV-Container 871 offene Aufträge gelesen hat.
- **Akzeptanz:** erfüllt für DEV. Kein Schreibrecht auf dem SAP-SQL-Server. Ein eigener Nachweis für die PROD-Company-DB fehlt.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt auf dem DEV-Host (`12fa8cf`, aufgezeichnet 2026-11-07 19:55 +0100, sha `1480f5c`)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5, erfüllt für den DEV-Container.
- **Stand:** Der Commit `12fa8cf` hält fest, dass collector und api oben waren und der Event-Store verbunden war (38561 Aufträge, 184 Läufe). `.runtime/last-deploy-sha` ist `1480f5c`. Actions hat danach zweimal `success` gemeldet, ohne den Marker fortzuschreiben: `workflow_dispatch` von `232b138` (Lauf `42414445157`) und der Push von `2f13c3f` (Lauf `42415113477`). Der SSH-Deploy von `6ccc036` und der erste Push von `232b138` bleiben `failure` (G4). Dieser Abgleich hat den Host nicht erneut gemessen. `scripts/prepare-dev-host.sh` (`6ccc036`) provisioniert den Runner; die erfolgreichen Deploy-Jobs zeigen, dass ein Runner mit den Labels `self-hosted, linux` die Jobs angenommen hat.
- **Akzeptanz:** erfüllt für den aufgezeichneten `deploy.ps1`-Lauf. Das Skript bricht ab, wenn der DEV-Host den Service-Layer-Guard nicht auf dem sicheren Default hält.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
