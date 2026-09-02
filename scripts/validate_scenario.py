from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import ValidationError

from traffic_agents.config import validate_scenario_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a versioned scenario configuration.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        scenario = validate_scenario_config(args.path)
    except (OSError, ValueError, ValidationError) as error:
        print(f"Invalid scenario config: {error}")
        return 1

    print(f"Valid scenario config: {scenario.scenario_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
