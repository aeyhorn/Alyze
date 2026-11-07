"""Tests for the Service Layer write-back operations and the Kafka publisher."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from bdx.config import KafkaSettings, SapMode
from bdx.models.events import SLOperation
from bdx.sap_sl.client import DryRunError, ServiceLayerError
from bdx.sap_sl.operations import (
    PRODUCTION_ORDER_BASE_TYPE,
    close_order,
    cancel_order,
    release_order,
    report_production,
)


def _client(dry_run: bool = True) -> MagicMock:
    client = MagicMock()
    client.mode = SapMode.DEV
    client.company_db = "DEV_SBO_LEISINGER"
    client.dry_run = dry_run
    if dry_run:
        client.sl_call.side_effect = DryRunError("DRY_RUN active")
    return client


class TestReleaseCloseCancel:
    def test_release_dry_run_audits(self, session):
        client = _client(dry_run=True)
        res = release_order(session, client, 42)
        assert res.status == "dry_run" and res.dry_run is True
        client.sl_call.assert_called_once_with("PATCH", "ProductionOrders(42)", body={"Status": "R"})
        row = session.query(SLOperation).one()
        assert row.operation == "release" and row.status == "dry_run" and row.doc_entry == 42
        assert row.payload == {"Status": "R"} and row.mode == "dev"

    def test_release_success(self, session):
        client = _client(dry_run=False)
        res = release_order(session, client, 42)
        assert res.status == "success" and res.http_status == 204
        row = session.query(SLOperation).one()
        assert row.status == "success" and row.dry_run is False

    def test_close_and_cancel_bodies(self, session):
        client = _client(dry_run=True)
        close_order(session, client, 1)
        cancel_order(session, client, 1)
        calls = [c.args[1] for c in client.sl_call.call_args_list]
        assert calls == ["ProductionOrders(1)", "ProductionOrders(1)"]
        bodies = [c.kwargs["body"] for c in client.sl_call.call_args_list]
        assert bodies == [{"Status": "L"}, {"Status": "C"}]

    def test_failure_audited_with_http_status(self, session):
        client = _client(dry_run=False)
        client.sl_call.side_effect = ServiceLayerError(400, "order already released")
        res = release_order(session, client, 42)
        assert res.status == "failed" and res.http_status == 400 and "already released" in res.error
        row = session.query(SLOperation).one()
        assert row.status == "failed" and row.http_status == 400

    def test_unexpected_exception_audited(self, session):
        client = _client(dry_run=False)
        client.sl_call.side_effect = RuntimeError("boom")
        res = close_order(session, client, 1)
        assert res.status == "failed" and res.http_status is None
        assert session.query(SLOperation).one().error == "boom"


class TestReportProduction:
    def test_dry_run_body(self, session):
        client = _client(dry_run=True)
        res = report_production(session, client, 42, 25.0, "W01", doc_num=420)
        assert res.status == "dry_run"
        client.sl_call.assert_called_once_with(
            "POST", "ReceiptFromProduction",
            body={"BaseEntry": 42, "BaseType": PRODUCTION_ORDER_BASE_TYPE, "Quantity": 25.0, "Warehouse": "W01"},
        )
        row = session.query(SLOperation).one()
        assert row.operation == "report_production" and row.doc_num == 420

    def test_with_batch(self, session):
        client = _client(dry_run=True)
        report_production(session, client, 42, 10.0, "W01", batch_number="B-2026-1")
        body = client.sl_call.call_args.kwargs["body"]
        assert body["BatchNumber"] == "B-2026-1" and body["BaseType"] == "202"


# ── Kafka publisher ───────────────────────────────────────────────────────────

def _event(event_type: str = "ORDER_CREATED", source_key: str = "OWOR:1"):
    from bdx.models.events import DomainEvent, EventType

    return DomainEvent(
        event_id="e1",
        event_type=EventType(event_type).value,
        source_key=source_key,
        doc_entry=1, doc_num=1, item_code="A", machine_id=None,
        payload={"x": 1}, occurred_at=datetime.now(timezone.utc), snapshot_run_id="r",
    )


class TestKafkaPublisher:
    def test_build_disabled(self):
        from bdx.publish.base import NullPublisher
        from bdx.publish.kafka import build_kafka_publisher

        assert isinstance(build_kafka_publisher(KafkaSettings(enabled=False, bootstrap_servers="")), NullPublisher)
        assert isinstance(build_kafka_publisher(KafkaSettings(enabled=True, bootstrap_servers="")), NullPublisher)
        from bdx.publish.kafka import KafkaPublisher

        assert isinstance(build_kafka_publisher(KafkaSettings(enabled=True, bootstrap_servers="broker:9092")), KafkaPublisher)

    def test_publish_with_mock_producer(self):
        from bdx.publish.kafka import KafkaPublisher

        producer = MagicMock()
        pub = KafkaPublisher(KafkaSettings(enabled=True, bootstrap_servers="b:9092", topic="t"), producer=producer)
        sent = pub.publish([_event(), _event("ORDER_CLOSED", "OWOR:2")])
        assert sent == 2
        assert producer.produce.call_count == 2
        first = producer.produce.call_args_list[0]
        assert first.args[0] == "t"
        assert first.kwargs["key"] == b"OWOR:1"
        assert b'"event_type": "ORDER_CREATED"' in first.kwargs["value"]
        producer.poll.assert_called_once_with(0)
        assert pub.health_check() is True
        pub.close()
        producer.flush.assert_called_once()

    def test_publish_empty(self):
        from bdx.publish.kafka import KafkaPublisher

        pub = KafkaPublisher(KafkaSettings(enabled=True, bootstrap_servers="b"), producer=MagicMock())
        assert pub.publish([]) == 0

    def test_error_drops_producer_and_never_raises(self):
        from bdx.publish.kafka import KafkaPublisher

        producer = MagicMock()
        producer.produce.side_effect = BufferError("queue full")
        pub = KafkaPublisher(KafkaSettings(enabled=True, bootstrap_servers="b"), producer=producer)
        assert pub.publish([_event()]) == 0
        assert pub.health_check() is False  # producer dropped → recreate fails (no real broker)

    def test_composite(self):
        from bdx.publish.kafka import _Composite
        from bdx.publish.mqtt import MqttPublisher

        mqtt = MagicMock()
        mqtt.name = "mqtt"
        mqtt.health_check.return_value = True
        kafka = MagicMock()
        kafka.name = "kafka"
        kafka.health_check.return_value = True
        comp = _Composite([mqtt, kafka])
        assert comp.publish([_event()]) == 1
        mqtt.publish.assert_called_once()
        kafka.publish.assert_called_once()
        assert comp.health_check() is True
        comp.close()
        mqtt.close.assert_called_once()
        kafka.close.assert_called_once()

    def test_build_all_publishers(self):
        import os
        from unittest.mock import patch

        from bdx.publish.base import NullPublisher
        from bdx.publish.mqtt import build_all_publishers

        with patch.dict(os.environ, {"MQTT_ENABLED": "false", "KAFKA_ENABLED": "false"}, clear=False):
            assert isinstance(build_all_publishers(), NullPublisher)
