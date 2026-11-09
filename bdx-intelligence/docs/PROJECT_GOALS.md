# BDX Intelligence – Project Goals

> **Zuletzt abgeglichen:** 2026-11-09 09:33 (UTC+1)
> **Git-Stand:** `main` `184a6bd` (2026-11-09, #57 Quoter Deep-Link-Contract). Kein neues Ziel: die Spec hängt an G5, der Anforderungskatalog hat keine Zeile.
>
> Stabile IDs. Nicht umnummerieren. Neue Ziele bekommen die nächste freie ID (`G12`).
> Quelle sind die im Repository genannten Sprint- und Visionsziele, nicht neu erfundene Anforderungen.
> „Im Git“ heißt: der beschriebene Code oder das Dokument liegt auf diesem Commit. Betriebsnachweise (DEV-Lauf, Exit-Kriterien) sind extra gekennzeichnet.

| ID | Ziel | Quelle | Stand gegen Git |
|---|---|---|---|
| G1 | SAP Business One nur lesend anbinden, Fertigungsauftragsänderungen idempotent erkennen, per REST und CLI bereitstellen | Sprint 001 in `PROJECT_STATUS.md`; Commit `4219156` | erfüllt im Git |
| G2 | Shop-Floor-Realität: inkrementelles SAP-Lesen, Maschinenzustand (XMSK), aus Telemetrie abgeleitete BDE | Sprint 002; Commits `60bb34a`, `936d8c8` | erfüllt im Git. BDE bleibt abgeleitet, kein Terminalsystem |
| G3 | Domain-Events veröffentlichen (MQTT/Kafka) und ein Betriebs-Dashboard zeigen; Service-Layer-Schreibvorgänge nur auditiert und standardmäßig ohne echten Schreiblauf | Sprint 003; `936d8c8` | Publisher, Dashboard und auditierte Operationen sind im Git. Ein Broker ist im Baum nicht konfiguriert. Echte Schreibvorgänge sind im Repository nicht freigeschaltet |
| G4 | CI/CD und Qualitätsgates; Produktion und SAP-Schreibvorgänge bleiben menschlich freizugeben | Sprint 004; Workflows auf `main` | Workflows, Agents und Integrations-Tests sind auf `main`. Ruff und mypy sind beratend. Coverage-Floor ist 68 % (`241b535`). `prod`-Deploy ist `workflow_dispatch`. `lint-cleanup.yml` ist auf `main`; `chore/ruff-cleanup-20261108` (`57411b2`) ist nicht gemergt |
| G5 | Eine Anfrage, parallele Domänenantworten (Material, Kapazität, Preis, Personal); Menschen nur bei fehlenden Daten | Q2P, #33 und #39 | Cockpit, Evaluator und Quoter-Adapter sind gemergt (#33, #39). Deep-Link-Contract (Deep Link + `return_url`) ist spezifiziert (#57, `docs/QUOTER_DEEP_LINK.md`); Quoter-Route und BDX-Button sind nicht in diesem Baum. Personal/Schichtqualifikation hat weiterhin keinen Feed |
| G6 | Kennzahlen, Anomalien, selbstjustierende Schwellwerte und eine Schwachstellen-/Diagnosesicht über den Event-Store | Sprint 005, #5, #6, #12; Migrationen `005`, `006` | Modul, API `/api/v1/analytics/*` und UI `/analytics` sind im Git. Ob die Schwellen auf DEV vertrauenswürdig sind, steht nicht im Git |
| G7 | Lebendiges Angebot als führendes Objekt, typisierte Gaps statt E-Mail-Ketten, entscheidbar mit Audit (Vision Phase A) | `VISION_PROMISE_PLATFORM.md`; #41, Migration `007` | Offer, Gap, Evidence, Engine, Cockpit `/promise` sind im Git. Exit „Vertrieb arbeitet nur noch über die Akte“ ist nicht belegt |
| G8 | Einkaufs- und Kapazitätsmaschine schlagen vor und schließen Gaps, ohne still verbindlich zu bestellen oder Slots zu binden (Vision Phase B) | Vision §4 und §6; `promise/agents/purchase.py`, `capacity.py` | Agenten sind im Git und erzeugen Vorschläge bzw. Gaps. Der Exit „>50 % der Gaps ohne Mail“ ist nicht belegt. Autonomes Bestellen ist Phase E und nicht im Code |
| G9 | Vertrag aus dem Promise, mit Version und interner Freigabe (Vision Phase C) | Vision §6; `promise/agents/contract.py` | Der Contract-Agent entwirft einen Vertragskörper. Exit „Angebot→Auftrag ohne Word als führendes System“ ist nicht belegt |
| G10 | Kundenportal als Projektion derselben Offer-/Contract-Wahrheit (Vision Phase D) | Vision §5; `api/routes/portal.py`, UI `/portal/{token}` | Token-Portal mit Annahme und Ablehnung ist im Git. Eigene Auth, Branding und Domain aus der Vision fehlen |
| G11 | Mehrere SAP-Firmen und SSO/SCIM | Sprint-Tabelle „TBD“ in `PROJECT_STATUS.md` | offen. Kein entsprechender Code auf `main`. SQL-Login-Skript und `docker-compose.yml` existieren für den Container-Betrieb einer Firma |
