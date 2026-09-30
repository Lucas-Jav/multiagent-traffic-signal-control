"""Controller-produced per-movement debug telemetry.

DEPRECATED FOR SCIENTIFIC METRICS: traffic measurements (queues, junction flows, phases) are
produced for every controller by ``NetworkTelemetryCollector`` (``network_telemetry.py``),
which stores unique incoming lanes only. The per-movement records built here repeat one lane
queue once per movement and exist only for optional debugging (``tracing.intersection_trace``)
and the demo view; sums over them must never be used as network or intersection queues.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, cast

from traffic_agents.config import TurningRatiosConfig
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
    internal_lane_persistence_events: int
    clearance_violations: int
    turn_completion_count: float
    movement_queue_mean: float
    movement_queue_max: int
    is_warmup: bool = False


@dataclass(frozen=True)
class JunctionStepMetrics:
    entries: int
    exits: int
    internal_lane_persistence_events: int
    internal_vehicle_count: int


@dataclass(frozen=True)
class MovementQueueStats:
    mean: float
    max: int


class InternalLaneVehicleReader(Protocol):
    def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]: ...  # noqa: N802


class _CommandLike(Protocol):
    @property
    def phase_id(self) -> str: ...


class _PhaseLike(Protocol):
    @property
    def phase_id(self) -> str: ...

    @property
    def kind(self) -> object: ...


class _SafetyLike(Protocol):
    @property
    def phases(self) -> tuple[_PhaseLike, ...]: ...

    @property
    def allowed_green_transitions(self) -> Mapping[str, tuple[str, ...]]: ...


class JunctionFlowTracker:
    def __init__(self) -> None:
        self._vehicle_ids_by_intersection: dict[IntersectionId, frozenset[str]] = {}

    def update(
        self,
        *,
        intersection_id: IntersectionId,
        internal_lane_ids: tuple[str, ...],
        lane_reader: InternalLaneVehicleReader | None,
    ) -> JunctionStepMetrics:
        return self.update_from_vehicle_ids(
            intersection_id=intersection_id,
            current_vehicle_ids=_read_internal_vehicle_ids(lane_reader, internal_lane_ids),
        )

    def update_from_vehicle_ids(
        self,
        *,
        intersection_id: IntersectionId,
        current_vehicle_ids: frozenset[str],
    ) -> JunctionStepMetrics:
        previous_vehicle_ids = self._vehicle_ids_by_intersection.get(
            intersection_id,
            frozenset(),
        )
        self._vehicle_ids_by_intersection[intersection_id] = current_vehicle_ids
        entries = len(current_vehicle_ids - previous_vehicle_ids)
        exits = len(previous_vehicle_ids - current_vehicle_ids)
        persistence_events = len(current_vehicle_ids & previous_vehicle_ids)
        return JunctionStepMetrics(
            entries=entries,
            exits=exits,
            internal_lane_persistence_events=persistence_events,
            internal_vehicle_count=len(current_vehicle_ids),
        )


class MovementQueueTracker:
    def __init__(self) -> None:
        self._total_by_movement: dict[str, int] = {}
        self._samples_by_movement: dict[str, int] = {}
        self._max_by_movement: dict[str, int] = {}

    def update(
        self,
        *,
        observation: AgentObservation,
        traffic_model: IntersectionTrafficModel,
        include_sample: bool = True,
    ) -> dict[str, MovementQueueStats]:
        stats: dict[str, MovementQueueStats] = {}
        for movement in traffic_model.movements:
            queue = observation.state.incoming_queue.get(movement.incoming_lane_id, 0)
            if not include_sample:
                stats[movement.movement_id] = self._current_stats(
                    movement_id=movement.movement_id,
                    queue=queue,
                )
                continue
            self._total_by_movement[movement.movement_id] = (
                self._total_by_movement.get(movement.movement_id, 0) + queue
            )
            self._samples_by_movement[movement.movement_id] = (
                self._samples_by_movement.get(movement.movement_id, 0) + 1
            )
            self._max_by_movement[movement.movement_id] = max(
                queue,
                self._max_by_movement.get(movement.movement_id, 0),
            )
            stats[movement.movement_id] = MovementQueueStats(
                mean=(
                    self._total_by_movement[movement.movement_id]
                    / self._samples_by_movement[movement.movement_id]
                ),
                max=self._max_by_movement[movement.movement_id],
            )
        return stats

    def _current_stats(self, *, movement_id: str, queue: int) -> MovementQueueStats:
        samples = self._samples_by_movement.get(movement_id, 0)
        if samples <= 0:
            return MovementQueueStats(mean=float(queue), max=queue)
        return MovementQueueStats(
            mean=self._total_by_movement[movement_id] / samples,
            max=self._max_by_movement[movement_id],
        )


def build_step_telemetry_records(
    *,
    step_index: int,
    observation: AgentObservation,
    action: TrafficLightAction,
    command: _CommandLike,
    safety: _SafetyLike,
    traffic_model: IntersectionTrafficModel,
    turning_ratios: TurningRatiosConfig,
    junction_metrics: JunctionStepMetrics,
    movement_queue_stats: Mapping[str, MovementQueueStats] | None = None,
    is_warmup: bool = False,
) -> tuple[StepTelemetryRecord, ...]:
    state = observation.state
    requested_phase = requested_phase_id(observation, action, safety)
    clearance_violations = _clearance_violations(
        command=command,
        safety=safety,
        internal_vehicle_count=junction_metrics.internal_vehicle_count,
    )
    turn_counts = _turn_counts(
        observation=observation,
        traffic_model=traffic_model,
        turning_ratios=turning_ratios,
    )
    turn_completion_counts = _turn_completion_counts(
        observation=observation,
        traffic_model=traffic_model,
        turning_ratios=turning_ratios,
        junction_exits=junction_metrics.exits,
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
            junction_entries=junction_metrics.entries,
            junction_exits=junction_metrics.exits,
            internal_lane_persistence_events=junction_metrics.internal_lane_persistence_events,
            clearance_violations=clearance_violations,
            turn_completion_count=turn_completion_counts.get(movement.movement_id, 0.0),
            movement_queue_mean=_movement_queue_stats(
                movement_queue_stats,
                movement.movement_id,
                state.incoming_queue.get(movement.incoming_lane_id, 0),
            ).mean,
            movement_queue_max=_movement_queue_stats(
                movement_queue_stats,
                movement.movement_id,
                state.incoming_queue.get(movement.incoming_lane_id, 0),
            ).max,
            is_warmup=is_warmup,
        )
        for movement in traffic_model.movements
    )


def requested_phase_id(
    observation: AgentObservation,
    action: TrafficLightAction,
    safety: _SafetyLike,
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
        and _phase_kind_value(current_phase) == "GREEN"
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


def _turn_completion_counts(
    *,
    observation: AgentObservation,
    traffic_model: IntersectionTrafficModel,
    turning_ratios: TurningRatiosConfig,
    junction_exits: int,
) -> dict[str, float]:
    if junction_exits <= 0:
        return {movement.movement_id: 0.0 for movement in traffic_model.movements}

    weights = {
        movement.movement_id: (
            observation.state.incoming_queue.get(movement.incoming_lane_id, 0)
            * _turn_ratio(turning_ratios, movement.turn_type)
        )
        for movement in traffic_model.movements
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        weights = {
            movement.movement_id: _turn_ratio(turning_ratios, movement.turn_type)
            for movement in traffic_model.movements
        }
        total_weight = sum(weights.values())

    return {
        movement_id: junction_exits * weight / total_weight
        for movement_id, weight in weights.items()
    }


def _clearance_violations(
    *,
    command: _CommandLike,
    safety: _SafetyLike,
    internal_vehicle_count: int,
) -> int:
    if internal_vehicle_count <= 0:
        return 0
    actual_phase = next(phase for phase in safety.phases if phase.phase_id == command.phase_id)
    if _phase_kind_value(actual_phase) == "GREEN":
        return 1
    return 0


def _phase_kind_value(phase: _PhaseLike) -> str:
    kind = phase.kind
    if hasattr(kind, "value"):
        return str(kind.value)
    return str(kind)


def _movement_queue_stats(
    movement_queue_stats: Mapping[str, MovementQueueStats] | None,
    movement_id: str,
    current_queue: int,
) -> MovementQueueStats:
    if movement_queue_stats is None:
        return MovementQueueStats(mean=float(current_queue), max=current_queue)
    return movement_queue_stats.get(
        movement_id,
        MovementQueueStats(mean=float(current_queue), max=current_queue),
    )


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
