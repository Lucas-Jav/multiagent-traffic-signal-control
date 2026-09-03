from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, cast

import pytest

from traffic_agents.communication import grid_3x3_communication_topology
from traffic_agents.config import CommunicationConfig, load_scenario_config
from traffic_agents.controllers import (
    COOPERATIVE_COMPACT_CONTROLLER_ID,
    COOPERATIVE_COMPACT_CONTROLLER_VERSION,
    CooperativeCompactController,
    CooperativePressureAdjustment,
    CooperativePressureConfig,
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
    CompactNeighborMessage,
    ControllerDecision,
    IntersectionState,
    NeighborMessage,
    TrafficLightActionKind,
)
from traffic_agents.traffic_model import Direction, IntersectionTrafficModel, Movement, TurnType


def make_movement(
    movement_id: str,
    *,
    incoming_edge_id: str,
    outgoing_edge_id: str,
    turn_type: str,
    link_index: int,
) -> Movement:
    return Movement(
        movement_id=movement_id,
        intersection_id="A1",
        traffic_light_id="A1",
        from_direction=cast(Direction, "north"),
        to_direction=cast(Direction, "south"),
        turn_type=cast(TurnType, turn_type),
        incoming_lane_id=f"{incoming_edge_id}_0",
        outgoing_lane_id=f"{outgoing_edge_id}_0",
        incoming_edge_id=incoming_edge_id,
        outgoing_edge_id=outgoing_edge_id,
        link_index=link_index,
    )


MOVEMENTS = (
    make_movement(
        "A1:from_A2_straight",
        incoming_edge_id="A2A1",
        outgoing_edge_id="A1A4",
        turn_type="straight",
        link_index=0,
    ),
    make_movement(
        "A1:from_A2_left",
        incoming_edge_id="A2A1",
        outgoing_edge_id="A1exit_left",
        turn_type="left",
        link_index=1,
    ),
    make_movement(
        "A1:from_A2_right",
        incoming_edge_id="A2A1",
        outgoing_edge_id="A1exit_right",
        turn_type="right",
        link_index=2,
    ),
    make_movement(
        "A1:to_A2",
        incoming_edge_id="A4A1",
        outgoing_edge_id="A1A2",
        turn_type="straight",
        link_index=3,
    ),
    make_movement(
        "A1:from_A4",
        incoming_edge_id="A4A1",
        outgoing_edge_id="A1A2",
        turn_type="right",
        link_index=4,
    ),
)

PHASES = (
    PhaseDefinition(
        phase_id="phase_0",
        phase_index=0,
        signal_state="GGGrr",
        duration_seconds=20.0,
        movement_ids=("A1:from_A2_straight", "A1:from_A2_left", "A1:from_A2_right"),
    ),
    PhaseDefinition(
        phase_id="phase_1",
        phase_index=1,
        signal_state="yyyrr",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="phase_2",
        phase_index=2,
        signal_state="rrrrr",
        duration_seconds=2.0,
    ),
    PhaseDefinition(
        phase_id="phase_3",
        phase_index=3,
        signal_state="rrrGG",
        duration_seconds=20.0,
        movement_ids=("A1:to_A2", "A1:from_A4"),
    ),
    PhaseDefinition(
        phase_id="phase_4",
        phase_index=4,
        signal_state="rrryy",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="phase_5",
        phase_index=5,
        signal_state="rrrrr",
        duration_seconds=2.0,
    ),
)


def make_traffic_model() -> IntersectionTrafficModel:
    return IntersectionTrafficModel(
        intersection_id="A1",
        traffic_light_id="A1",
        movements=MOVEMENTS,
        conflicts={movement.movement_id: () for movement in MOVEMENTS},
        phases=PHASES,
    )


def make_safety() -> PhaseSafetyManager:
    return PhaseSafetyManager(phases=PHASES, min_green_seconds=10.0)


def make_phase_calculator(
    local_config: LocalPressureConfig | None = None,
) -> PhasePressureCalculator:
    return PhasePressureCalculator(
        phases=PHASES,
        movement_pressure_calculator=MovementPressureCalculator(
            config=local_config or LocalPressureConfig(),
            movements=MOVEMENTS,
        ),
    )


def make_adjustment(
    config: CooperativePressureConfig | None = None,
) -> CooperativePressureAdjustment:
    return CooperativePressureAdjustment(
        config=config or CooperativePressureConfig(),
        traffic_model=make_traffic_model(),
        neighbor_ids=("A2", "A4"),
    )


def make_observation(
    *,
    current_phase: str = "phase_0",
    timestamp: float = 20.0,
    a2_queue: int = 0,
    a4_queue: int = 0,
    a1a2_occupancy: float = 0.0,
    messages: tuple[CompactNeighborMessage | NeighborMessage, ...] = (),
) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=timestamp,
            current_phase=current_phase,
            phase_elapsed=10.0,
            incoming_queue={
                "A2A1_0": a2_queue,
                "A4A1_0": a4_queue,
            },
            incoming_occupancy={
                "A2A1_0": 0.0,
                "A4A1_0": 0.0,
            },
            incoming_speed={
                "A2A1_0": 13.9,
                "A4A1_0": 13.9,
            },
            outgoing_occupancy={
                "A1A2_0": a1a2_occupancy,
                "A1A4_0": 0.0,
                "A1exit_left_0": 0.0,
                "A1exit_right_0": 0.0,
            },
            arrival_rate={
                "A2A1": 0.0,
                "A4A1": 0.0,
            },
        ),
        messages=messages,
    )


def make_message(
    *,
    source: str = "A2",
    destination: str = "A1",
    created_step: int = 20,
    downstream_occupancy: float = 0.0,
    outgoing_pressure: float = 0.0,
    queue_summary: dict[str, float] | None = None,
    arrival_trend: float = 0.0,
) -> CompactNeighborMessage:
    return CompactNeighborMessage(
        source=source,
        destination=destination,
        created_step=created_step,
        sequence=0,
        source_timestamp=float(created_step),
        outgoing_pressure=outgoing_pressure,
        outgoing_queue_summary=queue_summary or {},
        arrival_trend=arrival_trend,
        downstream_occupancy=downstream_occupancy,
        active_phase_group="phase_0",
    )


def make_c1(
    config: CooperativePressureConfig | None = None,
) -> CooperativeCompactController:
    controller_config = config or CooperativePressureConfig()
    return CooperativeCompactController(
        config=controller_config,
        phase_calculator=make_phase_calculator(controller_config.local_pressure),
        adjustment=make_adjustment(controller_config),
        safety=make_safety(),
    )


def make_b2(local_config: LocalPressureConfig | None = None) -> LocalPressureController:
    return LocalPressureController(
        config=local_config or LocalPressureConfig(),
        phase_calculator=make_phase_calculator(local_config),
        safety=make_safety(),
    )


def test_build_controller_registers_c1_cooperative_compact() -> None:
    controller = build_controller(COOPERATIVE_COMPACT_CONTROLLER_ID)

    assert isinstance(controller, CooperativeCompactController)
    assert controller.controller_id == "C1_COOPERATIVE_COMPACT"
    assert controller.controller_version == COOPERATIVE_COMPACT_CONTROLLER_VERSION
    assert controller.manifest_metadata()["communication_enabled"] is True
    assert controller.manifest_metadata()["local_pressure_controller_id"] == "B2_LOCAL_PRESSURE"


def test_without_valid_messages_c1_matches_b2() -> None:
    config = LocalPressureConfig(switch_score_margin=0.0)
    observation = make_observation(current_phase="phase_0", a2_queue=1, a4_queue=4)

    assert make_c1(CooperativePressureConfig(local_pressure=config)).decide(observation) == make_b2(
        config
    ).decide(observation)


def test_downstream_neighbor_saturation_reduces_corresponding_phase_score() -> None:
    adjustment = make_adjustment(
        CooperativePressureConfig(
            downstream_congestion_weight=10.0,
            projected_incoming_weight=0.0,
            directed_pressure_weight=0.0,
        )
    )
    local_scores = {"phase_0": 0.0, "phase_3": 8.0}

    result = adjustment.adjust(
        local_phase_scores=local_scores,
        observation=make_observation(
            messages=(make_message(downstream_occupancy=0.7),),
        ),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(0.0)
    assert result.phase_scores["phase_3"] == pytest.approx(1.0)
    assert result.valid_messages == 1


def test_high_future_incoming_flow_increases_related_phase_score() -> None:
    adjustment = make_adjustment(
        CooperativePressureConfig(
            projected_incoming_weight=1.0,
            directed_pressure_weight=0.0,
            downstream_congestion_weight=0.0,
        )
    )

    result = adjustment.adjust(
        local_phase_scores={"phase_0": 0.0, "phase_3": 0.0},
        observation=make_observation(
            messages=(
                make_message(
                    queue_summary={"straight": 10.0},
                    arrival_trend=5.0,
                    outgoing_pressure=100.0,
                ),
            ),
        ),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(15.0)
    assert result.phase_scores["phase_3"] == pytest.approx(0.0)


def test_stale_message_is_ignored() -> None:
    adjustment = make_adjustment(CooperativePressureConfig(stale_after_steps=1))

    result = adjustment.adjust(
        local_phase_scores={"phase_0": 0.0, "phase_3": 0.0},
        observation=make_observation(
            messages=(make_message(created_step=18, queue_summary={"straight": 100.0}),),
        ),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(0.0)
    assert result.stale_messages == 1
    assert result.valid_messages == 0


def test_non_neighbor_message_is_rejected() -> None:
    adjustment = make_adjustment()

    result = adjustment.adjust(
        local_phase_scores={"phase_0": 0.0, "phase_3": 0.0},
        observation=make_observation(
            messages=(make_message(source="A9", queue_summary={"straight": 100.0}),),
        ),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(0.0)
    assert result.rejected_messages == 1


def test_invalid_message_schema_is_registered_and_ignored() -> None:
    adjustment = make_adjustment()
    invalid_message = NeighborMessage(
        message_id="A2:0",
        source="A2",
        destination="A1",
        created_step=20,
        sequence=0,
        payload={"not": "a compact message"},
    )

    result = adjustment.adjust(
        local_phase_scores={"phase_0": 0.0, "phase_3": 0.0},
        observation=make_observation(messages=(invalid_message,)),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(0.0)
    assert result.invalid_messages == 1


def test_conflicting_movements_remain_impossible() -> None:
    with pytest.raises(UnsafePhaseProgramError, match="conflicting movements"):
        PhaseSafetyManager(
            phases=(
                PhaseDefinition(
                    phase_id="unsafe",
                    phase_index=0,
                    signal_state="GG",
                    duration_seconds=20.0,
                    movement_ids=("a", "b"),
                ),
            ),
            min_green_seconds=10.0,
            movement_conflicts={"a": ("b",), "b": ("a",)},
        )


def test_turning_traffic_affects_only_related_movements() -> None:
    adjustment = make_adjustment(
        CooperativePressureConfig(
            projected_incoming_weight=1.0,
            directed_pressure_weight=0.0,
            downstream_congestion_weight=0.0,
            straight_turn_weight=0.5,
            left_turn_weight=0.3,
            right_turn_weight=0.2,
        )
    )
    result = adjustment.adjust(
        local_phase_scores={"phase_0": 0.0, "phase_3": 0.0},
        observation=make_observation(
            messages=(make_message(queue_summary={"left": 12.0}, arrival_trend=8.0),),
        ),
        current_step=20,
    )

    assert result.phase_scores["phase_0"] == pytest.approx(20.0)
    assert result.phase_scores["phase_3"] == pytest.approx(0.0)


def test_c1_uses_phase_safety_manager_for_min_green_and_clearance() -> None:
    controller = make_c1()
    observation = make_observation(
        current_phase="phase_0",
        a2_queue=0,
        a4_queue=30,
        messages=(make_message(downstream_occupancy=1.0),),
    )
    action = controller.decide(observation)
    safety = controller.safety
    assert safety is not None

    command = safety.resolve(
        AgentObservation(
            state=observation.state.model_copy(update={"phase_elapsed": 9.0}),
            messages=observation.messages,
        ),
        ControllerDecision(
            intersection_id="A1",
            timestamp=observation.state.timestamp,
            action=action,
        ),
    )

    assert action.kind == TrafficLightActionKind.SWITCH_PHASE
    assert command.phase_id == "phase_0"


def test_c1_never_uses_global_state_or_raw_signal_commands() -> None:
    tree = ast.parse(
        Path("src/traffic_agents/controllers/cooperative_compact.py").read_text(encoding="utf-8")
    )
    forbidden_attributes = {
        "setRedYellowGreenState",
        "setLinkState",
        "getIDList",
        "getSubscriptionResults",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attributes
        if isinstance(node, ast.Import):
            assert all(alias.name != "traci" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "traci"


def test_runtime_message_bus_uses_explicit_communication_topology() -> None:
    topology = grid_3x3_communication_topology()

    assert topology.can_communicate("A1", "A2")
    assert not topology.can_communicate("A1", "A9")


def test_configure_uses_scenario_communication_delay_steps() -> None:
    scenario = load_scenario_config(Path("scenarios/grid_3x3/scenario.yaml")).model_copy(
        update={"communication": CommunicationConfig(delay_steps=3)}
    )
    controller = CooperativeCompactController()

    controller.configure(
        scenario_config=scenario,
        scenario_dir=Path("scenarios/grid_3x3"),
    )

    assert controller.config.message_bus.delay_steps == 3


@pytest.mark.parametrize(
    "kwargs",
    [
        {"stale_after_steps": -1},
        {"projected_incoming_weight": -0.1},
        {"directed_pressure_weight": -0.1},
        {"downstream_congestion_weight": -0.1},
        {"straight_turn_weight": -0.1},
        {"left_turn_weight": -0.1},
        {"right_turn_weight": -0.1},
    ],
)
def test_cooperative_pressure_config_rejects_invalid_values(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        CooperativePressureConfig(**kwargs)
