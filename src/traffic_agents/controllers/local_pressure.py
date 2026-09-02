from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, cast

from traffic_agents.config import ScenarioConfig
from traffic_agents.controllers.phase_safety import (
    PhaseCommandKind,
    PhaseDefinition,
    PhaseKind,
    PhaseSafetyManager,
)
from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    IntersectionId,
    MovementId,
    TrafficLightAction,
)
from traffic_agents.metrics import (
    JunctionFlowTracker,
    MovementQueueTracker,
    StepTelemetryRecord,
    build_step_telemetry_records,
    internal_lane_vehicle_reader,
)
from traffic_agents.traffic_model import (
    IntersectionTrafficModel,
    Movement,
    load_grid_traffic_models,
)

if TYPE_CHECKING:
    from traffic_agents.simulation.traci_sensor_adapter import TraCISensorAdapter

LOCAL_PRESSURE_CONTROLLER_ID = "B2_LOCAL_PRESSURE"
LOCAL_PRESSURE_CONTROLLER_VERSION = "0.1.0"
FULL_OCCUPANCY = 1.0


@dataclass(frozen=True)
class LocalPressureConfig:
    """Configuration for the local pressure baseline.

    For each movement, pressure is:

        queue_weight * upstream_halting_vehicles
        + arrival_rate_weight * upstream_vehicle_arrival_rate
        - downstream_occupancy_weight * min(
            outgoing_lane_occupancy / downstream_saturation_occupancy,
            1.0,
        )

    All inputs come from the local IntersectionState. Queue and arrival rate model
    upstream demand; normalized occupancy of the movement destination models
    downstream congestion.
    """

    min_green_seconds: float = 10.0
    max_green_seconds: float = 60.0
    queue_weight: float = 1.0
    arrival_rate_weight: float = 0.0
    downstream_occupancy_weight: float = 10.0
    downstream_saturation_occupancy: float = 1.0
    switch_score_margin: float = 0.0
    internal_clearance_halting_threshold: int = 1

    def __post_init__(self) -> None:
        if self.min_green_seconds < 0:
            msg = "min_green_seconds must be non-negative"
            raise ValueError(msg)
        if self.max_green_seconds <= 0:
            msg = "max_green_seconds must be positive"
            raise ValueError(msg)
        if self.max_green_seconds < self.min_green_seconds:
            msg = "max_green_seconds must be greater than or equal to min_green_seconds"
            raise ValueError(msg)
        if self.queue_weight < 0:
            msg = "queue_weight must be non-negative"
            raise ValueError(msg)
        if self.arrival_rate_weight < 0:
            msg = "arrival_rate_weight must be non-negative"
            raise ValueError(msg)
        if self.downstream_occupancy_weight < 0:
            msg = "downstream_occupancy_weight must be non-negative"
            raise ValueError(msg)
        if self.downstream_saturation_occupancy <= 0:
            msg = "downstream_saturation_occupancy must be positive"
            raise ValueError(msg)
        if self.downstream_saturation_occupancy > FULL_OCCUPANCY:
            msg = "downstream_saturation_occupancy must be at most 1.0"
            raise ValueError(msg)
        if self.switch_score_margin < 0:
            msg = "switch_score_margin must be non-negative"
            raise ValueError(msg)
        if self.internal_clearance_halting_threshold < 0:
            msg = "internal_clearance_halting_threshold must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True, init=False)
class MovementPressureCalculator:
    config: LocalPressureConfig
    movements: Mapping[MovementId, Movement]

    def __init__(
        self,
        *,
        config: LocalPressureConfig,
        movements: Mapping[MovementId, Movement] | tuple[Movement, ...],
    ) -> None:
        movement_map = (
            {movement.movement_id: movement for movement in movements}
            if isinstance(movements, tuple)
            else dict(movements)
        )
        if not movement_map:
            msg = "movements must not be empty"
            raise ValueError(msg)
        object.__setattr__(self, "config", config)
        object.__setattr__(self, "movements", MappingProxyType(movement_map))

    def calculate(self, observation: AgentObservation) -> dict[MovementId, float]:
        return {
            movement_id: self.score_movement(observation, movement_id)
            for movement_id in self.movements
        }

    def score_movement(
        self,
        observation: AgentObservation,
        movement_id: MovementId,
    ) -> float:
        movement = self.movements[movement_id]
        return self.upstream_queue_component(observation, movement) - (
            self.downstream_congestion_component(observation, movement)
        )

    def upstream_queue_component(
        self,
        observation: AgentObservation,
        movement: Movement,
    ) -> float:
        state = observation.state
        queue = state.incoming_queue.get(movement.incoming_lane_id, 0)
        arrival_rate = state.arrival_rate.get(movement.incoming_edge_id, 0.0)
        return self.config.queue_weight * queue + self.config.arrival_rate_weight * arrival_rate

    def downstream_congestion_component(
        self,
        observation: AgentObservation,
        movement: Movement,
    ) -> float:
        occupancy = observation.state.outgoing_occupancy.get(movement.outgoing_lane_id, 0.0)
        normalized_occupancy = min(
            occupancy / self.config.downstream_saturation_occupancy,
            FULL_OCCUPANCY,
        )
        return self.config.downstream_occupancy_weight * normalized_occupancy


@dataclass(frozen=True, init=False)
class PhasePressureCalculator:
    phases: tuple[PhaseDefinition, ...]
    movement_pressure_calculator: MovementPressureCalculator

    def __init__(
        self,
        *,
        phases: tuple[PhaseDefinition, ...],
        movement_pressure_calculator: MovementPressureCalculator,
    ) -> None:
        green_phases = tuple(phase for phase in phases if phase.kind == PhaseKind.GREEN)
        if not green_phases:
            msg = "phases must contain at least one green phase"
            raise ValueError(msg)
        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "movement_pressure_calculator", movement_pressure_calculator)

    def calculate(self, observation: AgentObservation) -> dict[str, float]:
        movement_pressures = self.movement_pressure_calculator.calculate(observation)
        return {
            phase.phase_id: self.score_phase(phase, movement_pressures)
            for phase in self.phases
            if phase.kind == PhaseKind.GREEN
        }

    def score_phase(
        self,
        phase: PhaseDefinition,
        movement_pressures: Mapping[MovementId, float],
    ) -> float:
        return sum(movement_pressures[movement_id] for movement_id in phase.movement_ids)


@dataclass
class _PressureIntersectionRuntime:
    traffic_light_id: str
    internal_lane_ids: tuple[str, ...]
    traffic_model: IntersectionTrafficModel
    phase_calculator: PhasePressureCalculator
    safety: PhaseSafetyManager


class _PressureTrafficLight(Protocol):
    def setPhase(self, tls_id: str, index: int) -> None: ...  # noqa: N802


class _PressureLane(Protocol):
    def getLastStepHaltingNumber(self, lane_id: str) -> int: ...  # noqa: N802


class _PressureConnection(Protocol):
    trafficlight: _PressureTrafficLight
    lane: _PressureLane


@dataclass
class LocalPressureController:
    controller_id: ClassVar[str] = LOCAL_PRESSURE_CONTROLLER_ID
    controller_version: ClassVar[str] = LOCAL_PRESSURE_CONTROLLER_VERSION

    config: LocalPressureConfig = field(default_factory=LocalPressureConfig)
    phase_calculator: PhasePressureCalculator | None = None
    safety: PhaseSafetyManager | None = None
    _scenario_config: ScenarioConfig | None = field(default=None, init=False, repr=False)
    _scenario_dir: Path | None = field(default=None, init=False, repr=False)
    _sensor_provider: TraCISensorAdapter | None = field(default=None, init=False, repr=False)
    _runtime_by_intersection: dict[IntersectionId, _PressureIntersectionRuntime] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _junction_flow_tracker: JunctionFlowTracker = field(
        default_factory=JunctionFlowTracker,
        init=False,
        repr=False,
    )
    _movement_queue_tracker: MovementQueueTracker = field(
        default_factory=MovementQueueTracker,
        init=False,
        repr=False,
    )
    _step_index: int = field(default=0, init=False, repr=False)
    _telemetry_records: list[StepTelemetryRecord] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def configure(self, *, scenario_config: ScenarioConfig, scenario_dir: Path) -> None:
        self._scenario_config = scenario_config
        self._scenario_dir = scenario_dir
        self._sensor_provider = None
        self._runtime_by_intersection.clear()
        self._junction_flow_tracker = JunctionFlowTracker()
        self._movement_queue_tracker = MovementQueueTracker()
        self._step_index = 0
        self._telemetry_records.clear()

    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        if self.phase_calculator is None or self.safety is None:
            msg = "LocalPressureController.decide requires phase_calculator and safety"
            raise RuntimeError(msg)
        return self._decide_action(observation, self.phase_calculator, self.safety)

    def before_simulation_step(self, connection: Any) -> None:
        from traffic_agents.simulation.traci_sensor_adapter import (
            TraCISensorAdapter,
            TraCISensorConnection,
        )

        scenario_config = self._require_scenario_config()
        scenario_dir = self._require_scenario_dir()
        pressure_connection = cast(_PressureConnection, connection)
        if self._sensor_provider is None:
            traffic_light_ids = _load_traffic_light_ids(scenario_dir / "metadata.json")
            self._sensor_provider = TraCISensorAdapter(
                connection=cast(TraCISensorConnection, connection),
                intersections=scenario_config.intersections,
                traffic_light_ids=traffic_light_ids,
                step_length=scenario_config.step_length,
            )
            self._runtime_by_intersection.update(
                _build_pressure_runtime_by_intersection(
                    scenario_config=scenario_config,
                    scenario_dir=scenario_dir,
                    traffic_light_ids=traffic_light_ids,
                    config=self.config,
                )
            )

        for intersection in scenario_config.intersections:
            runtime = self._runtime_by_intersection[intersection.intersection_id]
            state = self._sensor_provider.observe(intersection.intersection_id)
            observation = AgentObservation(state=state)
            action = self._decide_action(
                observation,
                runtime.phase_calculator,
                runtime.safety,
            )
            decision = ControllerDecision(
                intersection_id=intersection.intersection_id,
                timestamp=state.timestamp,
                action=action,
            )
            command = runtime.safety.resolve(observation, decision)
            junction_metrics = self._junction_flow_tracker.update(
                intersection_id=intersection.intersection_id,
                internal_lane_ids=runtime.internal_lane_ids,
                lane_reader=internal_lane_vehicle_reader(pressure_connection),
            )
            movement_queue_stats = self._movement_queue_tracker.update(
                observation=observation,
                traffic_model=runtime.traffic_model,
            )
            self._telemetry_records.extend(
                build_step_telemetry_records(
                    step_index=self._step_index,
                    observation=observation,
                    action=action,
                    command=command,
                    safety=runtime.safety,
                    traffic_model=runtime.traffic_model,
                    turning_ratios=scenario_config.traffic.turning_ratios,
                    junction_metrics=junction_metrics,
                    movement_queue_stats=movement_queue_stats,
                )
            )
            if command.kind == PhaseCommandKind.SET_PHASE:
                if _opens_green(command.phase_id, runtime.safety) and _has_stopped_internal_vehicle(
                    pressure_connection,
                    runtime.internal_lane_ids,
                    self.config.internal_clearance_halting_threshold,
                ):
                    continue
                pressure_connection.trafficlight.setPhase(
                    runtime.traffic_light_id,
                    command.phase_index,
                )
        self._step_index += 1

    def after_simulation_step(self, connection: Any) -> None:
        return None

    def pop_step_telemetry_records(self) -> tuple[StepTelemetryRecord, ...]:
        records = tuple(self._telemetry_records)
        self._telemetry_records.clear()
        return records

    def manifest_metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": True,
            "communication_enabled": False,
            "pressure_formula": (
                "queue_weight * upstream_queue + arrival_rate_weight * arrival_rate "
                "- downstream_occupancy_weight * min(outgoing_occupancy / "
                "downstream_saturation_occupancy, 1.0)"
            ),
            "min_green_seconds": self.config.min_green_seconds,
            "max_green_seconds": self.config.max_green_seconds,
            "queue_weight": self.config.queue_weight,
            "arrival_rate_weight": self.config.arrival_rate_weight,
            "downstream_occupancy_weight": self.config.downstream_occupancy_weight,
            "downstream_saturation_occupancy": self.config.downstream_saturation_occupancy,
            "switch_score_margin": self.config.switch_score_margin,
            "internal_clearance_halting_threshold": (
                self.config.internal_clearance_halting_threshold
            ),
        }

    def _decide_action(
        self,
        observation: AgentObservation,
        phase_calculator: PhasePressureCalculator,
        safety: PhaseSafetyManager,
    ) -> TrafficLightAction:
        phase_scores = phase_calculator.calculate(observation)
        return self._decide_action_from_phase_scores(observation, phase_scores, safety)

    def _decide_action_from_phase_scores(
        self,
        observation: AgentObservation,
        phase_scores: Mapping[str, float],
        safety: PhaseSafetyManager,
    ) -> TrafficLightAction:
        current_phase_id = observation.state.current_phase
        if current_phase_id not in phase_scores:
            return TrafficLightAction.keep_phase()

        candidate_phase_ids = safety.allowed_green_transitions.get(current_phase_id, ())
        if not candidate_phase_ids:
            return TrafficLightAction.keep_phase()

        scored_candidates = [
            (phase_id, phase_scores[phase_id])
            for phase_id in candidate_phase_ids
            if phase_id in phase_scores
        ]
        if not scored_candidates:
            return TrafficLightAction.keep_phase()

        target_phase_id, target_score = max(scored_candidates, key=lambda item: (item[1], item[0]))
        current_score = phase_scores[current_phase_id]
        if observation.state.phase_elapsed >= self.config.max_green_seconds:
            return TrafficLightAction.switch_phase(target_phase_id)
        if target_score > current_score + self.config.switch_score_margin:
            return TrafficLightAction.switch_phase(target_phase_id)
        return TrafficLightAction.keep_phase()

    def _require_scenario_config(self) -> ScenarioConfig:
        if self._scenario_config is None:
            msg = "LocalPressureController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_config

    def _require_scenario_dir(self) -> Path:
        if self._scenario_dir is None:
            msg = "LocalPressureController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_dir


def _build_pressure_runtime_by_intersection(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
    traffic_light_ids: Mapping[IntersectionId, str],
    config: LocalPressureConfig,
) -> dict[IntersectionId, _PressureIntersectionRuntime]:
    traffic_models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=scenario_dir,
    )
    internal_lane_ids_by_traffic_light_id = _load_internal_lane_ids_by_traffic_light_id(
        scenario_dir / scenario_config.network_file
    )
    runtime_by_intersection: dict[IntersectionId, _PressureIntersectionRuntime] = {}
    for intersection in scenario_config.intersections:
        traffic_light_id = traffic_light_ids[intersection.intersection_id]
        traffic_model = traffic_models[intersection.intersection_id]
        movement_calculator = MovementPressureCalculator(
            config=config,
            movements=traffic_model.movements,
        )
        phase_calculator = PhasePressureCalculator(
            phases=traffic_model.phases,
            movement_pressure_calculator=movement_calculator,
        )
        runtime_by_intersection[intersection.intersection_id] = _PressureIntersectionRuntime(
            traffic_light_id=traffic_light_id,
            internal_lane_ids=internal_lane_ids_by_traffic_light_id.get(traffic_light_id, ()),
            traffic_model=traffic_model,
            phase_calculator=phase_calculator,
            safety=_build_phase_safety_manager(traffic_model, config),
        )
    return runtime_by_intersection


def _build_phase_safety_manager(
    traffic_model: IntersectionTrafficModel,
    config: LocalPressureConfig,
) -> PhaseSafetyManager:
    return PhaseSafetyManager(
        phases=traffic_model.phases,
        min_green_seconds=config.min_green_seconds,
        movement_conflicts=traffic_model.conflicts,
    )


def _opens_green(phase_id: str, safety: PhaseSafetyManager) -> bool:
    for phase in safety.phases:
        if phase.phase_id == phase_id:
            return phase.kind == PhaseKind.GREEN
    return False


def _has_stopped_internal_vehicle(
    connection: _PressureConnection,
    internal_lane_ids: tuple[str, ...],
    halting_threshold: int,
) -> bool:
    if halting_threshold <= 0:
        return False
    return any(
        connection.lane.getLastStepHaltingNumber(lane_id) >= halting_threshold
        for lane_id in internal_lane_ids
    )


def _load_internal_lane_ids_by_traffic_light_id(
    network_path: Path,
) -> dict[str, tuple[str, ...]]:
    import xml.etree.ElementTree as ET

    tree = ET.parse(network_path)
    root = tree.getroot()
    return {
        junction.attrib["id"]: tuple(junction.attrib.get("intLanes", "").split())
        for junction in root.findall("junction")
        if junction.attrib.get("type") == "traffic_light"
    }


def _load_traffic_light_ids(path: Path) -> dict[IntersectionId, str]:
    with path.open(encoding="utf-8") as file:
        payload: Any = json.load(file)

    traffic_light_ids = payload.get("traffic_light_ids") if isinstance(payload, dict) else None
    if not isinstance(traffic_light_ids, dict):
        msg = f"traffic_light_ids mapping not found in {path}"
        raise ValueError(msg)

    parsed: dict[IntersectionId, str] = {}
    for intersection_id, traffic_light_id in traffic_light_ids.items():
        if not isinstance(intersection_id, str) or not isinstance(traffic_light_id, str):
            msg = f"traffic_light_ids must map strings to strings in {path}"
            raise ValueError(msg)
        parsed[intersection_id] = traffic_light_id
    return parsed
