from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from traffic_agents.domain import IntersectionId

GRID_3X3_COMMUNICATION_TOPOLOGY_ID = "GRID_3X3_ADJACENT_INTERSECTIONS"
GRID_3X3_INTERSECTION_IDS: tuple[IntersectionId, ...] = (
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A6",
    "A7",
    "A8",
    "A9",
)
GRID_3X3_COMMUNICATION_NEIGHBORS: Mapping[IntersectionId, tuple[IntersectionId, ...]] = (
    MappingProxyType(
        {
            "A1": ("A2", "A4"),
            "A2": ("A1", "A3", "A5"),
            "A3": ("A2", "A6"),
            "A4": ("A1", "A5", "A7"),
            "A5": ("A2", "A4", "A6", "A8"),
            "A6": ("A3", "A5", "A9"),
            "A7": ("A4", "A8"),
            "A8": ("A5", "A7", "A9"),
            "A9": ("A6", "A8"),
        }
    )
)


class CommunicationTopologyError(ValueError):
    """Raised when an agent communication query violates the topology."""


@dataclass(frozen=True, init=False)
class CommunicationTopology:
    topology_id: str
    neighbors_by_agent: Mapping[IntersectionId, tuple[IntersectionId, ...]]

    def __init__(
        self,
        *,
        topology_id: str,
        neighbors_by_agent: Mapping[IntersectionId, tuple[IntersectionId, ...]],
    ) -> None:
        if not topology_id:
            msg = "topology_id must not be empty"
            raise ValueError(msg)
        if not neighbors_by_agent:
            msg = "neighbors_by_agent must not be empty"
            raise ValueError(msg)

        normalized = {
            agent_id: tuple(neighbor_ids) for agent_id, neighbor_ids in neighbors_by_agent.items()
        }
        _validate_topology(normalized)
        object.__setattr__(self, "topology_id", topology_id)
        object.__setattr__(self, "neighbors_by_agent", MappingProxyType(normalized))

    @property
    def agent_ids(self) -> tuple[IntersectionId, ...]:
        return tuple(self.neighbors_by_agent)

    @property
    def topology_hash(self) -> str:
        payload = {
            "topology_id": self.topology_id,
            "neighbors_by_agent": {
                agent_id: list(self.neighbors_by_agent[agent_id])
                for agent_id in sorted(self.neighbors_by_agent)
            },
        }
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def neighbors_of(self, agent_id: IntersectionId) -> tuple[IntersectionId, ...]:
        try:
            return self.neighbors_by_agent[agent_id]
        except KeyError as exc:
            msg = f"unknown communication agent: {agent_id}"
            raise CommunicationTopologyError(msg) from exc

    def can_communicate(
        self,
        source: IntersectionId,
        destination: IntersectionId,
    ) -> bool:
        return destination in self.neighbors_of(source)

    def require_can_communicate(
        self,
        source: IntersectionId,
        destination: IntersectionId,
    ) -> None:
        if not self.can_communicate(source, destination):
            msg = f"communication from {source} to {destination} is not allowed by topology"
            raise CommunicationTopologyError(msg)


def grid_3x3_communication_topology() -> CommunicationTopology:
    return CommunicationTopology(
        topology_id=GRID_3X3_COMMUNICATION_TOPOLOGY_ID,
        neighbors_by_agent=GRID_3X3_COMMUNICATION_NEIGHBORS,
    )


def _validate_topology(
    neighbors_by_agent: Mapping[IntersectionId, tuple[IntersectionId, ...]],
) -> None:
    agent_ids = set(neighbors_by_agent)
    for agent_id, neighbor_ids in neighbors_by_agent.items():
        if not agent_id:
            msg = "agent ids must not be empty"
            raise ValueError(msg)
        if len(set(neighbor_ids)) != len(neighbor_ids):
            msg = f"duplicate communication neighbor for {agent_id}"
            raise ValueError(msg)
        for neighbor_id in neighbor_ids:
            if neighbor_id not in agent_ids:
                msg = f"unknown communication neighbor {neighbor_id} for {agent_id}"
                raise ValueError(msg)
            if neighbor_id == agent_id:
                msg = f"agent cannot communicate with itself: {agent_id}"
                raise ValueError(msg)
            reverse_neighbors = neighbors_by_agent[neighbor_id]
            if agent_id not in reverse_neighbors:
                msg = f"communication topology is not symmetric: {agent_id}, {neighbor_id}"
                raise ValueError(msg)
