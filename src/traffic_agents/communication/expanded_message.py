from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from traffic_agents.communication.compact_message import (
    FULL_OCCUPANCY,
    NO_DESTINATION_PHASE_GROUP,
    CompactNeighborMessageConfig,
)
from traffic_agents.communication.topology import (
    CommunicationTopology,
    CommunicationTopologyError,
)
from traffic_agents.domain import AgentObservation, ExpandedNeighborMessage, IntersectionId
from traffic_agents.traffic_model import IntersectionTrafficModel, Movement


class ExpandedNeighborMessageError(ValueError):
    """Raised when an expanded C2 message cannot be built from local data."""


@dataclass(frozen=True)
class ExpandedNeighborMessageFactory:
    traffic_model: IntersectionTrafficModel
    topology: CommunicationTopology
    traffic_light_ids_by_intersection: Mapping[IntersectionId, str] | None = None
    config: CompactNeighborMessageConfig = field(default_factory=CompactNeighborMessageConfig)

    def build(
        self,
        *,
        observation: AgentObservation,
        destination: IntersectionId,
        created_step: int,
        sequence: int,
    ) -> ExpandedNeighborMessage:
        source = observation.state.intersection_id
        if source != self.traffic_model.intersection_id:
            msg = (
                "observation intersection_id does not match traffic model: "
                f"{source} != {self.traffic_model.intersection_id}"
            )
            raise ExpandedNeighborMessageError(msg)
        try:
            self.topology.require_can_communicate(source, destination)
        except CommunicationTopologyError as exc:
            raise ExpandedNeighborMessageError(str(exc)) from exc

        directed_movements = self._movements_to_destination(source, destination)
        if not directed_movements:
            msg = f"no local movement from {source} toward communication neighbor {destination}"
            raise ExpandedNeighborMessageError(msg)

        outgoing_queue_summary = self._outgoing_queue_summary(observation, directed_movements)
        arrival_trend = self._arrival_trend(observation, directed_movements)
        downstream_occupancy = self._downstream_occupancy(observation, directed_movements)
        outgoing_pressure = (
            self.config.queue_weight * sum(outgoing_queue_summary.values())
            + self.config.arrival_trend_weight * arrival_trend
            - self.config.downstream_occupancy_weight
            * min(
                downstream_occupancy / self.config.downstream_saturation_occupancy,
                FULL_OCCUPANCY,
            )
        )

        return ExpandedNeighborMessage(
            source=source,
            destination=destination,
            created_step=created_step,
            sequence=sequence,
            source_timestamp=observation.state.timestamp,
            outgoing_pressure=outgoing_pressure,
            outgoing_queue_summary=outgoing_queue_summary,
            arrival_trend=arrival_trend,
            downstream_occupancy=downstream_occupancy,
            queue_per_outgoing_movement=self._queue_per_outgoing_movement(
                observation,
                directed_movements,
            ),
            occupancy_per_downstream_connection=self._occupancy_per_downstream_connection(
                observation,
                directed_movements,
            ),
            estimated_arrival_rate_per_relevant_movement=self._arrival_rate_per_relevant_movement(
                observation,
                directed_movements,
            ),
            directional_demand_summary=self._directional_demand_summary(
                observation,
                directed_movements,
            ),
            active_phase_group=self._active_phase_group(observation, directed_movements),
            phase_elapsed=observation.state.phase_elapsed,
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

    def _queue_per_outgoing_movement(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> dict[str, float]:
        return {
            movement.movement_id: float(
                observation.state.incoming_queue.get(movement.incoming_lane_id, 0)
            )
            for movement in movements
        }

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

    def _occupancy_per_downstream_connection(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> dict[str, float]:
        return {
            movement.movement_id: observation.state.outgoing_occupancy.get(
                movement.outgoing_lane_id,
                0.0,
            )
            for movement in movements
        }

    def _arrival_rate_per_relevant_movement(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> dict[str, float]:
        return {
            movement.movement_id: observation.state.arrival_rate.get(
                movement.incoming_edge_id,
                0.0,
            )
            for movement in movements
        }

    # Historical name: the value is a current-state estimate (measured arrival rate now),
    # not a temporal trend or forecast.
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

    def _directional_demand_summary(
        self,
        observation: AgentObservation,
        movements: tuple[Movement, ...],
    ) -> dict[str, float]:
        summary = {"straight": 0.0, "left": 0.0, "right": 0.0}
        for movement in movements:
            queue = float(observation.state.incoming_queue.get(movement.incoming_lane_id, 0))
            arrival_rate = observation.state.arrival_rate.get(movement.incoming_edge_id, 0.0)
            summary[movement.turn_type] += queue + arrival_rate
        return {turn_type: value for turn_type, value in summary.items() if value > 0.0}

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


def expanded_message_payload(message: ExpandedNeighborMessage) -> Mapping[str, object]:
    return message.model_dump(mode="json")
