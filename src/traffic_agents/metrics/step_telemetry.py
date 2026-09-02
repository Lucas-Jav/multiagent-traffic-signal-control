from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, cast

from traffic_agents.config import TurningRatiosConfig
from traffic_agents.controllers.phase_safety import (
    PhaseCommand,
    PhaseKind,
    PhaseSafetyManager,
)
from traffic_agents.domain import AgentObservation, IntersectionId, TrafficLightAction
from traffic_agents.traffic_model import IntersectionTrafficModel, TurnType


@dataclass(frozen=True)
class StepTelemetryRecord:
    step_index: int
    timestamp: float
    intersection_id: str
    movement_id: str
    approach_id: str
    queue: int
    occupancy: float
    speed: float
    current_phase: str
    phase_elapsed: float
    requested_phase: str
    actual_phase: str
    safety_override: bool
    turn_count_straight: float
    turn_count_left: float
    turn_count_right: float
    junction_entries: int
    junction_exits: int


class InternalLaneVehicleReader(Protocol):
    def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]: ...  # noqa: N802


class JunctionFlowTracker:
    def __init__(self) -> None:
        self._vehicle_ids_by_intersection: dict[IntersectionId, frozenset[str]] = {}

    def update(
        self,
        *,
        intersection_id: IntersectionId,
        internal_lane_ids: tuple[str, ...],
        lane_reader: InternalLaneVehicleReader | None,
    ) -> tuple[int, int]:
        current_vehicle_ids = _read_internal_vehicle_ids(lane_reader, internal_lane_ids)
        previous_vehicle_ids = self._vehicle_ids_by_intersection.get(
            intersection_id,
            frozenset(),
        )
        self._vehicle_ids_by_intersection[intersection_id] = current_vehicle_ids
        entries = len(current_vehicle_ids - previous_vehicle_ids)
        exits = len(previous_vehicle_ids - current_vehicle_ids)
        return entries, exits


def build_step_telemetry_records(
    *,
    step_index: int,
    observation: AgentObservation,
    action: TrafficLightAction,
    command: PhaseCommand,
    safety: PhaseSafetyManager,
    traffic_model: IntersectionTrafficModel,
    turning_ratios: TurningRatiosConfig,
    junction_entries: int,
    junction_exits: int,
) -> tuple[StepTelemetryRecord, ...]:
    state = observation.state
    requested_phase = requested_phase_id(observation, action, safety)
    turn_counts = _turn_counts(
        observation=observation,
        traffic_model=traffic_model,
        turning_ratios=turning_ratios,
    )
    return tuple(
        StepTelemetryRecord(
            step_index=step_index,
            timestamp=state.timestamp,
            intersection_id=state.intersection_id,
            movement_id=movement.movement_id,
            approach_id=movement.incoming_edge_id,
            queue=state.incoming_queue.get(movement.incoming_lane_id, 0),
            occupancy=state.incoming_occupancy.get(movement.incoming_lane_id, 0.0),
            speed=state.incoming_speed.get(movement.incoming_lane_id, 0.0),
            current_phase=state.current_phase,
            phase_elapsed=state.phase_elapsed,
            requested_phase=requested_phase,
            actual_phase=command.phase_id,
            safety_override=requested_phase != command.phase_id,
            turn_count_straight=turn_counts["straight"],
            turn_count_left=turn_counts["left"],
            turn_count_right=turn_counts["right"],
            junction_entries=junction_entries,
            junction_exits=junction_exits,
        )
        for movement in traffic_model.movements
    )


def requested_phase_id(
    observation: AgentObservation,
    action: TrafficLightAction,
    safety: PhaseSafetyManager,
) -> str:
    current_phase = next(
        phase for phase in safety.phases if phase.phase_id == observation.state.current_phase
    )
    if action.kind == TrafficLightAction.KEEP_PHASE:
        return current_phase.phase_id
    if action.kind == TrafficLightAction.SWITCH_PHASE and action.target_phase is not None:
        return action.target_phase
    if (
        action.kind == TrafficLightAction.REQUEST_NEXT_PHASE
        and current_phase.kind == PhaseKind.GREEN
    ):
        return safety.allowed_green_transitions[current_phase.phase_id][0]
    return current_phase.phase_id


def append_step_telemetry(path: Path, records: tuple[StepTelemetryRecord, ...]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(StepTelemetryRecord.__dataclass_fields__))
        if write_header:
            writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def internal_lane_vehicle_reader(
    connection: object,
) -> InternalLaneVehicleReader | None:
    lane = getattr(connection, "lane", None)
    if lane is None:
        return None
    reader = getattr(lane, "getLastStepVehicleIDs", None)
    if not callable(reader):
        return None
    return cast(InternalLaneVehicleReader, lane)


def _turn_counts(
    *,
    observation: AgentObservation,
    traffic_model: IntersectionTrafficModel,
    turning_ratios: TurningRatiosConfig,
) -> dict[TurnType, float]:
    turn_counts: dict[TurnType, float] = {"straight": 0.0, "left": 0.0, "right": 0.0}
    for movement in traffic_model.movements:
        queue = observation.state.incoming_queue.get(movement.incoming_lane_id, 0)
        turn_counts[movement.turn_type] += queue * _turn_ratio(turning_ratios, movement.turn_type)
    return turn_counts


def _turn_ratio(turning_ratios: TurningRatiosConfig, turn_type: TurnType) -> float:
    if turn_type == "straight":
        return turning_ratios.straight
    if turn_type == "left":
        return turning_ratios.left
    if turn_type == "right":
        return turning_ratios.right
    msg = f"unsupported turn_type: {turn_type}"
    raise ValueError(msg)


def _read_internal_vehicle_ids(
    lane_reader: InternalLaneVehicleReader | None,
    internal_lane_ids: tuple[str, ...],
) -> frozenset[str]:
    if lane_reader is None:
        return frozenset()
    vehicle_ids: set[str] = set()
    for lane_id in internal_lane_ids:
        vehicle_ids.update(lane_reader.getLastStepVehicleIDs(lane_id))
    return frozenset(vehicle_ids)
