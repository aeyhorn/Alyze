# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-07 21:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich folgt `origin/main` bei `6ccc036`.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Baum ist auf `main` (`2fcd60d`–`6ccc036`). CI für `6ccc036` ist grün (Run 42411199913). Coverage-Floor im Workflow ist 68 % (gemessen ~69.35 %); `TestAgent` verlangt weiter 80 %. ruff und mypy sind in CI nur beratend. `deploy.ps1` hat den DEV-Host ausgebracht. `scripts/prepare-dev-host.sh` liegt auf `main` (`6ccc036`) und ist dort nicht als ausgeführt nachgewiesen: der Actions-Deploy für `6ccc036` (Run 42411199922) ist pending und hat keine Jobs. Der Lauf für `1e38a68` (42405166649) wurde abgebrochen. Das Environment `prod` hat keine Protection Rules. Secret-Namen und Branch Protection waren über die API nicht lesbar (403).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. `CURSOR_API_KEY`, Deploy-Secrets und die nächtlichen Integrations-Secrets sind gesetzt. `prod` hat erforderliche Reviewer. `main` verlangt den Check aus `ci.yml`. Davon ist der Commit-Teil erfüllt, der Rest nicht nachgewiesen.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
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
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Guard in der echten Host-`.env` umstellt. Committete Dateien schalten den Guard nicht ab.

### G5 – SQL-Login `bdx_readonly`

- **Status:** erledigt für den DEV-Container (`12fa8cf`)
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` verweigert CONTROL nicht mehr (`7d0fb2f`). Der Deploy-Commit hält fest, dass der Login aus dem DEV-Container 871 offene Aufträge gelesen hat.
- **Akzeptanz:** erfüllt für DEV. Kein Schreibrecht auf dem SAP-SQL-Server. Ein eigener Nachweis für die PROD-Company-DB fehlt.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt auf dem DEV-Host (`12fa8cf`, aufgezeichnet 2026-11-07 19:55 UTC+1, sha `1480f5c`)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5, erfüllt für den DEV-Container.
- **Stand:** collector und api waren laut Deploy-Commit oben, der Event-Store verbunden (38561 Aufträge, 184 Läufe). Der Actions-SSH-Deploy ist davon unabhängig und noch pending (gehört zu G4).
- **Akzeptanz:** erfüllt für den aufgezeichneten `deploy.ps1`-Lauf. Das Skript bricht ab, wenn der DEV-Host den Service-Layer-Guard nicht auf dem sicheren Default hält.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
