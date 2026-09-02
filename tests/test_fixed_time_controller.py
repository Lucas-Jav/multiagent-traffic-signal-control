import pytest

from traffic_agents.controllers import (
    FIXED_TIME_CONTROLLER_ID,
    FIXED_TIME_CONTROLLER_VERSION,
    FixedTimeController,
    UnsupportedControllerError,
    build_controller,
)


class AdaptiveApiProbe:
    def __init__(self) -> None:
        self.calls = 0

    def setPhase(self) -> None:  # noqa: N802
        self.calls += 1


def test_fixed_time_controller_is_registered_baseline() -> None:
    controller = build_controller("B0_FIXED")

    assert isinstance(controller, FixedTimeController)
    assert controller.controller_id == FIXED_TIME_CONTROLLER_ID
    assert controller.controller_version == FIXED_TIME_CONTROLLER_VERSION


def test_fixed_time_controller_does_not_apply_adaptive_adjustments() -> None:
    probe = AdaptiveApiProbe()
    controller = FixedTimeController()

    controller.before_simulation_step(probe)
    controller.after_simulation_step(probe)

    assert probe.calls == 0
    assert controller.manifest_metadata() == {
        "controller_id": "B0_FIXED",
        "controller_version": FIXED_TIME_CONTROLLER_VERSION,
        "adaptive_adjustments_enabled": False,
    }


def test_build_controller_rejects_unknown_controller() -> None:
    with pytest.raises(UnsupportedControllerError, match="Unsupported controller_id"):
        build_controller("ADAPTIVE_EXPERIMENT")
