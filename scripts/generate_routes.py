from __future__ import annotations

import argparse
from pathlib import Path

from traffic_agents.config import load_scenario_config
from traffic_agents.simulation import TrafficDemandGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic route demand for a scenario.")
    parser.add_argument(
        "scenario_path",
        type=Path,
        nargs="?",
        default=Path("scenarios/grid_3x3/scenario.yaml"),
    )
    args = parser.parse_args()

    scenario_config = load_scenario_config(args.scenario_path)
    generator = TrafficDemandGenerator(
        scenario_config=scenario_config,
        scenario_dir=args.scenario_path.parent,
        seed=scenario_config.seed,
        demand_profile=scenario_config.traffic.demand_profile,
    )
    generated = generator.generate()

    print("Generated synthetic traffic demand")
    print(f"profile={generated.demand_profile}")
    print(f"seed={generated.seed}")
    print(f"route_file={generated.route_path}")
    print(f"metadata={generated.metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
