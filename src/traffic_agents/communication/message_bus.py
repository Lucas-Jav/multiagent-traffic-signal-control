from __future__ import annotations

import json
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

from traffic_agents.communication.topology import (
    CommunicationTopology,
    CommunicationTopologyError,
)
from traffic_agents.communication_seed import derive_communication_rng_seed
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
    rng_seed: int | None = None
    simulation_seed: int = 0

    def __post_init__(self) -> None:
        if self.delay_steps < 0:
            msg = "delay_steps must be non-negative"
            raise ValueError(msg)
        if self.drop_probability < 0.0 or self.drop_probability > 1.0:
            msg = "drop_probability must be between 0.0 and 1.0"
            raise ValueError(msg)
        if self.rng_seed is not None and self.rng_seed < 0:
            msg = "rng_seed must be non-negative when configured"
            raise ValueError(msg)
        if self.simulation_seed < 0:
            msg = "simulation_seed must be non-negative"
            raise ValueError(msg)

    @property
    def resolved_rng_seed(self) -> int:
        if self.rng_seed is not None:
            return self.rng_seed
        return derive_communication_rng_seed(
            simulation_seed=self.simulation_seed,
            delay_steps=self.delay_steps,
            drop_probability=self.drop_probability,
        )


@dataclass(frozen=True)
class MessageBusMetrics:
    messages_sent: int = 0
    messages_delivered: int = 0
    message_delay_steps: int = 0
    average_message_delay: float = 0.0
    max_message_delay: int = 0
    serialized_bytes: int = 0
    messages_dropped: int = 0
    observed_drop_rate: float = 0.0
    stale_messages: int = 0


@dataclass(frozen=True)
class _QueuedMessage:
    delivery_step: int
    message: CommunicationMessage


@dataclass
class MessageBus:
    """Deterministic in-memory bus driven by simulation steps.

    Messages created at step t are first counted as sent. The drop decision is
    made immediately during publish with the bus' dedicated RNG; dropped
    messages never enter the delivery schedule. Messages that are not dropped
    are scheduled for t + delay_steps. A call to receive(destination=...,
    current_step=s) happens before that destination's controller decision for
    simulation step s, so a message scheduled for s can influence the decision
    taken in the same step.
    """

    destinations: Iterable[IntersectionId]
    config: MessageBusConfig = field(default_factory=MessageBusConfig)
    topology: CommunicationTopology | None = None
    rng: MessageBusRng | None = None
    _rng: MessageBusRng = field(init=False, repr=False)
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
    _scheduled_by_delivery_step: dict[int, list[_QueuedMessage]] = field(
        default_factory=lambda: defaultdict(list),
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
        self._rng = self.rng or random.Random(self.config.resolved_rng_seed)
        self._destinations = destination_set
        self._sequence_by_source = defaultdict(int)
        self._scheduled_by_delivery_step = defaultdict(list)
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
        scheduled_delivery_step = created_step + self.config.delay_steps
        message = NeighborMessage(
            message_id=f"{source}:{sequence}",
            source=source,
            destination=destination,
            created_step=created_step,
            scheduled_delivery_step=scheduled_delivery_step,
            delivered_step=None,
            sequence=sequence,
            payload=dict(payload),
        )
        self._record_sent(message)

        if self._should_drop():
            self._record_dropped()
            return message

        self._scheduled_by_delivery_step[scheduled_delivery_step].append(
            _QueuedMessage(
                delivery_step=scheduled_delivery_step,
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
        scheduled_delivery_step = message.created_step + self.config.delay_steps
        scheduled_message = message.model_copy(
            update={
                "scheduled_delivery_step": scheduled_delivery_step,
                "delivered_step": None,
            }
        )
        self._record_sent(scheduled_message)

        if self._should_drop():
            self._record_dropped()
            return scheduled_message

        self._scheduled_by_delivery_step[scheduled_delivery_step].append(
            _QueuedMessage(
                delivery_step=scheduled_delivery_step,
                message=scheduled_message,
            )
        )
        return scheduled_message

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

        deliverable: list[_QueuedMessage] = []
        delivery_steps = sorted(
            delivery_step
            for delivery_step in self._scheduled_by_delivery_step
            if delivery_step <= current_step
        )
        for delivery_step in delivery_steps:
            queue = self._scheduled_by_delivery_step[delivery_step]
            pending: list[_QueuedMessage] = []
            for queued in queue:
                if queued.message.destination != destination:
                    pending.append(queued)
                    continue
                deliverable.append(queued)

            if pending:
                self._scheduled_by_delivery_step[delivery_step] = pending
            else:
                del self._scheduled_by_delivery_step[delivery_step]

        deliverable.sort(
            key=lambda queued: (
                queued.delivery_step,
                queued.message.created_step,
                queued.message.sequence,
                queued.message.source,
                queued.message.destination,
            )
        )
        messages = tuple(
            _mark_delivered(queued.message, delivered_step=current_step) for queued in deliverable
        )
        delivered_delays = tuple(
            message.delivered_step - message.created_step
            for message in messages
            if message.delivered_step is not None
        )
        total_delay_steps = self._metrics.message_delay_steps + sum(delivered_delays)
        messages_delivered = self._metrics.messages_delivered + len(messages)
        self._metrics = MessageBusMetrics(
            messages_sent=self._metrics.messages_sent,
            messages_delivered=messages_delivered,
            message_delay_steps=total_delay_steps,
            average_message_delay=(
                total_delay_steps / messages_delivered if messages_delivered > 0 else 0.0
            ),
            max_message_delay=max(
                (self._metrics.max_message_delay, *delivered_delays),
                default=0,
            ),
            serialized_bytes=self._metrics.serialized_bytes,
            messages_dropped=self._metrics.messages_dropped,
            observed_drop_rate=_observed_drop_rate(
                messages_dropped=self._metrics.messages_dropped,
                messages_sent=self._metrics.messages_sent,
            ),
            stale_messages=self._metrics.stale_messages,
        )
        return messages

    def pending_count(self, destination: IntersectionId | None = None) -> int:
        if destination is not None:
            if destination not in self._destinations:
                msg = f"invalid message destination: {destination}"
                raise MessageBusError(msg)
            return sum(
                1
                for queue in self._scheduled_by_delivery_step.values()
                for queued in queue
                if queued.message.destination == destination
            )
        return sum(len(queue) for queue in self._scheduled_by_delivery_step.values())

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
            message_delay_steps=self._metrics.message_delay_steps,
            average_message_delay=self._metrics.average_message_delay,
            max_message_delay=self._metrics.max_message_delay,
            serialized_bytes=self._metrics.serialized_bytes + serialized_bytes,
            messages_dropped=self._metrics.messages_dropped,
            observed_drop_rate=_observed_drop_rate(
                messages_dropped=self._metrics.messages_dropped,
                messages_sent=self._metrics.messages_sent + 1,
            ),
            stale_messages=self._metrics.stale_messages,
        )

    def _record_dropped(self) -> None:
        self._metrics = MessageBusMetrics(
            messages_sent=self._metrics.messages_sent,
            messages_delivered=self._metrics.messages_delivered,
            message_delay_steps=self._metrics.message_delay_steps,
            average_message_delay=self._metrics.average_message_delay,
            max_message_delay=self._metrics.max_message_delay,
            serialized_bytes=self._metrics.serialized_bytes,
            messages_dropped=self._metrics.messages_dropped + 1,
            observed_drop_rate=_observed_drop_rate(
                messages_dropped=self._metrics.messages_dropped + 1,
                messages_sent=self._metrics.messages_sent,
            ),
            stale_messages=self._metrics.stale_messages,
        )

    def _should_drop(self) -> bool:
        if self.config.drop_probability <= 0.0:
            return False
        return self._rng.random() < self.config.drop_probability


def serialize_message(message: CommunicationMessage) -> bytes:
    payload = message.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return encoded.encode("utf-8")


def _mark_delivered(
    message: CommunicationMessage,
    *,
    delivered_step: int,
) -> CommunicationMessage:
    return message.model_copy(update={"delivered_step": delivered_step})


def _observed_drop_rate(
    *,
    messages_dropped: int,
    messages_sent: int,
) -> float:
    if messages_sent == 0:
        return 0.0
    return messages_dropped / messages_sent


def freeze_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))
