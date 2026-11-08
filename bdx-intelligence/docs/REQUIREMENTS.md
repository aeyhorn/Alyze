# BDX Intelligence – Requirements

> **Zuletzt abgeglichen:** 2026-11-08 17:36 (CET)
> Gegen `origin/main` `283ee4b`. Die Zeilen stammen aus dem Code, aus `AGENTS.md` und aus dem Git-Stand, nicht aus einem freigegebenen Pflichtenheft. Nächste freie ID: `R021`. Status fortschreiben, IDs nicht umnummerieren, Zeilen nicht löschen.

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| R001 | Der MSSQL-Kanal darf nur lesen. INSERT, UPDATE, DELETE und DDL werden abgewiesen | erfüllt | `src/bdx/db/sap.py` wirft `PermissionError` vor dem Cursor |
| R002 | SQL an SAP ist parametrisiert, ohne String-Interpolation | erfüllt | `src/bdx/db/queries.py`, Regel in `AGENTS.md` |
| R003 | Zugangsdaten kommen nur aus der Umgebung. `.env` wird nicht committet | erfüllt als Regel | `.env` ist gitignored. Dieser Abgleich hat keine Secret-Werte gelesen |
| R004 | Service-Layer-Schreibvorgänge laufen über das Audit in `sl_operations`. Der Dry-Run ist der committete Standard | teilweise | Audit in `sap_sl/operations.py`, Migration `003`. `ServiceLayerSettings.dry_run` defaultet auf aus, und `.env.example` lässt Dry-Run ebenfalls aus. DEV-Deploy-Skripte brechen ab, wenn die Host-Umgebung Dry-Run nicht eingeschaltet lässt. Lauf [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) ist success |
| R005 | SAP-Statuscodes sind `P` geplant, `R` freigegeben, `L` geschlossen, `C` storniert | erfüllt | `AGENTS.md`, `docs/SAP_MAPPING.md` |
| R006 | Inkrementelles Lesen holt offene Aufträge nach und verpasst Schließungen nicht | erfüllt | `collector/`, beschrieben in `docs/ARCHITECTURE.md` |
| R007 | Events sind über `event_id` idempotent | erfüllt | `persist_events()`, `AGENTS.md` |
| R008 | Eine numerische XMSK-Auftragsnummer ist die SAP-`DocNum`. Freitext bleibt unverknüpft | erfüllt | `collector/machines.py`, Statusdokument |
| R009 | REST, Dashboard und CLI zeigen Aufträge, Events, Maschinen, BDE und Läufe | erfüllt | Routen in `src/bdx/api/routes/`, `/dashboard` |
| R010 | Eine Schwachstellen-Sicht bündelt überfällige Aufträge, festgefahrene freigegebene Aufträge, Planänderungen, stillstehende Maschinen, Offline-Events, Collector-Fehler und den Lauftrend | erfüllt | `GET /api/v1/analytics/weaknesses`, Seite `/analytics`. Neun Tests in `tests/test_weaknesses.py` (die `def test_engine` / `test_session_factory` dort sind Fixtures). Darstellung in `6850feb` |
| R011 | Jeder Push und jeder PR nach `main` baut, testet und hält eine Coverage-Untergrenze | teilweise | `ci.yml`. Untergrenze ist 68 %, nicht die in `AGENTS.md` genannten 80 %. Lauf [42499222986](https://github.com/aeyhorn/Alyze/actions/runs/42499222986) auf `283ee4b` ist success. Ruff und mypy sind `continue-on-error` |
| R012 | Ein grüner Push nach `main` rollt DEV automatisch aus und prüft `/health/live`, ohne echte Service-Layer-Schreibvorgänge | erfüllt laut letztem Lauf | `deploy-dev.yml` auf dem Self-hosted-Runner. Lauf [42499223057](https://github.com/aeyhorn/Alyze/actions/runs/42499223057) für `283ee4b` ist success und hat Alembic `004 -> 005` und `005 -> 006` geloggt. Der Job bricht ab, wenn die Host-Umgebung Dry-Run ausschaltet |
| R013 | PROD-Deploy nur manuell, mit Reviewern, und Migrationen nur nach ausdrücklicher Freigabe | erfüllt als Workflow | `deploy-prod.yml`, `ALEMBIC_ALLOW_PROD` in `alembic/env.py`. Ob die GitHub-Environment-Reviewer gesetzt sind, wurde nicht geprüft (Branch-Protection-API 403) |
| R014 | Nächtliche Integrationstests gegen DEV SAP (lesen) und den Service Layer im Dry-Run | nicht erfüllt im letzten Lauf | `integration.yml`. Lauf [42469243262](https://github.com/aeyhorn/Alyze/actions/runs/42469243262) (2026-11-08 09:55 UTC, `6710fdc`) scheiterte beim ODBC-Install (`gpg` ohne TTY, Exit 2). Pytest lief nicht. Kein neuerer Lauf |
| R015 | Lokale Qualitätsprüfung ohne Datenbank: Doku, Tests, Lint | erfüllt | `src/bdx/agents/`, CLI `bdx-collect check` |
| R016 | API-Zugang im LAN optional über einen gemeinsamen Schlüssel | erfüllt | `API_KEY` / `X-API-Key` |
| R017 | Automatisches PR-Review auf Fehler und Sicherheit | nicht erfüllt | `pr-review.yml` hat zwei `env:`-Schlüssel im Schritt „Fetch PR diff“. Lauf [42499221888](https://github.com/aeyhorn/Alyze/actions/runs/42499221888) auf dem Push von `283ee4b` hat keine Jobs. Dieselbe Ablehnung liegt auf dem Push von `2796032` (Lauf [42498523815](https://github.com/aeyhorn/Alyze/actions/runs/42498523815)) |
| R018 | Ruff-Fund im Bestand wird per Cleanup-PR beseitigt, damit das Lint-Gate blockieren kann | offen | Lauf [42473962358](https://github.com/aeyhorn/Alyze/actions/runs/42473962358) hat `chore/ruff-cleanup-20261108` (`57411b2`, 47 Dateien) gepusht und dann kein PR erzeugt, weil das Label `trivial` fehlt |
| R019 | Sprint-005-KPI-Engine (Snapshots, Schwellen, Anomalien, Beschaffung, Diagnose) | erfüllt | PR #5 squash-gemergt als `283ee4b` (2026-11-08 17:18 +0100). `src/bdx/analytics/`, Alembic `005` und `006`. CI 42499222986 und DEV-Deploy 42499223057 success. 40 Tests in `tests/test_analytics.py`, 10 in `tests/test_diagnosis.py`. Dieser Abgleich hat pytest nicht erneut ausgeführt |
| R020 | Mehrere Buchungskreise und SSO/SCIM | offen | kein Implementierungsstand auf `main`. Ziel G10 |

Abgleich 2026-11-08 17:36 (CET): R019 ist erfüllt, weil die KPI-Engine auf `main` liegt. Quote-to-Promise (`2796032`, PR #33) hat keine Zeile. Nächste freie ID bleibt `R021`.
