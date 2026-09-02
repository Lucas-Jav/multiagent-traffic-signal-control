"""Agent communication primitives."""

from traffic_agents.communication.message_bus import (
    MessageBus,
    MessageBusConfig,
    MessageBusError,
    MessageBusMetrics,
    serialize_message,
)
from traffic_agents.communication.topology import (
    GRID_3X3_COMMUNICATION_NEIGHBORS,
    GRID_3X3_COMMUNICATION_TOPOLOGY_ID,
    GRID_3X3_INTERSECTION_IDS,
    CommunicationTopology,
    CommunicationTopologyError,
    grid_3x3_communication_topology,
)

__all__ = [
    "GRID_3X3_COMMUNICATION_NEIGHBORS",
    "GRID_3X3_COMMUNICATION_TOPOLOGY_ID",
    "GRID_3X3_INTERSECTION_IDS",
    "CommunicationTopology",
    "CommunicationTopologyError",
    "MessageBus",
    "MessageBusConfig",
    "MessageBusError",
    "MessageBusMetrics",
    "grid_3x3_communication_topology",
    "serialize_message",
]
