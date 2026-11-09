# Q2P ↔ bdx-quoter Integration

## Role

`bdx-quoter` turns a **Datenraum** (drawings, SAP BOM exports, Anfrage-XLSX) into a
`Kalkulation` (`netto_eur`, `offen[]`, …). Q2P uses that as the **pricing** domain
instead of (or before) SAP price lists, and maps every `offen` entry to a human
`open_question` — so Kalkulations-Klärungen nicht mehr per E-Mail laufen.

## Runtime

| | |
|---|---|
| Container | `bdx-quoter` (compose project `bdx-quoter`) |
| Port | **8020** |
| Typical URL | `http://192.168.82.33:8020` |
| UI proxy | Vite `/api` → backend |

## BDX configuration

```env
QUOTER_ENABLED=true
QUOTER_BASE_URL=http://192.168.82.33:8020
QUOTER_TIMEOUT_SECONDS=120
QUOTER_HEALTH_PATH=/api/health
QUOTER_RUN_PATH=/api/run
QUOTER_PROJEKT_PATH=/api/projekt
```

## Assumed HTTP contract

`web/server.py` was not in the uploaded sources. The client therefore tries aliases
and allows path overrides. Preferred contract:

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/api/health` | – | 2xx |
| GET | `/api/projekt?datenraum=` | path | `projekt.json` shape |
| POST | `/api/run` | `{datenraum, kunde?, llm?, fresh?, item_code?, qty?}` | kalkulation or `{job_id,status}` |

Accepted kalkulation shapes match quoter export:

```json
{
  "kalkulation": {
    "netto_eur": 1234.5,
    "brutto_eur": 1470.0,
    "offen": ["…"],
    "positionen": []
  }
}
```

If the real routes differ: set `QUOTER_*_PATH` or adjust
`src/bdx/adapters/quoter.py` aliases after inspecting `/openapi.json` on the host.

## Q2P usage

1. Create inquiry with `datenraum` (and optional `kunde` / `use_llm`)
2. Evaluate → pricing domain calls quoter
3. `offen[]` → `open_questions` (domain `pricing`)
4. Without `datenraum`, pricing falls back to SAP `ITM1`

UI: `/q2p` form fields **Quoter-Datenraum** / **Quoter-Kunde**.

## Deep Link (Entscheidung)

**Gewählt:** UI Deep Link + `return_url` zwischen Promise-Akte und Quoter
(nicht nur blinder API-Recompute).

Vollständiger Contract + kopierbarer Prompt für das Quoter-Repo:
[`docs/QUOTER_DEEP_LINK.md`](QUOTER_DEEP_LINK.md).

Geplante BDX-Env-Ergänzung:

```env
QUOTER_UI_URL=http://192.168.82.33:8020
```

(`QUOTER_BASE_URL` bleibt die API-Basis; `QUOTER_UI_URL` steuert den Browser-Einstieg.)
