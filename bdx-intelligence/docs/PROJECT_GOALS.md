# BDX Intelligence – Projektziele

> **Zuletzt abgeglichen:** 2026-11-08 20:37 (CET)
>
> Stand gegen `origin/main` `283ee4b`. IDs `G#` bleiben stabil: nicht wiederverwenden, nicht umbenennen. Operativer Stand: [`PROJECT_STATUS.md`](PROJECT_STATUS.md). Anforderungen: [`REQUIREMENTS.md`](REQUIREMENTS.md).

| ID | Ziel | Status | Woran zu erkennen |
|---|---|---|---|
| G1 | SAP lesend anbinden, Änderungen idempotent in den Event-Store schreiben, per REST und CLI zeigen | done | Sprint 001 auf `main` (`4219156`, #1). Migrationen `001`–`002` |
| G2 | Inkrementell lesen, Maschinen (XMSK) und abgeleitete BDE anbinden | done | Sprint 002 auf `main` (`60bb34a`, `936d8c8`) |
| G3 | Events publizieren, Dashboard, Service-Layer-Schreibpfad mit Audit und Dry-Run-Guard | done | Sprint 003 auf `main` (`936d8c8`). Broker ist G8. Echte Schreibvorgänge bleiben ein Host-Schalter, keine committete Datei |
| G4 | CI, Deploy, Quality-Gate-Agents und HOTL-Prompts im Repo und grün | partial | Workflows auf `main`. CI und Deploy to DEV für `283ee4b` grün. ruff/mypy advisory, Coverage-Gate 68 %, Nightly-Integration und Lint-Cleanup am 2026-11-08 rot, `pr-review.yml` auf dem Push `283ee4b` rot, `docs/dora-metrics.md` fehlt |
| G5 | Quote-to-Promise: eine Anfrage, Domänen parallel aus SAP und Shop-Floor | done | PR #33, `2796032`, Migration `004`, UI `/q2p`. Personal bleibt G11 |
| G6 | Kennzahlen, Anomalien, selbst justierende Schwellen, Diagnose, Schwachstellen-Dashboard | done | PR #5 `283ee4b`, PR #6, PR #12. Migrationen `005` und `006`. Shop-Floor-Werte in diesem Abgleich nicht gemessen |
| G7 | Container auf dem DEV-Host mit read-only SQL-Login | partial | `deploy-dev.yml` läuft ohne SSH-Hop und war für `283ee4b` grün (`migrate` + `/health/live`). Login `bdx_readonly` fehlte am 2026-11-07; nicht erneut geprüft |
| G8 | MQTT- oder Kafka-Broker an die vorhandenen Publisher hängen | open | `publish/mqtt.py` und `publish/kafka.py` im Baum, kein Broker konfiguriert |
| G9 | Collector lesend gegen PROD, Event-Store getrennt von DEV | open | Prod-Migrations-Guard und `deploy-prod.yml` existieren. Letzte Prod-Probe 2026-11-07 war ein einzelner FA, kein laufender Collector |
| G10 | Mehrere SAP-Firmenmandanten, SSO/SCIM | open | nicht im Baum |
| G11 | Q2P-Personal und Qualifikation aus einem Feed statt als offene Frage | open | `q2p/service.py` setzt die Domain fest auf `needs_human` |

Neue Ziele nur, wenn eine Anforderung in `REQUIREMENTS.md` keinem `G#` zugeordnet ist.
