from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, Self

from traffic_agents.communication import (
    GRID_3X3_COMMUNICATION_NEIGHBORS as _GRID_3X3_COMMUNICATION_NEIGHBORS,
)
from traffic_agents.communication import (
    GRID_3X3_INTERSECTION_IDS as _GRID_3X3_INTERSECTION_IDS,
)
from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionId,
    TrafficLightAction,
)


class AgentController(Protocol):
    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        """Choose the traffic-light action for a prepared observation."""


@dataclass(frozen=True)
class TrafficAgent:
    intersection_id: IntersectionId
    controller: AgentController
    neighbor_ids: tuple[IntersectionId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "neighbor_ids", tuple(self.neighbor_ids))

    def decide(self, observation: AgentObservation) -> ControllerDecision:
        if observation.state.intersection_id != self.intersection_id:
            msg = (
                "observation intersection_id does not match agent intersection_id: "
                f"{observation.state.intersection_id} != {self.intersection_id}"
            )
            raise ValueError(msg)

        action = self.controller.decide(observation)
        return ControllerDecision(
            intersection_id=self.intersection_id,
            timestamp=observation.state.timestamp,
            action=action,
        )


GRID_3X3_INTERSECTION_IDS: tuple[IntersectionId, ...] = _GRID_3X3_INTERSECTION_IDS
GRID_3X3_NEIGHBOR_IDS: Mapping[IntersectionId, tuple[IntersectionId, ...]] = (
    _GRID_3X3_COMMUNICATION_NEIGHBORS
)


@dataclass(frozen=True, init=False)
class AgentRegistry:
    _agents: Mapping[IntersectionId, TrafficAgent]

    def __init__(self, agents: Iterable[TrafficAgent]) -> None:
        agent_map: dict[IntersectionId, TrafficAgent] = {}
        for agent in agents:
            if agent.intersection_id in agent_map:
                msg = f"duplicate agent intersection_id: {agent.intersection_id}"
                raise ValueError(msg)
            agent_map[agent.intersection_id] = agent

        object.__setattr__(self, "_agents", MappingProxyType(agent_map))

    @classmethod
    def for_grid_3x3(cls, controller_factory: Callable[[IntersectionId], AgentController]) -> Self:
        return cls(
            TrafficAgent(
                intersection_id=intersection_id,
                controller=controller_factory(intersection_id),
                neighbor_ids=GRID_3X3_NEIGHBOR_IDS[intersection_id],
            )
            for intersection_id in GRID_3X3_INTERSECTION_IDS
        )

    @property
    def intersection_ids(self) -> tuple[IntersectionId, ...]:
        return tuple(self._agents)

    def get(self, intersection_id: IntersectionId) -> TrafficAgent:
        return self._agents[intersection_id]

    def neighbor_ids_for(self, intersection_id: IntersectionId) -> tuple[IntersectionId, ...]:
        return self.get(intersection_id).neighbor_ids

    def can_query_agent(
        self,
        source: IntersectionId,
        destination: IntersectionId,
    ) -> bool:
        return destination in self.neighbor_ids_for(source)

    def __contains__(self, intersection_id: object) -> bool:
        return intersection_id in self._agents

    def __iter__(self) -> Iterator[TrafficAgent]:
        return iter(self._agents.values())

    def __len__(self) -> int:
        return len(self._agents)
