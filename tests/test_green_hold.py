from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from traffic_agents.controllers import (
    FixedTimeController,
    PhaseCommand,
    PhaseCommandKind,
    PhaseDefinition,
    PhaseSafetyManager,
)
from traffic_agents.domain import (
    AgentObservation,
    IntersectionState,
    TrafficLightAction,
)
from traffic_agents.traffic_light_actuator import TrafficLightActuator

# O programa SUMO do grid_3x3: quatro verdes de aproximação protegidos, cada um seguido de
# amarelo (3 s) e vermelho total (2 s). As strings de estado são os estados reais de 12 sinais.
GRID_PROGRAM: tuple[tuple[str, float], ...] = (
    ("GGGrrrrrrrrr", 18.0),
    ("yyyrrrrrrrrr", 3.0),
    ("rrrrrrrrrrrr", 2.0),
    ("rrrGGGrrrrrr", 20.0),
    ("rrryyyrrrrrr", 3.0),
    ("rrrrrrrrrrrr", 2.0),
    ("rrrrrrGGGrrr", 20.0),
    ("rrrrrryyyrrr", 3.0),
    ("rrrrrrrrrrrr", 2.0),
    ("rrrrrrrrrGGG", 20.0),
    ("rrrrrrrrryyy", 3.0),
    ("rrrrrrrrrrrr", 2.0),
)
MIN_GREEN = 10.0
MAX_GREEN = 60.0
TLS_ID = "J1"


def make_phases() -> tuple[PhaseDefinition, ...]:
    return tuple(
        PhaseDefinition(
            phase_id=f"phase_{index}",
            phase_index=index,
            signal_state=state,
            duration_seconds=duration,
            movement_ids=(f"m{index // 3}",) if "G" in state else (),
        )
        for index, (state, duration) in enumerate(GRID_PROGRAM)
    )


def make_safety(max_green: float | None = MAX_GREEN) -> PhaseSafetyManager:
    return PhaseSafetyManager(
        phases=make_phases(),
        min_green_seconds=MIN_GREEN,
        max_green_seconds=max_green,
        conflicting_signal_groups=(),
        movement_conflicts={"m0": ("m1", "m2", "m3"), "m1": ("m0", "m2", "m3")},
    )


def make_observation(phase_index: int, elapsed: float) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A1",
            timestamp=0.0,
            current_phase=f"phase_{phase_index}",
            phase_elapsed=elapsed,
            incoming_queue={},
            incoming_occupancy={},
            incoming_speed={},
            outgoing_occupancy={},
            arrival_rate={},
        )
    )


@dataclass
class FakeSumoTrafficLight:
    """Emula o temporizador de fase do SUMO: o programa estático avança ao expirar, salvo se
    estendido.
    """

    program: tuple[tuple[str, float], ...] = GRID_PROGRAM
    phase: int = 0
    spent: float = 0.0
    remaining: float = GRID_PROGRAM[0][1]
    set_phase_calls: list[int] = field(default_factory=list)
    set_duration_calls: list[float] = field(default_factory=list)
    visited: list[tuple[int, float]] = field(default_factory=list)

    def setPhase(self, tls_id: str, index: int) -> None:  # noqa: N802
        assert tls_id == TLS_ID
        self.set_phase_calls.append(index)
        self.phase = index
        self.spent = 0.0
        self.remaining = self.program[index][1]

    def setPhaseDuration(self, tls_id: str, duration: float) -> None:  # noqa: N802
        assert tls_id == TLS_ID
        self.set_duration_calls.append(duration)
        self.remaining = duration

    def advance_one_second(self) -> None:
        self.visited.append((self.phase, self.spent))
        self.spent += 1.0
        self.remaining -= 1.0
        if self.remaining <= 0:
            self.phase = (self.phase + 1) % len(self.program)
            self.spent = 0.0
            self.remaining = self.program[self.phase][1]


def run_closed_loop(
    tls: FakeSumoTrafficLight,
    safety: PhaseSafetyManager,
    *,
    steps: int,
    wants_switch: bool = False,
) -> list[PhaseCommand]:
    actuator = TrafficLightActuator(trafficlight=tls)
    commands: list[PhaseCommand] = []
    for _ in range(steps):
        observation = make_observation(tls.phase, tls.spent)
        action = (
            TrafficLightAction.request_next_phase()
            if wants_switch
            else TrafficLightAction.keep_phase()
        )
        command = safety.resolve_action(observation, action)
        actuator.apply(traffic_light_id=TLS_ID, command=command)
        commands.append(command)
        tls.advance_one_second()
    return commands


def green_segments(tls: FakeSumoTrafficLight) -> list[tuple[int, int]]:
    """(phase_index, duration_seconds) de cada segmento de verde concluído."""
    green_indexes = {index for index, (state, _) in enumerate(GRID_PROGRAM) if "G" in state}
    segments: list[tuple[int, int]] = []
    current_phase: int | None = None
    length = 0
    for phase, _spent in tls.visited:
        if phase != current_phase:
            if current_phase in green_indexes:
                segments.append((current_phase, length))
            current_phase, length = phase, 0
        length += 1
    return segments


def test_keep_phase_at_15_seconds_extends_green_by_remaining_max_green() -> None:
    safety = make_safety()
    command = safety.resolve_action(make_observation(0, 15.0), TrafficLightAction.keep_phase())
    tls = FakeSumoTrafficLight(phase=0, spent=15.0, remaining=3.0)

    applied = TrafficLightActuator(trafficlight=tls).apply(traffic_light_id=TLS_ID, command=command)

    assert command.kind == PhaseCommandKind.KEEP_PHASE
    assert command.hold_remaining_seconds == pytest.approx(MAX_GREEN - 15.0)
    assert applied is True
    assert tls.set_duration_calls == [pytest.approx(45.0)]
    assert tls.set_phase_calls == []
    assert tls.remaining == pytest.approx(45.0)


def test_keep_phase_continues_beyond_default_program_duration() -> None:
    tls = FakeSumoTrafficLight()

    run_closed_loop(tls, make_safety(), steps=30)

    # Sem a retenção, o SUMO teria saído da fase 0 após 18 s.
    assert {phase for phase, _ in tls.visited} == {0}
    assert max(spent for _, spent in tls.visited) == 29.0
    assert tls.phase == 0
    assert tls.spent == 30.0


def test_green_can_reach_more_than_twenty_seconds_and_never_exceeds_max_green() -> None:
    tls = FakeSumoTrafficLight()

    run_closed_loop(tls, make_safety(), steps=400)

    durations = [duration for _phase, duration in green_segments(tls)]
    assert durations, "at least one green must complete"
    assert max(durations) > 20
    assert all(duration <= MAX_GREEN for duration in durations)
    assert MAX_GREEN in durations


def test_max_green_is_forced_through_the_regular_yellow_and_all_red_sequence() -> None:
    tls = FakeSumoTrafficLight()
    safety = make_safety(max_green=30.0)

    run_closed_loop(tls, safety, steps=30 + 3 + 2 + 5)

    # A retenção nunca concede mais que max_green: o temporizador expira (ou o gerenciador de
    # segurança força SET_PHASE) exatamente em 30 s, e sempre vai para o amarelo.
    assert [phase for phase, _ in tls.visited[:30]] == [0] * 30
    assert tls.visited[30][0] == 1  # amarelo, nunca direto para o próximo verde
    visited_order = []
    for phase, _ in tls.visited:
        if not visited_order or visited_order[-1] != phase:
            visited_order.append(phase)
    assert visited_order[:4] == [0, 1, 2, 3]  # verde, amarelo, vermelho total, próximo verde
    yellow_seconds = sum(1 for phase, _ in tls.visited if phase == 1)
    all_red_seconds = sum(1 for phase, _ in tls.visited if phase == 2)
    assert (yellow_seconds, all_red_seconds) == (3, 2)


def test_change_request_still_respects_min_green_and_keeps_green_held() -> None:
    tls = FakeSumoTrafficLight()
    safety = make_safety()

    commands = run_closed_loop(tls, safety, steps=int(MIN_GREEN) + 1, wants_switch=True)

    for command in commands[: int(MIN_GREEN)]:
        assert command.kind == PhaseCommandKind.KEEP_PHASE
        assert command.hold_remaining_seconds is not None
    switch = commands[int(MIN_GREEN)]
    assert switch.kind == PhaseCommandKind.SET_PHASE
    assert switch.phase_index == 1
    # O verde pôde cumprir seu min_green completo (10 s) mesmo tendo pedido para sair.
    assert green_segments(tls) == [] or all(d >= MIN_GREEN for _, d in green_segments(tls))
    assert tls.phase == 1


def test_only_program_states_are_ever_used_and_no_conflicting_movement_opens() -> None:
    tls = FakeSumoTrafficLight()
    safety = make_safety(max_green=25.0)

    run_closed_loop(tls, safety, steps=300)

    green_sets = {index // 3 for index, (state, _) in enumerate(GRID_PROGRAM) if "G" in state}
    assert green_sets == {0, 1, 2, 3}
    previous = None
    for phase, _ in tls.visited:
        state = GRID_PROGRAM[phase][0]
        assert state == make_phases()[phase].signal_state  # estado do programa intocado
        assert state.count("G") in {0, 3}  # exatamente uma aproximação aberta por vez
        if previous is not None and phase != previous:
            # as fases só avançam para a próxima fase do programa (amarelo/vermelho total nunca são
            # pulados)
            assert phase == (previous + 1) % len(GRID_PROGRAM)
        previous = phase


def test_transition_phases_are_not_extended() -> None:
    safety = make_safety()

    yellow = safety.resolve_action(make_observation(1, 1.0), TrafficLightAction.keep_phase())
    all_red = safety.resolve_action(make_observation(2, 1.0), TrafficLightAction.keep_phase())

    assert yellow.kind == PhaseCommandKind.KEEP_PHASE
    assert yellow.hold_remaining_seconds is None
    assert all_red.hold_remaining_seconds is None
    tls = FakeSumoTrafficLight(phase=1, spent=1.0, remaining=2.0)
    assert (
        TrafficLightActuator(trafficlight=tls).apply(traffic_light_id=TLS_ID, command=yellow)
        is False
    )
    assert tls.set_duration_calls == []


def test_safety_manager_without_max_green_keeps_legacy_behaviour() -> None:
    safety = make_safety(max_green=None)

    command = safety.resolve_action(make_observation(0, 15.0), TrafficLightAction.keep_phase())

    assert command.hold_remaining_seconds is None
    forced = safety.resolve_action(make_observation(0, 500.0), TrafficLightAction.keep_phase())
    assert forced.kind == PhaseCommandKind.KEEP_PHASE


def test_max_green_below_min_green_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_green_seconds"):
        PhaseSafetyManager(phases=make_phases(), min_green_seconds=10.0, max_green_seconds=5.0)


def test_fixed_time_controller_issues_no_traffic_light_commands() -> None:
    class RecordingTrafficLight:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def setPhase(self, *args: object) -> None:  # noqa: N802
            self.calls.append("setPhase")

        def setPhaseDuration(self, *args: object) -> None:  # noqa: N802
            self.calls.append("setPhaseDuration")

    class Connection:
        def __init__(self) -> None:
            self.trafficlight = RecordingTrafficLight()

    connection = Connection()
    controller = FixedTimeController()

    for _ in range(30):
        controller.before_simulation_step(connection)
        controller.after_simulation_step(connection)

    assert connection.trafficlight.calls == []


def test_safety_manager_forces_set_phase_at_max_green_when_timer_was_not_extended() -> None:
    safety = make_safety(max_green=30.0)

    forced = safety.resolve_action(make_observation(0, 30.0), TrafficLightAction.keep_phase())

    assert forced.kind == PhaseCommandKind.SET_PHASE
    assert forced.phase_index == 1
    assert forced.hold_remaining_seconds is None
