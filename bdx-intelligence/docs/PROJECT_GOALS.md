# BDX Intelligence – Project Goals

> **Zuletzt abgeglichen:** 2026-11-08 16:38 (CET)
> Gegen `origin/main` `6710fdc`. `main` ist seit 15:33 CET nicht weitergelaufen. Ziel-IDs bleiben. Status ändern, IDs nicht umnummerieren. Details stehen in `PROJECT_STATUS.md`.

| ID | Ziel | Status | Beleg auf `main` |
|---|---|---|---|
| G1 | SAP Business One nur lesend anbinden, Änderungen an Fertigungsaufträgen idempotent erkennen und über REST sowie CLI bereitstellen | erledigt | Sprint 001, Commit `4219156`. Schreibschutz in `src/bdx/db/sap.py` |
| G2 | Inkrementell lesen, Maschinenzustand (Mazak XMSK) und abgeleitete BDE-Sätze an den Fertigungsauftrag hängen | erledigt | Sprint 002, im Bundle `936d8c8` |
| G3 | Domain-Events veröffentlichen, ein Betriebsdashboard ausliefern und einen auditierten Service-Layer-Schreibweg bereithalten | teilweise | Publisher und Dashboard sind auf `main`. Kein MQTT-/Kafka-Broker konfiguriert. Echte Schreibvorgänge sind keine committete Einstellung |
| G4 | CI, Qualitätsgates, nächtliche Integration, automatisches DEV-Deploy und ein freigabepflichtiges PROD-Deploy | teilweise | Workflows auf `main`. CI-Lauf 42464604714 und Deploy-to-DEV-Lauf 42464604728 auf `6710fdc` erfolgreich. Ruff und mypy bleiben beratend, Coverage-Gate ist 68 %. `pr-review.yml` startet nicht (letzter gesehener Fehlschlag 42490429453, 14:33 UTC, Branch von Entwurf #31, dieselbe doppelte `env:`). Die nächtliche Integration stoppt beim ODBC-Install |
| G5 | Schwachstellen der laufenden Fertigung in einem zweiten Dashboard zeigen | erledigt | PR #6 (`2f13c3f`) und Darstellung #12 (`6850feb`): `GET /api/v1/analytics/weaknesses`, Seite `/analytics` |
| G6 | DEV per Container über einen Self-hosted-Runner auf dem DEV-Host ausrollen | erledigt laut Workflow | `deploy-dev.yml` läuft ohne SSH-Hop. Lauf 42464604728 erfolgreich, inklusive `/health/live`. Shopfloor nicht erneut geprüft |
| G7 | KPI-Engine mit Anomalien, Selbstjustierung und Beschaffungsdiagnose (Sprint 005) | offen | PR #5, nicht gemergt, mergeable CONFLICTING, `mergeStateStatus` DIRTY. Auf `main` kein `src/bdx/analytics/` und keine Migration nach `003` |
| G8 | Ruff- und MyPy-Gates blockierend machen und die Coverage-Schwelle in Richtung 80 % anheben | offen | CI-Floor 68 %. Branch `chore/ruff-cleanup-20261108` ohne PR, weil das Label `trivial` fehlt |
| G9 | Fertigung gegen PROD lesen, ohne DEV- und PROD-Daten im Event Store zu mischen | offen | Nur Einzelproben dokumentiert (2026-11-07). Eigener Postgres oder modus-präfixierter `source_key` fehlt |
| G10 | Mehrere SAP-Firmen und SSO/SCIM | offen | Im Status als TBD, kein Code auf `main` |
