# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-16 06:35 (UTC+1)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> IDs bleiben stabil. Der Zeitstempel oben ist der letzte Abgleich mit `origin/main`.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** in Arbeit
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand (Abgleich 2026-11-16 gegen `origin/main` `cd6440f`):** Workflows, Agents, Skripte und Prompts liegen auf `main`. CI auf diesem Commit ist grün. Ruff und mypy bleiben advisory, das Coverage-Gate steht auf 68. `Deploy to DEV` läuft ohne SSH auf dem Self-Hosted-Runner. Die nächtliche Integration scheitert im Schritt „Install ODBC Driver 18“ (letzter Lauf 2026-11-15). Das Environment `prod` hat keine Protection-Rules. Branch Protection auf `main` war mit diesem Token nicht lesbar (HTTP 403). `origin/chore/ruff-cleanup-20261108` und `origin/chore/ruff-cleanup-20261115` sind nicht gemergt und haben keinen PR.
- **Akzeptanz:** Sprint-004-Baum ist committet und gemergt (erfüllt). `prod` hat erforderliche Reviewer (offen). `main` verlangt den Check aus `ci.yml` (hier nicht geprüft). Nächtliche Integration grün (offen). Lint-Cleanup gemergt (offen).

### G5 – SQL-Login `bdx_readonly`

- **Status:** offen
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** Skript `docs/sql/create_bdx_readonly.sql` liegt auf `main`. `7d0fb2f` hat ein `DENY CONTROL` entfernt, das `CONNECT` blockierte. Ob der Login auf LDSAP existiert, ist in diesem Lauf nicht geprüft. Der grüne DEV-Deploy hängt nicht an dieser Prüfung.
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

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt (DEV, laut Actions)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Stand:** `deploy-dev.yml` baut das Image, deployed auf dem Self-Hosted-Runner auf dem DEV-Host und verlangt `/health/live`. Letzter grüner Lauf: 2026-11-10 06:22 UTC für `cd6440f`. Der Job bricht ab, wenn die Host-Umgebung den Dry-Run abschaltet. Die Datei `.runtime/last-deploy-sha` hinkt hinterher (`6ccc036`, 2026-11-07 21:50 +01:00). G5 bleibt davon unabhängig offen.
- **Akzeptanz:** erfüllt für den letzten grünen DEV-Lauf. Ein Operator stellt den Dry-Run auf dem Host nur bewusst um. Committete Dateien schalten ihn nicht ab.

### G3 – Publishing, Dashboard, Write-back

- **Status:** erledigt als Code (Sprint 003). Der Broker bleibt G7. Der DEV-Deploy ist G6.
- **Ziel:** Events publizieren, Dashboard, Service-Layer-Write-back mit Audit.
- **Akzeptanz:** Code und DRY_RUN-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator `SL_DRY_RUN` in der echten `.env` setzt. Committete Dateien setzen das Flag nie auf `false`.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
