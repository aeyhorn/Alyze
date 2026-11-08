"""Publisher interface and helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable

import structlog

from bdx.models.events import DomainEvent, DomainEventDTO

logger = structlog.get_logger(__name__)


def event_to_message(event: DomainEvent) -> tuple[str, str]:
    """Return (topic_suffix, json_payload) for a domain event.

    Topic suffix: ``<event_type>/<source_key>`` with ':' replaced by '/' so that
    MQTT wildcards work, e.g. ``ORDER_RELEASED/OWOR/38561`` or
    ``MACHINE_STATE_CHANGED/MACHINE/QT350MY``.
    """
    dto = DomainEventDTO.model_validate(event)
    suffix = f"{dto.event_type.value}/{dto.source_key.replace(':', '/')}"
    return suffix, json.dumps(dto.model_dump(mode="json"), ensure_ascii=False)


class EventPublisher(ABC):
    """Fire-and-forget publisher.  Implementations must never raise into the collector."""

    name = "base"

    @abstractmethod
    def publish(self, events: Iterable[DomainEvent]) -> int:
        """Publish events; return how many were handed to the transport."""

    def health_check(self) -> bool:
        return True

    def close(self) -> None:  # noqa: B027 – optional hook
        pass


class NullPublisher(EventPublisher):
    """Default when no broker is configured."""

    name = "null"

    def publish(self, events: Iterable[DomainEvent]) -> int:
        return 0
