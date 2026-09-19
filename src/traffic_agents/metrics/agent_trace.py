from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from traffic_agents.controllers.phase_safety import (
    PhaseCommand,
    PhaseKind,
    PhaseSafetyManager,
)
from traffic_agents.domain import AgentObservation, TrafficLightAction
from traffic_agents.metrics.step_telemetry import requested_phase_id

AGENT_TRACE_FILE = "agent_trace.jsonl"


@dataclass(frozen=True)
class AgentDecisionTraceSettings:
    enabled: bool = False
    agents: frozenset[str] = frozenset()

    @classmethod
    def from_config(cls, config: object | None) -> AgentDecisionTraceSettings:
        if config is None:
            return cls()
        enabled = bool(getattr(config, "agent_decisions", False))
        agents = frozenset(str(agent) for agent in getattr(config, "agents", ()))
        return cls(enabled=enabled, agents=agents)

    def enabled_for(self, agent_id: str) -> bool:
        return self.enabled and (not self.agents or agent_id in self.agents)


class AgentDecisionTraceWriter:
    def __init__(
        self,
        *,
        run_id: str,
        path: Path,
        settings: AgentDecisionTraceSettings,
    ) -> None:
        self.run_id = run_id
        self.path = path
        self.settings = settings

    def enabled_for(self, agent_id: str) -> bool:
        return self.settings.enabled_for(agent_id)

    def append(self, record: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


@dataclass(frozen=True)
class DecisionTimer:
    started_at: float

    @classmethod
    def start(cls) -> DecisionTimer:
        return cls(started_at=perf_counter())

    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started_at) * 1000


def build_agent_decision_trace_record(
    *,
    run_id: str,
    simulation_step: int,
    controller_id: str,
    observation: AgentObservation,
    action: TrafficLightAction,
    command: PhaseCommand,
    safety: PhaseSafetyManager,
    movement_pressure: Mapping[str, float],
    phase_scores: Mapping[str, float],
    computation_ms: float,
    local_phase_scores: Mapping[str, float] | None = None,
    neighbor_message_count: int | None = None,
    messages_used: int | None = None,
    messages_ignored: int | None = None,
    message_age_summary: Mapping[str, float | int] | None = None,
    stale_count: int | None = None,
    cooperative_adjustment: Mapping[str, float] | None = None,
) -> dict[str, object]:
    state = observation.state
    requested_phase = requested_phase_id(observation, action, safety)
    actual_phase = command.phase_id
    safety_decision = _safety_decision(
        current_phase=state.current_phase,
        requested_phase=requested_phase,
        command=command,
        safety=safety,
    )
    record: dict[str, object] = {
        "run_id": run_id,
        "simulation_step": int(simulation_step),
        "agent_id": state.intersection_id,
        "controller_id": controller_id,
        "local_state_summary": {
            "incoming_queues": dict(sorted(state.incoming_queue.items())),
            "outgoing_occupancies": dict(sorted(state.outgoing_occupancy.items())),
            "arrival_rates": dict(sorted(state.arrival_rate.items())),
        },
        "current_phase": state.current_phase,
        "phase_elapsed": float(state.phase_elapsed),
        "movement_pressure": _sorted_float_map(movement_pressure),
        "phase_scores": _sorted_float_map(phase_scores),
        "requested_phase": requested_phase,
        "safety_decision": safety_decision,
        "actual_phase": actual_phase,
        "computation_ms": round(computation_ms, 6),
    }
    if requested_phase != actual_phase:
        record["safety_override_reason"] = safety_decision
    if local_phase_scores is not None:
        record["local_phase_scores"] = _sorted_float_map(local_phase_scores)
    if neighbor_message_count is not None:
        record.update(
            {
                "neighbor_message_count": int(neighbor_message_count),
                "messages_used": int(messages_used or 0),
                "messages_ignored": int(messages_ignored or 0),
                "message_age_summary": dict(message_age_summary or {}),
                "stale_count": int(stale_count or 0),
                "cooperative_adjustment": _sorted_float_map(cooperative_adjustment or {}),
            }
        )
    return record


def inspect_agent_trace(
    *,
    run_id: str,
    agent_id: str,
    artifacts_dir: Path,
    limit: int = 20,
) -> str:
    trace_path = find_agent_trace_path(run_id=run_id, artifacts_dir=artifacts_dir)
    records = list(_read_jsonl(trace_path))
    selected = [
        record
        for record in records
        if record.get("run_id") == run_id and record.get("agent_id") == agent_id
    ]
    relevant = [record for record in selected if _is_relevant(record)]
    if relevant:
        selected = relevant
    if limit > 0:
        selected = selected[:limit]
    if not selected:
        return f"no trace records found for run={run_id} agent={agent_id}"
    return "\n\n".join(_format_record(record) for record in selected)


def find_agent_trace_path(*, run_id: str, artifacts_dir: Path) -> Path:
    candidates = [
        artifacts_dir / "runs" / run_id / AGENT_TRACE_FILE,
        artifacts_dir / run_id / AGENT_TRACE_FILE,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for candidate in artifacts_dir.rglob(AGENT_TRACE_FILE):
        if candidate.parent.name == run_id:
            return candidate
    msg = f"agent trace not found for run: {run_id}"
    raise FileNotFoundError(msg)


def _safety_decision(
    *,
    current_phase: str,
    requested_phase: str,
    command: PhaseCommand,
    safety: PhaseSafetyManager,
) -> str:
    actual_phase = command.phase_id
    actual_kind = _phase_kind(actual_phase, safety)
    current_kind = _phase_kind(current_phase, safety)
    if actual_phase == requested_phase:
        return "APPLIED" if requested_phase != current_phase else "KEEP"
    if current_kind == PhaseKind.GREEN and actual_phase == current_phase:
        return "MIN_GREEN"
    if actual_kind == PhaseKind.YELLOW:
        return "WAIT_YELLOW"
    if actual_kind == PhaseKind.INTERGREEN:
        return "WAIT_INTERGREEN"
    return "SAFETY_OVERRIDE"


def _phase_kind(phase_id: str, safety: PhaseSafetyManager) -> PhaseKind:
    for phase in safety.phases:
        if phase.phase_id == phase_id:
            return phase.kind
    return PhaseKind.INTERGREEN


def _sorted_float_map(values: Mapping[str, float]) -> dict[str, float]:
    return {key: round(float(value), 6) for key, value in sorted(values.items())}


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                payload = json.loads(stripped)
                if isinstance(payload, dict):
                    yield payload


def _is_relevant(record: Mapping[str, Any]) -> bool:
    if record.get("requested_phase") != record.get("actual_phase"):
        return True
    if record.get("requested_phase") != record.get("current_phase"):
        return True
    adjustment = record.get("cooperative_adjustment")
    if isinstance(adjustment, dict):
        return any(abs(float(value)) > 0.000001 for value in adjustment.values())
    return False


def _format_record(record: Mapping[str, Any]) -> str:
    lines = [
        f"STEP {record['simulation_step']}",
        str(record["agent_id"]),
        f"current={record['current_phase']}",
        "",
        "local pressure:",
    ]
    lines.extend(_format_scores(record.get("phase_scores")))
    adjustment = record.get("cooperative_adjustment")
    if isinstance(adjustment, dict) and adjustment:
        non_zero = {
            str(key): float(value)
            for key, value in adjustment.items()
            if abs(float(value)) > 0.000001
        }
        if non_zero:
            lines.extend(["", "neighbor adjustment:"])
            lines.extend(f"{key} {value:+.1f}" for key, value in sorted(non_zero.items()))
    lines.extend(
        [
            "",
            "requested:",
            str(record["requested_phase"]),
            "",
            "safety:",
            str(record["safety_decision"]),
            "",
            "actual:",
            str(record["actual_phase"]),
        ]
    )
    return "\n".join(lines)


def _format_scores(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [f"{key} {float(score):.1f}" for key, score in sorted(value.items())]
