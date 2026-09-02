from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from traffic_agents.domain import (
    AgentObservation,
    ControllerDecision,
    TrafficLightAction,
    TrafficLightActionKind,
)


class PhaseSafetyViolationError(ValueError):
    """Raised when a controller intent cannot be converted to a safe phase command."""


class UnsafePhaseProgramError(ValueError):
    """Raised when the configured SUMO phase program contains unsafe definitions."""


class PhaseCommandKind(StrEnum):
    KEEP_PHASE = "KEEP_PHASE"
    SET_PHASE = "SET_PHASE"


class PhaseKind(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    INTERGREEN = "INTERGREEN"


@dataclass(frozen=True)
class PhaseDefinition:
    phase_id: str
    phase_index: int
    signal_state: str
    duration_seconds: float

    @property
    def kind(self) -> PhaseKind:
        if any(_is_yellow(signal) for signal in self.signal_state):
            return PhaseKind.YELLOW
        if any(_is_green(signal) for signal in self.signal_state):
            return PhaseKind.GREEN
        return PhaseKind.INTERGREEN


@dataclass(frozen=True)
class PhaseCommand:
    kind: PhaseCommandKind
    phase_id: str
    phase_index: int

    @classmethod
    def keep_phase(cls, phase: PhaseDefinition) -> PhaseCommand:
        return cls(
            kind=PhaseCommandKind.KEEP_PHASE,
            phase_id=phase.phase_id,
            phase_index=phase.phase_index,
        )

    @classmethod
    def set_phase(cls, phase: PhaseDefinition) -> PhaseCommand:
        return cls(
            kind=PhaseCommandKind.SET_PHASE,
            phase_id=phase.phase_id,
            phase_index=phase.phase_index,
        )


@dataclass(frozen=True, init=False)
class PhaseSafetyManager:
    phases: tuple[PhaseDefinition, ...]
    min_green_seconds: float
    allowed_green_transitions: Mapping[str, tuple[str, ...]]

    def __init__(
        self,
        *,
        phases: tuple[PhaseDefinition, ...],
        min_green_seconds: float,
        allowed_green_transitions: Mapping[str, tuple[str, ...]] | None = None,
        conflicting_signal_groups: tuple[tuple[int, ...], ...] = (),
    ) -> None:
        if min_green_seconds < 0:
            msg = "min_green_seconds must be non-negative"
            raise ValueError(msg)
        if not phases:
            msg = "phases must not be empty"
            raise ValueError(msg)

        _validate_phase_program(phases, conflicting_signal_groups)
        transition_map = _build_allowed_green_transitions(phases, allowed_green_transitions)

        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "min_green_seconds", min_green_seconds)
        object.__setattr__(self, "allowed_green_transitions", MappingProxyType(transition_map))

    def resolve(self, observation: AgentObservation, decision: ControllerDecision) -> PhaseCommand:
        if decision.intersection_id != observation.state.intersection_id:
            msg = (
                "decision intersection_id does not match observation intersection_id: "
                f"{decision.intersection_id} != {observation.state.intersection_id}"
            )
            raise PhaseSafetyViolationError(msg)
        return self.resolve_action(observation, decision.action)

    def resolve_action(
        self,
        observation: AgentObservation,
        action: TrafficLightAction,
    ) -> PhaseCommand:
        current_phase = self._phase_by_id(observation.state.current_phase)

        if current_phase.kind != PhaseKind.GREEN:
            return self._resolve_transition_phase(observation, current_phase)

        if action.kind == TrafficLightActionKind.KEEP_PHASE:
            return PhaseCommand.keep_phase(current_phase)

        if observation.state.phase_elapsed < self.min_green_seconds:
            return PhaseCommand.keep_phase(current_phase)

        target_phase_id = self._target_phase_id(current_phase, action)
        if target_phase_id == current_phase.phase_id:
            return PhaseCommand.keep_phase(current_phase)

        allowed_targets = self.allowed_green_transitions[current_phase.phase_id]
        if target_phase_id not in allowed_targets:
            msg = (
                f"transition from {current_phase.phase_id} to {target_phase_id} is not allowed"
            )
            raise PhaseSafetyViolationError(msg)

        return PhaseCommand.set_phase(self._next_phase_after(current_phase))

    def _resolve_transition_phase(
        self,
        observation: AgentObservation,
        current_phase: PhaseDefinition,
    ) -> PhaseCommand:
        if observation.state.phase_elapsed < current_phase.duration_seconds:
            return PhaseCommand.keep_phase(current_phase)
        return PhaseCommand.set_phase(self._next_phase_after(current_phase))

    def _target_phase_id(
        self,
        current_phase: PhaseDefinition,
        action: TrafficLightAction,
    ) -> str:
        if action.kind == TrafficLightActionKind.REQUEST_NEXT_PHASE:
            return self.allowed_green_transitions[current_phase.phase_id][0]
        if action.kind == TrafficLightActionKind.SWITCH_PHASE:
            if action.target_phase is None:
                msg = "target_phase is required for SWITCH_PHASE"
                raise PhaseSafetyViolationError(msg)
            target_phase = self._phase_by_id(action.target_phase)
            if target_phase.kind != PhaseKind.GREEN:
                msg = f"target phase {target_phase.phase_id} is not a controllable green phase"
                raise PhaseSafetyViolationError(msg)
            return target_phase.phase_id
        msg = f"unsupported traffic light action: {action.kind}"
        raise PhaseSafetyViolationError(msg)

    def _phase_by_id(self, phase_id: str) -> PhaseDefinition:
        for phase in self.phases:
            if phase.phase_id == phase_id:
                return phase

        msg = f"unknown phase_id: {phase_id}"
        raise PhaseSafetyViolationError(msg)

    def _next_phase_after(self, phase: PhaseDefinition) -> PhaseDefinition:
        next_index = (self.phases.index(phase) + 1) % len(self.phases)
        return self.phases[next_index]


def _validate_phase_program(
    phases: tuple[PhaseDefinition, ...],
    conflicting_signal_groups: tuple[tuple[int, ...], ...],
) -> None:
    phase_ids = {phase.phase_id for phase in phases}
    if len(phase_ids) != len(phases):
        msg = "phase IDs must be unique"
        raise UnsafePhaseProgramError(msg)

    phase_indexes = {phase.phase_index for phase in phases}
    if len(phase_indexes) != len(phases):
        msg = "phase indexes must be unique"
        raise UnsafePhaseProgramError(msg)
    for phase in phases:
        if phase.phase_index < 0:
            msg = f"phase index must be non-negative: {phase.phase_id}"
            raise UnsafePhaseProgramError(msg)
        if phase.duration_seconds < 0:
            msg = f"phase duration must be non-negative: {phase.phase_id}"
            raise UnsafePhaseProgramError(msg)

    state_lengths = {len(phase.signal_state) for phase in phases}
    if state_lengths == {0}:
        msg = "signal states must not be empty"
        raise UnsafePhaseProgramError(msg)
    if len(state_lengths) != 1:
        msg = "all signal states must have the same length"
        raise UnsafePhaseProgramError(msg)

    state_length = state_lengths.pop()
    for group in conflicting_signal_groups:
        for signal_index in group:
            if signal_index < 0 or signal_index >= state_length:
                msg = f"conflicting signal index out of range: {signal_index}"
                raise UnsafePhaseProgramError(msg)

    for phase in phases:
        for group in conflicting_signal_groups:
            green_indexes = [
                signal_index
                for signal_index in group
                if _is_green(phase.signal_state[signal_index])
            ]
            if len(green_indexes) > 1:
                msg = (
                    f"phase {phase.phase_id} contains conflicting green signals: "
                    f"{tuple(green_indexes)}"
                )
                raise UnsafePhaseProgramError(msg)


def _build_allowed_green_transitions(
    phases: tuple[PhaseDefinition, ...],
    configured_transitions: Mapping[str, tuple[str, ...]] | None,
) -> dict[str, tuple[str, ...]]:
    green_phase_ids = tuple(phase.phase_id for phase in phases if phase.kind == PhaseKind.GREEN)
    if not green_phase_ids:
        msg = "phase program must contain at least one green phase"
        raise UnsafePhaseProgramError(msg)

    if configured_transitions is None:
        return {
            phase_id: (green_phase_ids[(index + 1) % len(green_phase_ids)],)
            for index, phase_id in enumerate(green_phase_ids)
        }

    transition_map: dict[str, tuple[str, ...]] = {}
    green_phase_id_set = set(green_phase_ids)
    for source_phase_id, target_phase_ids in configured_transitions.items():
        if source_phase_id not in green_phase_id_set:
            msg = f"transition source is not a green phase: {source_phase_id}"
            raise UnsafePhaseProgramError(msg)
        if not target_phase_ids:
            msg = f"green phase must have at least one allowed target: {source_phase_id}"
            raise UnsafePhaseProgramError(msg)
        for target_phase_id in target_phase_ids:
            if target_phase_id not in green_phase_id_set:
                msg = f"transition target is not a green phase: {target_phase_id}"
                raise UnsafePhaseProgramError(msg)
            if target_phase_id != _next_green_phase_id_after(phases, source_phase_id):
                msg = (
                    f"transition from {source_phase_id} to {target_phase_id} would skip "
                    "SUMO yellow/intergreen sequence"
                )
                raise UnsafePhaseProgramError(msg)
        transition_map[source_phase_id] = tuple(target_phase_ids)

    missing_phase_ids = green_phase_id_set - set(transition_map)
    if missing_phase_ids:
        msg = f"missing allowed transitions for green phases: {tuple(sorted(missing_phase_ids))}"
        raise UnsafePhaseProgramError(msg)

    return transition_map


def _next_green_phase_id_after(phases: tuple[PhaseDefinition, ...], phase_id: str) -> str:
    source_index = next(index for index, phase in enumerate(phases) if phase.phase_id == phase_id)
    for offset in range(1, len(phases) + 1):
        candidate = phases[(source_index + offset) % len(phases)]
        if candidate.kind == PhaseKind.GREEN:
            return candidate.phase_id

    msg = "phase program must contain at least one green phase"
    raise UnsafePhaseProgramError(msg)


def _is_green(signal: str) -> bool:
    return signal in {"G", "g"}


def _is_yellow(signal: str) -> bool:
    return signal in {"y", "Y"}
