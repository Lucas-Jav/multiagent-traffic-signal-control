"""Generate the V1 scenario YAMLs (S1-S4) and their seeded route artifacts.

The scenario definitions live here so the repository artifacts are reproducible:

    uv run python scripts/generate_scenarios.py

For every scenario and every seed of the fixed V1 seed pool this writes
``scenario_<profile>_seed_<seed>.yaml``, ``routes_<sN>_seed_<seed>.rou.xml`` and the route
metadata; the seed-42 scenario is also written as the scenario's base file
(``scenario.yaml`` for S1).

All scenarios share the timing of the approved protocol: 300 s warmup, 3600 s measurement,
1 s steps (total 3900 s). S3 places its shock at 50% of the MEASUREMENT window
(300 + 3600 / 2 = 2100 s of simulation time).

Demand intensities are the ``CALIBRATED`` parameters below (Prompt 46.7). They were selected
with ``scripts/calibrate_scenarios.py`` using only ``B0_FIXED`` and dedicated calibration seeds,
by predeclared controller-independent criteria (see the calibration artifacts). They must not
be tuned from controller results.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from traffic_agents.config import ScenarioConfig
from traffic_agents.simulation import TrafficDemandGenerator

SEEDS: tuple[int, ...] = (42, 2027, 3253, 4517, 5791)
WARMUP_SECONDS = 300
MEASUREMENT_SECONDS = 3600
TOTAL_SECONDS = WARMUP_SECONDS + MEASUREMENT_SECONDS
SHOCK_START_SECONDS = WARMUP_SECONDS + MEASUREMENT_SECONDS // 2
STEP_LENGTH = 1.0
SCENARIO_DIR = Path("scenarios/grid_3x3")

WEST_ENTRIES = ("left0A0", "left1A1", "left2A2")
EAST_ENTRIES = ("right0C0", "right1C1", "right2C2")
NORTH_ENTRIES = ("top0A2", "top1B2", "top2C2")
SOUTH_ENTRIES = ("bottom0A0", "bottom1B0", "bottom2C0")
ALL_ENTRIES = WEST_ENTRIES + EAST_ENTRIES + NORTH_ENTRIES + SOUTH_ENTRIES
CENTRAL_ENTRIES = ("left1A1", "right1C1", "top1B2", "bottom1B0")

PROTOCOL_TURNING = {"straight": 0.70, "left": 0.15, "right": 0.15}
STRAIGHT_BIASED_TURNING = {"straight": 0.90, "left": 0.05, "right": 0.05}

Rates = dict[str, float]


@dataclass(frozen=True)
class DemandParameters:
    """The only calibrated degrees of freedom: border entry rates (veh/h, MEDIUM level)."""

    s1_rate: float  # every one of the 12 borders
    s2_dominant_rate: float  # each west border; every other border gets dominant / 12
    s3_shock_rate: float  # each west border, added on top of the S1 base rate
    s4_scale: float  # multiplies S4 background (40) and hotspot (110) veh/h per border


S4_BACKGROUND_RATE = 40.0
S4_HOTSPOT_RATE = 110.0
S2_RESIDUAL_DIVISOR = 12.0  # offered dominant share = 3d / (3d + 9d/12) = 0.80

# Calibrated levels (Prompt 46.7, artifacts/calibration/pilot_v2-scenario-calibration): highest
# grid candidate satisfying every predeclared, controller-independent criterion on all three
# calibration seeds (101, 1009, 2029), observed with B0_FIXED only.
CALIBRATED = DemandParameters(
    s1_rate=150.0, s2_dominant_rate=320.0, s3_shock_rate=150.0, s4_scale=2.0
)


def _level_rates(medium: float) -> Rates:
    return {"LOW": round(medium * 2 / 3, 3), "MEDIUM": medium, "HIGH": round(medium * 4 / 3, 3)}


def _entry(
    demand_id: str,
    edge: str,
    rates: Rates,
    *,
    begin: float = 0,
    end: float = TOTAL_SECONDS,
    group: str = "base",
    turning: dict[str, float] | None = None,
    via: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "demand_id": demand_id,
        "entry_edge_id": edge,
        "group": group,
        "begin_seconds": begin,
        "end_seconds": end,
        "vehicles_per_hour": rates,
    }
    if turning is not None:
        payload["turning_ratios"] = dict(turning)
    if via is not None:
        payload["via_intersection_id"] = via
    return payload


@dataclass(frozen=True)
class ScenarioDefinition:
    profile: str
    short: str
    file_stem: str
    base_file: str
    description: str
    entries: Callable[[DemandParameters], list[dict[str, Any]]]
    schedule: Callable[[], list[dict[str, Any]]]
    shock_start_seconds: float | None = None


def s1_entries(params: DemandParameters) -> list[dict[str, Any]]:
    # Balanced demand from ALL 12 borders, identical rate at every entry.
    return [_entry(f"base_{edge}", edge, _level_rates(params.s1_rate)) for edge in ALL_ENTRIES]


def s2_entries(params: DemandParameters) -> list[dict[str, Any]]:
    # West -> East directional peak: the three west border entries inject 80% of the offered
    # demand (3d of 3d + 9d/12); the other nine borders inject a residual 20%.
    dominant = _level_rates(params.s2_dominant_rate)
    residual = _level_rates(params.s2_dominant_rate / S2_RESIDUAL_DIVISOR)
    entries = [
        _entry(f"dominant_{edge}", edge, dominant, group="dominant") for edge in WEST_ENTRIES
    ]
    entries += [
        _entry(f"residual_{edge}", edge, residual, group="residual")
        for edge in ALL_ENTRIES
        if edge not in WEST_ENTRIES
    ]
    return entries


def s3_entries(params: DemandParameters) -> list[dict[str, Any]]:
    # First half: S1-like balanced traffic. Second half: the S1 base continues and an abrupt
    # one-border (west) directional shock is added on the three west entries; shock vehicles
    # are routed through A5.
    entries = [_entry(f"base_{edge}", edge, _level_rates(params.s1_rate)) for edge in ALL_ENTRIES]
    entries += [
        _entry(
            f"shock_{edge}",
            edge,
            _level_rates(params.s3_shock_rate),
            begin=SHOCK_START_SECONDS,
            end=TOTAL_SECONDS,
            group="shock",
            turning=STRAIGHT_BIASED_TURNING,
            via="A5",
        )
        for edge in WEST_ENTRIES
    ]
    return entries


def s4_entries(params: DemandParameters) -> list[dict[str, Any]]:
    # Localized saturation: light S1-like background from every border plus hotspot demand from
    # every border that is routed through the central intersection A5.
    background = _level_rates(S4_BACKGROUND_RATE * params.s4_scale)
    hotspot = _level_rates(S4_HOTSPOT_RATE * params.s4_scale)
    entries = [_entry(f"base_{edge}", edge, background) for edge in ALL_ENTRIES]
    entries += [
        _entry(
            f"hotspot_{edge}",
            edge,
            hotspot,
            group="hotspot",
            turning=STRAIGHT_BIASED_TURNING,
            via="A5",
        )
        for edge in ALL_ENTRIES
    ]
    return entries


def _full_run_schedule(description: str) -> Callable[[], list[dict[str, Any]]]:
    def build() -> list[dict[str, Any]]:
        return [
            {
                "window_id": "full_run",
                "begin_seconds": 0,
                "end_seconds": TOTAL_SECONDS,
                "description": description,
            }
        ]

    return build


def s3_schedule() -> list[dict[str, Any]]:
    return [
        {
            "window_id": "balanced_base",
            "begin_seconds": 0,
            "end_seconds": SHOCK_START_SECONDS,
            "description": (
                "S1-like stable balanced traffic (warmup plus first half of the measurement "
                "window)."
            ),
        },
        {
            "window_id": "west_shock",
            "begin_seconds": SHOCK_START_SECONDS,
            "end_seconds": TOTAL_SECONDS,
            "description": (
                "Balanced base continues; an abrupt west-border shock routed through A5 is added."
            ),
        },
    ]


SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        profile="S1_BALANCED",
        short="s1",
        file_stem="scenario_s1_balanced",
        base_file="scenario.yaml",
        description="Stationary balanced demand from all borders.",
        entries=s1_entries,
        schedule=_full_run_schedule("Stationary balanced demand across the full simulation."),
    ),
    ScenarioDefinition(
        profile="S2_DIRECTIONAL_PEAK",
        short="s2",
        file_stem="scenario_s2_directional_peak",
        base_file="scenario_s2_directional_peak.yaml",
        description="West to East directional peak (80% dominant offered demand).",
        entries=s2_entries,
        schedule=_full_run_schedule("West-border dominant demand with residual demand elsewhere."),
    ),
    ScenarioDefinition(
        profile="S3_DEMAND_SHIFT",
        short="s3",
        file_stem="scenario_s3_demand_shift",
        base_file="scenario_s3_demand_shift.yaml",
        description=(
            "Balanced first half, abrupt one-border shock through A5 at 50% of measurement."
        ),
        entries=s3_entries,
        schedule=s3_schedule,
        shock_start_seconds=SHOCK_START_SECONDS,
    ),
    ScenarioDefinition(
        profile="S4_LOCAL_SATURATION",
        short="s4",
        file_stem="scenario_s4_local_saturation",
        base_file="scenario_s4_local_saturation.yaml",
        description="Hotspot demand converging through the central intersection A5.",
        entries=s4_entries,
        schedule=_full_run_schedule("Background demand plus hotspot demand routed through A5."),
    ),
)


def build_scenario_payload(
    definition: ScenarioDefinition,
    seed: int,
    template: dict[str, Any],
    params: DemandParameters = CALIBRATED,
) -> dict[str, Any]:
    traffic: dict[str, Any] = {
        "demand_profile": definition.profile,
        "demand_level": "MEDIUM",
        "turning_ratios": dict(PROTOCOL_TURNING),
        "schedule": definition.schedule(),
    }
    if definition.shock_start_seconds is not None:
        traffic["shock_start_seconds"] = definition.shock_start_seconds
    traffic["entries"] = definition.entries(params)
    return {
        "scenario_id": template["scenario_id"],
        "network_file": template["network_file"],
        "route_file": f"routes_{definition.short}_seed_{seed}.rou.xml",
        "simulation": {
            "warmup_seconds": WARMUP_SECONDS,
            "measurement_duration_seconds": MEASUREMENT_SECONDS,
            "step_length": STEP_LENGTH,
            "seed": seed,
        },
        "controller_id": "B0_FIXED",
        "traffic": traffic,
        "communication": template["communication"],
        "intersections": template["intersections"],
    }


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    text = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, width=100)
    path.write_text(text, encoding="utf-8", newline="\n")


def generate(
    scenario_dir: Path,
    *,
    seeds: tuple[int, ...],
    params: DemandParameters = CALIBRATED,
    definitions: tuple[ScenarioDefinition, ...] | None = None,
    write_base_files: bool = True,
) -> list[Path]:
    template_path = scenario_dir / "scenario.yaml"
    template = yaml.safe_load(template_path.read_text(encoding="utf-8-sig"))
    written: list[Path] = []
    for definition in definitions or SCENARIOS:
        for seed in seeds:
            payload = build_scenario_payload(definition, seed, template, params)
            scenario_path = scenario_dir / f"{definition.file_stem}_seed_{seed}.yaml"
            write_yaml(scenario_path, payload)
            written.append(scenario_path)
            scenario_config = ScenarioConfig.model_validate(payload)
            generated = TrafficDemandGenerator(
                scenario_config=scenario_config,
                scenario_dir=scenario_dir,
                seed=seed,
                demand_profile=scenario_config.traffic.demand_profile,
            ).generate()
            written.extend([generated.route_path, generated.metadata_path])
            if write_base_files and seed == seeds[0]:
                base_path = scenario_dir / definition.base_file
                write_yaml(base_path, payload)
                written.append(base_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--scenario-dir", type=Path, default=SCENARIO_DIR)
    parser.add_argument("--seed", type=int, action="append", dest="seeds")
    args = parser.parse_args(argv)
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    written = generate(args.scenario_dir, seeds=seeds)
    for path in written:
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
