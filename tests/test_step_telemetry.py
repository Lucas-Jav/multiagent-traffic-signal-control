from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

from traffic_agents.config import TurningRatiosConfig
from traffic_agents.controllers import PhaseDefinition, PhaseSafetyManager
from traffic_agents.domain import AgentObservation, IntersectionState, TrafficLightAction
from traffic_agents.metrics import (
    JunctionFlowTracker,
    JunctionStepMetrics,
    MovementQueueStats,
    MovementQueueTracker,
    StepTelemetryRecord,
    append_step_telemetry,
    build_step_telemetry_records,
)
from traffic_agents.traffic_model import Direction, IntersectionTrafficModel, Movement, TurnType


def make_movement(
    movement_id: str,
    *,
    turn_type: str,
    incoming_lane_id: str,
    link_index: int,
) -> Movement:
    return Movement(
        movement_id=movement_id,
        intersection_id="A1",
        traffic_light_id="A1",
        from_direction=cast(Direction, "north"),
        to_direction=cast(Direction, "south"),
        turn_type=cast(TurnType, turn_type),
        incoming_lane_id=incoming_lane_id,
        outgoing_lane_id=f"out_{link_index}_0",
        incoming_edge_id=incoming_lane_id.rsplit("_", 1)[0],
        outgoing_edge_id=f"out_{link_index}",
        link_index=link_index,
    )


def make_traffic_model() -> IntersectionTrafficModel:
    movements = (
        make_movement(
            "A1:straight",
            turn_type="straight",
            incoming_lane_id="north_in_0",
            link_index=0,
        ),
        make_movement(
            "A1:left",
            turn_type="left",
            incoming_lane_id="north_in_0",
            link_index=1,
        ),
        make_movement(
            "A1:right",
            turn_type="right",
            incoming_lane_id="east_in_0",
            link_index=2,
        ),
    )
    return IntersectionTrafficModel(
        intersection_id="A1",
        traffic_light_id="A1",
        movements=movements,
        conflicts={movement.movement_id: () for movement in movements},
        phases=(
            PhaseDefinition(
                phase_id="phase_0",
                phase_index=0,
                signal_state="Grr",
                duration_seconds=20.0,
                movement_ids=("A1:straight",),
            ),
            PhaseDefinition(
                phase_id="phase_1",
                phase_index=1,
                signal_state="yrr",
                duration_seconds=3.0,
            ),
            PhaseDefinition(
                phase_id="phase_2",
                phase_index=2,
                signal_state="rrr",
                duration_seconds=2.0,
            ),
            PhaseDefinition(
                phase_id="phase_3",
                phase_index=3,
                signal_state="rGG",
                duration_seconds=20.0,
                movement_ids=("A1:left", "A1:right"),
            ),
        ),
    )


def make_observation() -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=30.0,
            current_phase="phase_0",
            phase_elapsed=10.0,
            incoming_queue={"north_in_0": 10, "east_in_0": 5},
            incoming_occupancy={"north_in_0": 0.5, "east_in_0": 0.25},
            incoming_speed={"north_in_0": 6.0, "east_in_0": 8.0},
            outgoing_occupancy={"out_0_0": 0.0, "out_1_0": 0.0, "out_2_0": 0.0},
            arrival_rate={"north_in": 1.0, "east_in": 2.0},
        )
    )


def test_build_step_telemetry_records_contains_scientific_debug_fields() -> None:
    traffic_model = make_traffic_model()
    safety = PhaseSafetyManager(phases=traffic_model.phases, min_green_seconds=10.0)
    command = safety.resolve_action(
        make_observation(),
        TrafficLightAction.switch_phase("phase_3"),
    )

    records = build_step_telemetry_records(
        step_index=12,
        observation=make_observation(),
        action=TrafficLightAction.switch_phase("phase_3"),
        command=command,
        safety=safety,
        traffic_model=traffic_model,
        turning_ratios=TurningRatiosConfig(straight=0.6, left=0.2, right=0.2),
        junction_metrics=JunctionStepMetrics(
            entries=3,
            exits=1,
            blocking_events=2,
            internal_vehicle_count=1,
        ),
        movement_queue_stats={
            "A1:straight": MovementQueueStats(mean=7.5, max=10),
            "A1:left": MovementQueueStats(mean=7.5, max=10),
            "A1:right": MovementQueueStats(mean=2.5, max=5),
        },
        is_warmup=True,
    )

    assert len(records) == 3
    first = records[0]
    assert first.intersection_id == "A1"
    assert first.movement_id == "A1:straight"
    assert first.approach_id == "north_in"
    assert first.queue == 10
    assert first.occupancy == 0.5
    assert first.speed == 6.0
    assert first.current_phase == "phase_0"
    assert first.phase_elapsed == 10.0
    assert first.requested_phase == "phase_3"
    assert first.actual_phase == "phase_1"
    assert first.safety_override is True
    assert first.turn_count_straight == 6.0
    assert first.turn_count_left == 2.0
    assert first.turn_count_right == 1.0
    assert first.junction_entries == 3
    assert first.junction_exits == 1
    assert first.junction_blocking_events == 2
    assert first.clearance_violations == 0
    assert abs(first.turn_completion_count - (6 / 9)) < 0.000001
    assert first.movement_queue_mean == 7.5
    assert first.movement_queue_max == 10
    assert first.is_warmup is True


def test_junction_flow_tracker_counts_entries_and_exits_without_logging_vehicle_positions() -> None:
    class FakeLaneReader:
        def __init__(self) -> None:
            self.vehicle_ids = {
                ":A1_0_0": ("veh-a", "veh-b"),
                ":A1_1_0": (),
            }

        def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]:  # noqa: N802
            return self.vehicle_ids[lane_id]

    tracker = JunctionFlowTracker()
    lane_reader = FakeLaneReader()

    first = tracker.update(
        intersection_id="A1",
        internal_lane_ids=(":A1_0_0", ":A1_1_0"),
        lane_reader=lane_reader,
    )
    assert first.entries == 2
    assert first.exits == 0
    assert first.blocking_events == 0
    lane_reader.vehicle_ids = {
        ":A1_0_0": ("veh-b", "veh-c"),
        ":A1_1_0": (),
    }

    second = tracker.update(
        intersection_id="A1",
        internal_lane_ids=(":A1_0_0", ":A1_1_0"),
        lane_reader=lane_reader,
    )
    assert second.entries == 1
    assert second.exits == 1
    assert second.blocking_events == 1


def test_clearance_violation_flags_green_with_internal_vehicle_present() -> None:
    traffic_model = make_traffic_model()
    safety = PhaseSafetyManager(phases=traffic_model.phases, min_green_seconds=10.0)
    command = safety.resolve_action(make_observation(), TrafficLightAction.keep_phase())

    records = build_step_telemetry_records(
        step_index=12,
        observation=make_observation(),
        action=TrafficLightAction.keep_phase(),
        command=command,
        safety=safety,
        traffic_model=traffic_model,
        turning_ratios=TurningRatiosConfig(straight=0.6, left=0.2, right=0.2),
        junction_metrics=JunctionStepMetrics(
            entries=0,
            exits=0,
            blocking_events=1,
            internal_vehicle_count=1,
        ),
    )

    assert records[0].clearance_violations == 1


def test_movement_queue_tracker_reports_running_mean_and_max() -> None:
    traffic_model = make_traffic_model()
    tracker = MovementQueueTracker()
    tracker.update(observation=make_observation(), traffic_model=traffic_model)
    updated = tracker.update(
        observation=AgentObservation(
            state=make_observation().state.model_copy(
                update={"incoming_queue": {"north_in_0": 4, "east_in_0": 9}}
            )
        ),
        traffic_model=traffic_model,
    )

    assert updated["A1:straight"].mean == 7.0
    assert updated["A1:straight"].max == 10
    assert updated["A1:right"].mean == 7.0
    assert updated["A1:right"].max == 9


def test_movement_queue_tracker_excludes_warmup_samples_from_running_stats() -> None:
    traffic_model = make_traffic_model()
    tracker = MovementQueueTracker()
    warmup = tracker.update(
        observation=make_observation(),
        traffic_model=traffic_model,
        include_sample=False,
    )
    measurement = tracker.update(
        observation=AgentObservation(
            state=make_observation().state.model_copy(
                update={"incoming_queue": {"north_in_0": 4, "east_in_0": 9}}
            )
        ),
        traffic_model=traffic_model,
    )

    assert warmup["A1:straight"].mean == 10.0
    assert warmup["A1:straight"].max == 10
    assert measurement["A1:straight"].mean == 4.0
    assert measurement["A1:straight"].max == 4


def test_append_step_telemetry_writes_csv_without_vehicle_position_columns(tmp_path: Path) -> None:
    path = tmp_path / "intersection_trace.csv"
    append_step_telemetry(
        path,
        (
            StepTelemetryRecord(
                step_index=1,
                timestamp=1.0,
                intersection_id="A1",
                movement_id="m1",
                approach_id="edge-a",
                queue=2,
                occupancy=0.1,
                speed=5.0,
                current_phase="phase_0",
                phase_elapsed=1.0,
                requested_phase="phase_3",
                actual_phase="phase_1",
                safety_override=True,
                turn_count_straight=1.2,
                turn_count_left=0.4,
                turn_count_right=0.4,
                junction_entries=1,
                junction_exits=0,
                junction_blocking_events=0,
                clearance_violations=0,
                turn_completion_count=0.0,
                movement_queue_mean=2.0,
                movement_queue_max=2,
                is_warmup=True,
            ),
        ),
    )

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["movement_id"] == "m1"
    assert rows[0]["safety_override"] == "True"
    assert rows[0]["is_warmup"] == "True"
    assert "vehicle_id" not in rows[0]
    assert "vehicle_position" not in rows[0]
