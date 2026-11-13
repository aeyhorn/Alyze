# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-13 11:37 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `origin/main` (`cd6440f`). CI-Gate ist `--cov-fail-under=68`; ruff und mypy sind advisory (Lauf `43402940008`, 10:38 UTC+1, PR #125: mypy 68 Fehler in 14 Dateien, ruff 582 Fehler, beide Schritte Exit 1, Jobs grün; pytest 179 passed, TOTAL 74 %). Environment `prod` hat keine Protection Rules. Repository-Rulesets: 0. Branch Protection für `main` und die Secret-Liste antworteten 403; Werte wurden nicht gelesen. Die nächtlichen Integrationsläufe 2026-11-08 bis 2026-11-12 sterben in „Install ODBC Driver 18“ (`gpg` ohne `/dev/tty`, danach `curl: Failed writing body`), vor pytest. Am 2026-11-13 11:37 (UTC+1) gibt es noch keinen Lauf dieses Tages. Docs-PR-CI war von 01:36 bis 06:38 (UTC+1) rot und ist seit 07:35 wieder grün. Der Push-Lauf auf `main` vom 2026-11-10 bleibt grün. `pr-review.yml` hat im Schritt „Fetch PR diff“ zwei `env`-Schlüssel; Push-Läufe enden ohne Jobs (zuletzt `43402916981`, 10:37 UTC+1, Jobliste leer).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt (erfüllt). Secrets gesetzt (nicht geprüft). `prod` hat erforderliche Reviewer (Rules leer, offen). `main` verlangt den Check aus `ci.yml` (nicht prüfbar, 403).

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist im Repo. DENY CONTROL ist entfernt, weil es CONNECT blockiert hat (Fehler 18456, state 38). Ob der Login auf LDSAP existiert und der Collector ihn nutzt, ist aus Git nicht sichtbar.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind implementiert. `MQTT_ENABLED=false`, kein Broker konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge. `deploy-prod.yml` hat keine Läufe.
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

- **Status:** erledigt als Code (Sprint 003). Der DEV-Deploy ist G6. Der Broker bleibt G7.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run in der Host-Umgebung abschaltet. Committete Dateien schalten ihn nicht ab.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt (DEV)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev.yml` deployt auf dem Self-hosted-Runner dieses Hosts. Letzter grüner Lauf 2026-11-10 07:22 (UTC+1) für `cd6440f`: Migration und `/health/live`. `bdx-collect diagnose` ist im Workflow nicht fehlschlagend und belegt den SAP-Login nicht (das bleibt G5). Die Dateien `.runtime/last-deploy-*` auf `main` zeigen noch 2026-11-07 / `6ccc036`. `deploy-prod.yml` hat keine Läufe.
- **Akzeptanz:** `collector` und `api` werden im Compose-Stack neu erzeugt, `/health/live` war beim letzten Lauf grün. Der Workflow bricht ab, wenn die Host-Umgebung den Dry-Run abschaltet; der grüne Lauf hat diesen Abbruch nicht ausgelöst.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
