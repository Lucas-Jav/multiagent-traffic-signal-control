from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from time import perf_counter
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from pydantic import ValidationError

from traffic_agents.communication import (
    CommunicationMessage,
    CompactNeighborMessageFactory,
    ExpandedNeighborMessageFactory,
    MessageBus,
    MessageBusConfig,
    grid_3x3_communication_topology,
)
from traffic_agents.controllers.local_pressure import (
    LocalPressureConfig,
    LocalPressureController,
    MovementPressureCalculator,
    PhasePressureCalculator,
    _build_phase_safety_manager,
    _has_stopped_internal_vehicle,
    _load_internal_lane_ids_by_traffic_light_id,
    _load_traffic_light_ids,
    _opens_green,
    _PressureConnection,
)
from traffic_agents.controllers.phase_safety import (
    PhaseCommandKind,
    PhaseKind,
    PhaseSafetyManager,
)
from traffic_agents.domain import (
    AgentObservation,
    CompactNeighborMessage,
    ControllerDecision,
    ExpandedNeighborMessage,
    IntersectionId,
    MovementId,
    NeighborMessage,
    TrafficLightAction,
)
from traffic_agents.metrics import (
    AgentDecisionTraceWriter,
    ControllerPerformanceTimings,
    DecisionTimer,
    JunctionFlowTracker,
    MovementQueueTracker,
    StepTelemetryRecord,
    build_agent_decision_trace_record,
    build_step_telemetry_records,
    internal_lane_vehicle_reader,
)
from traffic_agents.traffic_light_actuator import TrafficLightActuator
from traffic_agents.traffic_model import (
    IntersectionTrafficModel,
    Movement,
    TurnType,
    load_grid_traffic_models,
)

if TYPE_CHECKING:
    from traffic_agents.simulation.traci_sensor_adapter import TraCISensorAdapter

COOPERATIVE_COMPACT_CONTROLLER_ID = "C1_COOPERATIVE_COMPACT"
COOPERATIVE_COMPACT_CONTROLLER_VERSION = "0.1.0"
COOPERATIVE_EXPANDED_CONTROLLER_ID = "C2_COOPERATIVE_EXPANDED"
COOPERATIVE_EXPANDED_CONTROLLER_VERSION = "0.1.0"
FULL_OCCUPANCY = 1.0
CooperativeMessageSchema = Literal["compact", "expanded"]


class CooperativeCompactSensorConnection(Protocol):
    simulation: object


@dataclass(frozen=True)
class CooperativePressureConfig:
    local_pressure: LocalPressureConfig = field(default_factory=LocalPressureConfig)
    message_bus: MessageBusConfig = field(default_factory=MessageBusConfig)
    message_schema: CooperativeMessageSchema = "compact"
    max_message_age_steps: int = 1
    stale_after_steps: int | None = None
    projected_incoming_weight: float = 1.0
    directed_pressure_weight: float = 0.25
    downstream_congestion_weight: float = 10.0
    straight_turn_weight: float = 0.60
    left_turn_weight: float = 0.20
    right_turn_weight: float = 0.20

    def __post_init__(self) -> None:
        if self.stale_after_steps is not None:
            if self.stale_after_steps < 0:
                msg = "stale_after_steps must be non-negative"
                raise ValueError(msg)
            object.__setattr__(self, "max_message_age_steps", self.stale_after_steps)
        if self.max_message_age_steps < 0:
            msg = "max_message_age_steps must be non-negative"
            raise ValueError(msg)
        if self.message_schema not in {"compact", "expanded"}:
            msg = f"unsupported message_schema: {self.message_schema}"
            raise ValueError(msg)
        for field_name, value in (
            ("projected_incoming_weight", self.projected_incoming_weight),
            ("directed_pressure_weight", self.directed_pressure_weight),
            ("downstream_congestion_weight", self.downstream_congestion_weight),
            ("straight_turn_weight", self.straight_turn_weight),
            ("left_turn_weight", self.left_turn_weight),
            ("right_turn_weight", self.right_turn_weight),
        ):
            if value < 0:
                msg = f"{field_name} must be non-negative"
                raise ValueError(msg)

    def turn_weight(self, turn_type: TurnType) -> float:
        if turn_type == "straight":
            return self.straight_turn_weight
        if turn_type == "left":
            return self.left_turn_weight
        if turn_type == "right":
            return self.right_turn_weight
        msg = f"unsupported turn_type: {turn_type}"
        raise ValueError(msg)


@dataclass(frozen=True)
class MessageUsageTrace:
    source: IntersectionId
    destination: IntersectionId
    created_step: int
    message_age_steps: int
    used: bool
    reason: str | None = None


@dataclass(frozen=True)
class CooperativeAdjustmentResult:
    phase_scores: Mapping[str, float]
    valid_messages: int = 0
    stale_messages: int = 0
    messages_fresh: int = 0
    messages_stale: int = 0
    average_message_age: float = 0.0
    max_observed_message_age: int = 0
    invalid_messages: int = 0
    rejected_messages: int = 0
    message_usage_traces: tuple[MessageUsageTrace, ...] = ()


@dataclass(frozen=True, init=False)
class CooperativePressureAdjustment:
    config: CooperativePressureConfig
    traffic_model: IntersectionTrafficModel
    neighbor_ids: tuple[IntersectionId, ...]
    traffic_light_ids_by_intersection: Mapping[IntersectionId, str] | None
    movements_by_incoming_edge: Mapping[str, tuple[Movement, ...]]
    movements_by_outgoing_edge: Mapping[str, tuple[Movement, ...]]
    phase_ids_by_movement_id: Mapping[MovementId, tuple[str, ...]]

    def __init__(
        self,
        *,
        config: CooperativePressureConfig,
        traffic_model: IntersectionTrafficModel,
        neighbor_ids: tuple[IntersectionId, ...],
        traffic_light_ids_by_intersection: Mapping[IntersectionId, str] | None = None,
    ) -> None:
        object.__setattr__(self, "config", config)
        object.__setattr__(self, "traffic_model", traffic_model)
        object.__setattr__(self, "neighbor_ids", tuple(neighbor_ids))
        object.__setattr__(
            self,
            "traffic_light_ids_by_intersection",
            MappingProxyType(dict(traffic_light_ids_by_intersection))
            if traffic_light_ids_by_intersection is not None
            else None,
        )
        object.__setattr__(
            self,
            "movements_by_incoming_edge",
            MappingProxyType(_group_movements_by_edge(traffic_model.movements, incoming=True)),
        )
        object.__setattr__(
            self,
            "movements_by_outgoing_edge",
            MappingProxyType(_group_movements_by_edge(traffic_model.movements, incoming=False)),
        )
        object.__setattr__(
            self,
            "phase_ids_by_movement_id",
            MappingProxyType(_build_phase_ids_by_movement_id(traffic_model)),
        )

    def adjust(
        self,
        *,
        local_phase_scores: Mapping[str, float],
        observation: AgentObservation,
        current_step: int,
    ) -> CooperativeAdjustmentResult:
        adjusted_scores = dict(local_phase_scores)
        valid_messages = 0
        stale_messages = 0
        invalid_messages = 0
        rejected_messages = 0
        observed_ages: list[int] = []
        usage_traces: list[MessageUsageTrace] = []
        for raw_message in observation.messages:
            message = self._parse_message(raw_message)
            if message is None:
                invalid_messages += 1
                continue
            if message.destination != observation.state.intersection_id:
                rejected_messages += 1
                continue
            if message.source not in self.neighbor_ids:
                rejected_messages += 1
                continue
            message_age = current_step - message.created_step
            if message_age < 0:
                invalid_messages += 1
                continue
            observed_ages.append(message_age)
            if message_age > self.config.max_message_age_steps:
                stale_messages += 1
                usage_traces.append(
                    MessageUsageTrace(
                        source=message.source,
                        destination=message.destination,
                        created_step=int(message.created_step),
                        message_age_steps=message_age,
                        used=False,
                        reason="STALE",
                    )
                )
                continue

            valid_messages += 1
            usage_traces.append(
                MessageUsageTrace(
                    source=message.source,
                    destination=message.destination,
                    created_step=int(message.created_step),
                    message_age_steps=message_age,
                    used=True,
                )
            )
            self._apply_message_adjustment(adjusted_scores, message)

        return CooperativeAdjustmentResult(
            phase_scores=MappingProxyType(adjusted_scores),
            valid_messages=valid_messages,
            stale_messages=stale_messages,
            messages_fresh=valid_messages,
            messages_stale=stale_messages,
            average_message_age=(sum(observed_ages) / len(observed_ages) if observed_ages else 0.0),
            max_observed_message_age=max(observed_ages, default=0),
            invalid_messages=invalid_messages,
            rejected_messages=rejected_messages,
            message_usage_traces=tuple(usage_traces),
        )

    def _parse_message(
        self,
        message: CommunicationMessage,
    ) -> CompactNeighborMessage | ExpandedNeighborMessage | None:
        if isinstance(message, CompactNeighborMessage | ExpandedNeighborMessage):
            return message
        if isinstance(message, NeighborMessage):
            for message_model in (ExpandedNeighborMessage, CompactNeighborMessage):
                try:
                    return message_model.model_validate(message.payload)
                except ValidationError:
                    continue
        return None

    def _apply_message_adjustment(
        self,
        adjusted_scores: dict[str, float],
        message: CompactNeighborMessage | ExpandedNeighborMessage,
    ) -> None:
        if isinstance(message, ExpandedNeighborMessage):
            self._apply_expanded_message_adjustment(adjusted_scores, message)
            return

        incoming_edge_id = self._edge_id_between(message.source, message.destination)
        # "projected" é um nome histórico: estimativa do estado atual, não uma previsão temporal.
        projected_demand = sum(message.outgoing_queue_summary.values()) + message.arrival_trend
        pressure_bonus = max(message.outgoing_pressure, 0.0) * self.config.directed_pressure_weight
        for movement in self.movements_by_incoming_edge.get(incoming_edge_id, ()):
            self._add_to_movement_phases(
                adjusted_scores,
                movement.movement_id,
                (
                    self.config.projected_incoming_weight
                    * projected_demand
                    * self.config.turn_weight(movement.turn_type)
                )
                + (pressure_bonus * self.config.turn_weight(movement.turn_type)),
            )

        outgoing_edge_id = self._edge_id_between(message.destination, message.source)
        congestion_penalty = self.config.downstream_congestion_weight * min(
            message.downstream_occupancy, FULL_OCCUPANCY
        )
        downstream_phase_ids = {
            phase_id
            for movement in self.movements_by_outgoing_edge.get(outgoing_edge_id, ())
            for phase_id in self.phase_ids_by_movement_id.get(movement.movement_id, ())
        }
        for phase_id in downstream_phase_ids:
            if phase_id in adjusted_scores:
                adjusted_scores[phase_id] -= congestion_penalty

    def _apply_expanded_message_adjustment(
        self,
        adjusted_scores: dict[str, float],
        message: ExpandedNeighborMessage,
    ) -> None:
        incoming_edge_id = self._edge_id_between(message.source, message.destination)
        expanded_projected_demand = sum(message.queue_per_outgoing_movement.values()) + sum(
            message.estimated_arrival_rate_per_relevant_movement.values()
        )
        pressure_bonus = max(message.outgoing_pressure, 0.0) * self.config.directed_pressure_weight
        for movement in self.movements_by_incoming_edge.get(incoming_edge_id, ()):
            self._add_to_movement_phases(
                adjusted_scores,
                movement.movement_id,
                (
                    self.config.projected_incoming_weight
                    * expanded_projected_demand
                    * self.config.turn_weight(movement.turn_type)
                )
                + (pressure_bonus * self.config.turn_weight(movement.turn_type)),
            )

        outgoing_edge_id = self._edge_id_between(message.destination, message.source)
        downstream_occupancy = max(
            message.occupancy_per_downstream_connection.values(),
            default=0.0,
        )
        congestion_penalty = self.config.downstream_congestion_weight * min(
            downstream_occupancy,
            FULL_OCCUPANCY,
        )
        downstream_phase_ids = {
            phase_id
            for movement in self.movements_by_outgoing_edge.get(outgoing_edge_id, ())
            for phase_id in self.phase_ids_by_movement_id.get(movement.movement_id, ())
        }
        for phase_id in downstream_phase_ids:
            if phase_id in adjusted_scores:
                adjusted_scores[phase_id] -= congestion_penalty

    def _add_to_movement_phases(
        self,
        adjusted_scores: dict[str, float],
        movement_id: MovementId,
        adjustment: float,
    ) -> None:
        for phase_id in self.phase_ids_by_movement_id.get(movement_id, ()):
            if phase_id in adjusted_scores:
                adjusted_scores[phase_id] += adjustment

    def _edge_id_between(
        self,
        source: IntersectionId,
        destination: IntersectionId,
    ) -> str:
        if self.traffic_light_ids_by_intersection is None:
            return f"{source}{destination}"
        source_tls = self.traffic_light_ids_by_intersection[source]
        destination_tls = self.traffic_light_ids_by_intersection[destination]
        return f"{source_tls}{destination_tls}"


@dataclass
class _CooperativeIntersectionRuntime:
    traffic_light_id: str
    internal_lane_ids: tuple[str, ...]
    traffic_model: IntersectionTrafficModel
    phase_calculator: PhasePressureCalculator
    adjustment: CooperativePressureAdjustment
    safety: PhaseSafetyManager
    message_factory: CompactNeighborMessageFactory | ExpandedNeighborMessageFactory


@dataclass
class CooperativeCompactController:
    config: CooperativePressureConfig = field(default_factory=CooperativePressureConfig)
    local_core: LocalPressureController = field(default_factory=LocalPressureController)
    controller_id: str = COOPERATIVE_COMPACT_CONTROLLER_ID
    controller_version: str = COOPERATIVE_COMPACT_CONTROLLER_VERSION
    phase_calculator: PhasePressureCalculator | None = None
    adjustment: CooperativePressureAdjustment | None = None
    safety: PhaseSafetyManager | None = None
    _scenario_config: Any | None = field(default=None, init=False, repr=False)
    _scenario_dir: Path | None = field(default=None, init=False, repr=False)
    _sensor_provider: TraCISensorAdapter | None = field(default=None, init=False, repr=False)
    _runtime_by_intersection: dict[IntersectionId, _CooperativeIntersectionRuntime] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _message_bus: MessageBus | None = field(default=None, init=False, repr=False)
    debug_telemetry_enabled: bool = True
    _step_index: int = field(default=0, init=False, repr=False)
    _sequence_by_source: dict[IntersectionId, int] = field(
        default_factory=lambda: defaultdict(int),
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
    _telemetry_records: list[StepTelemetryRecord] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _trace_writer: AgentDecisionTraceWriter | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _decision_timings_ms: list[float] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _messages_fresh: int = field(default=0, init=False, repr=False)
    _messages_stale: int = field(default=0, init=False, repr=False)
    _message_age_total: int = field(default=0, init=False, repr=False)
    _message_age_samples: int = field(default=0, init=False, repr=False)
    _max_observed_message_age: int = field(default=0, init=False, repr=False)
    last_adjustment_result: CooperativeAdjustmentResult | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.local_core.config = self.config.local_pressure

    def configure(self, *, scenario_config: Any, scenario_dir: Path) -> None:
        self._scenario_config = scenario_config
        self._scenario_dir = scenario_dir
        self.config = replace(
            self.config,
            message_bus=replace(
                self.config.message_bus,
                delay_steps=scenario_config.communication.delay_steps,
                drop_probability=scenario_config.communication.drop_probability,
                rng_seed=scenario_config.communication.rng_seed,
                simulation_seed=scenario_config.seed,
            ),
            max_message_age_steps=scenario_config.communication.max_message_age_steps,
        )
        self._sensor_provider = None
        self._runtime_by_intersection.clear()
        self._message_bus = None
        self._step_index = 0
        self._sequence_by_source.clear()
        self._junction_flow_tracker = JunctionFlowTracker()
        self._movement_queue_tracker = MovementQueueTracker()
        self._telemetry_records.clear()
        self._trace_writer = None
        self._decision_timings_ms.clear()
        self._messages_fresh = 0
        self._messages_stale = 0
        self._message_age_total = 0
        self._message_age_samples = 0
        self._max_observed_message_age = 0

    def configure_agent_decision_tracing(
        self,
        trace_writer: AgentDecisionTraceWriter | None,
    ) -> None:
        self._trace_writer = trace_writer

    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        if self.phase_calculator is None or self.adjustment is None or self.safety is None:
            msg = (
                "CooperativeCompactController.decide requires phase_calculator, "
                "adjustment, and safety"
            )
            raise RuntimeError(msg)
        action, result = self._decide_action(
            observation=observation,
            phase_calculator=self.phase_calculator,
            adjustment=self.adjustment,
            safety=self.safety,
            current_step=int(observation.state.timestamp),
        )
        self._record_adjustment_metrics(result)
        self.last_adjustment_result = result
        return action

    def before_simulation_step(self, connection: Any) -> None:
        from traffic_agents.simulation.traci_sensor_adapter import (
            TraCISensorAdapter,
            TraCISensorConnection,
        )

        scenario_config = self._require_scenario_config()
        scenario_dir = self._require_scenario_dir()
        cooperative_connection = cast(_PressureConnection, connection)
        if self._sensor_provider is None:
            traffic_light_ids = _load_traffic_light_ids(scenario_dir / "metadata.json")
            topology = grid_3x3_communication_topology()
            self._message_bus = MessageBus(
                destinations=topology.agent_ids,
                config=self.config.message_bus,
                topology=topology,
            )
            self._sensor_provider = TraCISensorAdapter(
                connection=cast(TraCISensorConnection, connection),
                intersections=scenario_config.intersections,
                traffic_light_ids=traffic_light_ids,
                step_length=scenario_config.step_length,
            )
            self._runtime_by_intersection.update(
                _build_cooperative_runtime_by_intersection(
                    scenario_config=scenario_config,
                    scenario_dir=scenario_dir,
                    traffic_light_ids=traffic_light_ids,
                    config=self.config,
                )
            )

        message_bus = self._require_message_bus()
        observations = {
            intersection.intersection_id: AgentObservation(
                state=self._sensor_provider.observe(intersection.intersection_id)
            )
            for intersection in scenario_config.intersections
        }
        for intersection_id, observation in observations.items():
            runtime = self._runtime_by_intersection[intersection_id]
            for destination in runtime.adjustment.neighbor_ids:
                message_bus.publish_compact(
                    runtime.message_factory.build(
                        observation=observation,
                        destination=destination,
                        created_step=self._step_index,
                        sequence=self._next_sequence(intersection_id),
                    )
                )

        for intersection in scenario_config.intersections:
            is_warmup = scenario_config.is_warmup_step(self._step_index)
            runtime = self._runtime_by_intersection[intersection.intersection_id]
            local_observation = observations[intersection.intersection_id]
            observation = AgentObservation(
                state=local_observation.state,
                messages=message_bus.receive(
                    destination=intersection.intersection_id,
                    current_step=self._step_index,
                ),
            )
            trace_enabled = self._trace_writer is not None and self._trace_writer.enabled_for(
                intersection.intersection_id
            )
            timer = DecisionTimer.start() if trace_enabled else None
            decision_started_at = perf_counter()
            movement_pressures = runtime.phase_calculator.movement_pressure_calculator.calculate(
                observation
            )
            local_phase_scores = {
                phase.phase_id: runtime.phase_calculator.score_phase(phase, movement_pressures)
                for phase in runtime.phase_calculator.phases
                if phase.kind == PhaseKind.GREEN
            }
            result = runtime.adjustment.adjust(
                local_phase_scores=local_phase_scores,
                observation=observation,
                current_step=self._step_index,
            )
            self._record_adjustment_metrics(result)
            action = self.local_core._decide_action_from_phase_scores(
                observation,
                result.phase_scores,
                runtime.safety,
            )
            self.last_adjustment_result = result
            decision = ControllerDecision(
                intersection_id=intersection.intersection_id,
                timestamp=observation.state.timestamp,
                action=action,
            )
            command = runtime.safety.resolve(observation, decision)
            self._decision_timings_ms.append((perf_counter() - decision_started_at) * 1000)
            if trace_enabled and self._trace_writer is not None and timer is not None:
                self._trace_writer.append(
                    build_agent_decision_trace_record(
                        run_id=self._trace_writer.run_id,
                        simulation_step=self._step_index,
                        controller_id=self.controller_id,
                        observation=observation,
                        action=action,
                        command=command,
                        safety=runtime.safety,
                        movement_pressure=movement_pressures,
                        phase_scores=result.phase_scores,
                        computation_ms=timer.elapsed_ms(),
                        local_phase_scores=local_phase_scores,
                        neighbor_message_count=len(observation.messages),
                        messages_used=result.valid_messages,
                        messages_ignored=(
                            result.stale_messages
                            + result.invalid_messages
                            + result.rejected_messages
                        ),
                        message_age_summary={
                            "average": round(result.average_message_age, 6),
                            "max": result.max_observed_message_age,
                        },
                        stale_count=result.stale_messages,
                        cooperative_adjustment={
                            phase_id: (
                                float(result.phase_scores.get(phase_id, 0.0))
                                - float(local_phase_scores.get(phase_id, 0.0))
                            )
                            for phase_id in result.phase_scores
                        },
                    )
                )
            if self.debug_telemetry_enabled:
                junction_metrics = self._junction_flow_tracker.update(
                    intersection_id=intersection.intersection_id,
                    internal_lane_ids=runtime.internal_lane_ids,
                    lane_reader=internal_lane_vehicle_reader(cooperative_connection),
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
                    cooperative_connection,
                    runtime.internal_lane_ids,
                    self.config.local_pressure.internal_clearance_halting_threshold,
                )
            ):
                continue
            TrafficLightActuator.from_connection(cooperative_connection).apply(
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
        bus_metrics = self._message_bus.metrics if self._message_bus is not None else None
        return ControllerPerformanceTimings(
            decision_timings_ms=tuple(self._decision_timings_ms),
            message_bus_publish_time_ms=(
                float(bus_metrics.publish_time_ms) if bus_metrics is not None else 0.0
            ),
            message_bus_receive_time_ms=(
                float(bus_metrics.receive_time_ms) if bus_metrics is not None else 0.0
            ),
        )

    def communication_metrics(self) -> dict[str, object]:
        bus_metrics = self._message_bus.metrics if self._message_bus is not None else None
        sent = bus_metrics.messages_sent if bus_metrics is not None else 0
        delivered = bus_metrics.messages_delivered if bus_metrics is not None else 0
        bytes_sent = bus_metrics.serialized_bytes if bus_metrics is not None else 0
        bytes_delivered = bus_metrics.delivered_serialized_bytes if bus_metrics is not None else 0
        return {
            "messages_sent": int(sent),
            "messages_delivered": int(delivered),
            "messages_dropped": int(bus_metrics.messages_dropped if bus_metrics is not None else 0),
            "messages_stale": int(self._messages_stale),
            "messages_fresh": int(self._messages_fresh),
            "bytes_sent": int(bytes_sent),
            "bytes_delivered": int(bytes_delivered),
            "mean_message_size_bytes": (bytes_sent / sent if sent > 0 else 0.0),
            "mean_delivered_message_size_bytes": (
                bytes_delivered / delivered if delivered > 0 else 0.0
            ),
            "mean_message_age_steps": (
                self._message_age_total / self._message_age_samples
                if self._message_age_samples > 0
                else 0.0
            ),
            "max_message_age_steps": int(self._max_observed_message_age),
            "configured_delay_steps": int(self.config.message_bus.delay_steps),
            "configured_drop_probability": float(self.config.message_bus.drop_probability),
        }

    def manifest_metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": True,
            "communication_enabled": True,
            "communication_message": _message_name(self.config.message_schema),
            "communication_message_schema": self.config.message_schema,
            "message_bus_delay_steps": self.config.message_bus.delay_steps,
            "message_bus_drop_probability": self.config.message_bus.drop_probability,
            "max_message_age_steps": self.config.max_message_age_steps,
            "projected_incoming_weight": self.config.projected_incoming_weight,
            "directed_pressure_weight": self.config.directed_pressure_weight,
            "downstream_congestion_weight": self.config.downstream_congestion_weight,
            "local_pressure_controller_id": self.local_core.controller_id,
            "local_pressure_controller_version": self.local_core.controller_version,
        }

    def _record_adjustment_metrics(self, result: CooperativeAdjustmentResult) -> None:
        self._messages_fresh += result.messages_fresh
        self._messages_stale += result.messages_stale
        observed_count = result.messages_fresh + result.messages_stale
        if observed_count <= 0:
            return
        self._message_age_total += round(result.average_message_age * observed_count)
        self._message_age_samples += observed_count
        self._max_observed_message_age = max(
            self._max_observed_message_age,
            result.max_observed_message_age,
        )

    def _decide_action(
        self,
        *,
        observation: AgentObservation,
        phase_calculator: PhasePressureCalculator,
        adjustment: CooperativePressureAdjustment,
        safety: PhaseSafetyManager,
        current_step: int,
    ) -> tuple[TrafficLightAction, CooperativeAdjustmentResult]:
        local_phase_scores = phase_calculator.calculate(observation)
        result = adjustment.adjust(
            local_phase_scores=local_phase_scores,
            observation=observation,
            current_step=current_step,
        )
        action = self.local_core._decide_action_from_phase_scores(
            observation,
            result.phase_scores,
            safety,
        )
        return action, result

    def _next_sequence(self, source: IntersectionId) -> int:
        sequence = self._sequence_by_source[source]
        self._sequence_by_source[source] = sequence + 1
        return sequence

    def _require_scenario_config(self) -> Any:
        if self._scenario_config is None:
            msg = "CooperativeCompactController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_config

    def _require_scenario_dir(self) -> Path:
        if self._scenario_dir is None:
            msg = "CooperativeCompactController must be configured before use"
            raise RuntimeError(msg)
        return self._scenario_dir

    def _require_message_bus(self) -> MessageBus:
        if self._message_bus is None:
            msg = "CooperativeCompactController message bus is not initialized"
            raise RuntimeError(msg)
        return self._message_bus


def _build_cooperative_runtime_by_intersection(
    *,
    scenario_config: Any,
    scenario_dir: Path,
    traffic_light_ids: Mapping[IntersectionId, str],
    config: CooperativePressureConfig,
) -> dict[IntersectionId, _CooperativeIntersectionRuntime]:
    topology = grid_3x3_communication_topology()
    traffic_models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=scenario_dir,
    )
    internal_lane_ids_by_traffic_light_id = _load_internal_lane_ids_by_traffic_light_id(
        scenario_dir / scenario_config.network_file
    )
    runtime_by_intersection: dict[IntersectionId, _CooperativeIntersectionRuntime] = {}
    for intersection in scenario_config.intersections:
        traffic_light_id = traffic_light_ids[intersection.intersection_id]
        traffic_model = traffic_models[intersection.intersection_id]
        movement_calculator = MovementPressureCalculator(
            config=config.local_pressure,
            movements=traffic_model.movements,
        )
        phase_calculator = PhasePressureCalculator(
            phases=traffic_model.phases,
            movement_pressure_calculator=movement_calculator,
        )
        runtime_by_intersection[intersection.intersection_id] = _CooperativeIntersectionRuntime(
            traffic_light_id=traffic_light_id,
            internal_lane_ids=internal_lane_ids_by_traffic_light_id.get(traffic_light_id, ()),
            traffic_model=traffic_model,
            phase_calculator=phase_calculator,
            adjustment=CooperativePressureAdjustment(
                config=config,
                traffic_model=traffic_model,
                neighbor_ids=topology.neighbors_of(intersection.intersection_id),
                traffic_light_ids_by_intersection=traffic_light_ids,
            ),
            safety=_build_phase_safety_manager(traffic_model, config.local_pressure),
            message_factory=CompactNeighborMessageFactory(
                traffic_model=traffic_model,
                topology=topology,
                traffic_light_ids_by_intersection=traffic_light_ids,
            )
            if config.message_schema == "compact"
            else ExpandedNeighborMessageFactory(
                traffic_model=traffic_model,
                topology=topology,
                traffic_light_ids_by_intersection=traffic_light_ids,
            ),
        )
    return runtime_by_intersection


def _message_name(message_schema: CooperativeMessageSchema) -> str:
    if message_schema == "compact":
        return "CompactNeighborMessage"
    if message_schema == "expanded":
        return "ExpandedNeighborMessage"
    msg = f"unsupported message_schema: {message_schema}"
    raise ValueError(msg)


def _group_movements_by_edge(
    movements: tuple[Movement, ...],
    *,
    incoming: bool,
) -> dict[str, tuple[Movement, ...]]:
    grouped: dict[str, list[Movement]] = defaultdict(list)
    for movement in movements:
        edge_id = movement.incoming_edge_id if incoming else movement.outgoing_edge_id
        grouped[edge_id].append(movement)
    return {edge_id: tuple(values) for edge_id, values in grouped.items()}


def _build_phase_ids_by_movement_id(
    traffic_model: IntersectionTrafficModel,
) -> dict[MovementId, tuple[str, ...]]:
    phase_ids_by_movement_id: dict[MovementId, list[str]] = defaultdict(list)
    for phase in traffic_model.phases:
        if phase.kind != PhaseKind.GREEN:
            continue
        for movement_id in phase.movement_ids:
            phase_ids_by_movement_id[movement_id].append(phase.phase_id)
    return {
        movement_id: tuple(phase_ids) for movement_id, phase_ids in phase_ids_by_movement_id.items()
    }
