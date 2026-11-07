# BDX Intelligence – Requirements

> **Zuletzt abgeglichen:** 2026-11-07 21:38 (CET)
> **Git:** `main` @ `6ccc036185b5`

Anforderungen, die Code und Doku auf `main` festlegen. Wo Regel und Code auseinanderlaufen, steht das in „Abweichungen“. Dieses Dokument ändert kein Verhalten.

## Sicherheit

1. **MSSQL ist read-only.** Kein INSERT, UPDATE, DELETE oder DDL gegen den SAP-SQL-Server. `src/bdx/db/sap.py` blockiert das in SQLAlchemy. Das DB-Konto muss ebenfalls nur lesen dürfen. `docs/sql/create_bdx_readonly.sql` vergibt SELECT auf `OWOR` und `OITM` und verweigert INSERT, UPDATE, DELETE, ALTER. `DENY CONTROL` darf nicht zurück, weil CONTROL auch CONNECT umfasst.
2. **Service-Layer-Schreibvorgänge laufen durch `sap_sl/operations.py`.** Jeder Aufruf wird in `sl_operations` protokolliert (Migration 003). Operationen: Release, Close, Cancel, Report-Production.
3. **Dry-Run soll der sichere Zustand sein.** `AGENTS.md` und `.cursor/rules/bdx-conventions.mdc`: Schreibvorgänge bleiben blockiert, bis ein Operator das in der nicht versionierten Umgebung umstellt. Die Zuweisung, die Dry-Run ausschaltet, darf in keiner committeten Datei stehen. `deploy-dev.yml` bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet.
4. **PROD-Migrationen sind opt-in.** `alembic/env.py` verweigert die PROD-Event-Store-DSN, solange `ALEMBIC_ALLOW_PROD` nicht gesetzt ist. `deploy-prod.yml` setzt das nur, wenn der Mensch den Migrations-Input bestätigt. Das Opt-in-Flag wird nicht ins Repository geschrieben.
5. **Kein String-Interpolieren in SQL.** Parameterisierte `text()`-Queries mit `:param`, wie in `src/bdx/db/queries.py`.
6. **Geheimnisse nur aus der Umgebung.** `.env` ist gitignored. `.env.example` enthält Platzhalter. Keine Zugangsdaten in Code, Tests oder Doku.
7. **Die UDFs `U_Type`, `U_Priority`, `U_BDX_Machine` existieren in den Leisinger-Firmendatenbanken nicht.** `queries.py` selektiert `NULL`. Code darf nicht davon ausgehen, dass sie gefüllt sind.
8. **Maschinen- und BDE-Adapter sind read-only HTTP GET.** Es gibt keine Methoden, die Maschinen steuern. XmskSvr wird nur über den SCADA-Proxy gelesen.
9. **API-Schlüssel ist optional.** Leerer `API_KEY` lässt `/api/v1/*` offen. Die API bleibt im LAN, solange kein Gateway oder mTLS davor steht.

## Verhalten, das der Baum implementiert

- SAP-Status: `P` geplant, `R` freigegeben, `L` geschlossen, `C` storniert.
- `order_state` ist eine Zeile pro Auftrag, Upsert über Fingerprint. `order_snapshots` nur bei Änderung. `source_key` ist `<company_db>:<doc_entry>`.
- Events sind über `event_id` idempotent. `persist_events()` überspringt Duplikate.
- Inkrementelles Fenster: `since = max(sap_update_date) − INCREMENTAL_LOOKBACK_DAYS`. Offene Aufträge werden immer gelesen. Verschwundene offene Aufträge werden per DocEntry nachgelesen, damit Schliessungen nicht fehlen.
- Numerisches XMSK-`Order` ist eine SAP-`DocNum`. Freitext (zum Beispiel `10886/NEU`) bleibt `order_ref` und wird nicht verknüpft.
- Auftrags-Events: `ORDER_CREATED`, `ORDER_RELEASED`, `QUANTITY_CHANGED`, `DUE_DATE_CHANGED`, `ORDER_PARTIAL_COMPLETE`, `ORDER_CLOSED`.
- Maschinen-Events: `MACHINE_ONLINE`, `MACHINE_OFFLINE`, `MACHINE_STATE_CHANGED`, `MACHINE_ORDER_STARTED`, `MACHINE_ORDER_FINISHED`, `MACHINE_PIECES_REPORTED`.
- Mengen in Payloads als String, Datum als ISO-String.
- MQTT-Topic `<prefix>/events/<EVENT_TYPE>/<source_key mit ':' → '/'>`. Kafka-Key ist `source_key`. Publisher-Fehler dürfen den Collector nicht abbrechen. Beide Transports sind per Default aus.
- BDE-Sätze werden aus SCADA-Telemetrie abgeleitet (`BDE_GAP_SECONDS`). Ausschuss ist damit immer 0. Es gibt kein BDE-Terminal.
- Polling: SAP alle `POLL_INTERVAL_SECONDS` (60 s), Maschinen alle `MACHINE_POLL_INTERVAL_SECONDS` (15 s), mit Retry über tenacity.

## Qualitätssicherung, wie sie konfiguriert ist

| Tor | Wo | Wirksam |
|---|---|---|
| ruff check + format | `ci.yml` Job `lint` | beratend (`continue-on-error`) |
| mypy `src/bdx` | `ci.yml` Job `typecheck` | beratend (`continue-on-error`) |
| pytest + Coverage | `ci.yml` | `--cov-fail-under=68`. Kommentar in derselben Datei sagt noch 80 %. `addopts` schliesst den Marker `integration` aus |
| Integration gegen DEV | `integration.yml` | nightly 03:00 UTC, nur mit gesetzten SAP-/SL-/Postgres-Variablen |
| Docker-Import-Smoke | `ci.yml` | `import bdx` im Image |
| `bdx-collect check` | `src/bdx/agents/` | Doku-Pflicht: `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `SAP_MAPPING.md`. Status älter als 90 Tage → Warnung. TestAgent: 80 % gesamt, 50 % pro Modul, Skip-Anteil über 10 % → Warnung |
| DEV-Deploy | `deploy-dev.yml` | Push auf `main`. Image-Build auf GitHub-hosted, SSH-Deploy auf `[self-hosted, linux]`. Smoke: `/health/live` |
| PROD-Deploy | `deploy-prod.yml` | nur manuell, Self-hosted-Runner, Reviewer-Environment |
| Auto-Merge | `auto-merge.yml` | Label `trivial`, nur Test- und Doku-Pfade, keine geschützten Pfade |

Neue Pfade unter `collector/`, `adapters/`, `sap_sl/`, `db/`, `publish/` brauchen einen pytest. Tests laufen auf SQLite in-memory. Im Baum liegen 104 Unit- und 8 Integrationstestfunktionen (gezählt über `def test_` am 2026-11-07, ohne pytest-Lauf).

`PROJECT_STATUS.md` trägt unter der Überschrift **Zuletzt aktualisiert:** mit Datum, Uhrzeit und Zeitzone. Jede Bearbeitung setzt den Stempel neu.

## Abweichungen (Regel ≠ Baum)

Diese Punkte sind Anforderungen der Agent-Regeln, die `main` heute nicht erfüllt. Sie sind offen, nicht stillschweigend akzeptiert.

1. **`ServiceLayerSettings.dry_run` defaultet auf aus** (`config.py`). `.env.example` lässt Dry-Run ebenfalls aus. Die Regel verlangt den umgekehrten Default und verbietet, die Ausschalt-Zuweisung zu committen. Die Beispiel-Datei auf `main` enthält sie bereits. Dieser Abgleich fügt sie nicht erneut ein und ändert die Beispiel-Datei nicht (nur die drei Status-Dokumente).
2. **CI-Coverage-Kommentar (80 %) und TestAgent (80 %) liegen über dem ausführenden Gate (68 %).** `241b535` dokumentiert den Floor bei etwa 69 % und eine Ratsche nach oben. Das Gate darf nicht weiter sinken.
3. **`docs/ARCHITECTURE.md` sagt an zwei Stellen, Service-Layer-Schreiboperationen seien noch nicht implementiert.** `sap_sl/operations.py` implementiert sie. Die Architektur-Datei ist nicht Teil dieses Abgleichs.
4. **`README.md` nennt 87 Tests und einen Security-Absatz, der Schreiboperationen noch als „prepared, no write operations“ beschreibt.** Beides ist älter als der Baum. Die README ist nicht Teil dieses Abgleichs.

## Nicht verlangt auf diesem Stand

- Multi-Company und SSO/SCIM (TBD, kein Code).
- Ein MQTT- oder Kafka-Broker im Repository.
- Analytics, KPI-Engine oder ein Schwachstellen-Dashboard. Dafür gibt es offene PRs, sie sind nicht auf `main`.
- Eine Skill-Datei `.cursor/skills/dev-sync/SKILL.md`. Sie liegt auf `main` nicht.
