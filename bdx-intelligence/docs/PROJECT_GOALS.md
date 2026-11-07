# BDX Intelligence – Project Goals

> **Zuletzt abgeglichen:** 2026-11-07 21:38 (CET)
> **Git:** `main` @ `6ccc036185b5` (2026-11-07 21:28 +0100)

Ziele, die der Baum auf `main` selbst beschreibt (`README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`). Offene Pull Requests sind kein Ziel dieses Stands.

## Produktziel

BDX Intelligence verbindet SAP Business One und die Fertigung mit einem lokalen PostgreSQL-Event-Store und stellt das Ergebnis als REST-API, Dashboard, CLI und optional als MQTT- oder Kafka-Events bereit.

- **Lesen:** SAP-B1-SQL-Server (nur SELECT), Mazak-XmskSvr über den SCADA-Proxy, SCADA-Telemetrie für abgeleitete BDE-Sätze.
- **Schreiben:** SAP Service Layer, nur mit Audit in `sl_operations`. Dry-Run soll Schreibvorgänge blockieren, bis ein Operator sie ausserhalb von Git freigibt. Der Code-Default tut das heute nicht; siehe `docs/REQUIREMENTS.md`.
- **Speichern:** eine Zeile pro Auftrag in `order_state`, Historie nur bei Änderung, Events idempotent über `event_id`.
- **Menschen aus der Schleife** für Lint, Tests, DEV-Deploy und Triage. SAP-Schreibfreigaben und PROD-Deploy bleiben menschlich.

## Geliefert auf `main`

| Ziel | Stand |
|---|---|
| Read-only SAP-Collector, idempotente Auftragsevents, REST und CLI | Sprint 001, Commit `4219156` und Folgecommits |
| Inkrementelles Lesen, Maschinenlage, abgeleitete BDE, Docker-Paket | Sprint 002, ab `60bb34a` / `936d8c8` |
| MQTT- und Kafka-Publisher, Dashboard, Service-Layer-Schreiboperationen mit Audit | Sprint 003, `936d8c8`. Broker sind nicht an (Defaults aus) |
| CI, nächtliche Integrationstests, DEV- und PROD-Deploy-Workflows, Quality-Gate-Agents, HOTL-Prompts | Sprint 004, auf `main`. Lint und mypy beratend, Coverage-Gate 68 %, DEV-Deploy von `6ccc036` beim Abgleich noch `pending` |
| Self-hosted Runner für LAN-Deploy | Workflows verlangen `[self-hosted, linux]`. `scripts/prepare-dev-host.sh` (`6ccc036`) ist das Provisioning, kein Beleg, dass der Runner registriert ist |
| Docker-Context-Deploy ohne den GitHub-SSH-Job | `scripts/deploy.ps1` (`12fa8cf`) |

## Noch offen, im Baum benannt

- SQL-Login `bdx_readonly` auf LDSAP als Voraussetzung für Linux-Container. Das Skript ist da, die Existenz auf dem Server ist aus Git nicht ablesbar.
- Laufender Collector gegen PROD mit getrenntem Event-Store, damit DEV- und PROD-Daten nicht in `order_state` mischen.
- MQTT- oder Kafka-Broker, sobald ein Abnehmer da ist.
- Coverage von 68 % Richtung dem Agent-Ziel 80 % anheben, danach ruff und mypy in CI scharf schalten.
- `pr-review.yml` läuft aktuell nicht durch (Failures nach 0 s, Ursache hier nicht gelesen).
- Multi-Company-SAP, SSO/SCIM: in der Sprint-Tabelle als TBD, kein Code auf `main`.
- Maschinenfelder `User` und `LastProdEnd` kommen im Feed leer; das ist eine MDE-Konfiguration, kein BDX-Code.

## Bewusst nicht Ziel dieses Abgleichs

Pull Requests 2, 3, 4, 5, 6 und 7 sind offen und nicht in `6ccc036`. Dazu gehören eine Analytics-/KPI-Linie (PR 5), ein Schwachstellen-Dashboard (PR 6) und ein Dev-Sync-Agent (PR 3). Solange sie nicht auf `main` sind, sind sie keine Projektziele dieses Dokuments.
