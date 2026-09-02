from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from traffic_agents.controllers import (
    LOCAL_ADAPTIVE_CONTROLLER_ID,
    LOCAL_ADAPTIVE_CONTROLLER_VERSION,
    LocalAdaptiveConfig,
    LocalAdaptiveController,
    LocalAdaptivePolicy,
    build_controller,
)
from traffic_agents.controllers.local_adaptive import (
    _has_stopped_internal_vehicle,
    _load_internal_lane_ids_by_traffic_light_id,
)
from traffic_agents.domain import (
    AgentObservation,
    IntersectionState,
    TrafficLightActionKind,
)


def make_policy(
    config: LocalAdaptiveConfig | None = None,
) -> LocalAdaptivePolicy:
    return LocalAdaptivePolicy(
        config=config
        or LocalAdaptiveConfig(
            min_green_seconds=10.0,
            significant_queue_threshold=3,
            pressure_margin=2.0,
            max_green_seconds=60.0,
        ),
        phase_lane_ids={
            "phase_0": ("north_in", "south_in"),
            "phase_2": ("east_in", "west_in"),
        },
    )


def make_observation(
    *,
    current_phase: str = "phase_0",
    elapsed: float = 10.0,
    north_queue: int = 0,
    south_queue: int = 0,
    east_queue: int = 0,
    west_queue: int = 0,
) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=20.0,
            current_phase=current_phase,
            phase_elapsed=elapsed,
            incoming_queue={
                "north_in": north_queue,
                "south_in": south_queue,
                "east_in": east_queue,
                "west_in": west_queue,
            },
            incoming_occupancy={
                "north_in": 0.1,
                "south_in": 0.1,
                "east_in": 0.1,
                "west_in": 0.1,
            },
            incoming_speed={
                "north_in": 10.0,
                "south_in": 10.0,
                "east_in": 10.0,
                "west_in": 10.0,
            },
            outgoing_occupancy={"north_out": 0.1},
            arrival_rate={"edge-a": 1.0},
        )
    )


def test_build_controller_registers_b1_local_adaptive() -> None:
    controller = build_controller(LOCAL_ADAPTIVE_CONTROLLER_ID)

    assert isinstance(controller, LocalAdaptiveController)
    assert controller.controller_id == "B1_LOCAL_ADAPTIVE"
    assert controller.controller_version == LOCAL_ADAPTIVE_CONTROLLER_VERSION
    assert controller.manifest_metadata()["communication_enabled"] is False


def test_policy_keeps_phase_before_min_green_even_with_competing_pressure() -> None:
    action = make_policy().decide(
        make_observation(
            elapsed=9.999,
            north_queue=0,
            south_queue=0,
            east_queue=10,
            west_queue=0,
        )
    )

    assert action.kind == TrafficLightActionKind.KEEP_PHASE


def test_policy_keeps_phase_when_current_queue_is_significant_and_competitor_is_close() -> None:
    action = make_policy().decide(
        make_observation(
            elapsed=10.0,
            north_queue=3,
            south_queue=2,
            east_queue=6,
            west_queue=0,
        )
    )

    assert action.kind == TrafficLightActionKind.KEEP_PHASE


def test_policy_requests_competing_phase_when_pressure_is_clearly_higher() -> None:
    action = make_policy().decide(
        make_observation(
            elapsed=10.0,
            north_queue=1,
            south_queue=0,
            east_queue=5,
            west_queue=0,
        )
    )

    assert action.kind == TrafficLightActionKind.REQUEST_NEXT_PHASE
    assert action.target_phase is None


def test_policy_keeps_when_no_competing_pressure_exists() -> None:
    action = make_policy().decide(
        make_observation(
            elapsed=10.0,
            north_queue=2,
            south_queue=0,
            east_queue=0,
            west_queue=0,
        )
    )

    assert action.kind == TrafficLightActionKind.KEEP_PHASE


def test_policy_uses_configured_max_green_threshold() -> None:
    action = make_policy().decide(
        make_observation(
            elapsed=60.0,
            north_queue=10,
            south_queue=0,
            east_queue=3,
            west_queue=0,
        )
    )

    assert action.kind == TrafficLightActionKind.REQUEST_NEXT_PHASE
    assert action.target_phase is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_green_seconds": -0.1},
        {"significant_queue_threshold": -1},
        {"pressure_margin": -0.1},
    ],
)
def test_config_rejects_negative_thresholds(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        LocalAdaptiveConfig(**kwargs)


def test_config_rejects_negative_internal_clearance_threshold() -> None:
    with pytest.raises(ValueError):
        LocalAdaptiveConfig(internal_clearance_halting_threshold=-1)


def test_load_internal_lane_ids_by_traffic_light_id(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <junction id="J1" type="traffic_light" intLanes=":J1_0_0 :J1_1_0"/>
    <junction id="dead" type="dead_end" intLanes=""/>
</net>
""",
        encoding="utf-8",
    )

    internal_lane_ids = _load_internal_lane_ids_by_traffic_light_id(network_path)

    assert internal_lane_ids == {"J1": (":J1_0_0", ":J1_1_0")}


def test_has_stopped_internal_vehicle_detects_halting_lane() -> None:
    class FakeLane:
        def __init__(self) -> None:
            self.halting_numbers = {":J1_0_0": 0, ":J1_1_0": 1}

        def getLastStepHaltingNumber(self, lane_id: str) -> int:  # noqa: N802
            return self.halting_numbers[lane_id]

    class FakeTrafficLight:
        def getAllProgramLogics(self, tls_id: str) -> Any:  # noqa: N802
            return ()

        def setPhase(self, tls_id: str, index: int) -> None:  # noqa: N802
            return None

    class FakeConnection:
        def __init__(self) -> None:
            self.lane = FakeLane()
            self.trafficlight = FakeTrafficLight()

    assert _has_stopped_internal_vehicle(
        cast(Any, FakeConnection()),
        (":J1_0_0", ":J1_1_0"),
        halting_threshold=1,
    )
