"""Tests for the SCADA-telemetry BDE adapter and the event publishers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import httpx

from bdx.adapters.bde import NullBDEAdapter, ScadaTelemetryBDEAdapter, telemetry_to_records
from bdx.config import MqttSettings
from bdx.models.events import DomainEvent
from bdx.publish.base import NullPublisher, event_to_message
from bdx.publish.mqtt import MqttPublisher, build_publisher

T0 = datetime(2026, 11, 7, 8, 0, tzinfo=UTC)


def _pt(minutes: int, order: str | None, pieces: int | None, state: str = "running") -> dict:
    return {
        "timestamp": (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "order": order,
        "pieces": pieces,
        "state": state,
        "machineId": "QT 250MY",
    }


class TestTelemetryToRecords:
    def test_groups_by_order_and_gap(self):
        points = [
            _pt(0, "100", 0),
            _pt(5, "100", 2),
            _pt(10, "100", 4),
            _pt(60, "100", 5),  # gap 50 min > 15 min → new record
            _pt(65, "200", 0),
            _pt(70, "200", 3),
            _pt(75, "", None),  # empty order closes the record
            _pt(80, "200", 3),
        ]
        recs = telemetry_to_records("QT 250MY", points, gap_seconds=900)
        assert [(r.order_id, r.sample_count) for r in recs] == [
            ("100", 3),
            ("100", 1),
            ("200", 2),
            ("200", 1),
        ]
        first = recs[0]
        assert first.start_time == T0 and first.end_time == T0 + timedelta(minutes=10)
        assert first.quantity_good == 4.0 and first.duration_seconds == 600
        assert first.sap_doc_num == 100
        assert recs[2].quantity_good == 3.0

    def test_unsorted_input_and_missing_pieces(self):
        points = [_pt(10, "7", None), _pt(0, "7", 1), _pt(5, "7", None)]
        recs = telemetry_to_records("m", points)
        assert len(recs) == 1 and recs[0].quantity_good == 0.0 and recs[0].start_time == T0

    def test_empty(self):
        assert telemetry_to_records("m", []) == []


class TestScadaAdapter:
    def _adapter(self, machines, telemetry):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/api/machines":
                return httpx.Response(200, json=machines)
            if req.url.path.endswith("/telemetry"):
                return httpx.Response(200, json=telemetry)
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        return ScadaTelemetryBDEAdapter("http://scada:3888/", client=client)

    def test_fetch_recent(self):
        adapter = self._adapter([{"machineId": "QT 250MY"}], [_pt(0, "1", 0), _pt(5, "1", 2)])
        assert adapter.health_check() is True
        recs = adapter.fetch_recent(T0 - timedelta(hours=1))
        assert len(recs) == 1 and recs[0].machine_id == "QT 250MY" and recs[0].quantity_good == 2

    def test_filters_old_records(self):
        adapter = self._adapter([{"machineId": "m"}], [_pt(0, "1", 0), _pt(5, "1", 2)])
        assert adapter.fetch_recent(datetime.now(UTC)) == []

    def test_unreachable(self):
        def boom(req):
            raise httpx.ConnectError("down")

        adapter = ScadaTelemetryBDEAdapter(
            "http://x", client=httpx.Client(transport=httpx.MockTransport(boom))
        )
        assert adapter.health_check() is False
        assert adapter.fetch_recent(T0) == []

    def test_null_adapter(self):
        assert NullBDEAdapter().fetch_recent(T0) == [] and NullBDEAdapter().health_check()


def _event(event_type: str = "ORDER_CREATED", source_key: str = "OWOR:1", **kw) -> DomainEvent:
    return DomainEvent(
        event_id="e1",
        event_type=event_type,
        source_key=source_key,
        doc_entry=1,
        doc_num=1,
        item_code="A",
        payload={"x": 1},
        occurred_at=T0,
        snapshot_run_id="r",
        **kw,
    )


class TestPublisher:
    def test_event_to_message(self):
        suffix, payload = event_to_message(
            _event("MACHINE_STATE_CHANGED", "MACHINE:QT 250MY", machine_id="QT 250MY")
        )
        assert suffix == "MACHINE_STATE_CHANGED/MACHINE/QT 250MY"
        body = json.loads(payload)
        assert body["event_type"] == "MACHINE_STATE_CHANGED" and body["machine_id"] == "QT 250MY"
        assert body["payload"] == {"x": 1}

    def test_null_publisher(self):
        p = NullPublisher()
        assert p.publish([_event()]) == 0 and p.health_check() is True

    def test_build_publisher_disabled_by_default(self):
        assert isinstance(build_publisher(MqttSettings(enabled=False, host="")), NullPublisher)
        assert isinstance(build_publisher(MqttSettings(enabled=True, host="")), NullPublisher)
        assert isinstance(build_publisher(MqttSettings(enabled=True, host="broker")), MqttPublisher)

    def test_mqtt_publish_with_mock_client(self):
        client = MagicMock()
        client.publish.return_value.rc = 0
        pub = MqttPublisher(
            MqttSettings(enabled=True, host="broker", topic_prefix="bdx/test"), client=client
        )
        sent = pub.publish([_event(), _event("ORDER_CLOSED", "OWOR:2")])
        assert sent == 2
        client.connect.assert_called_once_with("broker", 1883, keepalive=60)
        topics = [c.args[0] for c in client.publish.call_args_list]
        assert topics == [
            "bdx/test/events/ORDER_CREATED/OWOR/1",
            "bdx/test/events/ORDER_CLOSED/OWOR/2",
        ]
        assert pub.health_check() is True
        pub.close()
        client.disconnect.assert_called_once()

    def test_mqtt_errors_do_not_raise(self):
        client = MagicMock()
        client.connect.side_effect = OSError("refused")
        pub = MqttPublisher(MqttSettings(enabled=True, host="broker"), client=client)
        assert pub.publish([_event()]) == 0
        assert pub.health_check() is False
