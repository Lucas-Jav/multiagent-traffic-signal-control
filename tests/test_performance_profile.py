from __future__ import annotations

import json
from pathlib import Path

import pytest

from traffic_agents.metrics import (
    CONTROLLER_DECISION_WINDOW,
    PERFORMANCE_FILE,
    TRACI_PROFILING_NOTE,
    ControllerPerformanceTimings,
    build_performance_payload,
    calculate_timing_stats,
    write_performance_json,
)


def test_statistics_calculation_uses_median_and_nearest_rank_p95() -> None:
    stats = calculate_timing_stats([5.0, 1.0, 3.0, 2.0, 4.0])

    assert stats.sample_count == 5
    assert stats.p50_ms == pytest.approx(3.0)
    assert stats.p95_ms == pytest.approx(5.0)
    assert stats.mean_ms == pytest.approx(3.0)
    assert stats.max_ms == pytest.approx(5.0)


def test_empty_timings_return_zero_statistics() -> None:
    stats = calculate_timing_stats([])

    assert stats.sample_count == 0
    assert stats.p50_ms == 0.0
    assert stats.p95_ms == 0.0
    assert stats.mean_ms == 0.0
    assert stats.max_ms == 0.0


def test_single_sample_uses_same_value_for_all_statistics() -> None:
    stats = calculate_timing_stats([7.25])

    assert stats.sample_count == 1
    assert stats.p50_ms == pytest.approx(7.25)
    assert stats.p95_ms == pytest.approx(7.25)
    assert stats.mean_ms == pytest.approx(7.25)
    assert stats.max_ms == pytest.approx(7.25)


def test_output_serialization_writes_performance_json(tmp_path: Path) -> None:
    payload = build_performance_payload(
        run_id="run-1",
        controller="C1_COOPERATIVE_COMPACT",
        simulation_steps=4,
        wall_time_seconds=2.0,
        controller_timings=ControllerPerformanceTimings(
            decision_timings_ms=(1.0, 2.0, 4.0),
            message_bus_publish_time_ms=0.4,
            message_bus_receive_time_ms=0.6,
        ),
        trace_enabled=True,
        result_collector_time_ms=0.25,
        use_gui=False,
    )
    path = tmp_path / PERFORMANCE_FILE

    write_performance_json(path, payload)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run-1"
    assert saved["controller"] == "C1_COOPERATIVE_COMPACT"
    assert saved["simulation_steps"] == 4
    assert saved["wall_time_seconds"] == 2.0
    assert saved["steps_per_second"] == 2.0
    assert saved["controller_decision_p50_ms"] == 2.0
    assert saved["controller_decision_p95_ms"] == 4.0
    assert saved["controller_decision_mean_ms"] == pytest.approx(2.333333)
    assert saved["controller_decision_max_ms"] == 4.0
    assert saved["message_bus_time_ms"] == 1.0
    assert saved["message_bus_publish_time_ms"] == 0.4
    assert saved["message_bus_receive_time_ms"] == 0.6
    assert saved["result_collector_time_ms"] == 0.25
    assert saved["trace_enabled"] is True
    assert saved["sumo_mode"] == "headless"
    assert saved["controller_decision_window"] == CONTROLLER_DECISION_WINDOW
    assert saved["traci_note"] == TRACI_PROFILING_NOTE
