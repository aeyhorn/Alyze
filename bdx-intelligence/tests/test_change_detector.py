"""Tests for the idempotent change detector."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from bdx.collector.change_detector import detect_changes, persist_events
from bdx.models.events import EventType
from bdx.models.sap import WorkOrder

_NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)
_RUN = "test-run-001"


def _make_wo(
    doc_entry: int, status: str = "R", planned: str = "100", due: date | None = None
) -> WorkOrder:
    return WorkOrder(
        doc_entry=doc_entry,
        doc_num=doc_entry * 10,
        status=status,
        item_code="PART-A",
        planned_qty=Decimal(planned),
        completed_qty=Decimal("0"),
        rejected_qty=Decimal("0"),
        due_date=due or date(2026, 12, 1),
        start_date=None,
        post_date=None,
    )


def _prev_from_wo(wo: WorkOrder) -> dict:
    return {
        "status": wo.status,
        "planned_qty": float(wo.planned_qty),
        "due_date": wo.due_date.isoformat() if wo.due_date else None,
    }


class TestDetectChanges:
    def test_new_order_raises_created(self):
        current = [_make_wo(1)]
        events = detect_changes({}, current, _RUN, _NOW)
        assert len(events) == 1
        assert events[0].event_type == EventType.ORDER_CREATED

    def test_no_change_no_events(self):
        wo = _make_wo(1)
        prev = {wo.source_key: _prev_from_wo(wo)}
        events = detect_changes(prev, [wo], _RUN, _NOW)
        assert events == []

    def test_released_event(self):
        # SAP: P = Planned → R = Released
        prev_wo = _make_wo(1, status="P")
        curr_wo = _make_wo(1, status="R")
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        types = {e.event_type for e in events}
        assert EventType.ORDER_RELEASED in types

    def test_closed_from_planned_is_not_released(self):
        prev_wo = _make_wo(1, status="L")
        curr_wo = _make_wo(1, status="R")
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        assert EventType.ORDER_RELEASED not in {e.event_type for e in events}

    def test_order_closed_with_L(self):
        prev_wo = _make_wo(1, status="R")
        curr_wo = _make_wo(1, status="L")
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        closed = [e for e in events if e.event_type == EventType.ORDER_CLOSED]
        assert len(closed) == 1
        assert closed[0].payload["new_status"] == "L"

    def test_partial_complete(self):
        prev_wo = _make_wo(1, status="R")
        prev = {prev_wo.source_key: {**_prev_from_wo(prev_wo), "completed_qty": 10}}
        curr_wo = _make_wo(1, status="R").model_copy(update={"completed_qty": Decimal("25")})
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        partial = [e for e in events if e.event_type == EventType.ORDER_PARTIAL_COMPLETE]
        assert len(partial) == 1
        assert partial[0].payload["new_completed_qty"] == "25"
        assert partial[0].payload["prev_completed_qty"] == "10"

    def test_partial_complete_not_on_closed(self):
        prev_wo = _make_wo(1, status="R")
        prev = {prev_wo.source_key: {**_prev_from_wo(prev_wo), "completed_qty": 10}}
        curr_wo = _make_wo(1, status="L").model_copy(update={"completed_qty": Decimal("100")})
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        types = {e.event_type for e in events}
        assert EventType.ORDER_CLOSED in types
        assert EventType.ORDER_PARTIAL_COMPLETE not in types

    def test_quantity_changed(self):
        prev_wo = _make_wo(1, planned="100")
        curr_wo = _make_wo(1, planned="150")
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        types = {e.event_type for e in events}
        assert EventType.QUANTITY_CHANGED in types

    def test_due_date_changed(self):
        prev_wo = _make_wo(1, due=date(2026, 12, 1))
        curr_wo = _make_wo(1, due=date(2026, 12, 15))
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        types = {e.event_type for e in events}
        assert EventType.DUE_DATE_CHANGED in types

    def test_order_closed(self):
        prev_wo = _make_wo(1, status="R")
        curr_wo = _make_wo(1, status="C")
        prev = {prev_wo.source_key: _prev_from_wo(prev_wo)}
        events = detect_changes(prev, [curr_wo], _RUN, _NOW)
        types = {e.event_type for e in events}
        assert EventType.ORDER_CLOSED in types

    def test_multiple_orders(self):
        wo1 = _make_wo(1, status="R")
        wo2 = _make_wo(2, status="L")
        # wo3 is new
        wo3 = _make_wo(3, status="R")
        prev = {
            wo1.source_key: _prev_from_wo(wo1),
            wo2.source_key: _prev_from_wo(wo2),
        }
        events = detect_changes(prev, [wo1, wo2, wo3], _RUN, _NOW)
        created = [e for e in events if e.event_type == EventType.ORDER_CREATED]
        assert len(created) == 1
        assert created[0].source_key == wo3.source_key

    def test_idempotent_same_input(self):
        wo = _make_wo(1)
        prev = {wo.source_key: _prev_from_wo(wo)}
        events1 = detect_changes(prev, [wo], _RUN, _NOW)
        events2 = detect_changes(prev, [wo], _RUN, _NOW)
        assert events1 == events2 == []


class TestPersistEvents:
    def test_persist_events_to_db(self, session):
        wo = _make_wo(99)
        events = detect_changes({}, [wo], _RUN, _NOW)
        persist_events(session, events)

        from sqlalchemy import select

        from bdx.models.events import DomainEvent

        stored = session.execute(select(DomainEvent)).scalars().all()
        assert len(stored) == 1
        assert stored[0].event_type == EventType.ORDER_CREATED

    def test_duplicate_events_skipped(self, session):
        wo = _make_wo(99)
        events = detect_changes({}, [wo], _RUN, _NOW)
        persist_events(session, events)
        persist_events(session, events)  # second call must be a no-op

        from sqlalchemy import select

        from bdx.models.events import DomainEvent

        stored = session.execute(select(DomainEvent)).scalars().all()
        assert len(stored) == 1
