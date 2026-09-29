from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from traffic_agents.controllers.phase_safety import PhaseCommand, PhaseCommandKind


class TrafficLightApi(Protocol):
    def setPhase(self, tls_id: str, index: int) -> None: ...  # noqa: N802


class TrafficLightConnection(Protocol):
    trafficlight: TrafficLightApi


@dataclass(frozen=True)
class TrafficLightActuator:
    """Applies phase commands after PhaseSafetyManager has resolved them."""

    trafficlight: TrafficLightApi

    @classmethod
    def from_connection(cls, connection: TrafficLightConnection) -> TrafficLightActuator:
        return cls(trafficlight=connection.trafficlight)

    def apply(self, *, traffic_light_id: str, command: PhaseCommand) -> bool:
        if command.kind != PhaseCommandKind.SET_PHASE:
            return False
        self.trafficlight.setPhase(traffic_light_id, command.phase_index)
        return True
