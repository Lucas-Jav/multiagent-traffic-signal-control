from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from traffic_agents.controllers.cooperative_compact import (
    COOPERATIVE_COMPACT_CONTROLLER_ID,
    COOPERATIVE_EXPANDED_CONTROLLER_ID,
    CooperativeCompactController,
    CooperativePressureConfig,
)
from traffic_agents.controllers.fixed_time_plan import (
    FIXED_TIME_PLAN_CONTROLLER_ID,
    FixedTimePlanController,
)
from traffic_agents.controllers.local_adaptive import (
    LOCAL_ADAPTIVE_CONTROLLER_ID,
    LocalAdaptiveController,
)
from traffic_agents.controllers.local_pressure import (
    LOCAL_PRESSURE_CONTROLLER_ID,
    LocalPressureController,
)
from traffic_agents.metrics import ControllerPerformanceTimings

FIXED_TIME_CONTROLLER_ID = "B0_FIXED"
FIXED_TIME_CONTROLLER_VERSION = "0.1.0"


class UnsupportedControllerError(ValueError):
    """Raised when a simulation requests an unsupported controller."""


@dataclass(frozen=True)
class FixedTimeController:
    """Baseline controller that leaves the SUMO fixed-time program untouched.

    This is the historical Pilot V2 baseline (documented as ``B0_FIXED_STATIC``): the static
    98 s plan stored in ``network.net.xml``. Its ``controller_id`` stays ``B0_FIXED`` so that Pilot
    V2 artifacts remain valid. The final calibrated variant is ``B0_FIXED_CALIBRATED``
    (``fixed_time_plan.py``).
    """

    controller_id: ClassVar[str] = FIXED_TIME_CONTROLLER_ID
    controller_version: ClassVar[str] = FIXED_TIME_CONTROLLER_VERSION

    def before_simulation_step(self, connection: Any) -> None:
        return None

    def after_simulation_step(self, connection: Any) -> None:
        return None

    def manifest_metadata(self) -> dict[str, str | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": False,
        }

    def performance_timings(self) -> ControllerPerformanceTimings:
        return ControllerPerformanceTimings()


def build_controller(
    controller_id: str,
) -> (
    FixedTimeController
    | FixedTimePlanController
    | LocalAdaptiveController
    | LocalPressureController
    | CooperativeCompactController
):
    if controller_id == FIXED_TIME_CONTROLLER_ID:
        return FixedTimeController()
    if controller_id == FIXED_TIME_PLAN_CONTROLLER_ID:
        return FixedTimePlanController()
    if controller_id == COOPERATIVE_COMPACT_CONTROLLER_ID:
        return CooperativeCompactController()
    if controller_id == COOPERATIVE_EXPANDED_CONTROLLER_ID:
        return CooperativeCompactController(
            config=CooperativePressureConfig(message_schema="expanded"),
            controller_id=COOPERATIVE_EXPANDED_CONTROLLER_ID,
        )
    if controller_id == LOCAL_ADAPTIVE_CONTROLLER_ID:
        return LocalAdaptiveController()
    if controller_id == LOCAL_PRESSURE_CONTROLLER_ID:
        return LocalPressureController()

    msg = f"Unsupported controller_id: {controller_id}"
    raise UnsupportedControllerError(msg)
