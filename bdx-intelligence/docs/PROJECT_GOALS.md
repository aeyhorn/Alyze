# BDX Intelligence – Project Goals

> **Zuletzt abgeglichen:** 2026-11-09 05:37 (UTC+1)
> **Git-Stand:** `main` `723f794` (2026-11-08)
>
> Diese Datei fehlte auf `main`. Die IDs `G1`–`G10` werden hier aus den committeten Dokumenten und dem Baum vergeben. Ein Ziel gilt nur als erreicht, wenn der Git-Stand es trägt. Exit-Kriterien, die nur in der Vision stehen und nicht im Baum oder in einer Messung liegen, bleiben offen.

| ID | Ziel | Quelle | Git-Stand |
|---|---|---|---|
| G1 | SAP-Fertigungsaufträge read-only, idempotent und inkrementell lesen; Events und REST/CLI bereitstellen | Sprint 001 in `PROJECT_STATUS.md`, `AGENTS.md` | Im Baum seit `4219156` (#1). DEV-Messung im Status stammt vom 2026-11-07 und wurde hier nicht wiederholt |
| G2 | Maschinen (XMSK), BDE aus SCADA, inkrementelles Lesen, Dashboard | Sprint 002/003, Commit `936d8c8` | Im Baum. MQTT/Kafka-Publisher sind im Code; ein Broker ist im Repo nicht konfiguriert |
| G3 | Service-Layer-Schreibwege nur mit Audit und ohne stillen Produktiv-Schreibzugriff | `AGENTS.md` SAP Safety, `sap_sl/operations.py`, Migration `003` | Operationen und Audit-Tabelle sind im Baum. `ServiceLayerSettings.dry_run` defaultet im Code auf aus. `AGENTS.md` beschreibt den sicheren Default umgekehrt. Dieser Abgleich schaltet keine Schreibwege frei |
| G4 | CI, nächtliche Integration, DEV-Deploy, freigabepflichtiges PROD-Deploy, lokale Quality-Gates | `.github/workflows/`, `src/bdx/agents/`, Sprint 004 | Workflows liegen auf `main`. Ruff und mypy sind in `ci.yml` beratend (`continue-on-error`). Coverage-Gate ist 68, nicht 80. `AGENTS.md` nennt noch 80 |
| G5 | KPI-Engine, Anomalien, selbstjustierende Schwellen, Schwachstellen-Diagnose | `src/bdx/analytics/`, Migrationen `005` und `006`, UI `/analytics` | Gemergt als Sprint 005 (`283ee4b`, #5) plus Dashboard-Folgecommits `2f13c3f` (#6) und `6850feb` (#12) |
| G6 | Anfragen parallel aus Material, Kapazität, Preis und Personal bewerten; Quoter-`offen` als Frage statt E-Mail | `src/bdx/q2p/`, `docs/Q2P_QUOTER.md`, Migrationen `004` und `008` | Cockpit `2796032` (#33), Quoter-Anbindung `0de31a7` (#39). Personal bleibt ohne Feed eine offene Frage |
| G7 | Internes Promise-OS: lebendiges Angebot, Gaps, Evidence, eine Akte, Entscheidung mit Audit (Vision Phase A) | `docs/VISION_PROMISE_PLATFORM.md` §6 Phase A, `src/bdx/promise/` | Code und Migration `007` in `1ce5fdf` (#41), UI `/promise`. Das Exit-Kriterium „Vertrieb arbeitet nur noch über die Akte“ ist im Git nicht belegt |
| G8 | Einkaufs- und Kapazitätsmaschine schlagen vor, bestellen nicht selbst (Vision Phase B, vor Phase E) | Vision §4.3–4.4 und §6 Phase B; `promise/agents/purchase.py`, `capacity.py` | Agenten laufen beim Recompute und erzeugen Gaps, Evidence und Vorschläge. Kein Bestell-Schreibweg im Purchase-Agent. Das Exit-Kriterium „>50 % der Gaps ohne Mail“ ist im Git nicht belegt |
| G9 | Vertragsentwurf aus dem Promise und dieselbe Wahrheit im Kundenportal (Vision Phase C und D, ohne Phase E) | Vision §4.5 und §5; `promise/agents/contract.py`, `api/routes/portal.py` | Entwurf, Publish und token-scoped Portal (`/portal/{token}`, Annahme/Ablehnung) sind im Baum. Eigenständige Portal-Auth, Branding und Domain aus Phase D fehlen. Phase E (Bestellen und Binden innerhalb von Limits) ist nicht implementiert |
| G10 | Mehrere SAP-Firmen, SSO/SCIM | Sprint-Tabelle „TBD“ im bisherigen Status | Kein Implementierungs-Commit auf `main`. SQL-Skripte `docs/sql/create_bdx_readonly.sql`, `reset_bdx_readonly.sql`, `grant_q2p_readonly.sql` liegen bei |

## Nicht als eigenes Ziel nummeriert

Diese Bausteine haben keinen eigenen Zielsatz über `G5`–`G9` hinaus:

- Schwachstellen-API `/api/v1/analytics/weaknesses` und Diagnose-Tabellen (Teil von G5).
- Vision-Entscheidungen V-1 bis V-5 in `docs/VISION_PROMISE_PLATFORM.md` §9. Das sind offene Entscheidungen, keine Ziele mit Liefernachweis.
- `docs/VISION_PROMISE_PLATFORM.md` §8 nennt als nächsten Bau-Schritt noch Offer/Gap-Tabellen. Die Tabellen sind in Migration `007` bereits auf `main`. Das Vision-Dokument ist damit älter als der Code, obwohl der Vision-Commit `723f794` danach liegt.

## Nächste Ziel-ID

`G11`. Neue IDs nur, wenn ein Commit auf `main` einen bisher nicht abgedeckten Lieferumfang einführt.
