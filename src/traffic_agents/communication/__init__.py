"""Agent communication primitives."""

from traffic_agents.communication.message_bus import (
    MessageBus,
    MessageBusConfig,
    MessageBusError,
    MessageBusMetrics,
    serialize_message,
)

__all__ = [
    "MessageBus",
    "MessageBusConfig",
    "MessageBusError",
    "MessageBusMetrics",
    "serialize_message",
]
