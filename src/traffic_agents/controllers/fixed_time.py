from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

FIXED_TIME_CONTROLLER_ID = "B0_FIXED"
FIXED_TIME_CONTROLLER_VERSION = "0.1.0"


class UnsupportedControllerError(ValueError):
    """Raised when a simulation requests an unsupported controller."""


@dataclass(frozen=True)
class FixedTimeController:
    """Baseline controller that leaves the SUMO fixed-time program untouched."""

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


def build_controller(controller_id: str) -> FixedTimeController:
    if controller_id == FIXED_TIME_CONTROLLER_ID:
        return FixedTimeController()

    msg = f"Unsupported controller_id: {controller_id}"
    raise UnsupportedControllerError(msg)
