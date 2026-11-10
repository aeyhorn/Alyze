# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-10 06:37 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Dieser erste Abgleich übernimmt den Stand aus `PROJECT_STATUS.md` (Stand 2026-11-07 19:51 UTC+1). IDs bleiben stabil.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Der Sprint-004-Baum liegt auf `origin/main` (`90a6593`): Workflows, Agents, Skripte, Prompts. CI-Run `42638402851` und Deploy-to-DEV `42638402840` starteten beide 2026-11-09 15:49 CET und sind grün. Ruff und mypy bleiben advisory, das Coverage-Gate steht auf 68. Die nächtliche Integration ist am 2026-11-08 und 2026-11-09 rot, bevor pytest startet (`gpg` öffnet `/dev/tty` nicht). Für 2026-11-10 ist bis 06:37 CET kein Lauf erfasst. Branch Protection auf `main` war nicht lesbar (403). Das Environment `prod` hat in der API keine Protection-Rules. Die Secret-Liste war nicht lesbar (403).
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt. Secrets, erforderliche Reviewer auf `prod` und der Pflicht-Check aus `ci.yml` auf `main` sind in diesem Lauf nicht belegt. Der Baum ist auf `main`. Die übrigen Punkte bleiben offen.

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` ist fertig. Am 2026-11-07 existierte der Login auf LDSAP noch nicht. Dieser Lauf hat das nicht erneut geprüft.
- **Akzeptanz:** Login angelegt, Collector verbindet sich damit read-only. Kein Schreibrecht auf dem SAP-SQL-Server.

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

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Broker bleibt G7. Der Container-Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Dry-Run auf dem Host bewusst abschaltet. Committete Dateien lassen Dry-Run an.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt (letzter grüner Lauf 2026-11-09)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev.yml` baut das Image, spielt es auf dem Self-hosted-Runner des DEV-Hosts aus (kein SSH-Hop) und verlangt `/health/live`. Lauf `42638402840` für `90a6593` ist grün. G5 bleibt offen; der Deploy belegt den SQL-Login nicht.
- **Akzeptanz:** erfüllt für diesen Lauf. Ob der Stack danach durchgehend lief, steht nicht in Git. Der Deploy-Job bricht ab, wenn die Host-Umgebung Dry-Run abschaltet.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
