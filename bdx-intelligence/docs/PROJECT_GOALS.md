# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-09 12:37 (CET)
> Operativer Stand: `docs/PROJECT_STATUS.md`. Neue Wünsche: `docs/REQUIREMENTS.md`.
> Abgleich gegen `origin/main` `77b8bd2` (PR #62, Dashboard-Kopf). Parent `184a6bd` ist die Quoter-Deep-Link-Spec (PR #57). IDs `G1`–`G10` bleiben. Ein neues Ziel nur, wenn eine Anforderung keinem Ziel zugeordnet ist. Quote-to-Promise (`2796032`), die Quoter-Verdrahtung (`0de31a7`), die KPI-Engine (`283ee4b`), die Promise Platform (`1ce5fdf`), die Vision (`723f794`), die Deep-Link-Spec (`184a6bd`) und die Kopf-Navigation (`77b8bd2`) liegen auf `main` und haben keine Ziel-ID, weil `REQUIREMENTS.md` keine Zeile dafür hat. Die KPI-Engine ist nicht G7 (Broker) und nicht G10 (Schwachstellen-Dashboard). Die Deep-Link-Spec und die Kopf-Navigation sind keine neuen Ziel-IDs. Der Quoter und die Promise-UI setzen die Spec noch nicht um. Stündliche Entwürfe bis PR #61 haben die IDs neu belegt (dort ist `G5` Quote-to-Promise und die nächste ID `G12`); dieser Abgleich übernimmt das nicht.

## Aktiv

### G4 – Sprint 004 landen

- **Status:** teilweise
- **Ziel:** CI/CD, Quality-Gates, Integrationstests und den HOTL-Workflow auf `main` haben, mit Secrets, `prod`-Environment und Branch Protection.
- **Stand:** Workflows, Agents, Skripte und Prompts liegen auf `main` (`184a6bd`). Ruff und mypy sind in `ci.yml` nur beratend. Das Coverage-Gate ist 68 %, nicht 80 %. Environments `dev`, `prod` und `CURSOR_API_KEY` existieren. Branch Protection war mit diesem Token nicht lesbar (HTTP 403). `pr-review.yml` ist beim Push von `723f794` wieder in 0 s ohne Jobs fehlgeschlagen (Lauf 42518586380), ebenso bei `1ce5fdf` (42518203439), `0de31a7` (42516284484), `283ee4b` (42499221888), `2796032` (42498523815), `6710fdc` (42464603622), `6850feb` (42420692054), `2f13c3f` und `184a6bd` (42585798231). Der Schritt „Fetch PR diff“ hat zwei `env:`-Schlüssel. Die nächtliche Integration (Lauf 42469243262, `6710fdc`) stoppt beim ODBC-Install (`gpg` ohne TTY, Exit 2), bevor pytest läuft. Lint-Cleanup-Lauf 42473962358 hat `chore/ruff-cleanup-20261108` gepusht und dann abgebrochen, weil das Label `trivial` fehlt; der Branch-Tip ist weiterhin `57411b2`, es gibt keinen PR. CI-Lauf 42518587593 für `723f794` ist grün, ebenso 42518204806 für `1ce5fdf` und 42585799915 für `184a6bd`. Deploy-to-DEV-Lauf 42516285446 für `0de31a7` ist im Migrate-Schritt fehlgeschlagen, weil Alembic-Revision `005` zweimal vorkam. `1ce5fdf` hat die Quoter-Migration nach `008` verschoben. Lauf 42518204744 hat `006 -> 007` und `007 -> 008` angewendet und ist grün. Lauf 42518587710 für `723f794` ist ebenfalls grün, ohne weitere Migration. Dieser Abgleich ändert weder den Workflow noch die Migrationen. Push von `77b8bd2`: CI-Lauf [42606020020](https://github.com/aeyhorn/Alyze/actions/runs/42606020020) ist grün, Deploy-to-DEV-Lauf [42606020404](https://github.com/aeyhorn/Alyze/actions/runs/42606020404) ist grün, `pr-review.yml` [42606017920](https://github.com/aeyhorn/Alyze/actions/runs/42606017920) ist wieder in 0 s ohne Jobs fehlgeschlagen. Schedule-Lauf [42605350114](https://github.com/aeyhorn/Alyze/actions/runs/42605350114) (2026-11-09 11:59 CET, SHA `184a6bd`) ist wieder im ODBC-Install an `gpg` ohne TTY gescheitert (Exit 2), bevor pytest läuft. `origin/main` ist seit 12:04 CET unverändert. Der Zielstatus bleibt teilweise.
- **Akzeptanz:** Sprint-004-Baum ist committet und auf `main` — erfüllt. Offen: nächtliche Integrations-Secrets, bestätigte Reviewer auf `prod`, Branch Protection mit dem Check aus `ci.yml`, Ruff/mypy wieder blockierend, Coverage-Ratchet.

### G7 – MQTT- oder Kafka-Broker

- **Status:** offen
- **Ziel:** Gebaute Publisher gegen einen echten Broker laufen lassen.
- **Stand:** `MqttPublisher` und `KafkaPublisher` sind auf `main`. Die Publisher-Settings defaulten auf aus. Ein Broker ist im Baum nicht konfiguriert.
- **Akzeptanz:** Entweder `MQTT_ENABLED=true` plus `MQTT_HOST`, oder `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`. Events verlassen den Collector, Fehler im Broker brechen den Collector nicht.

### G8 – PROD-Lesebetrieb

- **Status:** offen
- **Ziel:** Collector read-only gegen `SBO_LEISINGER`, ohne DEV- und PROD-Daten in `order_state` zu mischen.
- **Stand:** Einzelaufträge sind probeweise gelesen (FA 38574, letzter manueller Check). DEV hinkt PROD hinterher, deshalb fehlt auf DEV die Maschinen-Verknüpfung für laufende Aufträge.
- **Akzeptanz:** Eigene Postgres-Datenbank oder mode-prefixed `source_key`. Keine Schreibzugriffe auf SAP MSSQL.

## Erledigt

### G5 – SQL-Login `bdx_readonly`

- **Status:** erledigt für den DEV-Container (`12fa8cf`)
- **Ziel:** Read-only SQL-Login auf LDSAP, damit der Collector ohne Windows-Integrated-Auth im Container läuft.
- **Stand:** `docs/sql/create_bdx_readonly.sql` verweigert CONTROL nicht mehr (`7d0fb2f`). Der Commit `12fa8cf` hält fest, dass der Login aus dem DEV-Container 871 offene Aufträge gelesen hat. Dieser Abgleich hat LDSAP nicht erneut geprüft.
- **Akzeptanz:** erfüllt für DEV. Kein Schreibrecht auf dem SAP-SQL-Server. Ein eigener Nachweis für die PROD-Company-DB fehlt.

### G6 – Container-Deploy auf dem Docker-Host

- **Status:** erledigt auf dem DEV-Host (`12fa8cf`, aufgezeichnet 2026-11-07 19:55 +0100, sha `1480f5c`)
- **Ziel:** `docker-compose.yml` auf 192.168.82.33 betreiben. Postgres läuft dort bereits.
- **Abhängigkeit:** G5, erfüllt für den DEV-Container.
- **Stand:** `12fa8cf` hält fest, dass collector und api oben waren und der Event-Store verbunden war (38561 Aufträge, 184 Läufe). `.runtime/last-deploy-sha` im Git ist weiterhin `1480f5c`. Seit `232b138` deployt Actions direkt auf dem Self-hosted-Runner. Lauf `42415113477` für `2f13c3f` ist `success` und prüft `/health/live`. Lauf `42420693125` für `6850feb` ist seit 2026-11-08 09:39 (UTC+1) ebenfalls `success` (der Host-Job hing seit 2026-11-07 23:36 in der Queue). Lauf `42464604728` für `6710fdc` ist `success` (Host-Job 09:52 UTC+1). Lauf `42498525158` für `2796032` ist `success` (Host-Job 17:13 UTC+1) und hat Alembic `003 -> 004` angewendet. Lauf `42499223057` für `283ee4b` ist `success` (17:21 CET) und hat Alembic `004 -> 005` und `005 -> 006` angewendet, danach `/health/live`. Lauf `42516285446` für `0de31a7` hat das Image gepusht und ist im Migrate-Schritt fehlgeschlagen (Revision `005` doppelt, mehrere Heads, Exit 255), bevor `up -d --force-recreate` lief. Lauf `42518204744` für `1ce5fdf` ist `success` (21:06 CET) und hat Alembic `006 -> 007` und `007 -> 008` angewendet, danach `/health/live`. Lauf `42518587710` für `723f794` ist `success` (21:10 CET); die Migration fand nichts weiter. Lauf `42585799962` für `184a6bd` ist `success` (09:27 CET); das Migrate-Log zeigt keinen `Running upgrade`. Lauf `42606020404` für `77b8bd2` ist `success` (12:06 CET); das Migrate-Log zeigt `PostgresqlImpl` und keinen `Running upgrade`. Der letzte erfolgreiche DEV-Deploy ist damit `42606020404`. Der Host wurde nicht inspiziert. Shopfloor-Zahlen stammen weiter vom 2026-11-07.
- **Akzeptanz:** erfüllt für den aufgezeichneten `deploy.ps1`-Lauf und für den späteren Actions-Lauf. Das Skript bricht ab, wenn der DEV-Host den Service-Layer-Guard nicht auf dem sicheren Default hält.

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
- **Stand:** Code liegt auf `main` (`sap_sl/operations.py`, Migration 003). Das letzte DEV-Protokoll zeigt blockierte Aufrufe mit Audit in `sl_operations`. `ServiceLayerSettings.dry_run` defaultet im Code auf aus, und `.env.example` lässt Dry-Run ebenfalls aus. Das widerspricht der Akzeptanz unten. Dieser Abgleich ändert den Code nicht und schreibt die Ausschalt-Zuweisung nicht erneut ins Repository. `77b8bd2` (PR #62) hält die Links Betrieb, Schwachstellen, Q2P und Promise im Kopf von Dashboard und Schwachstellen sichtbar. Das bleibt G3 und ist kein neues Ziel.
- **Akzeptanz:** Code und die protokollierte Dry-Run-Prüfung auf DEV sind da. Echte SL-Schreibvorgänge bleiben aus, bis ein Operator den Guard in der nicht versionierten Host-Umgebung umstellt. Committete Dateien sollen den Guard nicht abschalten; der Default und die Beispieldatei tun das derzeit doch.

### G10 – Schwachstellen-Analyse

- **Status:** erledigt (PR #6 `2f13c3f`, Darstellung PR #12 `6850feb`, beides auf `main`)
- **Ziel:** Prozessschwächen aus dem Event-Store in einem Dashboard zeigen.
- **Stand:** `GET /api/v1/analytics/weaknesses` und `GET /analytics`. Neun Tests in `tests/test_analytics.py` (elf `def test_`, davon zwei Fixtures). PR #12 ändert nur `analytics.html`: Delta-Chips für Planänderungen, Balken für Verzug und Festgefahren, KPI-Kontext, Stillstandsdauer je Maschine, deutsche Event-Labels, Status-Pills. Keine neuen Tests. CI für `6850feb`, `6710fdc` und `2796032` ist grün. Der DEV-Deploy von `6850feb` (Lauf 42420693125), von `6710fdc` (Lauf 42464604728) und von `2796032` (Lauf 42498525158) ist `success`.
- **Abgrenzung:** Die KPI-Engine, die Beschaffungs-KPIs und die Diagnose liegen auf `main` (`283ee4b`, PR #5, Squash). Dafür gibt es weiter kein Ziel, solange keine Zeile in `REQUIREMENTS.md` steht. Migration `004` bleibt `004_q2p_inquiries.py`. Die Analytics-Tabellen sind `005_analytics_tables`, die Diagnose-Tabellen `006`. Die Quoter-Spalten liegen seit `1ce5fdf` in `008_q2p_quoter_fields.py` und revidieren `007`. Die doppelte Revisions-ID `005` ist auf `main` weg. Quote-to-Promise, die Quoter-Verdrahtung, die Promise Platform (`1ce5fdf`, PR #41) und die Vision (`723f794`, PR #40) haben ebenfalls keine Ziel-ID. Die Darstellung der Schwachstellen bleibt G10. Die Deep-Link-Spec (`184a6bd`, PR #57) hat keine Ziel-ID. CI für `184a6bd` (Lauf 42585799915) ist grün. Der DEV-Deploy (Lauf 42585799962) ist `success`. `77b8bd2` (PR #62) ändert nur die Köpfe von `dashboard.html` und `analytics.html` (vier Links, Umbruch). Betrieb stand auf der Schwachstellen-Seite schon. Keine neuen Tests. CI-Lauf 42606020020 und DEV-Deploy 42606020404 sind `success`. Das ist weiterhin G10, keine neue Ziel-ID.

## Geparkt

### G9 – Mehrere SAP-Firmen, SSO/SCIM

- **Status:** geparkt
- **Ziel:** Mehrere Company-DBs und SSO/SCIM. In `PROJECT_STATUS` als TBD geführt.
- **Akzeptanz:** noch nicht festgelegt. Neue Anforderungen dazu kommen nach `REQUIREMENTS.md`.
