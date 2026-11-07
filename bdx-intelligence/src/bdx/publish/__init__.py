"""Event publishing – push new domain events to a message broker (Sprint 003).

Only MQTT is implemented (paho-mqtt).  Publishing is optional: when no broker
is configured the :class:`NullPublisher` is used and events stay in PostgreSQL.
"""
from __future__ import annotations

from bdx.publish.base import EventPublisher, NullPublisher, event_to_message
from bdx.publish.mqtt import MqttPublisher, build_publisher

__all__ = ["EventPublisher", "NullPublisher", "MqttPublisher", "build_publisher", "event_to_message"]
