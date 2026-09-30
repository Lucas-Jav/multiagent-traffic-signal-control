from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, cast

from traffic_agents.config import IntersectionConfig, ScenarioConfig
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
    LaneId,
    TrafficLightAction,
)
from traffic_agents.metrics import (
    ControllerPerformanceTimings,
    JunctionFlowTracker,
    MovementQueueTracker,
    StepTelemetryRecord,
    build_step_telemetry_records,
    internal_lane_vehicle_reader,
)
from traffic_agents.traffic_light_actuator import (
    TrafficLightActuator,
    TrafficLightConnection,
)
from traffic_agents.traffic_model import (
    IntersectionTrafficModel,
    load_grid_traffic_models,
)

if TYPE_CHECKING:
    from traffic_agents.simulation.traci_sensor_adapter import TraCISensorAdapter

LOCAL_ADAPTIVE_CONTROLLER_ID = "B1_LOCAL_ADAPTIVE"
LOCAL_ADAPTIVE_CONTROLLER_VERSION = "0.1.0"


@dataclass(frozen=True)
class LocalAdaptiveConfig:
    min_green_seconds: float = 10.0
    significant_queue_threshold: int = 2
    pressure_margin: float = 1.0
    max_green_seconds: float = 60.0
    internal_clearance_halting_threshold: int = 1

    def __post_init__(self) -> None:
        if self.min_green_seconds < 0:
            msg = "min_green_seconds must be non-negative"
            raise ValueError(msg)
        if self.significant_queue_threshold < 0:
            msg = "significant_queue_threshold must be non-negative"
            raise ValueError(msg)
        if self.pressure_margin < 0:
            msg = "pressure_margin must be non-negative"
            raise ValueError(msg)
        if self.max_green_seconds <= 0:
            msg = "max_green_seconds must be positive"
            raise ValueError(msg)
        if self.internal_clearance_halting_threshold < 0:
            msg = "internal_clearance_halting_threshold must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True)
class LocalAdaptivePolicy:
    config: LocalAdaptiveConfig
    phase_lane_ids: Mapping[str, tuple[LaneId, ...]]

    def __post_init__(self) -> None:
        if not self.phase_lane_ids:
            msg = "phase_lane_ids must not be empty"
            raise ValueError(msg)
        for phase_id, lane_ids in self.phase_lane_ids.items():
            if not lane_ids:
                msg = f"phase {phase_id} must serve at least one lane"
                raise ValueError(msg)
        object.__setattr__(
            self,
            "phase_lane_ids",
            MappingProxyType({key: tuple(value) for key, value in self.phase_lane_ids.items()}),
        )

    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        state = observation.state
        current_lane_ids = self.phase_lane_ids.get(state.current_phase)
        if current_lane_ids is None:
            return TrafficLightAction.keep_phase()

        if state.phase_elapsed < self.config.min_green_seconds:
            return TrafficLightAction.keep_phase()

        pressures = self._phase_pressures(observation)
        current_pressure = pressures[state.current_phase]
        competing_pressures = {
            phase_id: pressure
            for phase_id, pressure in pressures.items()
            if phase_id != state.current_phase
        }
        if not competing_pressures:
            return TrafficLightAction.keep_phase()

        _target_phase_id, target_pressure = max(
            competing_pressures.items(),
            key=lambda item: (item[1], item[0]),
        )
        if (
            state.phase_elapsed >= self.config.max_green_seconds
            and target_pressure >= self.config.significant_queue_threshold
        ):
            return TrafficLightAction.request_next_phase()

        if (
            current_pressure >= self.config.significant_queue_threshold
            and target_pressure <= current_pressure + self.config.pressure_margin
        ):
            return TrafficLightAction.keep_phase()

        if target_pressure > current_pressure + self.config.pressure_margin:
            return TrafficLightAction.request_next_phase()

        return TrafficLightAction.keep_phase()

    def _phase_pressures(self, observation: AgentObservation) -> dict[str, float]:
        queue_by_lane = observation.state.incoming_queue
        return {
            phase_id: float(sum(queue_by_lane.get(lane_id, 0) for lane_id in lane_ids))
            for phase_id, lane_ids in self.phase_lane_ids.items()
        }


class _AdaptiveLane(Protocol):
    def getLastStepHaltingNumber(self, lane_id: str) -> int: ...  # noqa: N802


class _AdaptiveConnection(TrafficLightConnection, Protocol):
    lane: _AdaptiveLane


@dataclass
class _IntersectionRuntime:
    traffic_light_id: str
    internal_lane_ids: tuple[LaneId, ...]
    traffic_model: IntersectionTrafficModel
    policy: LocalAdaptivePolicy
    safety: PhaseSafetyManager


@dataclass
class LocalAdaptiveController:
    controller_id: ClassVar[str] = LOCAL_ADAPTIVE_CONTROLLER_ID
    controller_version: ClassVar[str] = LOCAL_ADAPTIVE_CONTROLLER_VERSION

    config: LocalAdaptiveConfig = field(default_factory=LocalAdaptiveConfig)
    _scenario_config: ScenarioConfig | None = field(default=None, init=False, repr=False)
    _scenario_dir: Path | None = field(default=None, init=False, repr=False)
    _sensor_provider: TraCISensorAdapter | None = field(default=None, init=False, repr=False)
    _runtime_by_intersection: dict[IntersectionId, _IntersectionRuntime] = field(
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
    debug_telemetry_enabled: bool = True
    _step_index: int = field(default=0, init=False, repr=False)
    _telemetry_records: list[StepTelemetryRecord] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _decision_timings_ms: list[float] = field(
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
        self._decision_timings_ms.clear()

    def before_simulation_step(self, connection: Any) -> None:
        from traffic_agents.simulation.traci_sensor_adapter import (
            TraCISensorAdapter,
            TraCISensorConnection,
        )

        scenario_config = self._require_scenario_config()
        scenario_dir = self._require_scenario_dir()
        adaptive_connection = cast(_AdaptiveConnection, connection)
        if self._sensor_provider is None:
            traffic_light_ids = _load_traffic_light_ids(scenario_dir / "metadata.json")
            self._sensor_provider = TraCISensorAdapter(
                connection=cast(TraCISensorConnection, connection),
                intersections=scenario_config.intersections,
                traffic_light_ids=traffic_light_ids,
                step_length=scenario_config.step_length,
            )
            self._runtime_by_intersection.update(
                _build_runtime_by_intersection(
                    intersections=scenario_config.intersections,
                    traffic_light_ids=traffic_light_ids,
                    internal_lane_ids_by_traffic_light_id=_load_internal_lane_ids_by_traffic_light_id(
                        scenario_dir / scenario_config.network_file
                    ),
                    traffic_models=load_grid_traffic_models(
                        scenario_config=scenario_config,
                        scenario_dir=scenario_dir,
                    ),
                    config=self.config,
                )
            )

        for intersection in scenario_config.intersections:
            is_warmup = scenario_config.is_warmup_step(self._step_index)
            runtime = self._runtime_by_intersection[intersection.intersection_id]
            state = self._sensor_provider.observe(intersection.intersection_id)
            observation = AgentObservation(state=state)
            decision_started_at = perf_counter()
            action = runtime.policy.decide(observation)
            decision = ControllerDecision(
                intersection_id=intersection.intersection_id,
                timestamp=state.timestamp,
                action=action,
            )
            command = runtime.safety.resolve(observation, decision)
            self._decision_timings_ms.append((perf_counter() - decision_started_at) * 1000)
            if self.debug_telemetry_enabled:
                junction_metrics = self._junction_flow_tracker.update(
                    intersection_id=intersection.intersection_id,
                    internal_lane_ids=runtime.internal_lane_ids,
                    lane_reader=internal_lane_vehicle_reader(adaptive_connection),
                )
                movement_queue_stats = self._movement_queue_tracker.update(
                    observation=observation,
                    traffic_model=runtime.traffic_model,
                    include_sample=not is_warmup,
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
                        is_warmup=is_warmup,
                    )
                )
            if (
                command.kind == PhaseCommandKind.SET_PHASE
                and _opens_green(command.phase_id, runtime.safety)
                and _has_stopped_internal_vehicle(
                    adaptive_connection,
                    runtime.internal_lane_ids,
                    self.config.internal_clearance_halting_threshold,
                )
            ):
                continue
            TrafficLightActuator.from_connection(adaptive_connection).apply(
                traffic_light_id=runtime.traffic_light_id,
                command=command,
            )
        self._step_index += 1

    def after_simulation_step(self, connection: Any) -> None:
        return None

    def pop_step_telemetry_records(self) -> tuple[StepTelemetryRecord, ...]:
        records = tuple(self._telemetry_records)
        self._telemetry_records.clear()
        return records

    def performance_timings(self) -> ControllerPerformanceTimings:
        return ControllerPerformanceTimings(
            decision_timings_ms=tuple(self._decision_timings_ms),
        )

    def manifest_metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": True,
            "communication_enabled": False,
            "min_green_seconds": self.config.min_green_seconds,
            "significant_queue_threshold": self.config.significant_queue_threshold,
            "pressure_margin": self.config.pressure_margin,
            "max_green_seconds": self.config.max_green_seconds,
            "internal_clearance_halting_threshold": (
                self.config.internal_clearance_halting_threshold
            ),
        }

    def _require_scenario_config(self) -> ScenarioConfig:
        if self._scenario_config is None:
            msg = "LocalAdaptiveController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_config

    def _require_scenario_dir(self) -> Path:
        if self._scenario_dir is None:
            msg = "LocalAdaptiveController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_dir


def _build_runtime_by_intersection(
    *,
    intersections: tuple[IntersectionConfig, ...],
    traffic_light_ids: Mapping[IntersectionId, str],
    internal_lane_ids_by_traffic_light_id: Mapping[str, tuple[LaneId, ...]],
    traffic_models: Mapping[IntersectionId, IntersectionTrafficModel],
    config: LocalAdaptiveConfig,
) -> dict[IntersectionId, _IntersectionRuntime]:
    runtime_by_intersection: dict[IntersectionId, _IntersectionRuntime] = {}
    for intersection in intersections:
        traffic_light_id = traffic_light_ids[intersection.intersection_id]
        traffic_model = traffic_models[intersection.intersection_id]
        phases = traffic_model.phases
        phase_lane_ids = _build_phase_lane_ids(intersection, phases)
        runtime_by_intersection[intersection.intersection_id] = _IntersectionRuntime(
            traffic_light_id=traffic_light_id,
            internal_lane_ids=internal_lane_ids_by_traffic_light_id.get(traffic_light_id, ()),
            traffic_model=traffic_model,
            policy=LocalAdaptivePolicy(config=config, phase_lane_ids=phase_lane_ids),
            safety=PhaseSafetyManager(
                phases=phases,
                min_green_seconds=config.min_green_seconds,
                max_green_seconds=config.max_green_seconds,
                movement_conflicts=traffic_model.conflicts,
            ),
        )
    return runtime_by_intersection


def _build_phase_lane_ids(
    intersection: IntersectionConfig,
    phases: tuple[PhaseDefinition, ...],
) -> Mapping[str, tuple[LaneId, ...]]:
    lane_count = len(intersection.incoming_lanes)
    phase_lane_ids: dict[str, tuple[LaneId, ...]] = {}
    for phase in phases:
        if "G" not in phase.signal_state and "g" not in phase.signal_state:
            continue
        if len(phase.signal_state) % lane_count != 0:
            msg = (
                f"SUMO phase {phase.phase_id} signal count is incompatible with "
                f"intersection {intersection.intersection_id}"
            )
            raise RuntimeError(msg)

        signals_per_lane = len(phase.signal_state) // lane_count
        served_lanes: list[LaneId] = []
        for lane_index, lane_id in enumerate(intersection.incoming_lanes):
            start = lane_index * signals_per_lane
            stop = start + signals_per_lane
            if any(signal in {"G", "g"} for signal in phase.signal_state[start:stop]):
                served_lanes.append(lane_id)
        if served_lanes:
            phase_lane_ids[phase.phase_id] = tuple(served_lanes)

    if not phase_lane_ids:
        msg = f"No controllable green phases found for {intersection.intersection_id}"
        raise RuntimeError(msg)
    return phase_lane_ids


def _opens_green(phase_id: str, safety: PhaseSafetyManager) -> bool:
    for phase in safety.phases:
        if phase.phase_id == phase_id:
            return phase.kind == PhaseKind.GREEN
    return False


def _has_stopped_internal_vehicle(
    connection: _AdaptiveConnection,
    internal_lane_ids: tuple[LaneId, ...],
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
) -> dict[str, tuple[LaneId, ...]]:
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
