"""High-level Service Layer write-back operations with audit logging.

Every call – successful, failed, or blocked by DRY_RUN – is recorded in the
``sl_operations`` audit table.  DRY_RUN is the safe default (``SL_DRY_RUN=true``);
writes only reach SAP when ``SL_DRY_RUN=false``.

Operations
----------
* ``release_order``          – PATCH ProductionOrders, Status P → R
* ``close_order``            – PATCH ProductionOrders, Status → L
* ``cancel_order``           – PATCH ProductionOrders, Status → C
* ``report_production``      – POST ReceiptFromProduction (confirm produced qty)

Status codes in the Service Layer match OWOR: P=Planned, R=Released, L=Closed,
C=Cancelled.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from bdx.models.events import SLOperation
from bdx.sap_sl.client import DryRunError, ServiceLayerClient, ServiceLayerError

logger = structlog.get_logger(__name__)

# SAP B1 Service Layer base type for production orders (DocumentType enumeration).
PRODUCTION_ORDER_BASE_TYPE = "202"


@dataclass
class OperationResult:
    operation_id: str
    operation: str
    status: str  # success | failed | dry_run
    http_status: int | None
    error: str | None
    dry_run: bool


def _audit(
    session: Session,
    *,
    operation_id: str,
    operation: str,
    client: ServiceLayerClient,
    doc_entry: int | None,
    doc_num: int | None,
    payload: dict,
    status: str,
    http_status: int | None,
    error: str | None,
    operator: str | None,
) -> SLOperation:
    row = SLOperation(
        operation_id=operation_id,
        occurred_at=datetime.now(UTC),
        operation=operation,
        mode=client.mode.value,
        company_db=client.company_db,
        doc_entry=doc_entry,
        doc_num=doc_num,
        payload=payload,
        dry_run=client.dry_run,
        status=status,
        http_status=http_status,
        error=(error[:2000] if error else None),
        operator=operator,
    )
    session.add(row)
    session.commit()
    return row


def _exec(
    session: Session,
    client: ServiceLayerClient,
    operation: str,
    method: str,
    path: str,
    body: dict,
    doc_entry: int | None,
    doc_num: int | None,
    operator: str | None = None,
) -> OperationResult:
    """Run one SL write call and audit it (success / failure / dry-run)."""
    operation_id = str(uuid.uuid4())
    try:
        client.sl_call(method, path, body=body)
    except DryRunError:
        logger.info("sl.dry_run", operation=operation, doc_entry=doc_entry)
        _audit(
            session,
            operation_id=operation_id,
            operation=operation,
            client=client,
            doc_entry=doc_entry,
            doc_num=doc_num,
            payload=body,
            status="dry_run",
            http_status=None,
            error=None,
            operator=operator,
        )
        return OperationResult(operation_id, operation, "dry_run", None, None, dry_run=True)
    except ServiceLayerError as exc:
        logger.warning(
            "sl.failed",
            operation=operation,
            doc_entry=doc_entry,
            status=exc.status,
            error=exc.message,
        )
        _audit(
            session,
            operation_id=operation_id,
            operation=operation,
            client=client,
            doc_entry=doc_entry,
            doc_num=doc_num,
            payload=body,
            status="failed",
            http_status=exc.status,
            error=exc.message,
            operator=operator,
        )
        return OperationResult(
            operation_id, operation, "failed", exc.status, exc.message, dry_run=client.dry_run
        )
    except Exception as exc:
        logger.error("sl.unexpected", operation=operation, doc_entry=doc_entry, error=str(exc))
        _audit(
            session,
            operation_id=operation_id,
            operation=operation,
            client=client,
            doc_entry=doc_entry,
            doc_num=doc_num,
            payload=body,
            status="failed",
            http_status=None,
            error=str(exc),
            operator=operator,
        )
        return OperationResult(
            operation_id, operation, "failed", None, str(exc), dry_run=client.dry_run
        )

    logger.info("sl.success", operation=operation, doc_entry=doc_entry, dry_run=False)
    _audit(
        session,
        operation_id=operation_id,
        operation=operation,
        client=client,
        doc_entry=doc_entry,
        doc_num=doc_num,
        payload=body,
        status="success",
        http_status=204,
        error=None,
        operator=operator,
    )
    return OperationResult(operation_id, operation, "success", 204, None, dry_run=False)


# ── Public operations ────────────────────────────────────────────────────────


def release_order(
    session: Session, client: ServiceLayerClient, doc_entry: int, operator: str | None = None
) -> OperationResult:
    """Release a planned production order (Status P → R)."""
    body = {"Status": "R"}
    return _exec(
        session,
        client,
        "release",
        "PATCH",
        f"ProductionOrders({doc_entry})",
        body,
        doc_entry,
        None,
        operator,
    )


def close_order(
    session: Session, client: ServiceLayerClient, doc_entry: int, operator: str | None = None
) -> OperationResult:
    """Close a production order (Status → L)."""
    body = {"Status": "L"}
    return _exec(
        session,
        client,
        "close",
        "PATCH",
        f"ProductionOrders({doc_entry})",
        body,
        doc_entry,
        None,
        operator,
    )


def cancel_order(
    session: Session, client: ServiceLayerClient, doc_entry: int, operator: str | None = None
) -> OperationResult:
    """Cancel a production order (Status → C)."""
    body = {"Status": "C"}
    return _exec(
        session,
        client,
        "cancel",
        "PATCH",
        f"ProductionOrders({doc_entry})",
        body,
        doc_entry,
        None,
        operator,
    )


def report_production(
    session: Session,
    client: ServiceLayerClient,
    doc_entry: int,
    completed_quantity: float,
    warehouse: str,
    *,
    doc_num: int | None = None,
    batch_number: str | None = None,
    operator: str | None = None,
) -> OperationResult:
    """Report produced quantity against a production order (Receipt from Production).

    Creates an SAP ``ReceiptFromProduction`` document that consumes the
    production order as its base and books *completed_quantity* into *warehouse*.
    """
    body: dict = {
        "BaseEntry": doc_entry,
        "BaseType": PRODUCTION_ORDER_BASE_TYPE,
        "Quantity": completed_quantity,
        "Warehouse": warehouse,
    }
    if batch_number:
        body["BatchNumber"] = batch_number
    return _exec(
        session,
        client,
        "report_production",
        "POST",
        "ReceiptFromProduction",
        body,
        doc_entry,
        doc_num,
        operator,
    )


__all__ = [
    "PRODUCTION_ORDER_BASE_TYPE",
    "OperationResult",
    "cancel_order",
    "close_order",
    "release_order",
    "report_production",
]
