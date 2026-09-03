from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, model_validator

type IntersectionId = Annotated[str, Field(min_length=1)]
type LaneId = Annotated[str, Field(min_length=1)]
type EdgeId = Annotated[str, Field(min_length=1)]
type MovementId = Annotated[str, Field(min_length=1)]
type Occupancy = Annotated[float, Field(ge=0.0, le=1.0)]

type QueueByLane = dict[LaneId, NonNegativeInt]
type OccupancyByLane = dict[LaneId, Occupancy]
type SpeedByLane = dict[LaneId, NonNegativeFloat]
type ArrivalRateByEdge = dict[EdgeId, NonNegativeFloat]
type QueueSummary = dict[str, NonNegativeFloat]


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IntersectionState(DomainModel):
    intersection_id: IntersectionId
    timestamp: NonNegativeFloat
    current_phase: Annotated[str, Field(min_length=1)]
    phase_elapsed: NonNegativeFloat
    incoming_queue: QueueByLane
    incoming_occupancy: OccupancyByLane
    incoming_speed: SpeedByLane
    outgoing_occupancy: OccupancyByLane
    arrival_rate: ArrivalRateByEdge


class TrafficLightActionKind(StrEnum):
    KEEP_PHASE = "KEEP_PHASE"
    REQUEST_NEXT_PHASE = "REQUEST_NEXT_PHASE"
    SWITCH_PHASE = "SWITCH_PHASE"


class TrafficLightAction(DomainModel):
    KEEP_PHASE: ClassVar[TrafficLightActionKind] = TrafficLightActionKind.KEEP_PHASE
    REQUEST_NEXT_PHASE: ClassVar[TrafficLightActionKind] = TrafficLightActionKind.REQUEST_NEXT_PHASE
    SWITCH_PHASE: ClassVar[TrafficLightActionKind] = TrafficLightActionKind.SWITCH_PHASE

    kind: TrafficLightActionKind
    target_phase: Annotated[str, Field(min_length=1)] | None = None

    @classmethod
    def keep_phase(cls) -> TrafficLightAction:
        return cls(kind=TrafficLightActionKind.KEEP_PHASE)

    @classmethod
    def request_next_phase(cls) -> TrafficLightAction:
        return cls(kind=TrafficLightActionKind.REQUEST_NEXT_PHASE)

    @classmethod
    def switch_phase(cls, target_phase: str) -> TrafficLightAction:
        return cls(kind=TrafficLightActionKind.SWITCH_PHASE, target_phase=target_phase)

    @model_validator(mode="after")
    def validate_parameters(self) -> Self:
        if (
            self.kind
            in {
                TrafficLightActionKind.KEEP_PHASE,
                TrafficLightActionKind.REQUEST_NEXT_PHASE,
            }
            and self.target_phase is not None
        ):
            msg = f"target_phase must be omitted for {self.kind}"
            raise ValueError(msg)
        if self.kind == TrafficLightActionKind.SWITCH_PHASE and self.target_phase is None:
            msg = "target_phase is required when switching phase"
            raise ValueError(msg)
        return self


class NeighborState(DomainModel):
    intersection_id: IntersectionId
    timestamp: NonNegativeFloat
    current_phase: Annotated[str, Field(min_length=1)]
    phase_elapsed: NonNegativeFloat
    incoming_queue: QueueByLane
    outgoing_occupancy: OccupancyByLane


class NeighborMessage(DomainModel):
    message_id: Annotated[str, Field(min_length=1)]
    source: IntersectionId
    destination: IntersectionId
    created_step: NonNegativeInt
    scheduled_delivery_step: NonNegativeInt | None = None
    delivered_step: NonNegativeInt | None = None
    sequence: NonNegativeInt
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_delivery_steps(self) -> Self:
        if (
            self.scheduled_delivery_step is not None
            and self.scheduled_delivery_step < self.created_step
        ):
            msg = "scheduled_delivery_step must be greater than or equal to created_step"
            raise ValueError(msg)
        if self.delivered_step is not None:
            if self.scheduled_delivery_step is None:
                msg = "scheduled_delivery_step is required when delivered_step is set"
                raise ValueError(msg)
            if self.delivered_step < self.scheduled_delivery_step:
                msg = "delivered_step must be greater than or equal to scheduled_delivery_step"
                raise ValueError(msg)
        return self


class CompactNeighborMessage(DomainModel):
    source: IntersectionId
    destination: IntersectionId
    created_step: NonNegativeInt
    scheduled_delivery_step: NonNegativeInt | None = None
    delivered_step: NonNegativeInt | None = None
    sequence: NonNegativeInt
    source_timestamp: NonNegativeFloat
    outgoing_pressure: float
    outgoing_queue_summary: QueueSummary
    arrival_trend: NonNegativeFloat
    downstream_occupancy: Occupancy
    active_phase_group: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_delivery_steps(self) -> Self:
        if (
            self.scheduled_delivery_step is not None
            and self.scheduled_delivery_step < self.created_step
        ):
            msg = "scheduled_delivery_step must be greater than or equal to created_step"
            raise ValueError(msg)
        if self.delivered_step is not None:
            if self.scheduled_delivery_step is None:
                msg = "scheduled_delivery_step is required when delivered_step is set"
                raise ValueError(msg)
            if self.delivered_step < self.scheduled_delivery_step:
                msg = "delivered_step must be greater than or equal to scheduled_delivery_step"
                raise ValueError(msg)
        return self


class AgentObservation(DomainModel):
    state: IntersectionState
    neighbor_states: tuple[NeighborState, ...] = Field(default_factory=tuple)
    messages: tuple[NeighborMessage | CompactNeighborMessage, ...] = Field(default_factory=tuple)


class ControllerDecision(DomainModel):
    intersection_id: IntersectionId
    timestamp: NonNegativeFloat
    action: TrafficLightAction


class SimulationStep(DomainModel):
    step_index: NonNegativeInt
    timestamp: NonNegativeFloat
    observations: tuple[AgentObservation, ...] = Field(default_factory=tuple)
    decisions: tuple[ControllerDecision, ...] = Field(default_factory=tuple)
