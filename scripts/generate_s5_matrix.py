from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml

DELAYS = (0, 1, 3, 5)
DROPS = (0.0, 0.05, 0.10, 0.25)
SEED = 42
MAX_MESSAGE_AGE_STEPS = 1
BASE_SCENARIO = Path("scenarios/grid_3x3/scenario_s2_directional_peak.yaml")
BASE_SCENARIO_PROFILE = "S2_DIRECTIONAL_PEAK"
COMMUNICATION_SEED_POLICY = "derived_from_simulation_seed_delay_drop"
B2_REFERENCE_CONTROLLER = "B2_LOCAL_PRESSURE"
COOPERATIVE_CONFIGS = (
    ("c1", "C1_COOPERATIVE_COMPACT"),
    ("c2", "C2_COOPERATIVE_EXPANDED"),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic S5 communication degradation configs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/configs"),
    )
    parser.add_argument(
        "--base-scenario",
        type=Path,
        default=BASE_SCENARIO,
    )
    args = parser.parse_args()

    written = generate_s5_configs(
        output_dir=args.output_dir,
        base_scenario=args.base_scenario,
    )
    for path in written:
        print(path)
    return 0


def generate_s5_configs(*, output_dir: Path, base_scenario: Path) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for controller_key, controller_id in COOPERATIVE_CONFIGS:
        output_path = output_dir / f"s5_communication_degradation_{controller_key}.yaml"
        payload = build_s5_payload(
            controller_key=controller_key,
            controller_id=controller_id,
            base_scenario=base_scenario,
            output_path=output_path,
        )
        output_path.write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )
        written.append(output_path)
    return tuple(written)


def build_s5_payload(
    *,
    controller_key: str,
    controller_id: str,
    base_scenario: Path,
    output_path: Path,
) -> dict[str, Any]:
    scenario = _relative_path(from_dir=output_path.parent, to_path=base_scenario)
    return {
        "experiment_id": f"s5_communication_degradation_{controller_key}",
        "description": (
            "S5 communication degradation matrix. Fixed S2 demand; "
            f"{controller_id} varies delay/drop and B2_LOCAL_PRESSURE is the "
            "local reference."
        ),
        "scenario": scenario,
        "controllers": [
            B2_REFERENCE_CONTROLLER,
            controller_id,
        ],
        "seeds": [SEED],
        "matrix": {
            "delay_steps": list(DELAYS),
            "drop_probability": list(DROPS),
        },
        "runs": [
            _reference_run(scenario=scenario),
            *[
                _cooperative_run(
                    controller_key=controller_key,
                    controller_id=controller_id,
                    scenario=scenario,
                    delay_steps=delay_steps,
                    drop_probability=drop_probability,
                )
                for delay_steps in DELAYS
                for drop_probability in DROPS
            ],
        ],
    }


def _reference_run(*, scenario: str) -> dict[str, Any]:
    return {
        "run_id": "s5_b2_reference",
        "scenario_base": BASE_SCENARIO_PROFILE,
        "scenario": scenario,
        "controller_id": B2_REFERENCE_CONTROLLER,
        "seed": SEED,
        "communication_seed_policy": COMMUNICATION_SEED_POLICY,
        "communication": _communication(
            delay_steps=0,
            drop_probability=0.0,
        ),
    }


def _cooperative_run(
    *,
    controller_key: str,
    controller_id: str,
    scenario: str,
    delay_steps: int,
    drop_probability: float,
) -> dict[str, Any]:
    return {
        "run_id": (f"s5_{controller_key}_delay{delay_steps}_drop{_drop_label(drop_probability)}"),
        "scenario_base": BASE_SCENARIO_PROFILE,
        "scenario": scenario,
        "controller_id": controller_id,
        "seed": SEED,
        "communication_seed_policy": COMMUNICATION_SEED_POLICY,
        "communication": _communication(
            delay_steps=delay_steps,
            drop_probability=drop_probability,
        ),
    }


def _communication(*, delay_steps: int, drop_probability: float) -> dict[str, Any]:
    return {
        "delay_steps": delay_steps,
        "drop_probability": drop_probability,
        "rng_seed": None,
        "max_message_age_steps": MAX_MESSAGE_AGE_STEPS,
    }


def _drop_label(drop_probability: float) -> str:
    if drop_probability == 0.0:
        return "0"
    return f"{round(drop_probability * 100):03d}"


def _relative_path(*, from_dir: Path, to_path: Path) -> str:
    return Path(os.path.relpath(to_path, from_dir)).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
