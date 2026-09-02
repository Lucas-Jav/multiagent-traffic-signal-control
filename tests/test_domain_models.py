import pytest
from pydantic import ValidationError

from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionState,
    NeighborMessage,
    NeighborState,
    SimulationStep,
    TrafficLightAction,
    TrafficLightActionKind,
)


def make_intersection_state() -> IntersectionState:
    return IntersectionState(
        intersection_id="intersection-a",
        timestamp=10.0,
        current_phase="north_south",
        phase_elapsed=4.0,
        incoming_queue={"lane-a": 3},
        incoming_occupancy={"lane-a": 0.5},
        incoming_speed={"lane-a": 12.5},
        outgoing_occupancy={"lane-b": 0.25},
        arrival_rate={"edge-a": 0.75},
    )


def make_neighbor_state() -> NeighborState:
    return NeighborState(
        intersection_id="intersection-b",
        timestamp=10.0,
        current_phase="east_west",
        phase_elapsed=2.0,
        incoming_queue={"lane-c": 1},
        outgoing_occupancy={"lane-d": 0.4},
    )


def test_intersection_state_accepts_valid_metrics() -> None:
    state = make_intersection_state()

    assert state.intersection_id == "intersection-a"
    assert state.incoming_queue["lane-a"] == 3
    assert state.incoming_occupancy["lane-a"] == 0.5
    assert state.incoming_speed["lane-a"] == 12.5


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("timestamp", -1.0),
        ("phase_elapsed", -1.0),
        ("incoming_queue", {"lane-a": -1}),
        ("incoming_occupancy", {"lane-a": 1.1}),
        ("incoming_speed", {"lane-a": -0.1}),
        ("outgoing_occupancy", {"lane-b": -0.1}),
        ("arrival_rate", {"edge-a": -0.1}),
    ],
)
def test_intersection_state_rejects_invalid_invariants(
    field_name: str,
    invalid_value: object,
) -> None:
    payload = make_intersection_state().model_dump()
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError):
        IntersectionState.model_validate(payload)


def test_traffic_light_action_validates_required_parameters() -> None:
    keep = TrafficLightAction.keep_phase()
    request_next = TrafficLightAction.request_next_phase()
    switch = TrafficLightAction.switch_phase("east_west")

    assert keep.kind == TrafficLightActionKind.KEEP_PHASE
    assert keep.target_phase is None
    assert request_next.kind == TrafficLightActionKind.REQUEST_NEXT_PHASE
    assert request_next.target_phase is None
    assert switch.kind == TrafficLightActionKind.SWITCH_PHASE
    assert switch.target_phase == "east_west"

    with pytest.raises(ValidationError, match="target_phase is required"):
        TrafficLightAction(kind=TrafficLightActionKind.SWITCH_PHASE)

    with pytest.raises(ValidationError, match="target_phase must be omitted"):
        TrafficLightAction(kind=TrafficLightActionKind.KEEP_PHASE, target_phase="east_west")

    with pytest.raises(ValidationError, match="target_phase must be omitted"):
        TrafficLightAction(
            kind=TrafficLightActionKind.REQUEST_NEXT_PHASE,
            target_phase="east_west",
        )


def test_agent_observation_decision_and_simulation_step() -> None:
    local_state = make_intersection_state()
    neighbor_state = make_neighbor_state()
    message = NeighborMessage(
        sender_id="intersection-b",
        receiver_id="intersection-a",
        timestamp=10.0,
        state=neighbor_state,
    )
    observation = AgentObservation(
        state=local_state,
        neighbor_states=(neighbor_state,),
        messages=(message,),
    )
    decision = ControllerDecision(
        intersection_id="intersection-a",
        timestamp=10.0,
        action=TrafficLightAction.keep_phase(),
    )
    step = SimulationStep(
        step_index=1,
        timestamp=10.0,
        observations=(observation,),
        decisions=(decision,),
    )

    assert step.observations[0].state == local_state
    assert step.observations[0].messages[0].sender_id == "intersection-b"
    assert step.decisions[0].action.kind == TrafficLightActionKind.KEEP_PHASE
