# BDX Intelligence – Requirements

> **Zuletzt abgeglichen:** 2026-11-08 16:38 (CET)
> Gegen `origin/main` `6710fdc`. `main` ist seit 15:33 CET nicht weitergelaufen. Auf `main` gab es keine Anforderungsliste und keine IDs. Die Zeilen sind aus dem Code, aus `AGENTS.md` und aus dem Git-Stand abgeleitet, nicht aus einem freigegebenen Pflichtenheft. Nächste freie ID: `R021`. Status fortschreiben, IDs nicht umnummerieren.

| ID | Anforderung | Status | Beleg |
|---|---|---|---|
| R001 | Der MSSQL-Kanal darf nur lesen. INSERT, UPDATE, DELETE und DDL werden abgewiesen | erfüllt | `src/bdx/db/sap.py` wirft `PermissionError` vor dem Cursor |
| R002 | SQL an SAP ist parametrisiert, ohne String-Interpolation | erfüllt | `src/bdx/db/queries.py`, Regel in `AGENTS.md` |
| R003 | Zugangsdaten kommen nur aus der Umgebung. `.env` wird nicht committet | erfüllt als Regel | `.env` ist gitignored. Dieser Abgleich hat keine Secret-Werte gelesen |
| R004 | Service-Layer-Schreibvorgänge laufen über das Audit in `sl_operations`. Der Dry-Run ist der committete Standard | erfüllt | `sap_sl/operations.py`, Migration `003`. Host-Umgebung kann den Dry-Run abschalten; das steht in keiner committeten Datei als aktiv |
| R005 | SAP-Statuscodes sind `P` geplant, `R` freigegeben, `L` geschlossen, `C` storniert | erfüllt | `AGENTS.md`, `docs/SAP_MAPPING.md` |
| R006 | Inkrementelles Lesen holt offene Aufträge nach und verpasst Schließungen nicht | erfüllt | `collector/`, beschrieben in `docs/ARCHITECTURE.md` |
| R007 | Events sind über `event_id` idempotent | erfüllt | `persist_events()`, `AGENTS.md` |
| R008 | Eine numerische XMSK-Auftragsnummer ist die SAP-`DocNum`. Freitext bleibt unverknüpft | erfüllt | `collector/machines.py`, Statusdokument |
| R009 | REST, Dashboard und CLI zeigen Aufträge, Events, Maschinen, BDE und Läufe | erfüllt | Routen in `src/bdx/api/routes/`, `/dashboard` |
| R010 | Eine Schwachstellen-Sicht bündelt überfällige Aufträge, festgefahrene freigegebene Aufträge, Planänderungen, stillstehende Maschinen, Offline-Events, Collector-Fehler und den Lauftrend | erfüllt | `GET /api/v1/analytics/weaknesses`, 11 Tests in `tests/test_analytics.py` |
| R011 | Jeder Push und jeder PR nach `main` baut, testet und hält eine Coverage-Untergrenze | teilweise | `ci.yml`. Untergrenze ist 68 %, nicht die in `AGENTS.md` genannten 80 %. Lauf 42464604714 grün. Ruff und mypy sind `continue-on-error` |
| R012 | Ein grüner Push nach `main` rollt DEV automatisch aus und prüft `/health/live`, ohne echte Service-Layer-Schreibvorgänge | erfüllt laut letztem Lauf | `deploy-dev.yml` auf dem Self-hosted-Runner. Lauf 42464604728 erfolgreich. Der Job bricht ab, wenn die Host-Umgebung echte Schreibvorgänge einschaltet |
| R013 | PROD-Deploy nur manuell, mit Reviewern, und Migrationen nur nach ausdrücklicher Freigabe | erfüllt als Workflow | `deploy-prod.yml`, `ALEMBIC_ALLOW_PROD` in `alembic/env.py`. Ob die GitHub-Environment-Reviewer gesetzt sind, wurde nicht geprüft |
| R014 | Nächtliche Integrationstests gegen DEV SAP (lesen) und den Service Layer im Dry-Run | nicht erfüllt im letzten Lauf | `integration.yml`. Lauf 42469243262 scheiterte beim ODBC-Install (`gpg` ohne TTY, Exit 2). Pytest lief nicht |
| R015 | Lokale Qualitätsprüfung ohne Datenbank: Doku, Tests, Lint | erfüllt | `src/bdx/agents/`, CLI `bdx-collect check` |
| R016 | API-Zugang im LAN optional über einen gemeinsamen Schlüssel | erfüllt | `API_KEY` / `X-API-Key` |
| R017 | Automatisches PR-Review auf Fehler und Sicherheit | nicht erfüllt | `pr-review.yml` hat zwei `env:`-Schlüssel im Schritt „Fetch PR diff“. Lauf 42464603622 auf `main` hat keine Jobs. Dieselbe Ablehnung liegt auch auf späteren Pushes, zuletzt Lauf 42490429453 (14:33 UTC, Branch von Entwurf #31). CI desselben Commits war grün (Lauf 42490451263) |
| R018 | Ruff-Fund im Bestand wird per Cleanup-PR beseitigt, damit das Lint-Gate blockieren kann | offen | Lauf 42473962358 hat `chore/ruff-cleanup-20261108` gepusht und dann kein PR erzeugt, weil Label `trivial` fehlt |
| R019 | Sprint-005-KPI-Engine (Snapshots, Schwellen, Anomalien, Beschaffung, Diagnose) | offen | nur PR #5, mergeable CONFLICTING, `mergeStateStatus` DIRTY, nicht auf `main` |
| R020 | Mehrere Buchungskreise und SSO/SCIM | offen | kein Implementierungsstand auf `main` |
