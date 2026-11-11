from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import ValidationError

from traffic_agents.config import IntersectionConfig
from traffic_agents.domain import EdgeId, IntersectionId, IntersectionState, LaneId


class SensorReadError(RuntimeError):
    """Lançada quando o TraCI não consegue fornecer um valor de sensor necessário."""


@runtime_checkable
class TrafficSensorProvider(Protocol):
    def observe(self, intersection_id: IntersectionId) -> IntersectionState: ...


class TraCITrafficLightSensor(Protocol):
    def getPhase(self, tls_id: str) -> int: ...  # noqa: N802

    def getSpentDuration(self, tls_id: str) -> float: ...  # noqa: N802


class TraCILaneSensor(Protocol):
    def getEdgeID(self, lane_id: str) -> str: ...  # noqa: N802

    def getLastStepHaltingNumber(self, lane_id: str) -> int: ...  # noqa: N802

    def getLastStepMeanSpeed(self, lane_id: str) -> float: ...  # noqa: N802

    def getLastStepOccupancy(self, lane_id: str) -> float: ...  # noqa: N802

    def getLastStepVehicleNumber(self, lane_id: str) -> int: ...  # noqa: N802


class TraCISimulationClock(Protocol):
    def getTime(self) -> float: ...  # noqa: N802


class TraCISensorConnection(Protocol):
    simulation: TraCISimulationClock
    trafficlight: TraCITrafficLightSensor
    lane: TraCILaneSensor


@dataclass(frozen=True)
class _IntersectionSensorConfig:
    traffic_light_id: str
    incoming_lanes: tuple[LaneId, ...]
    outgoing_lanes: tuple[LaneId, ...]


T = TypeVar("T")


class TraCISensorAdapter:
    def __init__(
        self,
        *,
        connection: TraCISensorConnection,
        intersections: tuple[IntersectionConfig, ...],
        traffic_light_ids: Mapping[IntersectionId, str],
        step_length: float,
    ) -> None:
        if step_length <= 0:
            msg = "step_length must be positive"
            raise ValueError(msg)

        self._connection = connection
        self._step_length = step_length
        self._intersections = _build_intersection_configs(intersections, traffic_light_ids)

    def observe(self, intersection_id: IntersectionId) -> IntersectionState:
        config = self._intersections.get(intersection_id)
        if config is None:
            msg = f"Sensor config not found for intersection_id={intersection_id}"
            raise SensorReadError(msg)

        tls_id = config.traffic_light_id
        timestamp = self._read_value("simulation time", self._connection.simulation.getTime)
        phase_index = self._read_value(
            f"traffic light phase for {intersection_id}",
            lambda: self._connection.trafficlight.getPhase(tls_id),
        )
        phase_elapsed = self._read_value(
            f"traffic light phase elapsed time for {intersection_id}",
            lambda: self._connection.trafficlight.getSpentDuration(tls_id),
        )

        incoming_queue = {
            lane_id: self._read_lane_queue(lane_id) for lane_id in config.incoming_lanes
        }
        incoming_occupancy = {
            lane_id: self._read_lane_occupancy(lane_id) for lane_id in config.incoming_lanes
        }
        incoming_speed = {
            lane_id: self._read_lane_speed(lane_id) for lane_id in config.incoming_lanes
        }
        outgoing_occupancy = {
            lane_id: self._read_lane_occupancy(lane_id) for lane_id in config.outgoing_lanes
        }
        arrival_rate = self._read_arrival_rate(config.incoming_lanes)

        try:
            return IntersectionState(
                intersection_id=intersection_id,
                timestamp=timestamp,
                current_phase=f"phase_{phase_index}",
                phase_elapsed=phase_elapsed,
                incoming_queue=incoming_queue,
                incoming_occupancy=incoming_occupancy,
                incoming_speed=incoming_speed,
                outgoing_occupancy=outgoing_occupancy,
                arrival_rate=arrival_rate,
            )
        except ValidationError as exc:
            msg = f"Invalid sensor state for intersection_id={intersection_id}"
            raise SensorReadError(msg) from exc

    def _read_lane_queue(self, lane_id: LaneId) -> int:
        queue = self._read_value(
            f"halting vehicle count for lane {lane_id}",
            lambda: self._connection.lane.getLastStepHaltingNumber(lane_id),
        )
        if queue < 0:
            msg = f"Invalid negative queue for lane {lane_id}: {queue}"
            raise SensorReadError(msg)
        return queue

    def _read_lane_occupancy(self, lane_id: LaneId) -> float:
        occupancy_percent = self._read_value(
            f"occupancy for lane {lane_id}",
            lambda: self._connection.lane.getLastStepOccupancy(lane_id),
        )
        occupancy = occupancy_percent / 100
        if occupancy < 0 or occupancy > 1:
            msg = f"Invalid occupancy for lane {lane_id}: {occupancy_percent}%"
            raise SensorReadError(msg)
        return occupancy

    def _read_lane_speed(self, lane_id: LaneId) -> float:
        speed = self._read_value(
            f"mean speed for lane {lane_id}",
            lambda: self._connection.lane.getLastStepMeanSpeed(lane_id),
        )
        if speed < 0:
            msg = f"Invalid negative speed for lane {lane_id}: {speed}"
            raise SensorReadError(msg)
        return speed

    def _read_arrival_rate(self, lane_ids: tuple[LaneId, ...]) -> dict[EdgeId, float]:
        arrival_rate: dict[EdgeId, float] = {}
        for lane_id in lane_ids:
            edge_id = self._read_lane_edge_id(lane_id)
            vehicles = self._read_lane_vehicle_count(lane_id)
            if vehicles < 0:
                msg = f"Invalid negative vehicle count for lane {lane_id}: {vehicles}"
                raise SensorReadError(msg)
            arrival_rate[edge_id] = arrival_rate.get(edge_id, 0.0) + vehicles / self._step_length
        return arrival_rate

    def _read_lane_edge_id(self, lane_id: LaneId) -> str:
        return self._read_value(
            f"edge id for lane {lane_id}",
            lambda: self._connection.lane.getEdgeID(lane_id),
        )

    def _read_lane_vehicle_count(self, lane_id: LaneId) -> int:
        return self._read_value(
            f"vehicle count for lane {lane_id}",
            lambda: self._connection.lane.getLastStepVehicleNumber(lane_id),
        )

    def _read_value(self, description: str, reader: Callable[[], T]) -> T:
        try:
            return reader()
        except SensorReadError:
            raise
        except Exception as exc:
            msg = f"Unable to read {description}"
            raise SensorReadError(msg) from exc


def _build_intersection_configs(
    intersections: tuple[IntersectionConfig, ...],
    traffic_light_ids: Mapping[IntersectionId, str],
) -> dict[IntersectionId, _IntersectionSensorConfig]:
    configs: dict[IntersectionId, _IntersectionSensorConfig] = {}
    for intersection in intersections:
        traffic_light_id = traffic_light_ids.get(intersection.intersection_id)
        if traffic_light_id is None:
            msg = (
                "Traffic light id not configured for "
                f"intersection_id={intersection.intersection_id}"
            )
            raise SensorReadError(msg)

        configs[intersection.intersection_id] = _IntersectionSensorConfig(
            traffic_light_id=traffic_light_id,
            incoming_lanes=intersection.incoming_lanes,
            outgoing_lanes=intersection.outgoing_lanes,
        )
    return configs
