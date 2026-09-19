from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from traffic_agents.controllers import PhaseDefinition, PhaseSafetyManager
from traffic_agents.domain import AgentObservation, IntersectionState, TrafficLightAction
from traffic_agents.metrics import (
    AGENT_TRACE_FILE,
    AgentDecisionTraceSettings,
    AgentDecisionTraceWriter,
    build_agent_decision_trace_record,
    inspect_agent_trace,
)

PHASES = (
    PhaseDefinition(
        phase_id="NS_THROUGH",
        phase_index=0,
        signal_state="Gr",
        duration_seconds=20.0,
        movement_ids=("A5:NS",),
    ),
    PhaseDefinition(
        phase_id="NS_TO_YELLOW",
        phase_index=1,
        signal_state="yr",
        duration_seconds=3.0,
    ),
    PhaseDefinition(
        phase_id="ALL_RED",
        phase_index=2,
        signal_state="rr",
        duration_seconds=2.0,
    ),
    PhaseDefinition(
        phase_id="EW_THROUGH",
        phase_index=3,
        signal_state="rG",
        duration_seconds=20.0,
        movement_ids=("A5:EW",),
    ),
)


def make_safety() -> PhaseSafetyManager:
    return PhaseSafetyManager(phases=PHASES, min_green_seconds=10.0)


def make_observation(*, elapsed: float = 10.0) -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A5",
            timestamp=520.0,
            current_phase="NS_THROUGH",
            phase_elapsed=elapsed,
            incoming_queue={"north_in_0": 12, "east_in_0": 19},
            incoming_occupancy={"north_in_0": 0.1, "east_in_0": 0.2},
            incoming_speed={"north_in_0": 10.0, "east_in_0": 8.0},
            outgoing_occupancy={"south_out_0": 0.4, "west_out_0": 0.7},
            arrival_rate={"north_in": 1.2, "east_in": 2.4},
        )
    )


def test_trace_disabled_has_minimal_enabled_check() -> None:
    settings = AgentDecisionTraceSettings.from_config(
        SimpleNamespace(agent_decisions=False, agents=("A5",))
    )

    assert settings.enabled_for("A5") is False
    assert settings.enabled_for("A1") is False


def test_trace_enabled_writes_valid_b2_jsonl_without_neighbor_data(tmp_path: Path) -> None:
    safety = make_safety()
    observation = make_observation(elapsed=10.0)
    action = TrafficLightAction.switch_phase("EW_THROUGH")
    command = safety.resolve_action(observation, action)
    writer = AgentDecisionTraceWriter(
        run_id="run-1",
        path=tmp_path / AGENT_TRACE_FILE,
        settings=AgentDecisionTraceSettings(enabled=True, agents=frozenset({"A5"})),
    )

    writer.append(
        build_agent_decision_trace_record(
            run_id="run-1",
            simulation_step=520,
            controller_id="B2_LOCAL_PRESSURE",
            observation=observation,
            action=action,
            command=command,
            safety=safety,
            movement_pressure={"A5:NS": 31.4, "A5:EW": 42.8},
            phase_scores={"NS_THROUGH": 31.4, "EW_THROUGH": 42.8},
            computation_ms=0.1234567,
        )
    )

    payload = json.loads((tmp_path / AGENT_TRACE_FILE).read_text(encoding="utf-8"))

    assert payload["run_id"] == "run-1"
    assert payload["agent_id"] == "A5"
    assert payload["safety_decision"] == "WAIT_YELLOW"
    assert payload["actual_phase"] == "NS_TO_YELLOW"
    assert payload["local_state_summary"]["incoming_queues"] == {
        "east_in_0": 19,
        "north_in_0": 12,
    }
    assert "neighbor_message_count" not in payload
    assert "vehicle" not in json.dumps(payload).lower()


def test_trace_records_c1_neighbor_data() -> None:
    safety = make_safety()
    observation = make_observation(elapsed=10.0)
    action = TrafficLightAction.switch_phase("EW_THROUGH")
    command = safety.resolve_action(observation, action)

    payload = build_agent_decision_trace_record(
        run_id="run-1",
        simulation_step=520,
        controller_id="C1_COOPERATIVE_COMPACT",
        observation=observation,
        action=action,
        command=command,
        safety=safety,
        movement_pressure={"A5:NS": 31.4, "A5:EW": 37.7},
        phase_scores={"NS_THROUGH": 31.4, "EW_THROUGH": 42.8},
        local_phase_scores={"NS_THROUGH": 31.4, "EW_THROUGH": 37.7},
        neighbor_message_count=2,
        messages_used=1,
        messages_ignored=1,
        message_age_summary={"average": 1.5, "max": 3},
        stale_count=1,
        cooperative_adjustment={"NS_THROUGH": 0.0, "EW_THROUGH": 5.1},
        computation_ms=0.2,
    )

    assert payload["neighbor_message_count"] == 2
    assert payload["messages_used"] == 1
    assert payload["messages_ignored"] == 1
    assert payload["message_age_summary"] == {"average": 1.5, "max": 3}
    assert payload["stale_count"] == 1
    assert payload["cooperative_adjustment"] == {"EW_THROUGH": 5.1, "NS_THROUGH": 0.0}


def test_trace_records_safety_override_reason_for_min_green() -> None:
    safety = make_safety()
    observation = make_observation(elapsed=9.0)
    action = TrafficLightAction.switch_phase("EW_THROUGH")
    command = safety.resolve_action(observation, action)

    payload = build_agent_decision_trace_record(
        run_id="run-1",
        simulation_step=12,
        controller_id="B2_LOCAL_PRESSURE",
        observation=observation,
        action=action,
        command=command,
        safety=safety,
        movement_pressure={"A5:NS": 0.0, "A5:EW": 10.0},
        phase_scores={"NS_THROUGH": 0.0, "EW_THROUGH": 10.0},
        computation_ms=0.1,
    )

    assert payload["requested_phase"] == "EW_THROUGH"
    assert payload["actual_phase"] == "NS_THROUGH"
    assert payload["safety_override_reason"] == "MIN_GREEN"


def test_trace_inspect_shows_relevant_decision_without_ai_explanation(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    safety = make_safety()
    observation = make_observation(elapsed=10.0)
    action = TrafficLightAction.switch_phase("EW_THROUGH")
    command = safety.resolve_action(observation, action)
    payload = build_agent_decision_trace_record(
        run_id="run-1",
        simulation_step=520,
        controller_id="C1_COOPERATIVE_COMPACT",
        observation=observation,
        action=action,
        command=command,
        safety=safety,
        movement_pressure={"A5:NS": 31.4, "A5:EW": 37.7},
        phase_scores={"NS_THROUGH": 31.4, "EW_THROUGH": 42.8},
        local_phase_scores={"NS_THROUGH": 31.4, "EW_THROUGH": 37.7},
        neighbor_message_count=1,
        messages_used=1,
        messages_ignored=0,
        message_age_summary={"average": 1.0, "max": 1},
        stale_count=0,
        cooperative_adjustment={"NS_THROUGH": 0.0, "EW_THROUGH": 5.1},
        computation_ms=0.2,
    )
    (run_dir / AGENT_TRACE_FILE).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    output = inspect_agent_trace(run_id="run-1", agent_id="A5", artifacts_dir=tmp_path)

    assert "STEP 520\nA5" in output
    assert "EW_THROUGH 42.8" in output
    assert "EW_THROUGH +5.1" in output
    assert "safety:\nWAIT_YELLOW" in output
    assert "actual:\nNS_TO_YELLOW" in output
