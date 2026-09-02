from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, model_validator

type IntersectionId = Annotated[str, Field(min_length=1)]
type LaneId = Annotated[str, Field(min_length=1)]
type EdgeId = Annotated[str, Field(min_length=1)]
type Occupancy = Annotated[float, Field(ge=0.0, le=1.0)]

type QueueByLane = dict[LaneId, NonNegativeInt]
type OccupancyByLane = dict[LaneId, Occupancy]
type SpeedByLane = dict[LaneId, NonNegativeFloat]
type ArrivalRateByEdge = dict[EdgeId, NonNegativeFloat]


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
        if self.kind in {
            TrafficLightActionKind.KEEP_PHASE,
            TrafficLightActionKind.REQUEST_NEXT_PHASE,
        } and self.target_phase is not None:
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
    sender_id: IntersectionId
    receiver_id: IntersectionId
    timestamp: NonNegativeFloat
    state: NeighborState


class AgentObservation(DomainModel):
    state: IntersectionState
    neighbor_states: tuple[NeighborState, ...] = Field(default_factory=tuple)
    messages: tuple[NeighborMessage, ...] = Field(default_factory=tuple)


class ControllerDecision(DomainModel):
    intersection_id: IntersectionId
    timestamp: NonNegativeFloat
    action: TrafficLightAction


class SimulationStep(DomainModel):
    step_index: NonNegativeInt
    timestamp: NonNegativeFloat
    observations: tuple[AgentObservation, ...] = Field(default_factory=tuple)
    decisions: tuple[ControllerDecision, ...] = Field(default_factory=tuple)
