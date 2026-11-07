"""MQTT publisher (paho-mqtt)."""
from __future__ import annotations

import threading
from typing import Any, Iterable

import structlog

from bdx.config import MqttSettings
from bdx.models.events import DomainEvent
from bdx.publish.base import EventPublisher, NullPublisher, event_to_message

logger = structlog.get_logger(__name__)


class MqttPublisher(EventPublisher):
    """Publishes every new domain event as retained=False JSON message.

    Topic layout: ``<prefix>/events/<EVENT_TYPE>/<source_key with ':' → '/'>``.
    The connection is lazy and re-established on failure; publishing errors are
    logged, never raised.
    """

    name = "mqtt"

    def __init__(self, settings: MqttSettings, client: Any | None = None) -> None:
        self._cfg = settings
        self._lock = threading.Lock()
        self._client = client  # injectable for tests
        self._connected = False

    # ── connection ────────────────────────────────────────────────────────────

    def _ensure_client(self) -> Any:
        if self._client is None:
            import paho.mqtt.client as mqtt  # imported lazily – optional dependency

            client = mqtt.Client(client_id=self._cfg.client_id, protocol=mqtt.MQTTv311)
            if self._cfg.username:
                client.username_pw_set(self._cfg.username, self._cfg.password or None)
            if self._cfg.tls:
                client.tls_set()
            self._client = client
        if not self._connected:
            self._client.connect(self._cfg.host, self._cfg.port, keepalive=60)
            self._client.loop_start()
            self._connected = True
            logger.info("mqtt.connected", host=self._cfg.host, port=self._cfg.port)
        return self._client

    def _drop_connection(self) -> None:
        try:
            if self._client is not None:
                self._client.loop_stop()
                self._client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        self._connected = False

    # ── EventPublisher ────────────────────────────────────────────────────────

    def publish(self, events: Iterable[DomainEvent]) -> int:
        events = list(events)
        if not events:
            return 0
        sent = 0
        with self._lock:
            try:
                client = self._ensure_client()
                for ev in events:
                    suffix, payload = event_to_message(ev)
                    topic = f"{self._cfg.topic_prefix}/events/{suffix}"
                    info = client.publish(topic, payload, qos=self._cfg.qos, retain=False)
                    rc = getattr(info, "rc", 0)
                    if rc == 0:
                        sent += 1
                    else:
                        logger.warning("mqtt.publish_failed", topic=topic, rc=rc)
            except Exception as exc:  # noqa: BLE001
                logger.warning("mqtt.error", error=str(exc))
                self._drop_connection()
        if sent:
            logger.info("mqtt.published", count=sent)
        return sent

    def health_check(self) -> bool:
        with self._lock:
            try:
                self._ensure_client()
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning("mqtt.health_failed", error=str(exc))
                self._drop_connection()
                return False

    def close(self) -> None:
        with self._lock:
            self._drop_connection()


def build_publisher(settings: MqttSettings | None = None) -> EventPublisher:
    """Return an MqttPublisher when MQTT_ENABLED=true and a host is set, else NullPublisher."""
    from bdx.config import load_mqtt_settings

    settings = settings or load_mqtt_settings()
    if settings.enabled and settings.host:
        return MqttPublisher(settings)
    return NullPublisher()


def build_all_publishers() -> EventPublisher:
    """Return a publisher covering every configured transport (MQTT + Kafka).

    A single transport returns its publisher directly; multiple transports
    return a composite that publishes to all of them.  Null when none are on.
    """
    from bdx.config import load_kafka_settings, load_mqtt_settings
    from bdx.publish.kafka import KafkaPublisher, _Composite

    publishers: list[EventPublisher] = []
    mqtt = load_mqtt_settings()
    if mqtt.enabled and mqtt.host:
        publishers.append(MqttPublisher(mqtt))
    kafka = load_kafka_settings()
    if kafka.configured:
        publishers.append(KafkaPublisher(kafka))
    if not publishers:
        return NullPublisher()
    if len(publishers) == 1:
        return publishers[0]
    return _Composite(publishers)
