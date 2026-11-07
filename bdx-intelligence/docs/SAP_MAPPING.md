# SAP Business One – Field Mapping

This document maps SAP B1 database columns to the BDX Intelligence domain model.

## OWOR – Production / Work Orders

| SAP Column | BDX Field | Type | Description |
|---|---|---|---|
| `DocEntry` | `doc_entry` | int | SAP primary key – used as `source_key = OWOR:{DocEntry}` |
| `DocNum` | `doc_num` | int | Human-readable production order number |
| `Status` | `status` | str(1) | `R`=Released, `L`=Planned, `C`=Closed, `X`=Cancelled |
| `ItemCode` | `item_code` | str | Finished-goods item being produced |
| `PlannedQty` | `planned_qty` | Decimal | Target production quantity |
| `CmpltQty` | `completed_qty` | Decimal | Quantity confirmed as completed |
| `RjctQty` | `rejected_qty` | Decimal | Quantity confirmed as rejected/scrap |
| `DueDate` | `due_date` | date | Scheduled completion date |
| `StartDate` | `start_date` | date | Scheduled start date |
| `PostDate` | `post_date` | date | SAP document posting date |
| `U_Type` | `u_type` | str | User-defined order type (custom field) |
| `U_Priority` | `u_priority` | str | User-defined priority (custom field) |
| `Comments` | `comments` | str | Free-text remarks |
| `UpdateDate` | `update_date` | date | Date of last SAP update |
| `UpdateTS` | `update_ts` | int | Timestamp of last SAP update |

### Source Key

```
source_key = f"OWOR:{doc_entry}"
```

The `source_key` is stable across snapshots and is the primary correlation key for change detection and domain events.

### Status Values

| Code | Meaning | Open? |
|---|---|---|
| `R` | Released – actively being produced | Yes |
| `L` | Planned – not yet released | Yes |
| `C` | Closed – production complete | No |
| `X` | Cancelled | No |

### Open Order Filter

```sql
WHERE wo.Status NOT IN ('C', 'X')
```

## OITM – Item Master Data

| SAP Column | BDX Field | Type | Description |
|---|---|---|---|
| `ItemCode` | `item_code` | str | SAP item code (joins to OWOR.ItemCode) |
| `ItemName` | `item_name` | str | Human-readable item description |
| `ItmsGrpCod` | `item_group_code` | int | Item group (e.g. finished goods, raw material) |
| `InvntItem` | `inventory_item` | str(Y/N) | Whether item is tracked in inventory |
| `PrfrmMrpStep` | `mrp_item` | str(Y/N) | Whether item participates in MRP |
| `U_BDX_Machine` | `machine_id` | str | Custom field: linked machine ID for routing |

## Domain Events – SAP Evidence Mapping

| Event | SAP Evidence |
|---|---|
| `ORDER_CREATED` | `source_key` appears for the first time in a snapshot |
| `ORDER_RELEASED` | `Status` changes from `L` → `R` between snapshots |
| `QUANTITY_CHANGED` | `PlannedQty` changes between snapshots |
| `DUE_DATE_CHANGED` | `DueDate` changes between snapshots |
| `ORDER_CLOSED` | `Status` changes from `R`/`L` → `C` or `X` between snapshots |

> **Note**: Events are derived by comparing consecutive snapshots.  They represent what BDX Intelligence *can observe* – not necessarily what triggered the change in SAP.  SAP itself does not emit events; the collector reconstructs them from state deltas.

## Read-Only Access – Required SQL Permissions

The SAP database user (`SAP_DB_USER`) must have:

```sql
-- Minimum required (SQL Server)
GRANT SELECT ON dbo.OWOR TO [bdx_readonly];
GRANT SELECT ON dbo.OITM TO [bdx_readonly];
```

No other permissions are required or should be granted.  The user must **not** have INSERT, UPDATE, DELETE, ALTER, or EXECUTE permissions on any SAP object.

## Custom Fields

BDX Intelligence reads two custom SAP fields that must be created in the company database before use:

| Field | Table | Purpose |
|---|---|---|
| `U_Type` | OWOR | Classify order type (e.g. standard, prototype, rework) |
| `U_Priority` | OWOR | Production priority level |
| `U_BDX_Machine` | OITM | Machine assignment for routing to BDE/machine adapters |

If these fields do not exist the query will fail.  Set them to `NULL` in the SQL or add them via SAP B1 User-Defined Fields (UDF) manager.
