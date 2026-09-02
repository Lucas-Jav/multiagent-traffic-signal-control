from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from traffic_agents.config import load_scenario_config
from traffic_agents.domain import IntersectionId, IntersectionState
from traffic_agents.simulation import TraCISimulationRunner

INTERSECTION_LABELS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one SUMO step of local intersection state."
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("scenarios/grid_3x3/scenario.yaml"),
    )
    args = parser.parse_args()

    scenario_config = load_scenario_config(args.scenario)
    traffic_light_ids = _load_traffic_light_ids(args.scenario.parent / "metadata.json")
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=args.scenario.parent,
        label="inspect-intersections",
        max_steps=1,
        write_manifest=False,
    )

    try:
        runner.start()
        runner.step()
        provider = runner.make_sensor_provider(traffic_light_ids=traffic_light_ids)
        print(
            "intersection timestamp phase phase_elapsed queue_total "
            "avg_in_occupancy avg_in_speed"
        )
        for intersection_id in INTERSECTION_LABELS:
            state = provider.observe(intersection_id)
            print(_format_state(state))
    finally:
        runner.stop()

    return 0


def _load_traffic_light_ids(path: Path) -> dict[IntersectionId, str]:
    with path.open(encoding="utf-8") as file:
        payload: Any = json.load(file)

    traffic_light_ids = payload.get("traffic_light_ids") if isinstance(payload, dict) else None
    if not isinstance(traffic_light_ids, dict):
        msg = f"traffic_light_ids mapping not found in {path}"
        raise ValueError(msg)

    parsed: dict[IntersectionId, str] = {}
    for intersection_id, traffic_light_id in traffic_light_ids.items():
        if not isinstance(intersection_id, str) or not isinstance(traffic_light_id, str):
            msg = f"traffic_light_ids must map strings to strings in {path}"
            raise ValueError(msg)
        parsed[intersection_id] = traffic_light_id
    return parsed


def _format_state(state: IntersectionState) -> str:
    queue_total = sum(state.incoming_queue.values())
    avg_in_occupancy = _mean(tuple(state.incoming_occupancy.values()))
    avg_in_speed = _mean(tuple(state.incoming_speed.values()))
    return (
        f"{state.intersection_id} "
        f"{state.timestamp:.1f} "
        f"{state.current_phase} "
        f"{state.phase_elapsed:.1f} "
        f"{queue_total} "
        f"{avg_in_occupancy:.3f} "
        f"{avg_in_speed:.3f}"
    )


def _mean(values: tuple[float, ...]) -> float:
    if not values:
        msg = "cannot calculate mean of empty values"
        raise ValueError(msg)
    return sum(values) / len(values)


if __name__ == "__main__":
    raise SystemExit(main())
