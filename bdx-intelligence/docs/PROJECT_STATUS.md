# BDX Intelligence – Project Status

> **Zuletzt aktualisiert:** 2026-11-14 15:37 (CET)
> _Diese Zeile muss bei jeder Bearbeitung dieses Dokuments auf das aktuelle Datum + Uhrzeit gesetzt werden (siehe `AGENTS.md`, Abschnitt „Dokumentation“)._

| Sprint | Scope | Status |
|---|---|---|
| 001 | SAP read-only collector, event store, REST/CLI | ✅ complete (shop-floor probe 2026-11-07; not re-measured this run) |
| 002 | BDE adapter, machine adapter, incremental reading | ✅ complete (same probe) |
| 003 | Event publishing (MQTT/Kafka), dashboard UI, SAP write-back | ✅ complete (publishers built, no broker; write-back dry-run; DEV Compose deploy is green) |
| 004 | CI/CD pipeline, quality-gate agents, integration tests, HOTL prompts | 🟡 on `main` (`cd6440f`). Pytest gate 68 %. Ruff and mypy advisory. Nightly integration fails in the ODBC Driver 18 install. `prod` has no protection rules. The `main` branch object reports unprotected. |
| 005 | Analytics: KPI engine, anomalies, weakness dashboard | ✅ merged (#5, #6, #12). Migrations `005` and `006`. |
| Q2P | Quote-to-Promise cockpit | ✅ merged (#33, #39). Migrations `004` and `008`. |
| Promise | Promise Platform (Offer/Gaps/Agents/Portal) | ✅ merged (#41). Migrations `007`+`008`. Vision: `docs/VISION_PROMISE_PLATFORM.md` |
| Vorgang | Vorgangsleitstand | ✅ merged (#67), included in the green DEV deploy of `cd6440f` |
| TBD | Multi-company SAP, SSO/SCIM | ⬜ open |

Test suite: 182 unit `test_*` functions on SQLite in-memory, plus 8 integration tests against DEV SAP/SL. The integration suite skips cleanly when DEV creds are absent. The nightly GitHub job fails in the ODBC install, before pytest.

---

## Sprint 001 – SAP Read-only Collector  ✅ Complete

**Goal**: Establish a reliable, read-only connection to SAP Business One SQL Server,
detect production order changes idempotently, and expose results via REST API and CLI.

| Feature | Status | Notes |
|---|---|---|
| SAP SQL Server connection (pyodbc + SQLAlchemy) | ✅ | TLS, timeouts, read-only guard, Windows integrated auth or SQL login |
| Parameterized queries for OWOR + OITM | ✅ | Fixed `text()` queries, no string interpolation |
| PostgreSQL event store (Alembic schema) | ✅ | migrations `001`, `002` |
| Initial full-load of production orders | ✅ | `OWOR_SNAPSHOT_SQL` on first run / `--full` |
| Periodic polling (60 s) | ✅ | `POLL_INTERVAL_SECONDS` |
| Idempotent change detection | ✅ | |
| Domain events: ORDER_CREATED / ORDER_RELEASED / QUANTITY_CHANGED / DUE_DATE_CHANGED / ORDER_CLOSED | ✅ | see status-code note below |
| Retry with exponential backoff (tenacity) | ✅ | |
| FastAPI REST API, healthcheck, CLI, structured logs, secrets from env | ✅ | |
| Service Layer client + Dev/Prod mode registry | ✅ | write-back itself **not** implemented |

## Sprint 002 – BDE, machines, incremental reading  ✅ Complete

| Feature | Status | Notes |
|---|---|---|
| **SAP status codes corrected** | ✅ | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (verified against OWOR). Sprint 001 treated `L` as open and `C`/`X` as closed → open-order count was 37 368; correct value is **871** |
| Incremental SAP read | ✅ | open orders (P/R) + `UpdateDate`/`CreateDate ≥ max(known UpdateDate) − `INCREMENTAL_LOOKBACK_DAYS`; open orders missing from the result are re-read by DocEntry so closures are never missed. Measured on DEV: **2 s per cycle** (was 47 s) |
| `order_state` table (one row per order, fingerprint upsert) | ✅ | `order_snapshots` is now history-on-change only (was +38 561 rows per cycle) |
| `snapshot_runs` bookkeeping | ✅ | mode, counts, duration, error per cycle → `/api/v1/runs`, `bdx-collect runs` |
| ORDER_PARTIAL_COMPLETE | ✅ | `CmpltQty` increases while order is open |
| Machine adapter `XmskMachineAdapter` | ✅ | reads Mazak XmskSvr `machstates` XML through the SCADA nginx proxy (`MACHINE_XMSK_URL`); read-only; 10 machines on the floor |
| Machine collector + `machine_state` table | ✅ | own interval (`MACHINE_POLL_INTERVAL_SECONDS=15`), offline detection |
| Machine events | ✅ | MACHINE_ONLINE / OFFLINE / STATE_CHANGED / ORDER_STARTED / ORDER_FINISHED / PIECES_REPORTED |
| Machine ↔ SAP link | ✅ | numeric XMSK `Order` = SAP `DocNum` → `order_state` → `doc_entry`, `item_code` on events and `/api/v1/machines` |
| BDE adapter `ScadaTelemetryBDEAdapter` | ✅ | derives BDE records (start/end/pieces per order & machine) from the SCADA telemetry REST API (`BDE_SCADA_BASE_URL`) |
| CLI `machines [--live]`, `runs`, `collect --full/--no-machines`, `serve`; `diagnose` covers PG/SAP/XMSK/SCADA/MQTT | ✅ | |

## Sprint 003 – Publishing, dashboard & write-back  ✅ Complete

| Feature | Status | Notes |
|---|---|---|
| Event publisher interface + `NullPublisher` | ✅ | collector and machine collector publish every new event |
| `MqttPublisher` (paho-mqtt, optional extra `.[mqtt]`) | ✅ | topic `<prefix>/events/<EVENT_TYPE>/<source_key ':'→'/'>`, JSON payload = `DomainEventDTO`; errors never break the collector. **No broker configured yet** (`MQTT_ENABLED=false`) |
| `KafkaPublisher` (confluent-kafka, optional extra `.[kafka]`) | ✅ | alternative to MQTT; key = `source_key` (partition affinity), JSON value; `build_all_publishers()` composes both when both are on |
| Kafka publisher | ✅ | `publish/kafka.py` (confluent-kafka, optional `.[kafka]`); `build_all_publishers()` composes MQTT + Kafka |
| Dashboard UI (`/dashboard`, static HTML/JS) | ✅ | KPIs, machine tiles with linked SAP order, events, open orders, runs, BDE records; auto-refresh |
| REST: `/orders` (state, open-only default, `/summary`, `/{doc_entry}` with history), `/events` (+`/summary`), `/machines` (+`/{id}`, `/{id}/live`), `/bde/records`, `/runs` | ✅ | |
| Optional API key (`API_KEY`, `X-API-Key` header or `?api_key=`) | ✅ | empty = open (LAN only) |
| `/health` reports collector freshness, machine feed, publisher | ✅ | |
| **SAP Service Layer write-back** (release / close / cancel / report-production) | ✅ | `sap_sl/operations.py` with `sl_operations` audit table (migration 003); CLI `release`/`close`/`cancel`/`report-production`/`sl-operations`; REST `POST /api/v1/service-layer/orders/{doc_entry}/{release,close,cancel,report-production}` + `GET /service-layer/operations`. **DRY_RUN-verified against DEV** (no real writes). Real writes happen only after an operator turns dry-run off in the host `.env`. |
| Dockerfile + docker-compose.yml | ✅ deployed on DEV | `deploy-dev.yml` on the self-hosted runner. Last green run: 2026-11-10 07:22 CET for `cd6440f` ([run 42768023481](https://github.com/aeyhorn/Alyze/actions/runs/42768023481)). In-tree markers `.runtime/last-deploy-at` / `last-deploy-sha` still read 2026-11-07 21:50 +01:00 / `6ccc036`. |

## Sprint 005 – Analytics and weakness dashboard  ✅ Merged (#5, #6, #12)

KPI snapshots, anomaly detection with self-tuning thresholds, measurement quality, flow segments, one lateness cause per late order, and a bottleneck rank. Alembic `005` (analytics tables) and `006` (diagnosis). REST under `/api/v1/analytics/*`, UI `/analytics`. Those merges are on `main` and went out with the later green DEV deploys, including `cd6440f`.

## Quote-to-Promise Cockpit  ✅ Merged (#33, #39)

**Goal**: Replace serial multi-person clarification on inquiries (material, capacity, price, personnel)
with one inquiry case that answers domains in parallel from SAP + shop floor. Humans only see
`open_questions` where the system has no data.

| Feature | Status | Notes |
|---|---|---|
| Inquiry case store `q2p_inquiries` (Alembic `004`) | ✅ | status draft/ready/blocked/decided; decision audit |
| Parallel evaluator `bdx.q2p.service.evaluate_promise` | ✅ | item / material / BOM / capacity / pricing / personnel |
| SAP reads OITW, OPOR/POR1, OITT/ITT1, ITM1/OPLN | ✅ | graceful degrade on missing SELECT |
| Capacity from `machine_state` + open `order_state` | ✅ | idle vs busy + backlog same item |
| REST `/api/v1/q2p/*` + ad-hoc `/q2p/promise` | ✅ | create, list, evaluate, decide |
| Cockpit UI `/q2p` | ✅ | form + case list + domain cards + human questions + decision |
| `bdx-collect serve` attaches SAP engine | ✅ | without engine → SAP domains become open questions |
| SQL grant script `docs/sql/grant_q2p_readonly.sql` | ✅ | run on DEV/PROD for live material/price |
| bdx-quoter HTTP adapter + pricing domain | ✅ | `QUOTER_*` env; datenraum on inquiry; `offen[]` → open_questions |
| Migration `008` (datenraum/kunde/use_llm on q2p_inquiries) | ✅ | renumbered after analytics `005` / promise `007` |

**Deploy notes**: `alembic upgrade head` (through `008`); run `grant_q2p_readonly.sql` on LDSAP;
set `QUOTER_ENABLED=true` + `QUOTER_BASE_URL=http://<docker-host>:8020`; open `http://<host>:8085/q2p`.

**Still human by design**: personnel/shift qualification (no feed yet). Quoter `offen` stays human until resolved in the datenraum. Confirm `/api/run` paths against real `web/server.py` if aliases miss.

## Promise Platform  ✅ Merged (#41)

**Goal**: Living Offer as system of record; Gaps instead of e-mail chains; fulfillment agents
(quote/purchase/capacity/contract); internal `/promise` cockpit + customer `/portal/{token}`.

| Feature | Status | Notes |
|---|---|---|
| Domain + Alembic `007` (offers/gaps/evidence/jobs/contracts) | ✅ | |
| Offer Engine (create / recompute / decide / resolve / publish) | ✅ | `bdx.promise.engine` |
| Agents: quote, purchase, capacity, contract | ✅ | quote delegates pricing to `evaluate_promise` + quoter |
| API `/api/v1/promise/*` + `/api/v1/portal/{token}` | ✅ | portal is token-scoped, no API key |
| UI `/promise` + `/portal/{token}` | ✅ | |
| Vision doc | ✅ | `docs/VISION_PROMISE_PLATFORM.md` |
| Quoter Deep Link Contract | 📝 spezifiziert | Entscheidung: Deep Link + `return_url`; Spec/Prompt: `docs/QUOTER_DEEP_LINK.md` (Quoter-Implementierung + BDX-UI folgen) |

**Deploy notes**: `alembic upgrade head` (`007`+`008`); open `/promise`; publish contract then share portal link.

## Vorgangsleitstand

`/vorgang` zeichnet offene Fertigungsaufträge als Balken von Start bis Fällig, die Maschinenbelegung im selben Fenster und den Arbeitsgang, den XMSK an der Maschine meldet. Meldungen (offline, Störung, überfällig) lassen sich in der Sitzung quittieren. SAP-Arbeitsgangfolgen und Kapazitätsstunden sind nicht angebunden; die Ansicht erfindet sie nicht.

## Sprint 004 – CI/CD pipeline, quality-gate agents, HOTL workflow  🟡 On main

**Goal**: Take the human out of the loop for everything except SAP-safety approvals —
automate lint/type/test/coverage gates, add nightly integration tests against
DEV, auto-deploy to DEV on green, gate PROD deploys behind a manual approval,
and add AI-assisted triage / PR review / DORA metrics. Plus a local
`bdx-collect check` command that audits the state of development (docs, tests,
code quality) without needing a database or SAP.

| Feature | Status | Notes |
|---|---|---|
| **`.github/workflows/ci.yml`** | ✅ on `main` | push/PR to `main`: ruff and mypy are advisory (`continue-on-error`), pytest with `--cov-fail-under=68`, Docker build smoke test (imports `bdx`). Working dir = `bdx-intelligence/` |
| **`.github/workflows/integration.yml`** | ✅ written | nightly cron `0 3 * * *` + `workflow_dispatch`; installs ODBC Driver 18 on Ubuntu, runs `pytest -m integration`; the fixture forces dry-run, so this workflow cannot write to SAP |
| **`.github/workflows/deploy-dev.yml`** | ✅ on `main`, DEV green | push to `main` builds `ghcr.io/<repo>/bdx-intelligence:dev` plus a sha tag, then the self-hosted runner on the DEV host runs compose (no SSH hop): pull, migrate, recreate `collector` + `api`, require `/health/live`. The job aborts when the host `.env` turns dry-run off. `bdx-collect diagnose` is best-effort. |
| **`.github/workflows/deploy-prod.yml`** | ✅ written | `workflow_dispatch` only; extra inputs `run_migrations` and `confirm_sl_write` (must be `true`); pulls chosen `image_tag`, optional migrations, recreate services, smoke `/health/live`. The workflow expects reviewers on environment `prod`; that environment's `protection_rules` list is empty. |
| **`.github/workflows/ci-triage.yml`** | ✅ written | `workflow_run` on failed CI → `scripts/ci_triage.py` fetches failed job logs, runs a Cursor cloud agent (`composer-2.5`) to produce a root-cause comment, posts it on the PR. Opt-in via `CURSOR_API_KEY` secret (no-op + green without it) |
| **`.github/workflows/pr-review.yml`** | 🟡 invalid YAML | on PR open/sync/reopen → `scripts/pr_review.py` would run two Cursor cloud agents (bug review + security review) and post one combined comment. The step `Fetch PR diff` declares `env` twice, so push runs fail with zero jobs. |
| **`.github/workflows/auto-merge.yml`** | ✅ written | PR labeled `trivial` + only test/doc files + no protected paths (`sap_sl/`, `db/`, `alembic/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`) → `gh pr merge --squash --auto --delete-branch` |
| **`.github/workflows/dora.yml`** | ✅ written | weekly Mon 06:00 UTC → `scripts/dora_metrics.py` computes deploy frequency, cycle time, MTTR, change-failure rate, CI flakiness from GitHub data, commits `docs/dora-metrics.md` |
| **Quality-gate agents** (`src/bdx/agents/`) | ✅ on `main` | `base.py`, `docs.py` (status freshness ≤90 d, routes and env vars vs `ARCHITECTURE.md`), `tests.py` (pytest; default coverage floor still 80 % overall / 50 % per module, which is stricter than the CI gate of 68 %), `quality.py` (ruff, mypy, smell scan), `runner.py`. Pure static — no DB/SAP import |
| **CLI `bdx-collect check`** | ✅ written | `check` (all agents), `check-docs`, `check-tests`, `check-quality`; each accepts `--json <path>` for a CI artifact; exit code 0 passed / 1 warned / 2 failed |
| **Integration tests** (`tests/integration/`) | ✅ written | `test_sap_read.py` (open-order count 700–1500, incremental <10 s, write guard raises `PermissionError`), `test_sl_contract.py` (SL login + release/close/cancel/report-production DRY_RUN audited to `sl_operations`), `conftest.py` skips the whole suite unless `SAP_DB_*`, `SL_*`, `POSTGRES_DSN` are set |
| **HOTL Cursor prompts** (`.cursor/prompts/`) | ✅ written | `from-notion-spec.mdc` (Notion spec → tasks → implement → PR → update Notion), `triage-issue.mdc` (label + branch + first task), `feature.mdc`, `bugfix.mdc`, `refactor.mdc`, `testgen.mdc` |
| **`AGENTS.md` + `.cursor/rules/bdx-conventions.mdc`** | ✅ written | canonical agent guide: SAP safety hard rules, architecture invariants, event naming, mandatory test pattern, code style, HOTL workflow, "never" list |
| **Helper scripts** (`scripts/`) | ✅ written | `ci_triage.py`, `pr_review.py`, `create_pr.py` (diff-based PR body via Cursor SDK), `dora_metrics.py` |
| **`pyproject.toml` / `docker-compose.yml`** | ✅ on `main` | committed with the Sprint 004 / deploy history. Ruff format cleanup of the legacy tree is still open (`chore/ruff-cleanup-20261108` is ahead of `main` and not merged). |
| **PROD migration guard** (`alembic/env.py`) | ✅ written | refuses to migrate against PROD DSN (`SAP_MODE=prod` + `POSTGRES_DSN_PROD`) unless `ALEMBIC_ALLOW_PROD=1`; `deploy-prod.yml` sets it only when the human checks the `run_migrations` approval input |

### Sprint 004 — status & open items

* **On `origin/main`.** The base of this reconciliation is `cd6440f` (2026-11-10 07:21 +0100). That tree was clean and not ahead of `origin/main`. Workflows, `scripts/`, `tests/integration/`, `src/bdx/agents/`, `AGENTS.md`, and `.cursor/prompts/` are in that history.
* **CI shape:** pytest coverage gate is 68 %. Ruff and mypy stay advisory. `bdx-collect check` still defaults its coverage floor to 80 %.
* **Nightly integration:** every scheduled run from 2026-11-08 through 2026-11-14 failed. The latest, [run 43582578926](https://github.com/aeyhorn/Alyze/actions/runs/43582578926) (2026-11-14 10:52 CET), dies in `Install ODBC Driver 18` with `gpg: can't open '/dev/tty': No such device or address` (exit 2). Pytest does not start. The cron is `0 3 * * *`; GitHub has been starting these runs late morning UTC.
* **GitHub settings re-read 2026-11-14 15:37 CET:** environments `prod`, `dev`, and `CURSOR_API_KEY` exist and each `protection_rules` list is empty. Repository rulesets are empty (length 0). The branch object for `main` reports `protected: false` and required status checks off. The classic branch-protection endpoint and the Actions secret-name list both returned HTTP 403, so this run did not read the full protection payload or which secret names exist. DEV deploy no longer uses SSH secrets; the runner is on the host.
* **`pr-review.yml`:** the step `Fetch PR diff` declares `env` twice, so the workflow file is invalid. Push runs finish failed with zero jobs. Latest example: [run 43600676877](https://github.com/aeyhorn/Alyze/actions/runs/43600676877) (2026-11-14 14:37 CET, PR #151). The prior push of PR #150 failed the same way ([run 43595824477](https://github.com/aeyhorn/Alyze/actions/runs/43595824477), 13:38 CET).
* **Unit CI on the same product tree:** push CI of `cd6440f` is green ([run 42768023614](https://github.com/aeyhorn/Alyze/actions/runs/42768023614)). Docs-PR pytest failed `tests/test_analytics.py::test_machine_utilization_with_calendar` (`machine_r is None`) through [run 43562318893](https://github.com/aeyhorn/Alyze/actions/runs/43562318893) (2026-11-14 06:36 CET). The test pins a shift to `datetime.now(UTC).weekday()` and 06:00–14:00. Docs-PR CI on that same tree is green from [run 43567158867](https://github.com/aeyhorn/Alyze/actions/runs/43567158867) (07:36 CET) through [run 43600690363](https://github.com/aeyhorn/Alyze/actions/runs/43600690363) (14:37 CET, PR #151).
* **Still open for G4:** required reviewers on `prod`, branch protection that requires `ci.yml`, a green nightly integration run, and a workflow file `pr-review.yml` that starts jobs.
* **Docs on `main` stay at the 2026-11-09 wording until one reconcile PR merges.** At 15:37 CET, 139 documentation PRs were open. Newest is #151. PR #2 still says `Sprint 004 complete`. No pull request has merged since `cd6440f` (2026-11-10). Product commit `57411b2` remains only on `origin/chore/ruff-cleanup-20261108`.



## Operational status (DEV, verified 2026-11-07)

| Check | Result |
|---|---|
| Service Layer login DEV / PROD | ✅ `DEV_SBO_LEISINGER`, `SBO_LEISINGER` – read calls OK (`SL_TIMEOUT_MS=120000` for cold start) |
| MSSQL read channel | ✅ Windows integrated auth (`SAP_DB_TRUSTED_CONNECTION=yes`, ODBC Driver 17); SQL login `bdx_readonly` does not exist yet on LDSAP |
| PostgreSQL event store | ✅ container `bdx-intelligence-postgres` on Docker host 192.168.82.33:5437, schema **002** applied |
| `bdx-collect diagnose` | ✅ PG, SAP (871 open orders), XMSK (10 machines), SCADA API; MQTT disabled |
| `bdx-collect collect --once` (incremental) | ✅ 871 orders / **2.2 s**, 0 events on unchanged data (idempotent) |
| `bdx-collect machines --live` | ✅ 10 machines → `machine_state`, 12 events (10× ONLINE, 2× ORDER_STARTED) |
| **PROD read probe** (FA 38574) | ✅ `SBO_LEISINGER`: Status R, Item 10886, 243 planned / 243 completed — matches Integrex i500S feed exactly. DEV lags PROD (FA 38560/38561 are R in PROD, P in DEV) |
| **SAP write-back DRY_RUN** (DEV) | ✅ `release 38559` and `report-production 38559 -q 5 -w W01` → both blocked by DRY_RUN, audited in `sl_operations` |
| API + `/dashboard` on :8085 | ✅ all endpoints return data; dashboard renders machines, orders, runs, BDE |

### Git and CI since the 2026-11-07 probe

This run did not re-probe SAP, XMSK, or the dashboard. From git and GitHub Actions:

* `origin/main` is `cd6440f` (2026-11-10). This reconciliation started from that commit with a clean tree.
* Deploy to DEV succeeded for that SHA on 2026-11-10 07:22 CET ([run 42768023481](https://github.com/aeyhorn/Alyze/actions/runs/42768023481)). `.runtime/last-deploy-at` and `.runtime/last-deploy-sha` still read `2026-11-07 21:50:15 +01:00` and `6ccc036`.
* Commit `7d0fb2f` records a CONNECT failure for SQL login `bdx_readonly` (error 18456, state 38) caused by `DENY CONTROL`, and adds `docs/sql/reset_bdx_readonly.sql`. The table row above still reflects the 2026-11-07 probe, which said the login did not exist yet. This run did not re-check LDSAP.
* Shop-floor figures in the table (871 open orders, 10 machines) are that probe, not a new measurement.

### Findings from the first real machine cycle

* **DEV database lags production**: machine *Integrex i500S* runs SAP order **38574**, but `DEV_SBO_LEISINGER` ends at DocNum 38561. The SAP link therefore shows no match on DEV – it will resolve as soon as the collector runs against PROD (`SAP_MODE=prod`, `SAP_DB_NAME=SBO_LEISINGER`).
* XMSK `Order` is not always a DocNum: *QT350MY* reports `10886/NEU` (free text = item + variant). Such references are kept raw (`order_ref`) and not linked.
* `MDE='0'` machines (*SQT250 MSY*) have no data acquisition → state `unknown`.

## Open items / next steps

| Item | Notes |
|---|---|
| **Finish Sprint 004 gates** | Code is on `main`. Nightly ODBC install fails before tests. `prod` has no protection rules. The `main` branch object reports unprotected; the classic protection endpoint returned HTTP 403. Ruff and mypy stay advisory. `pr-review.yml` fails before any job because the diff step declares `env` twice. Raise the 68 % coverage floor as tests land. |
| **SQL login `bdx_readonly` on LDSAP** | `create_bdx_readonly.sql` and `reset_bdx_readonly.sql` are on `main`. Commit `7d0fb2f` records CONNECT error 18456 state 38 from `DENY CONTROL`. Live login not re-checked this run. |
| Refresh `.runtime/last-deploy-*` | Markers lag the green DEV deploy of `cd6440f` (still 2026-11-07 / `6ccc036`). |
| MQTT / Kafka broker | set `MQTT_ENABLED=true` plus `MQTT_HOST`, or `KAFKA_ENABLED=true` plus `KAFKA_BOOTSTRAP_SERVERS`; `pip install -e .[mqtt]` / `.[kafka]` |
| Run collector against PROD | read-only; needs a separate Postgres database (or mode-prefixed `source_key`) so DEV and PROD rows do not mix in `order_state`. Only single-order probes so far. |
| SAP write-back for real | Stays dry-run on the host until an operator changes that `.env` on purpose. The DEV deploy aborts if the host file turns dry-run off. `.env.example` currently turns the guard off; the example should leave it on. Operations: release / close / cancel / report-production. |
| Multi-company SAP, SSO/SCIM | TBD |
| Machine `User`/operator and `LastProdEnd` are empty in the feed | needs MDE-side configuration |

## Known Limitations

1. **Custom SAP fields** (`U_Type`, `U_Priority`, `U_BDX_Machine`) do **not** exist in the Leisinger company databases. `queries.py` selects `NULL` placeholders; `u_type`/`u_priority` stay `None`. OWOR has other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags) that may be useful later.
2. **Net delta between cycles**: if two changes happen within one polling interval only the net delta is visible (events are derived from state diffs, not from SAP change logs).
3. **Incremental window**: orders that are closed *and* whose `UpdateDate` is older than the lookback window are only caught because BDX re-reads its known open orders by DocEntry. Orders unknown to BDX (created before the first full load and never open since) are not re-read – run `collect --once --full` after long outages or set `FULL_RELOAD_EVERY_CYCLES`.
4. **BDE is derived, not reported**: there is no BDE terminal system; records are reconstructed from SCADA telemetry (`BDE_GAP_SECONDS` splits segments). Scrap quantities are therefore always 0.
5. **API authentication** is an optional shared key only; do not expose the API outside the LAN without a gateway/mTLS.
6. **Legacy history**: the Sprint 001 migration seeded `order_state` with fingerprint `''`, so the first incremental cycle after upgrading rewrites one history row per open order (observed: 871, 30 s one-off).

## Repository Layout

```
bdx-intelligence/
├── src/bdx/
│   ├── config.py          # Env-var configuration (SAP, PG, collector, machine, BDE, MQTT, app)
│   ├── db/                # SAP/PG engines + parameterised OWOR/OITM queries
│   ├── models/            # Pydantic WorkOrder + ORM (order_state, order_snapshots, snapshot_runs,
│   │                      #   machine_state, domain_events, sl_operations)
│   ├── collector/         # polling (SAP, full/incremental), snapshots (state upsert),
│   │                      #   change_detector (order events), machines (machine events)
│   ├── adapters/          # machine.py (XMSK), bde.py (SCADA telemetry), quoter.py
│   ├── analytics/         # Sprint 005: KPIs, anomalies, diagnosis, bottleneck
│   ├── q2p/               # Quote-to-Promise inquiry evaluation
│   ├── promise/           # Offer engine, gaps, fulfillment agents
│   ├── publish/           # EventPublisher, NullPublisher, MqttPublisher, KafkaPublisher
│   ├── sap_sl/            # Service Layer client + Dev/Prod mode + operations (audited)
│   ├── agents/            # Sprint 004: quality-gate agents (docs, tests, quality, runner)
│   ├── api/               # FastAPI; dashboard, analytics, q2p, promise, portal, vorgang
│   └── cli/               # bdx-collect (incl. check / check-docs / check-tests / check-quality)
├── alembic/               # migrations 001–008
├── tests/                 # 182 unit test_* functions + 8 tests/integration/ (DEV SAP/SL)
├── scripts/               # ci_triage.py, pr_review.py, create_pr.py, dora_metrics.py
├── Dockerfile, docker-compose.yml
├── AGENTS.md              # canonical agent guide (SAP safety, invariants, workflow)
└── docs/                  # ARCHITECTURE, SAP_MAPPING, PROJECT_STATUS, PROJECT_GOALS, REQUIREMENTS (+ dora-metrics.md weekly)
```

Repo-root (sibling of `bdx-intelligence/`):

```
├── .github/workflows/     # ci, integration, deploy-dev, deploy-prod, ci-triage,
│                          #   pr-review, auto-merge, dora, lint-cleanup
└── .cursor/
    ├── prompts/           # from-notion-spec, triage-issue, feature, bugfix, refactor, testgen, sync-coordinator
    ├── rules/             # bdx-conventions.mdc, dev-sync.mdc (alwaysApply)
    └── skills/dev-sync/   # sync coordinator procedure
```
