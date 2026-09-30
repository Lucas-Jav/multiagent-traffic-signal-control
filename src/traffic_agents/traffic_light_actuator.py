from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from traffic_agents.controllers.phase_safety import PhaseCommand, PhaseCommandKind


class TrafficLightApi(Protocol):
    def setPhase(self, tls_id: str, index: int) -> None: ...  # noqa: N802

    def setPhaseDuration(self, tls_id: str, duration: float) -> None: ...  # noqa: N802


class TrafficLightConnection(Protocol):
    trafficlight: TrafficLightApi


@dataclass(frozen=True)
class TrafficLightActuator:
    """Applies phase commands after PhaseSafetyManager has resolved them.

    ``SET_PHASE`` switches to the next phase of the SUMO program (yellow/all-red
    sequencing is decided by the safety manager). ``KEEP_PHASE`` with a hold time
    extends the remaining duration of the current green through the TraCI
    phase-duration mechanism, so a green can outlive SUMO's static program
    duration until ``max_green``. Raw signal states are never manipulated.
    """

    trafficlight: TrafficLightApi

    @classmethod
    def from_connection(cls, connection: TrafficLightConnection) -> TrafficLightActuator:
        return cls(trafficlight=connection.trafficlight)

    def apply(self, *, traffic_light_id: str, command: PhaseCommand) -> bool:
        if command.kind == PhaseCommandKind.SET_PHASE:
            self.trafficlight.setPhase(traffic_light_id, command.phase_index)
            return True
        if command.hold_remaining_seconds is not None and command.hold_remaining_seconds > 0:
            self.trafficlight.setPhaseDuration(traffic_light_id, command.hold_remaining_seconds)
            return True
        return False
