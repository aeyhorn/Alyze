"""Kafka publisher (confluent-kafka).

Optional alternative to :mod:`bdx.publish.mqtt`.  Install the dependency with
``pip install -e ".[kafka]"``.  Like the MQTT publisher this implementation is
fire-and-forget: ``publish`` never raises into the collector.  Each event is
sent as a single JSON message to ``KAFKA_TOPIC``; the key is the event's
``source_key`` so that all events of one order/machine land on the same
partition (preserving order).
"""
from __future__ import annotations

import threading
from typing import Any, Iterable

import structlog

from bdx.config import KafkaSettings
from bdx.models.events import DomainEvent
from bdx.publish.base import EventPublisher, NullPublisher, event_to_message

logger = structlog.get_logger(__name__)


class KafkaPublisher(EventPublisher):
    """Publishes every domain event as a JSON message to a Kafka topic.

    The producer is created lazily and re-created on failure.  ``publish`` is
    thread-safe and never raises.
    """

    name = "kafka"

    def __init__(self, settings: KafkaSettings, producer: Any | None = None) -> None:
        self._cfg = settings
        self._lock = threading.Lock()
        self._producer = producer  # injectable for tests
        self._flushed = False

    # ── producer lifecycle ─────────────────────────────────────────────────────

    def _ensure_producer(self) -> Any:
        if self._producer is None:
            from confluent_kafka import Producer  # imported lazily – optional dependency

            conf = {
                "bootstrap.servers": self._cfg.bootstrap_servers,
                "client.id": self._cfg.client_id,
                "acks": self._cfg.acks,
                "request.timeout.ms": int(self._cfg.request_timeout * 1000),
                "security.protocol": self._cfg.security_protocol,
            }
            if self._cfg.security_protocol.startswith("SASL"):
                conf["sasl.mechanism"] = self._cfg.sasl_mechanism
                conf["sasl.username"] = self._cfg.username
                conf["sasl.password"] = self._cfg.password
            self._producer = Producer(conf, logger=logger.debug)
            logger.info("kafka.producer.created", brokers=self._cfg.bootstrap_servers, topic=self._cfg.topic)
        return self._producer

    def _drop(self) -> None:
        try:
            if self._producer is not None:
                self._producer.flush(timeout=2)
        except Exception:  # noqa: BLE001
            pass
        self._producer = None

    # ── EventPublisher ──────────────────────────────────────────────────────────

    def publish(self, events: Iterable[DomainEvent]) -> int:
        events = list(events)
        if not events:
            return 0
        sent = 0
        with self._lock:
            try:
                producer = self._ensure_producer()
                for ev in events:
                    suffix, payload = event_to_message(ev)
                    producer.produce(
                        self._cfg.topic,
                        key=ev.source_key.encode("utf-8"),
                        value=payload.encode("utf-8"),
                        callback=_delivery_logger,
                    )
                    sent += 1
                producer.poll(0)  # serve delivery callbacks without blocking
            except Exception as exc:  # noqa: BLE001
                logger.warning("kafka.error", error=str(exc), sent=sent)
                self._drop()
        if sent:
            logger.info("kafka.published", count=sent, topic=self._cfg.topic)
        return sent

    def health_check(self) -> bool:
        with self._lock:
            try:
                self._ensure_producer()
                # confluent_kafka has no cheap "ping"; poll(0) + metadata is the
                # closest lightweight check.  A missing broker surfaces on the
                # next produce/flush, so treat producer creation as success.
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning("kafka.health_failed", error=str(exc))
                self._drop()
                return False

    def close(self) -> None:
        with self._lock:
            self._drop()


def _delivery_logger(err, msg):  # noqa: ANN001
    if err is not None:
        logger.warning("kafka.delivery_failed", error=str(err), topic=msg.topic())


def build_kafka_publisher(settings: KafkaSettings | None = None) -> EventPublisher:
    """Return a KafkaPublisher when KAFKA_ENABLED=true and brokers are set."""
    from bdx.config import load_kafka_settings

    settings = settings or load_kafka_settings()
    if settings.configured:
        return KafkaPublisher(settings)
    return NullPublisher()


class _Composite(EventPublisher):
    """Publish to several publishers in parallel (used when MQTT and Kafka are both on)."""

    name = "composite"

    def __init__(self, publishers: list[EventPublisher]) -> None:
        self._publishers = [p for p in publishers if type(p).__name__ != "NullPublisher"]

    def publish(self, events: Iterable[DomainEvent]) -> int:
        events = list(events)
        for p in self._publishers:
            try:
                p.publish(events)
            except Exception as exc:  # noqa: BLE001
                logger.warning("composite.publish_failed", publisher=p.name, error=str(exc))
        return len(events)

    def health_check(self) -> bool:
        return all(_safe(p.health_check) for p in self._publishers)

    def close(self) -> None:
        for p in self._publishers:
            try:
                p.close()
            except Exception:  # noqa: BLE001
                pass


def _safe(fn) -> bool:  # noqa: ANN001
    try:
        return bool(fn())
    except Exception:
        return False


__all__ = ["KafkaPublisher", "build_kafka_publisher", "_Composite"]
