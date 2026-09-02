from __future__ import annotations

import pytest

from traffic_agents.agents import AgentRegistry, TrafficAgent
from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionState,
    TrafficLightAction,
    TrafficLightActionKind,
)


class FakeController:
    def __init__(self, action: TrafficLightAction | None = None) -> None:
        self.action = action or TrafficLightAction.keep_phase()
        self.observations: list[AgentObservation] = []

    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        self.observations.append(observation)
        return self.action


def make_observation(intersection_id: str = "A1", timestamp: float = 15.0) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id=intersection_id,
            timestamp=timestamp,
            current_phase="north_south",
            phase_elapsed=5.0,
            incoming_queue={"lane-a": 2},
            incoming_occupancy={"lane-a": 0.4},
            incoming_speed={"lane-a": 11.0},
            outgoing_occupancy={"lane-b": 0.2},
            arrival_rate={"edge-a": 0.7},
        )
    )


def test_traffic_agent_delegates_prepared_observation_to_controller() -> None:
    controller = FakeController(TrafficLightAction.switch_phase("east_west"))
    agent = TrafficAgent(
        intersection_id="A1",
        controller=controller,
        neighbor_ids=("A2", "A4"),
    )
    observation = make_observation()

    decision = agent.decide(observation)

    assert controller.observations == [observation]
    assert decision == ControllerDecision(
        intersection_id="A1",
        timestamp=15.0,
        action=TrafficLightAction.switch_phase("east_west"),
    )
    assert decision.action.kind == TrafficLightActionKind.SWITCH_PHASE
    assert agent.neighbor_ids == ("A2", "A4")


def test_traffic_agent_rejects_observation_from_other_intersection() -> None:
    agent = TrafficAgent(intersection_id="A1", controller=FakeController())

    with pytest.raises(ValueError, match="does not match"):
        agent.decide(make_observation(intersection_id="A2"))


def test_agent_registry_builds_grid_3x3_agents_without_singleton_state() -> None:
    created_for: list[str] = []

    def controller_factory(intersection_id: str) -> FakeController:
        created_for.append(intersection_id)
        return FakeController()

    registry = AgentRegistry.for_grid_3x3(controller_factory)

    assert len(registry) == 9
    assert registry.intersection_ids == ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")
    assert created_for == list(registry.intersection_ids)
    assert registry.get("A1").neighbor_ids == ("A2", "A4")
    assert registry.get("A5").neighbor_ids == ("A2", "A4", "A6", "A8")
    assert registry.get("A9").neighbor_ids == ("A6", "A8")
    assert [agent.intersection_id for agent in registry] == list(registry.intersection_ids)


def test_agent_registry_instances_are_independent() -> None:
    first = AgentRegistry.for_grid_3x3(lambda _intersection_id: FakeController())
    second = AgentRegistry.for_grid_3x3(lambda _intersection_id: FakeController())

    assert first is not second
    assert first.get("A1") is not second.get("A1")
    assert first.get("A1").controller is not second.get("A1").controller


def test_agent_registry_rejects_duplicate_intersection_ids() -> None:
    with pytest.raises(ValueError, match="duplicate agent"):
        AgentRegistry(
            (
                TrafficAgent(intersection_id="A1", controller=FakeController()),
                TrafficAgent(intersection_id="A1", controller=FakeController()),
            )
        )
