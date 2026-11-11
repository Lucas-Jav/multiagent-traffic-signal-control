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
    """Aplica comandos de fase depois que o PhaseSafetyManager os resolveu.

    ``SET_PHASE`` passa para a próxima fase do programa SUMO (a sequência de amarelo/vermelho
    total é decidida pelo gerenciador de segurança). ``KEEP_PHASE`` com tempo de retenção
    estende a duração restante do verde atual pelo mecanismo de duração de fase do TraCI, de
    modo que um verde pode ultrapassar a duração do programa estático do SUMO até o
    ``max_green``. Estados brutos de sinal nunca são manipulados.
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
