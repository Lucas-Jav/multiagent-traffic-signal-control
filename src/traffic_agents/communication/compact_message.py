from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from traffic_agents.communication.topology import (
    CommunicationTopology,
    CommunicationTopologyError,
)
from traffic_agents.domain import AgentObservation, CompactNeighborMessage, IntersectionId
from traffic_agents.traffic_model import IntersectionTrafficModel, Movement, TurnType

NO_DESTINATION_PHASE_GROUP = "NO_DESTINATION_MOVEMENT_ACTIVE"
FULL_OCCUPANCY = 1.0


class CompactNeighborMessageError(ValueError):
    """Lançada quando uma mensagem compacta C1 não pode ser construída a partir de dados locais."""


@dataclass(frozen=True)
class CompactNeighborMessageConfig:
    straight_turn_weight: float = 0.60
    left_turn_weight: float = 0.20
    right_turn_weight: float = 0.20
    queue_weight: float = 1.0
    arrival_trend_weight: float = 1.0
    downstream_occupancy_weight: float = 10.0
    downstream_saturation_occupancy: float = 1.0

    def __post_init__(self) -> None:
        for field_name, value in (
            ("straight_turn_weight", self.straight_turn_weight),
            ("left_turn_weight", self.left_turn_weight),
            ("right_turn_weight", self.right_turn_weight),
            ("queue_weight", self.queue_weight),
            ("arrival_trend_weight", self.arrival_trend_weight),
            ("downstream_occupancy_weight", self.downstream_occupancy_weight),
        ):
            if value < 0:
                msg = f"{field_name} must be non-negative"
                raise ValueError(msg)
        if self.downstream_saturation_occupancy <= 0:
            msg = "downstream_saturation_occupancy must be positive"
            raise ValueError(msg)
        if self.downstream_saturation_occupancy > FULL_OCCUPANCY:
            msg = "downstream_saturation_occupancy must be at most 1.0"
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
class CompactNeighborMessageFactory:
    traffic_model: IntersectionTrafficModel
    topology: CommunicationTopology
    traffic_light_ids_by_intersection: Mapping[IntersectionId, str] | None = None
    config: CompactNeighborMessageConfig = CompactNeighborMessageConfig()

    def build(
        self,
        *,
        observation: AgentObservation,
        destination: IntersectionId,
        created_step: int,
        sequence: int,
    ) -> CompactNeighborMessage:
        source = observation.state.intersection_id
        if source != self.traffic_model.intersection_id:
            msg = (
                "observation intersection_id does not match traffic model: "
                f"{source} != {self.traffic_model.intersection_id}"
            )
            raise CompactNeighborMessageError(msg)
        try:
            self.topology.require_can_communicate(source, destination)
        except CommunicationTopologyError as exc:
            raise CompactNeighborMessageError(str(exc)) from exc

        directed_movements = self._movements_to_destination(source, destination)
        if not directed_movements:
            msg = f"no local movement from {source} toward communication neighbor {destination}"
            raise CompactNeighborMessageError(msg)

        queue_summary = self._outgoing_queue_summary(observation, directed_movements)
        directed_queue = sum(queue_summary.values())
        arrival_trend = self._arrival_trend(observation, directed_movements)
        downstream_occupancy = self._downstream_occupancy(observation, directed_movements)
        outgoing_pressure = (
            self.config.queue_weight * directed_queue
            + self.config.arrival_trend_weight * arrival_trend
            - self.config.downstream_occupancy_weight
            * min(
                downstream_occupancy / self.config.downstream_saturation_occupancy,
                FULL_OCCUPANCY,
            )
        )
        return CompactNeighborMessage(
            source=source,
            destination=destination,
            created_step=created_step,
            sequence=sequence,
            source_timestamp=observation.state.timestamp,
            outgoing_pressure=outgoing_pressure,
            outgoing_queue_summary=queue_summary,
            arrival_trend=arrival_trend,
            downstream_occupancy=downstream_occupancy,
            active_phase_group=self._active_phase_group(observation, directed_movements),
        )

    def _movements_to_destination(
        self,
        source: IntersectionId,
        destination: IntersectionId,
    ) -> tuple[Movement, ...]:
        outgoing_edge_id = self._edge_id_between(source, destination)
        return tuple(
            movement
            for movement in self.traffic_model.movements
            if movement.outgoing_edge_id == outgoing_edge_id
        )

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

    def _outgoing_queue_summary(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> dict[str, float]:
        summary = {"straight": 0.0, "left": 0.0, "right": 0.0}
        for movement in movements:
            queue = observation.state.incoming_queue.get(movement.incoming_lane_id, 0)
            summary[movement.turn_type] += queue * self.config.turn_weight(movement.turn_type)
        return {turn_type: value for turn_type, value in summary.items() if value > 0.0}

    # Nome histórico: o valor é uma estimativa do estado atual (taxa de chegada medida agora),
    # e não uma tendência temporal nem uma previsão.
    def _arrival_trend(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> float:
        return sum(
            observation.state.arrival_rate.get(movement.incoming_edge_id, 0.0)
            * self.config.turn_weight(movement.turn_type)
            for movement in movements
        )

    def _downstream_occupancy(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> float:
        outgoing_lane_ids = {movement.outgoing_lane_id for movement in movements}
        occupancies = [
            observation.state.outgoing_occupancy.get(outgoing_lane_id, 0.0)
            for outgoing_lane_id in outgoing_lane_ids
        ]
        return max(occupancies, default=0.0)

    def _active_phase_group(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> str:
        directed_movement_ids = {movement.movement_id for movement in movements}
        for phase in self.traffic_model.phases:
            if phase.phase_id != observation.state.current_phase:
                continue
            if directed_movement_ids.intersection(phase.movement_ids):
                return phase.phase_id
            return NO_DESTINATION_PHASE_GROUP
        return NO_DESTINATION_PHASE_GROUP


def compact_message_payload(message: CompactNeighborMessage) -> Mapping[str, object]:
    return message.model_dump(mode="json")
