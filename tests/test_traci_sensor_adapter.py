from __future__ import annotations

from dataclasses import dataclass

import pytest

from traffic_agents.config import IntersectionConfig
from traffic_agents.domain import IntersectionState
from traffic_agents.simulation.traci_sensor_adapter import (
    SensorReadError,
    TraCISensorAdapter,
    TrafficSensorProvider,
)


class FakeSensorProvider:
    def __init__(self, state: IntersectionState) -> None:
        self._state = state

    def observe(self, intersection_id: str) -> IntersectionState:
        if intersection_id != self._state.intersection_id:
            msg = f"unexpected intersection_id={intersection_id}"
            raise SensorReadError(msg)
        return self._state


@dataclass
class FakeSimulationClock:
    time: float

    def getTime(self) -> float:  # noqa: N802
        return self.time


class FakeTrafficLightSensor:
    def __init__(self) -> None:
        self.phases = {"tls_A1": 2}
        self.spent_durations = {"tls_A1": 7.5}

    def getPhase(self, tls_id: str) -> int:  # noqa: N802
        return self.phases[tls_id]

    def getSpentDuration(self, tls_id: str) -> float:  # noqa: N802
        return self.spent_durations[tls_id]


class FakeLaneSensor:
    def __init__(self) -> None:
        self.edge_ids = {
            "in_west_0": "in_west",
            "in_north_0": "in_north",
            "out_east_0": "out_east",
        }
        self.halting_numbers = {"in_west_0": 3, "in_north_0": 1}
        self.occupancy_percent = {"in_west_0": 25.0, "in_north_0": 50.0, "out_east_0": 10.0}
        self.mean_speeds = {"in_west_0": 4.0, "in_north_0": 8.0}
        self.vehicle_numbers = {"in_west_0": 4, "in_north_0": 2}

    def getEdgeID(self, lane_id: str) -> str:  # noqa: N802
        return self.edge_ids[lane_id]

    def getLastStepHaltingNumber(self, lane_id: str) -> int:  # noqa: N802
        return self.halting_numbers[lane_id]

    def getLastStepMeanSpeed(self, lane_id: str) -> float:  # noqa: N802
        return self.mean_speeds[lane_id]

    def getLastStepOccupancy(self, lane_id: str) -> float:  # noqa: N802
        return self.occupancy_percent[lane_id]

    def getLastStepVehicleNumber(self, lane_id: str) -> int:  # noqa: N802
        return self.vehicle_numbers[lane_id]


class FakeTraCIConnection:
    def __init__(self) -> None:
        self.simulation = FakeSimulationClock(time=12.0)
        self.trafficlight = FakeTrafficLightSensor()
        self.lane = FakeLaneSensor()


def make_intersection_config() -> IntersectionConfig:
    return IntersectionConfig(
        intersection_id="A1",
        incoming_lanes=("in_west_0", "in_north_0"),
        outgoing_lanes=("out_east_0",),
        phases=("north_south", "east_west"),
    )


def make_state() -> IntersectionState:
    return IntersectionState(
        intersection_id="A1",
        timestamp=1.0,
        current_phase="phase_0",
        phase_elapsed=1.0,
        incoming_queue={"in_west_0": 0},
        incoming_occupancy={"in_west_0": 0.0},
        incoming_speed={"in_west_0": 0.0},
        outgoing_occupancy={"out_east_0": 0.0},
        arrival_rate={"in_west": 0.0},
    )


def test_fake_sensor_provider_satisfies_protocol() -> None:
    provider = FakeSensorProvider(make_state())

    assert isinstance(provider, TrafficSensorProvider)
    assert provider.observe("A1").intersection_id == "A1"


def test_traci_sensor_adapter_converts_traci_values_to_intersection_state() -> None:
    adapter = TraCISensorAdapter(
        connection=FakeTraCIConnection(),
        intersections=(make_intersection_config(),),
        traffic_light_ids={"A1": "tls_A1"},
        step_length=2.0,
    )

    state = adapter.observe("A1")

    assert state.intersection_id == "A1"
    assert state.timestamp == 12.0
    assert state.current_phase == "phase_2"
    assert state.phase_elapsed == 7.5
    assert state.incoming_queue == {"in_west_0": 3, "in_north_0": 1}
    assert state.incoming_occupancy == {"in_west_0": 0.25, "in_north_0": 0.5}
    assert state.incoming_speed == {"in_west_0": 4.0, "in_north_0": 8.0}
    assert state.outgoing_occupancy == {"out_east_0": 0.1}
    assert state.arrival_rate == {"in_west": 2.0, "in_north": 1.0}


def test_traci_sensor_adapter_rejects_missing_traffic_light_mapping() -> None:
    with pytest.raises(SensorReadError, match="Traffic light id not configured"):
        TraCISensorAdapter(
            connection=FakeTraCIConnection(),
            intersections=(make_intersection_config(),),
            traffic_light_ids={},
            step_length=1.0,
        )


def test_traci_sensor_adapter_rejects_missing_lane_sensor_value() -> None:
    connection = FakeTraCIConnection()
    del connection.lane.occupancy_percent["in_north_0"]
    adapter = TraCISensorAdapter(
        connection=connection,
        intersections=(make_intersection_config(),),
        traffic_light_ids={"A1": "tls_A1"},
        step_length=1.0,
    )

    with pytest.raises(SensorReadError, match="occupancy for lane in_north_0"):
        adapter.observe("A1")


def test_traci_sensor_adapter_rejects_out_of_range_occupancy() -> None:
    connection = FakeTraCIConnection()
    connection.lane.occupancy_percent["in_north_0"] = 120.0
    adapter = TraCISensorAdapter(
        connection=connection,
        intersections=(make_intersection_config(),),
        traffic_light_ids={"A1": "tls_A1"},
        step_length=1.0,
    )

    with pytest.raises(SensorReadError, match="Invalid occupancy"):
        adapter.observe("A1")
