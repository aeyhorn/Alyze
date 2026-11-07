# SAP Business One – Field Mapping

This document maps SAP B1 database columns (and the shop-floor feeds) to the BDX Intelligence domain model.

## OWOR – Production / Work Orders

| SAP Column | BDX Field | Type | Description |
|---|---|---|---|
| `DocEntry` | `doc_entry` | int | SAP primary key – used as `source_key = OWOR:{DocEntry}` |
| `DocNum` | `doc_num` | int | Human-readable production order number (identical to `DocEntry` at Leisinger) |
| `Status` | `status` | str(1) | `P`=Planned, `R`=Released, `L`=Closed, `C`=Cancelled (see below) |
| `ItemCode` | `item_code` | str | Finished-goods item being produced |
| `PlannedQty` | `planned_qty` | Decimal | Target production quantity |
| `CmpltQty` | `completed_qty` | Decimal | Quantity confirmed as completed |
| `RjctQty` | `rejected_qty` | Decimal | Quantity confirmed as rejected/scrap |
| `DueDate` | `due_date` | date | Scheduled completion date |
| `StartDate` | `start_date` | date | Scheduled start date |
| `PostDate` | `post_date` | date | SAP document posting date |
| `U_Type` | `u_type` | str | **does not exist** at Leisinger → selected as `NULL` |
| `U_Priority` | `u_priority` | str | **does not exist** at Leisinger → selected as `NULL` |
| `Comments` | `comments` | str | Free-text remarks |
| `CreateDate` | – | date | used by the incremental filter only |
| `UpdateDate` | `update_date` | date | Date of last SAP update (`NULL` for ~10 % of rows) |
| `UpdateTS` | `update_ts` | int | Time of last SAP update (HHMMSS) |

### Source Key

```
source_key = f"OWOR:{doc_entry}"          # production orders
source_key = f"MACHINE:{machine_id}"      # machine events
```

### Status Values (verified against `DEV_SBO_LEISINGER`, 2026-11-07)

| Code | Meaning | Open? | Count on DEV |
|---|---|---|---|
| `P` | Planned – not yet released | Yes | 3 |
| `R` | Released – actively being produced | Yes | 868 |
| `L` | Closed – production complete | No | 36 497 |
| `C` | Cancelled | No | 1 193 |

> Sprint 001 documented `L`=Planned and `C`/`X`=Closed. That was wrong (`X` never occurs); it inflated the open-order
> count to 37 368. Constants live in `bdx.models.sap` (`OPEN_STATUSES`, `CLOSED_STATUSES`, `STATUS_LABELS`).

### Queries

| Query | Filter | Used for |
|---|---|---|
| `OWOR_OPEN_ORDERS_SQL` | `Status IN ('P','R')` | diagnose |
| `OWOR_SNAPSHOT_SQL` | – | full load (first run, `--full`, every `FULL_RELOAD_EVERY_CYCLES`) |
| `OWOR_INCREMENTAL_SQL` | `Status IN ('P','R') OR UpdateDate >= :since OR CreateDate >= :since` | every polling cycle; `since = max(known UpdateDate) − INCREMENTAL_LOOKBACK_DAYS` |
| `OWOR_BY_DOCENTRIES_SQL_TEMPLATE` | `DocEntry IN (...)` (chunks of 500) | re-read of open orders that vanished from the incremental result |

## OITM – Item Master Data

| SAP Column | BDX Field | Type | Description |
|---|---|---|---|
| `ItemCode` | `item_code` | str | SAP item code (joins to OWOR.ItemCode) |
| `ItemName` | `item_name` | str | Human-readable item description |
| `ItmsGrpCod` | `item_group_code` | int | Item group |
| `InvntItem` | `inventory_item` | str(Y/N) | Whether item is tracked in inventory |
| `PrfrmMrpStep` | `mrp_item` | str(Y/N) | Whether item participates in MRP |
| `U_BDX_Machine` | `machine_id` | str | **does not exist** at Leisinger → `NULL` |

## Domain Events – Evidence Mapping

### Order events (SAP)

| Event | Evidence |
|---|---|
| `ORDER_CREATED` | `source_key` seen for the first time |
| `ORDER_RELEASED` | `Status` `P` → `R` |
| `ORDER_PARTIAL_COMPLETE` | `CmpltQty` increased while `Status ∈ {P,R}` |
| `QUANTITY_CHANGED` | `PlannedQty` changed |
| `DUE_DATE_CHANGED` | `DueDate` changed |
| `ORDER_CLOSED` | `Status` `P`/`R` → `L` or `C` (payload carries `new_status`, `completed_qty`, `planned_qty`) |

> Events are derived by comparing the current SAP read against `order_state`. They represent what BDX Intelligence
> *can observe* – SAP itself does not emit events.

### Machine events (XMSK feed)

Source: Mazak `XmskSvr` → `GET /machstates` (XML), reached through the SCADA nginx proxy
`http://192.168.82.33:3888/api/machstates` (direct access to `192.168.82.109:3202` returns 403 for other hosts).

| XMSK attribute | `machine_state` column | Notes |
|---|---|---|
| `Name` | `machine_id` | e.g. `Integrex i500S`, `QT350MY` |
| `MDE` | `mde_enabled` | `0` = no data acquisition → state `unknown` |
| `Exec` | `exec_state` | `AUS`, `Bereit`, … |
| `State` | `state` (normalised) | `Fertigen`/`Auftrag` → `running`, `Ruesten` → `setup`, `Exec=AUS` → `off`, else `idle` |
| `Mode` | `mode` | `MEM`, `RAPID`, `0` |
| `Order` | `order_ref` | raw; numeric → SAP `DocNum` link (`sap_doc_entry`, `sap_item_code`). Free text like `10886/NEU` stays unlinked |
| `Oper`, `Part`, `NCP` | `operation`, `part`, `nc_program` | `Part` is usually the SAP ItemCode (+ variant) |
| `Pieces` | `pieces`, `pieces_raw` | `"243 / 44"` → `pieces = 243` |
| `User` | `operator` | empty in the current feed |
| `Feed`, `Spindle`, `Rapid` | `*_override` (%) | |
| `Load0..2` | `load_spindle`, `load_axis_1`, `load_axis_2` | |
| `LastMsg`, `LastProdEnd` | `last_message`, `last_prod_end` | |

| Event | Evidence |
|---|---|
| `MACHINE_ONLINE` / `MACHINE_OFFLINE` | machine (re)appears in feed / missing for `MACHINE_OFFLINE_AFTER_SECONDS` |
| `MACHINE_STATE_CHANGED` | normalised `state` or `Exec` changed |
| `MACHINE_ORDER_STARTED` / `MACHINE_ORDER_FINISHED` | `Order` set / cleared or replaced |
| `MACHINE_PIECES_REPORTED` | `Pieces` counter increased on the same order |

### BDE records (SCADA telemetry)

Source: SCADA backend `GET /api/machines`, `GET /api/machines/{id}/telemetry?hours=N`
(JSON points `{timestamp, state, order, pieces, …}` every few seconds, persisted in SQL Server `BXProduction`).

A BDE record = consecutive telemetry points of one machine with the same `order`; closed by an order change,
an empty order or a gap > `BDE_GAP_SECONDS`. `quantity_good` = piece-counter delta, `quantity_scrap` = 0 (not available).

## Read-Only Access – Required SQL Permissions

Currently the collector uses Windows integrated authentication (`SAP_DB_TRUSTED_CONNECTION=yes`). For the container
deployment a SQL login is needed:

```sql
-- Minimum required (SQL Server)
GRANT SELECT ON dbo.OWOR TO [bdx_readonly];
GRANT SELECT ON dbo.OITM TO [bdx_readonly];
```

No other permissions are required or should be granted. The user must **not** have INSERT, UPDATE, DELETE, ALTER,
or EXECUTE permissions on any SAP object.

## Custom Fields

`U_Type`, `U_Priority` (OWOR) and `U_BDX_Machine` (OITM) were part of the original design but **do not exist** in the
Leisinger databases. The queries select `CAST(NULL AS NVARCHAR(50))` placeholders so the model shape is stable. OWOR does
contain other UDFs (`U_C_BDEInterface`, `U_Start`, `U_Ende`, work-step flags such as `U_Drehen_und_Fraesen`) that could be
mapped later.
