"""Event publishing – push new domain events to a message broker (Sprint 003).

MQTT and Kafka are optional. When no broker is configured the
:class:`NullPublisher` is used and events stay in PostgreSQL.
:class:`RecordingPublisher` captures events in memory for local checks/tests.
"""
from __future__ import annotations

from bdx.publish.base import (
    EventPublisher,
    NullPublisher,
    RecordingPublisher,
    event_to_message,
)
from bdx.publish.kafka import KafkaPublisher
from bdx.publish.mqtt import MqttPublisher, build_all_publishers, build_publisher

__all__ = [
    "EventPublisher",
    "NullPublisher",
    "RecordingPublisher",
    "MqttPublisher",
    "KafkaPublisher",
    "build_publisher",
    "build_all_publishers",
    "event_to_message",
]
