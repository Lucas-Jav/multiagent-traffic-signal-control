from __future__ import annotations

from typing import Any

import pytest

from traffic_agents.controllers import (
    LOCAL_PRESSURE_CONTROLLER_ID,
    LOCAL_PRESSURE_CONTROLLER_VERSION,
    LocalPressureConfig,
    LocalPressureController,
    MovementPressureCalculator,
    PhaseDefinition,
    PhasePressureCalculator,
    PhaseSafetyManager,
    UnsafePhaseProgramError,
    build_controller,
)
from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionState,
    NeighborMessage,
    NeighborState,
    TrafficLightAction,
    TrafficLightActionKind,
)
from traffic_agents.traffic_model import Movement


def make_movement(
    movement_id: str,
    *,
    from_direction: str,
    to_direction: str,
    turn_type: str,
    incoming_lane_id: str,
    outgoing_lane_id: str,
    link_index: int,
) -> Movement:
    return Movement(
        movement_id=movement_id,
        intersection_id="A1",
        traffic_light_id="A1",
        from_direction=from_direction,  # type: ignore[arg-type]
        to_direction=to_direction,  # type: ignore[arg-type]
        turn_type=turn_type,  # type: ignore[arg-type]
        incoming_lane_id=incoming_lane_id,
        outgoing_lane_id=outgoing_lane_id,
        incoming_edge_id=incoming_lane_id.rsplit("_", 1)[0],
        outgoing_edge_id=outgoing_lane_id.rsplit("_", 1)[0],
        link_index=link_index,
    )


MOVEMENTS = (
    make_movement(
        "A1:north_to_south",
        from_direction="north",
        to_direction="south",
        turn_type="straight",
        incoming_lane_id="north_in_0",
        outgoing_lane_id="south_out_0",
        link_index=0,
    ),
    make_movement(
        "A1:north_to_east",
        from_direction="north",
        to_direction="east",
        turn_type="left",
        incoming_lane_id="north_in_0",
        outgoing_lane_id="east_out_0",
        link_index=1,
    ),
    make_movement(
        "A1:east_to_west",
        from_direction="east",
        to_direction="west",
        turn_type="straight",
        incoming_lane_id="east_in_0",
        outgoing_lane_id="west_out_0",
        link_index=2,
    ),
    make_movement(
        "A1:west_to_east",
        from_direction="west",
        to_direction="east",
        turn_type="straight",
        incoming_lane_id="west_in_0",
        outgoing_lane_id="east_out_0",
        link_index=3,
    ),
)


PHASES = (
    PhaseDefinition(
        phase_id="phase_0",
        phase_index=0,
        signal_state="Grrr",
        duration_seconds=20.0,
        movement_ids=("A1:north_to_south",),
    ),
    PhaseDefinition(
        phase_id="phase_1",
        phase_index=1,
        signal_state="yrrr",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="phase_2",
        phase_index=2,
        signal_state="rrrr",
        duration_seconds=2.0,
    ),
    PhaseDefinition(
        phase_id="phase_3",
        phase_index=3,
        signal_state="rGrr",
        duration_seconds=20.0,
        movement_ids=("A1:north_to_east",),
    ),
    PhaseDefinition(
        phase_id="phase_4",
        phase_index=4,
        signal_state="ryrr",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="phase_5",
        phase_index=5,
        signal_state="rrrr",
        duration_seconds=2.0,
    ),
    PhaseDefinition(
        phase_id="phase_6",
        phase_index=6,
        signal_state="rrGg",
        duration_seconds=20.0,
        movement_ids=("A1:east_to_west", "A1:west_to_east"),
    ),
    PhaseDefinition(
        phase_id="phase_7",
        phase_index=7,
        signal_state="rryy",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="phase_8",
        phase_index=8,
        signal_state="rrrr",
        duration_seconds=2.0,
    ),
)


def make_observation(
    *,
    current_phase: str = "phase_0",
    elapsed: float = 10.0,
    north_queue: int = 0,
    east_queue: int = 0,
    west_queue: int = 0,
    south_out_occupancy: float = 0.0,
    east_out_occupancy: float = 0.0,
    west_out_occupancy: float = 0.0,
    neighbor_states: tuple[NeighborState, ...] = (),
    messages: tuple[NeighborMessage, ...] = (),
) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=20.0,
            current_phase=current_phase,
            phase_elapsed=elapsed,
            incoming_queue={
                "north_in_0": north_queue,
                "east_in_0": east_queue,
                "west_in_0": west_queue,
            },
            incoming_occupancy={
                "north_in_0": 0.0,
                "east_in_0": 0.0,
                "west_in_0": 0.0,
            },
            incoming_speed={
                "north_in_0": 13.9,
                "east_in_0": 13.9,
                "west_in_0": 13.9,
            },
            outgoing_occupancy={
                "south_out_0": south_out_occupancy,
                "east_out_0": east_out_occupancy,
                "west_out_0": west_out_occupancy,
            },
            arrival_rate={
                "north_in": 0.0,
                "east_in": 0.0,
                "west_in": 0.0,
            },
        ),
        neighbor_states=neighbor_states,
        messages=messages,
    )


def make_calculators(
    config: LocalPressureConfig | None = None,
) -> tuple[MovementPressureCalculator, PhasePressureCalculator]:
    movement_calculator = MovementPressureCalculator(
        config=config or LocalPressureConfig(downstream_occupancy_weight=10.0),
        movements=MOVEMENTS,
    )
    phase_calculator = PhasePressureCalculator(
        phases=PHASES,
        movement_pressure_calculator=movement_calculator,
    )
    return movement_calculator, phase_calculator


def make_safety() -> PhaseSafetyManager:
    return PhaseSafetyManager(
        phases=PHASES,
        min_green_seconds=10.0,
        movement_conflicts={
            "A1:north_to_south": ("A1:east_to_west",),
            "A1:north_to_east": ("A1:east_to_west", "A1:west_to_east"),
            "A1:east_to_west": ("A1:north_to_south", "A1:north_to_east"),
            "A1:west_to_east": ("A1:north_to_east",),
        },
    )


def make_controller(
    config: LocalPressureConfig | None = None,
) -> LocalPressureController:
    _movement_calculator, phase_calculator = make_calculators(config)
    return LocalPressureController(
        config=config or LocalPressureConfig(downstream_occupancy_weight=10.0),
        phase_calculator=phase_calculator,
        safety=make_safety(),
    )


def test_build_controller_registers_b2_local_pressure() -> None:
    controller = build_controller(LOCAL_PRESSURE_CONTROLLER_ID)

    assert isinstance(controller, LocalPressureController)
    assert controller.controller_id == "B2_LOCAL_PRESSURE"
    assert controller.controller_version == LOCAL_PRESSURE_CONTROLLER_VERSION
    assert controller.manifest_metadata()["communication_enabled"] is False


def test_large_upstream_queue_and_free_downstream_has_high_pressure() -> None:
    movement_calculator, _phase_calculator = make_calculators()

    scores = movement_calculator.calculate(
        make_observation(north_queue=12, south_out_occupancy=0.0)
    )

    assert scores["A1:north_to_south"] == pytest.approx(12.0)


def test_large_upstream_queue_and_saturated_downstream_is_penalized() -> None:
    movement_calculator, _phase_calculator = make_calculators()

    free_score = movement_calculator.score_movement(
        make_observation(north_queue=12, south_out_occupancy=0.0),
        "A1:north_to_south",
    )
    saturated_score = movement_calculator.score_movement(
        make_observation(north_queue=12, south_out_occupancy=1.0),
        "A1:north_to_south",
    )

    assert saturated_score == pytest.approx(2.0)
    assert saturated_score < free_score


def test_left_turn_with_high_queue_scores_its_origin_and_destination() -> None:
    _movement_calculator, phase_calculator = make_calculators()

    scores = phase_calculator.calculate(
        make_observation(
            current_phase="phase_0",
            north_queue=15,
            south_out_occupancy=1.0,
            east_out_occupancy=0.0,
        )
    )

    assert scores["phase_3"] == pytest.approx(15.0)
    assert scores["phase_3"] > scores["phase_0"]


def test_competing_movements_choose_highest_allowed_safe_phase() -> None:
    action = make_controller().decide(
        make_observation(
            current_phase="phase_3",
            elapsed=10.0,
            east_queue=4,
            west_queue=8,
            north_queue=0,
            east_out_occupancy=0.0,
            west_out_occupancy=0.0,
        )
    )

    assert action.kind == TrafficLightActionKind.SWITCH_PHASE
    assert action.target_phase == "phase_6"


def test_phase_switch_is_blocked_by_min_green() -> None:
    controller = make_controller()
    observation = make_observation(
        current_phase="phase_0",
        elapsed=9.0,
        north_queue=0,
        south_out_occupancy=1.0,
        east_out_occupancy=0.0,
    )
    decision = controller.decide(observation)

    command = controller.safety.resolve(  # type: ignore[union-attr]
        observation,
        ControllerDecision(
            intersection_id="A1",
            timestamp=observation.state.timestamp,
            action=decision,
        ),
    )

    assert decision.kind == TrafficLightActionKind.SWITCH_PHASE
    assert command.phase_id == "phase_0"


def test_higher_score_phase_opens_after_yellow_and_all_red_clearance() -> None:
    controller = make_controller()
    safety = controller.safety
    assert safety is not None
    green_observation = make_observation(
        current_phase="phase_0",
        elapsed=10.0,
        north_queue=0,
        south_out_occupancy=1.0,
    )
    green_action = controller.decide(green_observation)
    yellow_command = safety.resolve(
        green_observation,
        ControllerDecision(
            intersection_id="A1",
            timestamp=green_observation.state.timestamp,
            action=green_action,
        ),
    )
    all_red_command = safety.resolve_action(
        make_observation(current_phase="phase_1", elapsed=3.0),
        TrafficLightAction.keep_phase(),
    )
    target_command = safety.resolve_action(
        make_observation(current_phase="phase_2", elapsed=2.0),
        TrafficLightAction.keep_phase(),
    )

    assert green_action.target_phase == "phase_3"
    assert yellow_command.phase_id == "phase_1"
    assert all_red_command.phase_id == "phase_2"
    assert target_command.phase_id == "phase_3"


def test_neighbor_information_does_not_change_local_pressure_decision() -> None:
    controller = make_controller()
    local_only = make_observation(current_phase="phase_0", elapsed=10.0, north_queue=0)
    neighbor_state = NeighborState(
        intersection_id="A2",
        timestamp=20.0,
        current_phase="phase_6",
        phase_elapsed=55.0,
        incoming_queue={"remote_lane": 100},
        outgoing_occupancy={"remote_out": 1.0},
    )
    with_neighbor = make_observation(
        current_phase="phase_0",
        elapsed=10.0,
        north_queue=0,
        neighbor_states=(neighbor_state,),
        messages=(
            NeighborMessage(
                sender_id="A2",
                receiver_id="A1",
                timestamp=20.0,
                state=neighbor_state,
            ),
        ),
    )

    assert controller.decide(local_only) == controller.decide(with_neighbor)


def test_conflicting_green_phase_program_is_rejected_before_b2_can_use_it() -> None:
    with pytest.raises(UnsafePhaseProgramError, match="conflicting movements"):
        PhaseSafetyManager(
            phases=(
                PhaseDefinition(
                    phase_id="unsafe",
                    phase_index=0,
                    signal_state="GG",
                    duration_seconds=20.0,
                    movement_ids=("A1:north_to_east", "A1:east_to_west"),
                ),
            ),
            min_green_seconds=10.0,
            movement_conflicts={
                "A1:north_to_east": ("A1:east_to_west",),
                "A1:east_to_west": ("A1:north_to_east",),
            },
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_green_seconds": -0.1},
        {"max_green_seconds": 0.0},
        {"queue_weight": -0.1},
        {"arrival_rate_weight": -0.1},
        {"downstream_occupancy_weight": -0.1},
        {"downstream_saturation_occupancy": 0.0},
        {"downstream_saturation_occupancy": 1.1},
        {"switch_score_margin": -0.1},
        {"internal_clearance_halting_threshold": -1},
    ],
)
def test_config_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        LocalPressureConfig(**kwargs)
