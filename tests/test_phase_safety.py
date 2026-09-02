from __future__ import annotations

import pytest

from traffic_agents.controllers import (
    PhaseCommandKind,
    PhaseDefinition,
    PhaseSafetyManager,
    PhaseSafetyViolationError,
    UnsafePhaseProgramError,
)
from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionState,
    TrafficLightAction,
)


def make_phase_program() -> tuple[PhaseDefinition, ...]:
    return (
        PhaseDefinition(
            phase_id="north_south_green",
            phase_index=0,
            signal_state="Grrr",
            duration_seconds=30.0,
        ),
        PhaseDefinition(
            phase_id="north_south_yellow",
            phase_index=1,
            signal_state="yrrr",
            duration_seconds=3.0,
        ),
        PhaseDefinition(
            phase_id="all_red_to_east_west",
            phase_index=2,
            signal_state="rrrr",
            duration_seconds=1.0,
        ),
        PhaseDefinition(
            phase_id="east_west_green",
            phase_index=3,
            signal_state="rGrr",
            duration_seconds=30.0,
        ),
        PhaseDefinition(
            phase_id="east_west_yellow",
            phase_index=4,
            signal_state="ryrr",
            duration_seconds=3.0,
        ),
        PhaseDefinition(
            phase_id="all_red_to_north_south",
            phase_index=5,
            signal_state="rrrr",
            duration_seconds=1.0,
        ),
        PhaseDefinition(
            phase_id="left_turn_green",
            phase_index=6,
            signal_state="rrGr",
            duration_seconds=30.0,
        ),
        PhaseDefinition(
            phase_id="left_turn_yellow",
            phase_index=7,
            signal_state="rryr",
            duration_seconds=3.0,
        ),
        PhaseDefinition(
            phase_id="all_red_to_north_south_after_left",
            phase_index=8,
            signal_state="rrrr",
            duration_seconds=1.0,
        ),
    )


def make_manager() -> PhaseSafetyManager:
    return PhaseSafetyManager(
        phases=make_phase_program(),
        min_green_seconds=10.0,
        allowed_green_transitions={
            "north_south_green": ("east_west_green",),
            "east_west_green": ("left_turn_green",),
            "left_turn_green": ("north_south_green",),
        },
        conflicting_signal_groups=((0, 1), (0, 2), (1, 2)),
    )


def make_observation(phase_id: str, elapsed: float) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=42.0,
            current_phase=phase_id,
            phase_elapsed=elapsed,
            incoming_queue={"lane-a": 1},
            incoming_occupancy={"lane-a": 0.25},
            incoming_speed={"lane-a": 12.0},
            outgoing_occupancy={"lane-b": 0.1},
            arrival_rate={"edge-a": 0.5},
        )
    )


def make_decision(action: TrafficLightAction) -> ControllerDecision:
    return ControllerDecision(intersection_id="A1", timestamp=42.0, action=action)


def test_min_green_boundary_allows_switch_at_exact_limit() -> None:
    command = make_manager().resolve(
        make_observation("north_south_green", elapsed=10.0),
        make_decision(TrafficLightAction.request_next_phase()),
    )

    assert command.kind == PhaseCommandKind.SET_PHASE
    assert command.phase_id == "north_south_yellow"
    assert command.phase_index == 1


def test_early_switch_is_blocked_until_min_green_elapses() -> None:
    command = make_manager().resolve(
        make_observation("north_south_green", elapsed=9.999),
        make_decision(TrafficLightAction.request_next_phase()),
    )

    assert command.kind == PhaseCommandKind.KEEP_PHASE
    assert command.phase_id == "north_south_green"
    assert command.phase_index == 0


def test_valid_transition_respects_sumo_yellow_and_intergreen_phases() -> None:
    manager = make_manager()

    yellow_command = manager.resolve(
        make_observation("north_south_green", elapsed=10.0),
        make_decision(TrafficLightAction.switch_phase("east_west_green")),
    )
    all_red_command = manager.resolve(
        make_observation("north_south_yellow", elapsed=3.0),
        make_decision(TrafficLightAction.keep_phase()),
    )
    target_green_command = manager.resolve(
        make_observation("all_red_to_east_west", elapsed=1.0),
        make_decision(TrafficLightAction.keep_phase()),
    )

    assert yellow_command.phase_id == "north_south_yellow"
    assert all_red_command.phase_id == "all_red_to_east_west"
    assert target_green_command.phase_id == "east_west_green"
    assert all(
        command.kind == PhaseCommandKind.SET_PHASE
        for command in (yellow_command, all_red_command, target_green_command)
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(PhaseSafetyViolationError, match="not allowed"):
        make_manager().resolve(
            make_observation("north_south_green", elapsed=10.0),
            make_decision(TrafficLightAction.switch_phase("left_turn_green")),
        )


def test_yellow_transition_cannot_be_shortened() -> None:
    command = make_manager().resolve(
        make_observation("north_south_yellow", elapsed=2.999),
        make_decision(TrafficLightAction.request_next_phase()),
    )

    assert command.kind == PhaseCommandKind.KEEP_PHASE
    assert command.phase_id == "north_south_yellow"


def test_controller_cannot_target_yellow_phase() -> None:
    with pytest.raises(PhaseSafetyViolationError, match="not a controllable green phase"):
        make_manager().resolve(
            make_observation("north_south_green", elapsed=10.0),
            make_decision(TrafficLightAction.switch_phase("north_south_yellow")),
        )


def test_phase_program_rejects_conflicting_green_states() -> None:
    with pytest.raises(UnsafePhaseProgramError, match="conflicting green"):
        PhaseSafetyManager(
            phases=(
                PhaseDefinition(
                    phase_id="unsafe_green",
                    phase_index=0,
                    signal_state="GGrr",
                    duration_seconds=30.0,
                ),
            ),
            min_green_seconds=10.0,
            conflicting_signal_groups=((0, 1),),
        )


def test_phase_program_rejects_conflicting_green_movements() -> None:
    with pytest.raises(UnsafePhaseProgramError, match="conflicting movements"):
        PhaseSafetyManager(
            phases=(
                PhaseDefinition(
                    phase_id="unsafe_green",
                    phase_index=0,
                    signal_state="GG",
                    duration_seconds=30.0,
                    movement_ids=("A1:north_to_south", "A1:east_to_west"),
                ),
            ),
            min_green_seconds=10.0,
            movement_conflicts={
                "A1:north_to_south": ("A1:east_to_west",),
                "A1:east_to_west": ("A1:north_to_south",),
            },
        )


def test_allowed_transition_must_follow_sumo_sequence() -> None:
    with pytest.raises(UnsafePhaseProgramError, match="yellow/intergreen sequence"):
        PhaseSafetyManager(
            phases=make_phase_program(),
            min_green_seconds=10.0,
            allowed_green_transitions={
                "north_south_green": ("left_turn_green",),
                "east_west_green": ("left_turn_green",),
                "left_turn_green": ("north_south_green",),
            },
        )
