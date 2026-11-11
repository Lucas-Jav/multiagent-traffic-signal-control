"""Primitivas de comunicação entre agentes."""

from traffic_agents.communication.compact_message import (
    CompactNeighborMessageConfig,
    CompactNeighborMessageError,
    CompactNeighborMessageFactory,
    compact_message_payload,
)
from traffic_agents.communication.expanded_message import (
    ExpandedNeighborMessageError,
    ExpandedNeighborMessageFactory,
    expanded_message_payload,
)
from traffic_agents.communication.message_bus import (
    CommunicationMessage,
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
from traffic_agents.communication_seed import derive_communication_rng_seed

__all__ = [
    "GRID_3X3_COMMUNICATION_NEIGHBORS",
    "GRID_3X3_COMMUNICATION_TOPOLOGY_ID",
    "GRID_3X3_INTERSECTION_IDS",
    "CommunicationMessage",
    "CommunicationTopology",
    "CommunicationTopologyError",
    "CompactNeighborMessageConfig",
    "CompactNeighborMessageError",
    "CompactNeighborMessageFactory",
    "ExpandedNeighborMessageError",
    "ExpandedNeighborMessageFactory",
    "MessageBus",
    "MessageBusConfig",
    "MessageBusError",
    "MessageBusMetrics",
    "compact_message_payload",
    "derive_communication_rng_seed",
    "expanded_message_payload",
    "grid_3x3_communication_topology",
    "serialize_message",
]
