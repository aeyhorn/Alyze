"""Tests for the XMSK machine adapter and the machine collector."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from bdx.adapters.machine import MachineStatus, XmskMachineAdapter, normalise_state, parse_xmsk
from bdx.collector.machines import detect_machine_changes, run_machine_cycle
from bdx.models.events import DomainEvent, EventType, MachineState, OrderState

XML = """<?xml version="1.0"?>
<XMSK Timestamp='2026-11-07T12:29:29' Version='1.0'>
  <Devices>
    <Device Name='HQR100MSY-1' MDE='1' Exec='AUS' Order='' Oper='' Part='' NCP='' Pieces='' User=''
            LastProdEnd='' Mode='0' Feed='0' Spindle='0' Rapid='0' State='' LastMsg='' Load0='0' Load1='0' Load2='0'/>
    <Device Name='Integrex i500S' MDE='1' Exec='Bereit' Order='38574' Oper='CNC' Part='10886/UEBERGABE' NCP='227'
            Pieces='243 / 44' User='' LastProdEnd='' Mode='MEM' Feed='100' Spindle='100' Rapid='50' State='Fertigen'
            LastMsg='' Load0='48' Load1='0' Load2='48'/>
    <Device Name='QT 250MY' MDE='0' Exec='AUS' Order='' Oper='' Part='' NCP='' Pieces='' User='' LastProdEnd=''
            Mode='0' Feed='0' Spindle='0' Rapid='0' State='' LastMsg='' Load0='0' Load1='0' Load2='0'/>
  </Devices>
</XMSK>"""


def _xml_with(order: str, pieces: str, state: str = "Fertigen", exec_: str = "Bereit") -> str:
    return f"""<XMSK Timestamp='2026-11-07T12:30:00'><Devices>
      <Device Name='Integrex i500S' MDE='1' Exec='{exec_}' Order='{order}' Oper='CNC' Part='10886' NCP='227'
              Pieces='{pieces}' User='' Mode='MEM' Feed='100' Spindle='100' Rapid='50' State='{state}'
              LastMsg='' Load0='1' Load1='2' Load2='3'/>
    </Devices></XMSK>"""


class TestParse:
    def test_parse_xmsk(self):
        statuses = parse_xmsk(XML)
        assert [s.machine_id for s in statuses] == ["HQR100MSY-1", "Integrex i500S", "QT 250MY"]
        i500 = statuses[1]
        assert i500.state == "running"
        assert i500.order_ref == "38574" and i500.sap_doc_num == 38574
        assert i500.pieces == 243 and i500.pieces_raw == "243 / 44"
        assert i500.feed_override == 100 and i500.rapid_override == 50
        assert i500.load_spindle == 48.0 and i500.load_axis_2 == 48.0
        assert i500.program_name == "227"
        assert i500.timestamp.tzinfo is not None
        assert statuses[0].state == "off" and statuses[0].order_ref is None
        assert statuses[2].mde_enabled is False and statuses[2].state == "unknown"

    def test_normalise_state(self):
        assert normalise_state("Bereit", "Fertigen", True) == "running"
        assert normalise_state("Bereit", "Ruesten", True) == "setup"
        assert normalise_state("Bereit", "", True) == "idle"
        assert normalise_state("AUS", "", True) == "off"
        assert normalise_state("Bereit", "Fertigen", False) == "unknown"

    def test_empty_document(self):
        assert parse_xmsk("") == []

    def test_non_numeric_order_not_linked(self):
        st = MachineStatus(
            machine_id="x", timestamp=datetime.now(UTC), state="idle", order_ref="AB-12"
        )
        assert st.sap_doc_num is None


class TestAdapter:
    def _adapter(self, xml: str) -> XmskMachineAdapter:
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text=xml))
        return XmskMachineAdapter(
            "http://scada/api/machstates", client=httpx.Client(transport=transport)
        )

    def test_fetch_and_cache(self):
        adapter = self._adapter(XML)
        assert adapter.health_check() is True
        assert adapter.list_machines() == ["HQR100MSY-1", "Integrex i500S", "QT 250MY"]
        assert adapter.get_status("Integrex i500S").order_ref == "38574"
        assert adapter.get_status("missing") is None

    def test_transport_error_returns_empty(self):
        def boom(req):
            raise httpx.ConnectError("down")

        adapter = XmskMachineAdapter(
            "http://x", client=httpx.Client(transport=httpx.MockTransport(boom))
        )
        assert adapter.get_all_status() == []
        assert adapter.health_check() is False


def _seed_order(session, doc_entry: int = 38574):
    now = datetime.now(UTC)
    session.add(
        OrderState(
            source_key=f"OWOR:{doc_entry}",
            doc_entry=doc_entry,
            doc_num=doc_entry,
            status="R",
            item_code="10886",
            planned_qty=300,
            completed_qty=0,
            rejected_qty=0,
            due_date=None,
            start_date=None,
            u_type=None,
            u_priority=None,
            comments=None,
            sap_update_date=None,
            sap_update_ts=None,
            captured_at=now,
            snapshot_run_id="r",
            fingerprint="f",
            first_seen_at=now,
            last_changed_at=now,
        )
    )
    session.commit()


class TestCollector:
    def test_first_sight_emits_online_and_order_started(self, session):
        _seed_order(session)
        events = detect_machine_changes(session, parse_xmsk(XML), "run1")
        session.commit()
        types = [e.event_type for e in events]
        assert types.count(EventType.MACHINE_ONLINE.value) == 3
        started = [e for e in events if e.event_type == EventType.MACHINE_ORDER_STARTED.value]
        assert len(started) == 1
        assert started[0].doc_entry == 38574 and started[0].item_code == "10886"
        assert started[0].source_key == "MACHINE:Integrex i500S"
        rows = {r.machine_id: r for r in session.execute(select(MachineState)).scalars()}
        assert rows["Integrex i500S"].sap_doc_entry == 38574
        assert rows["Integrex i500S"].pieces == 243

    def test_no_change_no_events(self, session):
        detect_machine_changes(session, parse_xmsk(XML), "run1")
        session.commit()
        assert detect_machine_changes(session, parse_xmsk(XML), "run2") == []

    def test_pieces_state_and_order_change(self, session):
        detect_machine_changes(session, parse_xmsk(_xml_with("38574", "10 / 0")), "r1")
        session.commit()
        ev = detect_machine_changes(session, parse_xmsk(_xml_with("38574", "12 / 0")), "r2")
        assert [e.event_type for e in ev] == [EventType.MACHINE_PIECES_REPORTED.value]
        assert ev[0].payload["delta"] == 2
        session.commit()

        ev = detect_machine_changes(
            session, parse_xmsk(_xml_with("38574", "12 / 0", state="")), "r3"
        )
        assert [e.event_type for e in ev] == [EventType.MACHINE_STATE_CHANGED.value]
        assert ev[0].payload["new_state"] == "idle"
        session.commit()

        ev = detect_machine_changes(session, parse_xmsk(_xml_with("38600", "0 / 0")), "r4")
        types = [e.event_type for e in ev]
        assert EventType.MACHINE_ORDER_FINISHED.value in types
        assert EventType.MACHINE_ORDER_STARTED.value in types
        finished = next(e for e in ev if e.event_type == EventType.MACHINE_ORDER_FINISHED.value)
        assert finished.payload["order_ref"] == "38574" and finished.payload["pieces"] == 12

    def test_offline_and_back_online(self, session):
        t0 = datetime.now(UTC)
        detect_machine_changes(session, parse_xmsk(XML), "r1", now=t0)
        session.commit()
        # still within grace period → nothing
        assert detect_machine_changes(session, [], "r2", now=t0 + timedelta(seconds=30)) == []
        ev = detect_machine_changes(session, [], "r3", now=t0 + timedelta(seconds=200))
        assert {e.event_type for e in ev} == {EventType.MACHINE_OFFLINE.value}
        assert len(ev) == 3
        session.commit()
        ev = detect_machine_changes(session, parse_xmsk(XML), "r4", now=t0 + timedelta(seconds=300))
        assert [e.event_type for e in ev].count(EventType.MACHINE_ONLINE.value) == 3

    def test_run_machine_cycle_persists(self, engine):
        from sqlalchemy.orm import sessionmaker

        factory = sessionmaker(bind=engine)
        transport = httpx.MockTransport(lambda req: httpx.Response(200, text=XML))
        adapter = XmskMachineAdapter("http://x", client=httpx.Client(transport=transport))

        published: list = []

        class Pub:
            def publish(self, events):
                published.extend(events)

        statuses, events = run_machine_cycle(adapter, factory, publisher=Pub())
        assert len(statuses) == 3 and len(events) == 4
        assert len(published) == 4
        with factory() as s:
            assert s.execute(select(DomainEvent)).scalars().all().__len__() == 4
            # cleanup for other tests
            for t in (DomainEvent, MachineState):
                s.query(t).delete()
            s.commit()
