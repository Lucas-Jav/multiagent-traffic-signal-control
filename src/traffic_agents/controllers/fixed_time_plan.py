"""Baseline de tempo fixo calibrado (``B0_FIXED_CALIBRATED``).

O baseline histórico do Pilot V2 (``B0_FIXED``, também chamado ``B0_FIXED_STATIC``) deixa o
``tlLogic`` estático armazenado em ``network.net.xml`` intacto. ``B0_FIXED_CALIBRATED`` é o
baseline de tempo fixo final: instala um plano *estático* calibrado via TraCI uma única vez,
antes do primeiro passo de simulação, e depois nunca mais atua. Não é responsivo ao tráfego:
nenhuma observação é lida após a instalação e nenhuma fase é alterada durante a execução.

Um plano altera apenas as durações de verde e o deslocamento (offset) inicial dos programas que
já existem na rede. Os estados de fase, a ordem das fases, o tempo de amarelo e o tempo de
vermelho total são preservados, de modo que a rede, os movimentos legais e os tempos de
segurança são idênticos aos de todos os outros controladores.

A semântica do offset é a do atributo ``offset`` do ``tlLogic`` do SUMO (verificada contra o
programa nativo): o tempo do programa no instante de simulação ``t`` é ``(t - offset) mod cycle``.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from traffic_agents.metrics import ControllerPerformanceTimings

FIXED_TIME_PLAN_CONTROLLER_ID = "B0_FIXED_CALIBRATED"
FIXED_TIME_PLAN_CONTROLLER_VERSION = "0.1.0"
DEFAULT_FIXED_TIME_PLAN_PATH = (
    Path(__file__).resolve().parents[3] / "experiments" / "fixed_time" / "b0_fixed_calibrated.json"
)

APPROACH_COUNT = 4
PHASES_PER_APPROACH = 3  # verde, amarelo, vermelho total
YELLOW_SECONDS = 3
ALL_RED_SECONDS = 2
MIN_GREEN_SECONDS = 10
MAX_GREEN_SECONDS = 60


class FixedTimePlanError(ValueError):
    """Lançada quando um plano de tempo fixo é inconsistente com os programas da rede."""


@dataclass(frozen=True)
class TrafficLightTiming:
    """Segundos de verde por fase de aproximação (ordem de fases da rede) e offset do programa."""

    green_seconds: tuple[int, ...]
    offset_seconds: int


@dataclass(frozen=True)
class FixedTimePlan:
    plan_id: str
    cycle_seconds: int
    traffic_lights: Mapping[str, TrafficLightTiming]
    yellow_seconds: int = YELLOW_SECONDS
    all_red_seconds: int = ALL_RED_SECONDS
    method: str = "EMPIRICAL_FIXED_TIME"
    provenance: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        validate_plan(self)

    def phase_durations(self, traffic_light_id: str) -> tuple[int, ...]:
        timing = self.traffic_lights[traffic_light_id]
        durations: list[int] = []
        for green in timing.green_seconds:
            durations.extend((green, self.yellow_seconds, self.all_red_seconds))
        return tuple(durations)

    def to_payload(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "controller_id": FIXED_TIME_PLAN_CONTROLLER_ID,
            "method": self.method,
            "cycle_seconds": self.cycle_seconds,
            "yellow_seconds": self.yellow_seconds,
            "all_red_seconds": self.all_red_seconds,
            "traffic_lights": {
                tls_id: {
                    "green_seconds": list(timing.green_seconds),
                    "offset_seconds": timing.offset_seconds,
                }
                for tls_id, timing in sorted(self.traffic_lights.items())
            },
            "provenance": dict(self.provenance or {}),
        }

    def sha256(self) -> str:
        payload = self.to_payload()
        payload.pop("provenance", None)
        return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def validate_plan(plan: FixedTimePlan) -> None:
    if plan.yellow_seconds != YELLOW_SECONDS or plan.all_red_seconds != ALL_RED_SECONDS:
        msg = (
            f"safety timings must stay yellow={YELLOW_SECONDS}s all_red={ALL_RED_SECONDS}s, "
            f"got yellow={plan.yellow_seconds} all_red={plan.all_red_seconds}"
        )
        raise FixedTimePlanError(msg)
    if not plan.traffic_lights:
        msg = "plan has no traffic lights"
        raise FixedTimePlanError(msg)
    lost = APPROACH_COUNT * (plan.yellow_seconds + plan.all_red_seconds)
    for tls_id, timing in plan.traffic_lights.items():
        if len(timing.green_seconds) != APPROACH_COUNT:
            msg = f"{tls_id}: expected {APPROACH_COUNT} greens, got {len(timing.green_seconds)}"
            raise FixedTimePlanError(msg)
        for green in timing.green_seconds:
            if not MIN_GREEN_SECONDS <= green <= MAX_GREEN_SECONDS:
                msg = f"{tls_id}: green {green}s outside [{MIN_GREEN_SECONDS}, {MAX_GREEN_SECONDS}]"
                raise FixedTimePlanError(msg)
        cycle = sum(timing.green_seconds) + lost
        if cycle != plan.cycle_seconds:
            msg = f"{tls_id}: cycle {cycle}s differs from plan cycle {plan.cycle_seconds}s"
            raise FixedTimePlanError(msg)
        if not 0 <= timing.offset_seconds < plan.cycle_seconds:
            msg = f"{tls_id}: offset {timing.offset_seconds}s outside the cycle"
            raise FixedTimePlanError(msg)


def load_plan(path: Path) -> FixedTimePlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return plan_from_payload(payload)


def plan_from_payload(payload: Mapping[str, Any]) -> FixedTimePlan:
    return FixedTimePlan(
        plan_id=str(payload["plan_id"]),
        cycle_seconds=int(payload["cycle_seconds"]),
        yellow_seconds=int(payload.get("yellow_seconds", YELLOW_SECONDS)),
        all_red_seconds=int(payload.get("all_red_seconds", ALL_RED_SECONDS)),
        method=str(payload.get("method", "EMPIRICAL_FIXED_TIME")),
        provenance=payload.get("provenance") or {},
        traffic_lights={
            str(tls_id): TrafficLightTiming(
                green_seconds=tuple(int(g) for g in timing["green_seconds"]),
                offset_seconds=int(timing["offset_seconds"]),
            )
            for tls_id, timing in payload["traffic_lights"].items()
        },
    )


def cycle_start_state(durations: tuple[int, ...], offset_seconds: int) -> tuple[int, int]:
    """Índice da fase e segundos restantes no instante de simulação 0 (tempo do programa
    ``-offset``).
    """

    cycle = sum(durations)
    position = (-offset_seconds) % cycle
    elapsed = 0
    for index, duration in enumerate(durations):
        if position < elapsed + duration:
            return index, elapsed + duration - position
        elapsed += duration
    msg = "unreachable: position is inside the cycle"
    raise FixedTimePlanError(msg)


class FixedTimePlanController:
    """Instala um plano estático calibrado uma única vez; depois disso nunca atua."""

    controller_id: ClassVar[str] = FIXED_TIME_PLAN_CONTROLLER_ID
    controller_version: ClassVar[str] = FIXED_TIME_PLAN_CONTROLLER_VERSION

    def __init__(self, plan: FixedTimePlan | None = None, *, plan_path: Path | None = None) -> None:
        if plan is None:
            plan = load_plan(plan_path or DEFAULT_FIXED_TIME_PLAN_PATH)
        self.plan = plan
        self._installed = False

    @property
    def installed(self) -> bool:
        return self._installed

    def before_simulation_step(self, connection: Any) -> None:
        if self._installed:
            return
        for tls_id in sorted(self.plan.traffic_lights):
            self._install(connection, tls_id)
        self._installed = True

    def after_simulation_step(self, connection: Any) -> None:
        return None

    def _install(self, connection: Any, tls_id: str) -> None:
        trafficlight = connection.trafficlight
        logic = trafficlight.getAllProgramLogics(tls_id)[0]
        phases = list(logic.phases)
        expected = APPROACH_COUNT * PHASES_PER_APPROACH
        if len(phases) != expected:
            msg = f"{tls_id}: expected {expected} network phases, found {len(phases)}"
            raise FixedTimePlanError(msg)
        durations = self.plan.phase_durations(tls_id)
        installed = []
        for phase, duration in zip(phases, durations, strict=True):
            updated = copy.copy(phase)
            updated.duration = float(duration)
            updated.minDur = float(duration)
            updated.maxDur = float(duration)
            installed.append(updated)
        timing = self.plan.traffic_lights[tls_id]
        index, remaining = cycle_start_state(durations, timing.offset_seconds)
        logic.phases = tuple(installed)
        logic.currentPhaseIndex = index
        trafficlight.setProgramLogic(tls_id, logic)
        trafficlight.setPhase(tls_id, index)
        trafficlight.setPhaseDuration(tls_id, float(remaining))

    def manifest_metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": False,
            "traffic_responsive": False,
            "baseline_family": "FIXED_TIME_CALIBRATED",
            "fixed_time_plan_id": self.plan.plan_id,
            "fixed_time_plan_sha256": self.plan.sha256(),
            "fixed_time_cycle_seconds": self.plan.cycle_seconds,
            "fixed_time_method": self.plan.method,
        }

    def performance_timings(self) -> ControllerPerformanceTimings:
        return ControllerPerformanceTimings()
