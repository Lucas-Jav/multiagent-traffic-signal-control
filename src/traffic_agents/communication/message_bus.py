from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

from traffic_agents.communication.topology import (
    CommunicationTopology,
    CommunicationTopologyError,
)
from traffic_agents.domain import CompactNeighborMessage, IntersectionId, NeighborMessage

type CommunicationMessage = NeighborMessage | CompactNeighborMessage


class MessageBusError(ValueError):
    """Raised when a logical message cannot be accepted by the in-memory bus."""


class MessageBusRng(Protocol):
    def random(self) -> float: ...


@dataclass(frozen=True)
class MessageBusConfig:
    delay_steps: int = 0
    drop_probability: float = 0.0
    stale_after_steps: int | None = None

    def __post_init__(self) -> None:
        if self.delay_steps < 0:
            msg = "delay_steps must be non-negative"
            raise ValueError(msg)
        if self.drop_probability < 0.0 or self.drop_probability > 1.0:
            msg = "drop_probability must be between 0.0 and 1.0"
            raise ValueError(msg)
        if self.stale_after_steps is not None and self.stale_after_steps < 0:
            msg = "stale_after_steps must be non-negative when configured"
            raise ValueError(msg)


@dataclass(frozen=True)
class MessageBusMetrics:
    messages_sent: int = 0
    messages_delivered: int = 0
    serialized_bytes: int = 0
    messages_dropped: int = 0
    stale_messages: int = 0


@dataclass(frozen=True)
class _QueuedMessage:
    deliver_at_step: int
    message: CommunicationMessage


@dataclass
class MessageBus:
    destinations: Iterable[IntersectionId]
    config: MessageBusConfig = field(default_factory=MessageBusConfig)
    topology: CommunicationTopology | None = None
    rng: MessageBusRng | None = None
    _destinations: frozenset[IntersectionId] = field(
        default_factory=frozenset,
        init=False,
        repr=False,
    )
    _sequence_by_source: dict[IntersectionId, int] = field(
        default_factory=lambda: defaultdict(int),
        init=False,
        repr=False,
    )
    _queues_by_destination: dict[IntersectionId, list[_QueuedMessage]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _metrics: MessageBusMetrics = field(
        default_factory=MessageBusMetrics,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        destination_set = frozenset(self.destinations)
        if not destination_set:
            msg = "destinations must not be empty"
            raise ValueError(msg)
        if self.config.drop_probability > 0.0 and self.rng is None:
            msg = "rng is required when drop_probability is greater than zero"
            raise ValueError(msg)
        self._destinations = destination_set
        self._sequence_by_source = defaultdict(int)
        self._queues_by_destination = {destination: [] for destination in destination_set}
        self._metrics = MessageBusMetrics()

    @property
    def metrics(self) -> MessageBusMetrics:
        return self._metrics

    @property
    def registered_destinations(self) -> frozenset[IntersectionId]:
        return self._destinations

    def publish(
        self,
        *,
        source: IntersectionId,
        destination: IntersectionId,
        created_step: int,
        payload: Mapping[str, Any],
    ) -> NeighborMessage:
        self._validate_envelope(
            source=source,
            destination=destination,
            created_step=created_step,
        )
        sequence = self._next_sequence(source)
        message = NeighborMessage(
            message_id=f"{source}:{sequence}",
            source=source,
            destination=destination,
            created_step=created_step,
            sequence=sequence,
            payload=dict(payload),
        )
        self._record_sent(message)

        if self._should_drop():
            self._record_dropped()
            return message

        self._queues_by_destination[destination].append(
            _QueuedMessage(
                deliver_at_step=created_step + self.config.delay_steps,
                message=message,
            )
        )
        return message

    def publish_compact(self, message: CompactNeighborMessage) -> CompactNeighborMessage:
        self._validate_envelope(
            source=message.source,
            destination=message.destination,
            created_step=message.created_step,
        )
        self._record_sent(message)

        if self._should_drop():
            self._record_dropped()
            return message

        self._queues_by_destination[message.destination].append(
            _QueuedMessage(
                deliver_at_step=message.created_step + self.config.delay_steps,
                message=message,
            )
        )
        return message

    def receive(
        self,
        *,
        destination: IntersectionId,
        current_step: int,
    ) -> tuple[CommunicationMessage, ...]:
        if current_step < 0:
            msg = "current_step must be non-negative"
            raise MessageBusError(msg)
        if destination not in self._destinations:
            msg = f"invalid message destination: {destination}"
            raise MessageBusError(msg)

        queue = self._queues_by_destination[destination]
        deliverable: list[_QueuedMessage] = []
        pending: list[_QueuedMessage] = []
        stale_count = 0
        for queued in queue:
            if self._is_stale(queued.message, current_step):
                stale_count += 1
                continue
            if queued.deliver_at_step <= current_step:
                deliverable.append(queued)
            else:
                pending.append(queued)

        self._queues_by_destination[destination] = pending
        deliverable.sort(
            key=lambda queued: (
                queued.deliver_at_step,
                queued.message.created_step,
                queued.message.sequence,
                queued.message.source,
                queued.message.destination,
            )
        )
        messages = tuple(queued.message for queued in deliverable)
        self._metrics = MessageBusMetrics(
            messages_sent=self._metrics.messages_sent,
            messages_delivered=self._metrics.messages_delivered + len(messages),
            serialized_bytes=self._metrics.serialized_bytes,
            messages_dropped=self._metrics.messages_dropped,
            stale_messages=self._metrics.stale_messages + stale_count,
        )
        return messages

    def pending_count(self, destination: IntersectionId | None = None) -> int:
        if destination is not None:
            if destination not in self._destinations:
                msg = f"invalid message destination: {destination}"
                raise MessageBusError(msg)
            return len(self._queues_by_destination[destination])
        return sum(len(queue) for queue in self._queues_by_destination.values())

    def _next_sequence(self, source: IntersectionId) -> int:
        sequence = self._sequence_by_source[source]
        self._sequence_by_source[source] = sequence + 1
        return sequence

    def _validate_envelope(
        self,
        *,
        source: IntersectionId,
        destination: IntersectionId,
        created_step: int,
    ) -> None:
        if created_step < 0:
            msg = "created_step must be non-negative"
            raise MessageBusError(msg)
        if source not in self._destinations:
            msg = f"invalid message source: {source}"
            raise MessageBusError(msg)
        if destination not in self._destinations:
            msg = f"invalid message destination: {destination}"
            raise MessageBusError(msg)
        if self.topology is not None:
            try:
                self.topology.require_can_communicate(source, destination)
            except CommunicationTopologyError as exc:
                raise MessageBusError(str(exc)) from exc

    def _record_sent(self, message: CommunicationMessage) -> None:
        serialized_bytes = len(serialize_message(message))
        self._metrics = MessageBusMetrics(
            messages_sent=self._metrics.messages_sent + 1,
            messages_delivered=self._metrics.messages_delivered,
            serialized_bytes=self._metrics.serialized_bytes + serialized_bytes,
            messages_dropped=self._metrics.messages_dropped,
            stale_messages=self._metrics.stale_messages,
        )

    def _record_dropped(self) -> None:
        self._metrics = MessageBusMetrics(
            messages_sent=self._metrics.messages_sent,
            messages_delivered=self._metrics.messages_delivered,
            serialized_bytes=self._metrics.serialized_bytes,
            messages_dropped=self._metrics.messages_dropped + 1,
            stale_messages=self._metrics.stale_messages,
        )

    def _should_drop(self) -> bool:
        if self.config.drop_probability <= 0.0:
            return False
        if self.rng is None:
            msg = "rng is required when drop_probability is greater than zero"
            raise MessageBusError(msg)
        return self.rng.random() < self.config.drop_probability

    def _is_stale(self, message: CommunicationMessage, current_step: int) -> bool:
        if self.config.stale_after_steps is None:
            return False
        return current_step - message.created_step > self.config.stale_after_steps


def serialize_message(message: CommunicationMessage) -> bytes:
    payload = message.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return encoded.encode("utf-8")


def freeze_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))
