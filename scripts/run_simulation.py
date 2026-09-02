from __future__ import annotations

import argparse
from pathlib import Path

from traffic_agents.config import load_scenario_config
from traffic_agents.simulation import TraCISimulationRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a SUMO scenario without signal control.")
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    scenario_config = load_scenario_config(args.scenario)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=args.scenario.parent,
    )

    print("simulation start")
    summary = runner.run()
    print("simulation end")
    print(f"started_at={summary.started_at}")
    print(f"ended_at={summary.ended_at}")
    print(f"steps_executed={summary.steps_executed}")
    print(f"vehicles_departed={summary.vehicles_departed}")
    print(f"vehicles_arrived={summary.vehicles_arrived}")
    print(f"wall_time_seconds={summary.wall_time_seconds:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
