from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from pathlib import Path

PERFORMANCE_FILE = "performance.json"
TRACI_PROFILING_NOTE = (
    "TraCI is used for this run. If TraCI is measured as a relevant bottleneck during "
    "campaigns, libsumo can be evaluated later; this run does not infer that bottleneck."
)
CONTROLLER_DECISION_WINDOW = "all simulation steps, including warmup"


@dataclass(frozen=True)
class TimingStats:
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    mean_ms: float = 0.0
    max_ms: float = 0.0
    sample_count: int = 0


@dataclass(frozen=True)
class ControllerPerformanceTimings:
    decision_timings_ms: tuple[float, ...] = ()
    message_bus_publish_time_ms: float = 0.0
    message_bus_receive_time_ms: float = 0.0

    @property
    def message_bus_time_ms(self) -> float:
        return self.message_bus_publish_time_ms + self.message_bus_receive_time_ms


def calculate_timing_stats(samples_ms: Sequence[float]) -> TimingStats:
    if not samples_ms:
        return TimingStats()
    ordered = sorted(float(sample) for sample in samples_ms)
    return TimingStats(
        p50_ms=_median(ordered),
        p95_ms=_nearest_rank_percentile(ordered, 0.95),
        mean_ms=sum(ordered) / len(ordered),
        max_ms=ordered[-1],
        sample_count=len(ordered),
    )


def build_performance_payload(
    *,
    run_id: str,
    controller: str,
    simulation_steps: int,
    wall_time_seconds: float,
    controller_timings: ControllerPerformanceTimings,
    trace_enabled: bool,
    result_collector_time_ms: float = 0.0,
    use_gui: bool = False,
) -> dict[str, object]:
    stats = calculate_timing_stats(controller_timings.decision_timings_ms)
    steps_per_second = simulation_steps / wall_time_seconds if wall_time_seconds > 0 else 0.0
    return {
        "run_id": run_id,
        "controller": controller,
        "simulation_steps": int(simulation_steps),
        "wall_time_seconds": round(float(wall_time_seconds), 6),
        "steps_per_second": round(steps_per_second, 6),
        "controller_decision_p50_ms": round(stats.p50_ms, 6),
        "controller_decision_p95_ms": round(stats.p95_ms, 6),
        "controller_decision_mean_ms": round(stats.mean_ms, 6),
        "controller_decision_max_ms": round(stats.max_ms, 6),
        "controller_decision_sample_count": stats.sample_count,
        "controller_decision_window": CONTROLLER_DECISION_WINDOW,
        "message_bus_time_ms": round(controller_timings.message_bus_time_ms, 6),
        "message_bus_publish_time_ms": round(
            controller_timings.message_bus_publish_time_ms,
            6,
        ),
        "message_bus_receive_time_ms": round(
            controller_timings.message_bus_receive_time_ms,
            6,
        ),
        "result_collector_time_ms": round(float(result_collector_time_ms), 6),
        "trace_enabled": bool(trace_enabled),
        "sumo_mode": "gui" if use_gui else "headless",
        "traci_note": TRACI_PROFILING_NOTE,
    }


def write_performance_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _median(ordered: Sequence[float]) -> float:
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _nearest_rank_percentile(ordered: Sequence[float], percentile: float) -> float:
    rank = max(1, ceil(percentile * len(ordered)))
    return ordered[rank - 1]
