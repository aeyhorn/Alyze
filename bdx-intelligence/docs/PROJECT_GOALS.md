# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-12 20:34 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Dieser Abgleich hält den Stand gegen `origin/main` (`cd6440f`).

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`cd6440f`). Push-CI dieses Stands ist grün (Actions `42768023614`); Ruff und mypy bleiben advisory, das Coverage-Gate liegt bei 68 %. DEV-Deploy läuft über den Self-hosted-Runner, nicht über SSH, zuletzt grün für `cd6440f` (2026-11-10 07:22 UTC+1, Actions `42768023481`). Die nächtliche Integration scheitert vom 2026-11-08 bis 2026-11-12 im Schritt `Install ODBC Driver 18`, zuletzt Actions `43202844646` (`gpg` öffnet `/dev/tty` nicht, Exit 2, vor pytest). `prod` existiert und hat keine Protection-Rules (Environments-API, erneut 2026-11-12 20:34 UTC+1). Die Ruleset-Liste ist leer. Branch Protection und die Actions-Secret-Liste waren in diesem Lauf nicht lesbar (403). `pr-review.yml` hat im Schritt `Fetch PR diff` zwei `env`-Schlüssel; Pushes zeichnen einen fehlgeschlagenen Lauf dieser Workflow-Datei mit Dauer 0s auf.
- **Akzeptanz:** Baum auf `main` ist erfüllt. Offen: Secrets bestätigt, `prod` mit erforderlichen Reviewern, `main` verlangt den Check aus `ci.yml`, nächtliche Integration läuft bis pytest.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `7d0fb2f` hält fest, dass der Login existiert hat und `DENY CONTROL` die Verbindung blockierte. Die Skripte `docs/sql/create_bdx_readonly.sql` und `docs/sql/reset_bdx_readonly.sql` liegen auf `main`. Ob das Reset auf LDSAP gelaufen ist, steht nicht im Git. Dieser Lauf hat den Login nicht geprüft.
- **Akzeptanz:** Login angelegt ist im Commit belegt. Offen: Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
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

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt (DEV-Deploy von `cd6440f` erfolgreich, 2026-11-10 07:22 UTC+1)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5 war als Voraussetzung notiert. Der Deploy läuft; die Login-Abnahme von G5 ist davon getrennt noch offen.
- **Akzeptanz:** `deploy-dev.yml` zieht das Image, führt `alembic upgrade head` aus und startet `collector` und `api` neu. Der Lauf von `cd6440f` ist grün, und der Job bricht ab, wenn `/health/live` nicht grün ist. Derselbe Job bricht ab, wenn die Host-`.env` den Dry-Run ausschaltet. Dieser Lauf hat den Host nicht selbst abgefragt.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Broker bleibt G7. Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run in der Host-`.env` außerhalb von Git ausschaltet. `bdx-intelligence/.env.example` Zeile 24 schaltet den Dry-Run aus; die Regel verlangt, dass committete Dateien ihn an lassen. Dieser Abgleich ändert die Beispieldatei nicht.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
