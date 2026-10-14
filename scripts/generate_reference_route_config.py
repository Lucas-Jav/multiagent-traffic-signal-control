"""Generate the 20-run ``B0_FIXED_CALIBRATED`` config of the reference-route experiment.

    uv run python scripts/generate_reference_route_config.py

The runs reuse exactly the scenario/seed pairs and the communication block of Pilot V2
(``experiments/configs/pilot_v2.yaml``); only the controller changes. B1/B2/C1/C2 are not run:
their Pilot V2 data is reused by the analysis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SOURCE = Path("experiments/configs/pilot_v2.yaml")
OUTPUT = Path("experiments/configs/refroute_b0.yaml")
HISTORICAL_CONTROLLER = "B0_FIXED"
CALIBRATED_CONTROLLER = "B0_FIXED_CALIBRATED"
CAMPAIGN_ROLE = "REFERENCE_ROUTE_B0_CALIBRATED"
# Short id on purpose: Windows limits paths to 260 characters and the run directory names are long.
EXPERIMENT_ID = "refroute_b0"


def build_config(source: dict) -> dict:  # type: ignore[type-arg]
    runs = []
    for run in source["runs"]:
        if run["controller_id"] != HISTORICAL_CONTROLLER:
            continue
        converted = dict(run)
        converted["run_id"] = (
            run["run_id"]
            .replace("pilot_v2_", "rr_", 1)
            .replace("_b0_fixed", "_b0_fixed_calibrated")
        )
        converted["controller_id"] = CALIBRATED_CONTROLLER
        runs.append(converted)
    return {
        "experiment_id": EXPERIMENT_ID,
        "description": (
            f"campaign_role: {CAMPAIGN_ROLE}. Reference-route experiment: the B0_FIXED_CALIBRATED "
            "runs paired with the existing Pilot V2 B2/C1 runs (same scenarios, seeds, routes). "
            "Pre-final evidence; not a final campaign."
        ),
        "campaign_role": CAMPAIGN_ROLE,
        "controllers": [CALIBRATED_CONTROLLER],
        "seeds": source["seeds"],
        "runs": runs,
    }


def main() -> int:
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    config = build_config(source)
    OUTPUT.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(f"{OUTPUT}: {len(config['runs'])} runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
