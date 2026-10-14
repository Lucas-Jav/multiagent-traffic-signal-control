"""Final scientific campaign freeze (Prompt 59).

Single source of truth for the immutable specification of the FINAL TCC campaign: seeds,
controllers, the main (200 runs) and S5 (90 runs) matrices, the primary/secondary comparisons and
the statistical plan. The two canonical configs under ``experiments/configs`` are GENERATED from
this module and checked against it, so a hand edit of a frozen config is detected.

Nothing here runs a simulation. After the freeze, none of the values below may change; a
correctness defect requires a NEW freeze (see ``docs/methodology/final-campaign-freeze.md``).
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from traffic_agents.communication import grid_3x3_communication_topology
from traffic_agents.config import ScenarioConfig, load_scenario_config
from traffic_agents.controllers import build_controller
from traffic_agents.experiments import reference_route as rr
from traffic_agents.experiments.metric_definitions import (
    COMPANION_METRICS,
    CORRIDOR_DEFINITION,
    CORRIDOR_DEFINITION_VERSION,
    METRIC_DEFINITION_ALIASES,
    METRIC_DEFINITIONS,
    SCENARIO_METRICS,
)
from traffic_agents.experiments.route_artifacts import validate_route_artifacts
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    json_sha256,
    movement_model_sha256,
    phase_plan_sha256,
    route_generator_config_sha256,
    scenario_config_sha256,
    scenario_turning_config_sha256,
)
from traffic_agents.experiments.runner import ExperimentConfig, load_experiment_config
from traffic_agents.simulation.sumo_environment import detect_sumo_environment
from traffic_agents.traffic_model import load_grid_traffic_models

FREEZE_SCHEMA_VERSION = 1
CAMPAIGN_ROLE = "FINAL_SCIENTIFIC"

# --- Seeds --------------------------------------------------------------------------------------
PILOT_V2_SEEDS: tuple[int, ...] = (42, 2027, 3253, 4517, 5791)
EXTENSION_SEEDS: tuple[int, ...] = (6841, 8089, 10007, 12011, 16001)
FINAL_SEEDS: tuple[int, ...] = PILOT_V2_SEEDS + EXTENSION_SEEDS
SEED_PROVENANCE = (
    "First five seeds are the Pilot V2 seeds; the next five are a pre-reserved extension pool. "
    "No seed was selected according to controller performance."
)

# --- Controllers --------------------------------------------------------------------------------
B0_FINAL = "B0_FIXED_CALIBRATED"
FINAL_CONTROLLERS: tuple[str, ...] = (
    B0_FINAL,
    "B1_LOCAL_ADAPTIVE",
    "B2_LOCAL_PRESSURE",
    "C1_COOPERATIVE_COMPACT",
    "C2_COOPERATIVE_EXPANDED",
)
HISTORICAL_CONTROLLERS: tuple[str, ...] = ("B0_FIXED", "B0_FIXED_STATIC", "B0_FIXED_STATIC_V2")

B0_IDENTITY: dict[str, object] = {
    "controller_id": B0_FINAL,
    "plan_id": "fx_c84_demand_proportional_alternate",
    "cycle_seconds": 84,
    "yellow_seconds": 3,
    "all_red_seconds": 2,
    "split_strategy": "DEMAND_PROPORTIONAL",
    "offset_strategy": "ALTERNATE",
    "offsets_seconds": [0, 42],
}
B0_PLAN_RELATIVE_PATH = Path("experiments/fixed_time/b0_fixed_calibrated.json")
B0_EVIDENCE_RELATIVE_PATH = Path("docs/evidencias/fixed-time-calibration/b0_fixed_calibrated.json")

# --- Scenarios and matrices ---------------------------------------------------------------------
MAIN_SCENARIOS: tuple[str, ...] = (
    "S1_BALANCED",
    "S2_DIRECTIONAL_PEAK",
    "S3_DEMAND_SHIFT",
    "S4_LOCAL_SATURATION",
)
S5_BASE_SCENARIO = "S2_DIRECTIONAL_PEAK"
S5_DELAY_STEPS = 0
S5_DROP_PROBABILITIES: tuple[float, ...] = (0.0, 0.2, 0.5, 1.0)
S5_COOPERATIVE_CONTROLLERS: tuple[str, ...] = ("C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED")
S5_LOCAL_REFERENCE = "B2_LOCAL_PRESSURE"

MAIN_EXPERIMENT_ID = "final_main"
S5_EXPERIMENT_ID = "final_s5_packet_loss"
MAIN_CONFIG_RELATIVE_PATH = Path("experiments/configs/final_main.yaml")
S5_CONFIG_RELATIVE_PATH = Path("experiments/configs/final_s5_packet_loss.yaml")
SCENARIO_DIR_RELATIVE = Path("scenarios/grid_3x3")
COMMUNICATION_SEED_POLICY = "derived_from_simulation_seed_delay_drop"
MAX_MESSAGE_AGE_STEPS = 1

EXPECTED_MAIN_RUNS = 200
EXPECTED_S5_RUNS = 90
EXPECTED_TOTAL_RUNS = 290

# --- Comparisons --------------------------------------------------------------------------------
PRIMARY_COMPARISON: tuple[str, str] = ("B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT")
SECONDARY_COMPARISONS: tuple[tuple[str, str, str], ...] = (
    (
        B0_FINAL,
        "B2_LOCAL_PRESSURE",
        "effect of local pressure adaptation relative to calibrated fixed timing",
    ),
    (B0_FINAL, "B1_LOCAL_ADAPTIVE", "simple local adaptation comparison"),
    (
        "C1_COOPERATIVE_COMPACT",
        "C2_COOPERATIVE_EXPANDED",
        "effect/cost of richer communication",
    ),
)
FINAL_CONTROLLER_PAIRS: tuple[tuple[str, str], ...] = (
    PRIMARY_COMPARISON,
    *((baseline, treatment) for baseline, treatment, _ in SECONDARY_COMPARISONS),
)

# --- Statistics ---------------------------------------------------------------------------------
ANALYSIS_BOOTSTRAP_SEED = 20260910
REFERENCE_ROUTE_BOOTSTRAP_BASE_SEED = rr.BOOTSTRAP_BASE_SEED
BOOTSTRAP_RESAMPLES = 10_000

S4_TELEPORT_POLICY = "ALLOW_AND_MEASURE"
CONDITIONAL_METRICS: tuple[str, ...] = ("mean_waiting_time", "mean_time_loss", "mean_travel_time")
CONDITIONAL_COMPANIONS: tuple[str, ...] = (
    "departure_ratio",
    "completion_ratio_offered",
    "never_inserted_vehicle_count",
    "unfinished_in_network_count",
)

REQUIRED_CANONICAL_METRICS: tuple[str, ...] = (
    "offered_vehicle_count",
    "departed_vehicle_count",
    "arrived_vehicle_count",
    "never_inserted_vehicle_count",
    "unfinished_in_network_count",
    "throughput",
    "departure_ratio",
    "completion_ratio_offered",
    "completion_ratio_departed",
    "mean_depart_delay_seconds",
    "mean_waiting_time",
    "mean_time_loss",
    "mean_travel_time",
    "mean_stops",
    "mean_lane_queue_vehicles",
    "mean_network_queue_vehicles",
    "max_lane_queue_vehicles",
    "max_network_queue_vehicles",
    "internal_lane_persistence_events",
    "post_shock_queue_auc_vehicle_seconds",
    "sumo_teleports_total",
    "messages_sent",
    "messages_delivered",
    "messages_dropped",
    "messages_stale",
    "bytes_sent",
    "bytes_delivered",
    "mean_message_age_steps",
    "max_message_age_steps",
)

GLOSSARY_RELATIVE_PATH = Path("docs/methodology/intersection-glossary.md")
FREEZE_DOCS_DIR = Path("docs/evidencias/final-freeze")
FREEZE_ARTIFACT_RELATIVE_PATH = Path("artifacts/final-freeze/final-freeze-manifest.json")
FREEZE_DOC_RELATIVE_PATH = Path("docs/methodology/final-campaign-freeze.md")
METHODOLOGY_DOCS: tuple[Path, ...] = (
    Path("docs/methodology/scenario-validity-gates.md"),
    Path("docs/methodology/metrics.md"),
    Path("docs/methodology/reference-route.md"),
    GLOSSARY_RELATIVE_PATH,
    Path("docs/methodology/campaign-matrix.md"),
    Path("docs/methodology/experimental-protocol.md"),
    Path("docs/methodology/fixed-time-calibration.md"),
)

# Source files that define scientific behaviour. The replay package (presentation only) and this
# tooling module are tracked separately.
_SOURCE_EXCLUDED_PARTS = frozenset({"replay", "__pycache__"})
_SOURCE_EXCLUDED_FILES = frozenset({"final_freeze.py"})


class FinalFreezeError(ValueError):
    """Raised when the final campaign specification is inconsistent."""


@dataclass(frozen=True)
class FinalRun:
    campaign: str
    run_id: str
    scenario_base: str
    seed: int
    controller_id: str
    delay_steps: int
    drop_probability: float

    @property
    def scenario_relative_path(self) -> str:
        return scenario_file_name(self.scenario_base, self.seed)

    @property
    def identity(self) -> tuple[str, str, int, str, int, float]:
        return (
            self.campaign,
            self.scenario_base,
            self.seed,
            self.controller_id,
            self.delay_steps,
            self.drop_probability,
        )


def scenario_file_name(scenario_base: str, seed: int) -> str:
    return f"scenario_{scenario_base.lower()}_seed_{seed}.yaml"


def main_runs() -> tuple[FinalRun, ...]:
    return tuple(
        FinalRun(
            campaign=MAIN_EXPERIMENT_ID,
            run_id=f"{MAIN_EXPERIMENT_ID}_{scenario.lower()}_seed{seed}_{controller.lower()}",
            scenario_base=scenario,
            seed=seed,
            controller_id=controller,
            delay_steps=0,
            drop_probability=0.0,
        )
        for scenario in MAIN_SCENARIOS
        for seed in FINAL_SEEDS
        for controller in FINAL_CONTROLLERS
    )


def _drop_label(drop_probability: float) -> str:
    return f"drop{round(drop_probability * 100):03d}"


def s5_runs() -> tuple[FinalRun, ...]:
    runs: list[FinalRun] = []
    for seed in FINAL_SEEDS:
        # B2 does not use communication: ONE reference run per seed.
        runs.append(
            FinalRun(
                campaign=S5_EXPERIMENT_ID,
                run_id=f"{S5_EXPERIMENT_ID}_seed{seed}_b2_reference",
                scenario_base=S5_BASE_SCENARIO,
                seed=seed,
                controller_id=S5_LOCAL_REFERENCE,
                delay_steps=S5_DELAY_STEPS,
                drop_probability=0.0,
            )
        )
        for controller in S5_COOPERATIVE_CONTROLLERS:
            for drop in S5_DROP_PROBABILITIES:
                runs.append(
                    FinalRun(
                        campaign=S5_EXPERIMENT_ID,
                        run_id=(
                            f"{S5_EXPERIMENT_ID}_seed{seed}_{controller.split('_')[0].lower()}_"
                            f"{_drop_label(drop)}"
                        ),
                        scenario_base=S5_BASE_SCENARIO,
                        seed=seed,
                        controller_id=controller,
                        delay_steps=S5_DELAY_STEPS,
                        drop_probability=drop,
                    )
                )
    return tuple(runs)


def _run_payload(run: FinalRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "scenario_base": run.scenario_base,
        "scenario": f"../../{SCENARIO_DIR_RELATIVE.as_posix()}/{run.scenario_relative_path}",
        "controller_id": run.controller_id,
        "seed": run.seed,
        "communication_seed_policy": COMMUNICATION_SEED_POLICY,
        "communication": {
            "delay_steps": run.delay_steps,
            "drop_probability": run.drop_probability,
            "rng_seed": None,
            "max_message_age_steps": MAX_MESSAGE_AGE_STEPS,
        },
    }


def main_config_payload() -> dict[str, Any]:
    return {
        "experiment_id": MAIN_EXPERIMENT_ID,
        "description": (
            "campaign_role: FINAL_SCIENTIFIC. FROZEN final main campaign: 4 scenarios x 5 "
            "controllers x 10 seeds = 200 runs. Generated by "
            "scripts/build_final_freeze.py; do not edit by hand."
        ),
        "campaign_role": CAMPAIGN_ROLE,
        "controllers": list(FINAL_CONTROLLERS),
        "seeds": list(FINAL_SEEDS),
        "runs": [_run_payload(run) for run in main_runs()],
    }


def s5_config_payload() -> dict[str, Any]:
    return {
        "experiment_id": S5_EXPERIMENT_ID,
        "description": (
            "campaign_role: FINAL_SCIENTIFIC. FROZEN S5 packet-loss campaign over S2 directional "
            "demand: delay 0, loss 0/20/50/100% for C1 and C2 (80 runs) plus ONE B2 reference "
            "per seed (10 runs) = 90 runs. Generated by scripts/build_final_freeze.py; do not "
            "edit by hand."
        ),
        "campaign_role": CAMPAIGN_ROLE,
        "controllers": [S5_LOCAL_REFERENCE, *S5_COOPERATIVE_CONTROLLERS],
        "seeds": list(FINAL_SEEDS),
        "matrix": {
            "delay_steps": [S5_DELAY_STEPS],
            "drop_probability": list(S5_DROP_PROBABILITIES),
        },
        "runs": [_run_payload(run) for run in s5_runs()],
    }


def render_config_yaml(payload: Mapping[str, Any]) -> str:
    class _NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data: object) -> bool:
            return True

    return yaml.dump(
        dict(payload),
        Dumper=_NoAliasDumper,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )


def write_final_configs(repo_root: Path) -> tuple[Path, Path]:
    main_path = repo_root / MAIN_CONFIG_RELATIVE_PATH
    s5_path = repo_root / S5_CONFIG_RELATIVE_PATH
    main_path.write_text(render_config_yaml(main_config_payload()), encoding="utf-8", newline="\n")
    s5_path.write_text(render_config_yaml(s5_config_payload()), encoding="utf-8", newline="\n")
    return main_path, s5_path


# --- Statistical plan ---------------------------------------------------------------------------
def statistical_plan() -> dict[str, Any]:
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "frozen_before_final_results": True,
        "paired_comparison_unit": "scenario + seed",
        "descriptive_statistics": ["N", "mean", "median", "standard deviation", "IQR"],
        "paired_statistics": [
            "paired mean difference (treatment - baseline)",
            "paired median difference",
            "relative difference (mean difference / baseline mean)",
            "paired bootstrap 95% confidence interval of the mean difference",
        ],
        "bootstrap": {
            "method": "percentile bootstrap resampling the paired differences with replacement",
            "confidence_level": 0.95,
            "resamples": BOOTSTRAP_RESAMPLES,
            "analysis_rng_seed": ANALYSIS_BOOTSTRAP_SEED,
            "analysis_implementation": "analysis/statistics.py (random.Random(seed))",
            "reference_route_rng_base_seed": REFERENCE_ROUTE_BOOTSTRAP_BASE_SEED,
            "reference_route_implementation": (
                "traffic_agents.experiments.reference_route.paired_bootstrap_ci "
                "(numpy default_rng, label-stable seed = (base + crc32(label)) mod 2**32)"
            ),
        },
        "primary_comparison": {
            "baseline": PRIMARY_COMPARISON[0],
            "treatment": PRIMARY_COMPARISON[1],
            "rationale": (
                "B2 and C1 share the local-pressure control family; C1 adds compact information "
                "from neighbouring agents, so B2 vs C1 isolates the effect of cooperation."
            ),
        },
        "secondary_comparisons": [
            {"baseline": baseline, "treatment": treatment, "meaning": meaning}
            for baseline, treatment, meaning in SECONDARY_COMPARISONS
        ],
        "reference_route_comparison_controllers": list(rr.CONTROLLERS),
        "conditional_metric_rule": {
            "conditional_on_completed_trips": list(CONDITIONAL_METRICS),
            "must_be_interpreted_with": list(CONDITIONAL_COMPANIONS),
            "note": "Especially important in S2 and S4, where part of the demand may not complete.",
        },
        "no_new_inferential_methods_after_results": True,
    }


# --- Validation (no simulation) -----------------------------------------------------------------
def _load_config(path: Path) -> ExperimentConfig:
    return load_experiment_config(path)


def _scenario_config_for(run: FinalRun, scenario_dir: Path) -> ScenarioConfig:
    base = load_scenario_config(scenario_dir / run.scenario_relative_path)
    from traffic_agents.config import CommunicationConfig

    return base.model_copy(
        update={
            "controller_id": run.controller_id,
            "simulation": base.simulation.model_copy(update={"seed": run.seed}),
            "communication": CommunicationConfig(
                delay_steps=run.delay_steps,
                drop_probability=run.drop_probability,
                rng_seed=None,
                max_message_age_steps=MAX_MESSAGE_AGE_STEPS,
            ),
        }
    )


def _duplicates(values: Iterable[object]) -> list[object]:
    return [value for value, count in Counter(values).items() if count > 1]


def validate_final_campaign(repo_root: Path) -> dict[str, Any]:
    """Verify the frozen configs against this module without running any simulation."""

    problems: list[str] = []
    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE

    if len(FINAL_SEEDS) != 10 or len(set(FINAL_SEEDS)) != 10:
        problems.append("FINAL_SEEDS must contain exactly 10 distinct seeds")
    for controller_id in FINAL_CONTROLLERS:
        try:
            build_controller(controller_id)
        except Exception as exc:
            problems.append(f"controller {controller_id} does not resolve: {exc}")
    if set(FINAL_CONTROLLERS) & set(HISTORICAL_CONTROLLERS):
        problems.append("historical controllers must not be part of the final controllers")

    expected = {
        MAIN_CONFIG_RELATIVE_PATH: render_config_yaml(main_config_payload()),
        S5_CONFIG_RELATIVE_PATH: render_config_yaml(s5_config_payload()),
    }
    for relative, text in expected.items():
        path = repo_root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            problems.append(f"{relative.as_posix()} differs from the frozen specification")

    configs: dict[str, ExperimentConfig] = {}
    for key, relative in (("main", MAIN_CONFIG_RELATIVE_PATH), ("s5", S5_CONFIG_RELATIVE_PATH)):
        path = repo_root / relative
        if path.exists():
            configs[key] = _load_config(path)

    runs = {"main": main_runs(), "s5": s5_runs()}
    for key, config in configs.items():
        if config.campaign_role != CAMPAIGN_ROLE:
            problems.append(f"{key}: campaign_role must be {CAMPAIGN_ROLE}")
        if tuple(config.seeds) != FINAL_SEEDS:
            problems.append(f"{key}: seeds differ from FINAL_SEEDS")
        loaded_ids = [run.run_id for run in config.runs]
        if loaded_ids != [run.run_id for run in runs[key]]:
            problems.append(f"{key}: run ids differ from the frozen matrix")

    main = runs["main"]
    s5 = runs["s5"]
    duplicate_ids = _duplicates(run.run_id for run in (*main, *s5))
    duplicate_identities = _duplicates(run.identity for run in (*main, *s5))
    if duplicate_ids:
        problems.append(f"duplicate run ids: {duplicate_ids[:3]}")
    if duplicate_identities:
        problems.append(f"duplicate run identities: {duplicate_identities[:3]}")
    if len(main) != EXPECTED_MAIN_RUNS:
        problems.append(f"main has {len(main)} runs, expected {EXPECTED_MAIN_RUNS}")
    if len(s5) != EXPECTED_S5_RUNS:
        problems.append(f"S5 has {len(s5)} runs, expected {EXPECTED_S5_RUNS}")

    b2_s5 = Counter(run.seed for run in s5 if run.controller_id == S5_LOCAL_REFERENCE)
    if set(b2_s5) != set(FINAL_SEEDS) or any(count != 1 for count in b2_s5.values()):
        problems.append("B2 must appear exactly once per seed in S5")
    for controller in S5_COOPERATIVE_CONTROLLERS:
        per = Counter(run.seed for run in s5 if run.controller_id == controller)
        if any(per[seed] != len(S5_DROP_PROBABILITIES) for seed in FINAL_SEEDS):
            problems.append(f"{controller}: expected {len(S5_DROP_PROBABILITIES)} loss levels/seed")
    if any(run.scenario_base != S5_BASE_SCENARIO for run in s5):
        problems.append("S5 must use S2_DIRECTIONAL_PEAK as traffic base")

    scenario_cache: dict[Path, ScenarioConfig] = {}
    for run in (*main, *s5):
        scenario_path = scenario_dir / run.scenario_relative_path
        if not scenario_path.exists():
            problems.append(f"missing scenario file: {scenario_path.name}")
            continue
        if scenario_path not in scenario_cache:
            scenario_cfg = load_scenario_config(scenario_path)
            scenario_cache[scenario_path] = scenario_cfg
            if scenario_cfg.seed != run.seed:
                problems.append(f"{scenario_path.name}: seed {scenario_cfg.seed} != {run.seed}")
            if scenario_cfg.traffic.demand_profile != run.scenario_base:
                problems.append(f"{scenario_path.name}: unexpected demand profile")
            try:
                validate_route_artifacts(scenario_config=scenario_cfg, scenario_dir=scenario_dir)
            except Exception as exc:
                problems.append(f"{scenario_path.name}: route artifacts invalid: {exc}")

    problems.extend(_validate_b0(repo_root))
    problems.extend(_validate_metric_identity())

    report = {
        "seed_count": len(FINAL_SEEDS),
        "main_run_count": len(main),
        "s5_run_count": len(s5),
        "total_run_count": len(main) + len(s5),
        "duplicate_run_ids": len(duplicate_ids),
        "duplicate_run_identities": len(duplicate_identities),
        "b2_s5_runs_per_seed": dict(sorted(b2_s5.items())),
        "problems": problems,
    }
    if problems:
        msg = "final campaign validation failed: " + "; ".join(problems)
        raise FinalFreezeError(msg)
    return report


def _validate_b0(repo_root: Path) -> list[str]:
    problems: list[str] = []
    plan_path = repo_root / B0_PLAN_RELATIVE_PATH
    if not plan_path.exists():
        return [f"B0 plan missing: {B0_PLAN_RELATIVE_PATH.as_posix()}"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for key in ("plan_id", "controller_id", "cycle_seconds", "yellow_seconds", "all_red_seconds"):
        if plan.get(key) != B0_IDENTITY[key]:
            problems.append(f"B0 plan {key}={plan.get(key)!r}, frozen {B0_IDENTITY[key]!r}")
    offsets = sorted({int(t["offset_seconds"]) for t in plan["traffic_lights"].values()})
    if offsets != B0_IDENTITY["offsets_seconds"]:
        problems.append(f"B0 plan offsets {offsets} differ from the frozen alternate 0/42")
    evidence = repo_root / B0_EVIDENCE_RELATIVE_PATH
    if not evidence.exists() or file_sha256(evidence) != file_sha256(plan_path):
        problems.append("B0 plan differs from its calibration evidence copy")
    return problems


def _validate_metric_identity() -> list[str]:
    missing = [
        name
        for name in REQUIRED_CANONICAL_METRICS
        if name not in METRIC_DEFINITIONS and name not in METRIC_DEFINITION_ALIASES
    ]
    return [f"canonical metric not defined: {name}" for name in missing]


# --- Hashes -------------------------------------------------------------------------------------
def metric_definitions_sha256() -> str:
    return json_sha256(
        {
            "definitions": {name: d.as_dict() for name, d in sorted(METRIC_DEFINITIONS.items())},
            "scenario_metrics": {k: list(v) for k, v in sorted(SCENARIO_METRICS.items())},
            "aliases": dict(sorted(METRIC_DEFINITION_ALIASES.items())),
            "companion_metrics": list(COMPANION_METRICS),
            "corridor_definition_version": CORRIDOR_DEFINITION_VERSION,
            "corridor_definition": CORRIDOR_DEFINITION,
            "reference_route_metrics": list(rr.METRICS),
            "reference_route_population_keys": list(rr.POPULATION_KEYS),
            "required_canonical_metrics": list(REQUIRED_CANONICAL_METRICS),
        }
    )


def reference_route_definition() -> dict[str, Any]:
    return {
        "reference_route_id": rr.REFERENCE_ROUTE_ID,
        "edge_sequence": list(rr.REFERENCE_ROUTE_EDGES),
        "logical_path": list(rr.REFERENCE_ROUTE_LOGICAL_PATH),
        "cohort_rule": (
            "offered vehicles whose planned edge sequence EXACTLY equals edge_sequence and whose "
            "scheduled departure is in [warmup, warmup + measurement_duration); never selected "
            "by SUMO route id"
        ),
        "metrics": list(rr.METRICS),
        "primary_metric": rr.PRIMARY_METRIC,
        "completion_metric": rr.COMPLETION_METRIC,
        "population_keys": list(rr.POPULATION_KEYS),
        "controllers": list(rr.CONTROLLERS),
        "comparisons": [list(pair) for pair in rr.COMPARISONS],
        "pairing_fields": list(rr.PAIRING_FIELDS),
        "bootstrap_base_seed": rr.BOOTSTRAP_BASE_SEED,
        "bootstrap_resamples": rr.BOOTSTRAP_RESAMPLES,
    }


def _hash_files(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def scientific_source_sha256(repo_root: Path) -> str:
    """Hash of all scientific source (replay package and this tooling module excluded)."""

    files = [
        path
        for base in (repo_root / "src" / "traffic_agents", repo_root / "analysis")
        for path in base.rglob("*.py")
        if not _SOURCE_EXCLUDED_PARTS.intersection(path.relative_to(base).parts)
        and path.name not in _SOURCE_EXCLUDED_FILES
    ]
    return _hash_files(repo_root, files)


def replay_source_sha256(repo_root: Path) -> str:
    files = list((repo_root / "src" / "traffic_agents" / "replay").rglob("*.py"))
    files += [repo_root / "scripts" / "record_before_after.py"]
    files += sorted((repo_root / "config").glob("demo_*"))
    return _hash_files(repo_root, [path for path in files if "__pycache__" not in path.parts])


SCENARIO_INPUT_COLUMNS: tuple[str, ...] = (
    "scenario_base",
    "seed",
    "scenario_file_sha256",
    "route_file_sha256",
    "route_generator_config_sha256",
    "turning_config_sha256",
    "movement_model_sha256",
    "phase_plan_sha256",
    "scenario_neutral_sha256",
)


def scenario_input_rows(repo_root: Path) -> list[dict[str, object]]:
    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    rows: list[dict[str, object]] = []
    for scenario in MAIN_SCENARIOS:
        for seed in FINAL_SEEDS:
            path = scenario_dir / scenario_file_name(scenario, seed)
            config = load_scenario_config(path)
            models = load_grid_traffic_models(scenario_config=config, scenario_dir=scenario_dir)
            neutral = config.model_copy(update={"controller_id": "NEUTRAL"})
            rows.append(
                {
                    "scenario_base": scenario,
                    "seed": seed,
                    "scenario_file_sha256": file_sha256(path),
                    "route_file_sha256": file_sha256(scenario_dir / config.route_file),
                    "route_generator_config_sha256": route_generator_config_sha256(config),
                    "turning_config_sha256": scenario_turning_config_sha256(config),
                    "movement_model_sha256": movement_model_sha256(models),
                    "phase_plan_sha256": phase_plan_sha256(models),
                    "scenario_neutral_sha256": scenario_config_sha256(neutral),
                }
            )
    return rows


RUN_MATRIX_COLUMNS: tuple[str, ...] = (
    "campaign",
    "run_id",
    "scenario_base",
    "seed",
    "controller_id",
    "delay_steps",
    "drop_probability",
    "scenario_neutral_sha256",
    "route_file_sha256",
)


def run_matrix_rows(repo_root: Path) -> list[dict[str, object]]:
    """One row per final run; ``scenario_neutral_sha256`` ignores the controller id."""

    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    rows: list[dict[str, object]] = []
    for run in (*main_runs(), *s5_runs()):
        config = _scenario_config_for(run, scenario_dir)
        neutral = config.model_copy(update={"controller_id": "NEUTRAL"})
        rows.append(
            {
                "campaign": run.campaign,
                "run_id": run.run_id,
                "scenario_base": run.scenario_base,
                "seed": run.seed,
                "controller_id": run.controller_id,
                "delay_steps": run.delay_steps,
                "drop_probability": run.drop_probability,
                "scenario_neutral_sha256": scenario_config_sha256(neutral),
                "route_file_sha256": file_sha256(scenario_dir / config.route_file),
            }
        )
    return rows


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# --- Environment / git --------------------------------------------------------------------------
def _git(repo_root: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _uv_version() -> str | None:
    try:
        completed = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return None
    return completed.stdout.strip() or None


def environment_record(repo_root: Path) -> dict[str, Any]:
    sumo = detect_sumo_environment()
    status = _git(repo_root, "status", "--porcelain")
    return {
        "git_sha": _git(repo_root, "rev-parse", "HEAD"),
        "git_working_tree_dirty": bool(status),
        "python_version": platform.python_version(),
        "sumo_version": sumo.version,
        "traci_version": _package_version("traci"),
        "sumolib_version": _package_version("sumolib"),
        "uv_version": _uv_version(),
        "uv_lock_sha256": file_sha256(repo_root / "uv.lock"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": {
            name: _package_version(name)
            for name in (
                "numpy",
                "pydantic",
                "pydantic-settings",
                "pyarrow",
                "pyyaml",
                "matplotlib",
            )
        },
        "replay_only_packages": {
            name: _package_version(name) for name in ("pillow", "imageio-ffmpeg")
        },
    }


# --- Manifest -----------------------------------------------------------------------------------
def build_freeze_manifest(repo_root: Path, *, generated_at: str) -> dict[str, Any]:
    """Assemble the freeze manifest. Requires a valid campaign (see ``validate_final_campaign``)."""

    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    plan_path = repo_root / B0_PLAN_RELATIVE_PATH
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    from traffic_agents.controllers.fixed_time_plan import load_plan

    scenario_rows = scenario_input_rows(repo_root)
    matrix_rows = run_matrix_rows(repo_root)
    reference = reference_route_definition()
    plan = statistical_plan()
    first_config = load_scenario_config(scenario_dir / scenario_file_name(MAIN_SCENARIOS[0], 42))
    network_sha = file_sha256(scenario_dir / first_config.network_file)
    network_hashes = {
        file_sha256(scenario_dir / load_scenario_config(scenario_dir / row_path).network_file)
        for row_path in (
            scenario_file_name(s, seed) for s in MAIN_SCENARIOS for seed in FINAL_SEEDS
        )
    }
    if network_hashes != {network_sha}:
        msg = "all scenarios must share one network file"
        raise FinalFreezeError(msg)

    def digest(column: str) -> str:
        return json_sha256([row[column] for row in scenario_rows])

    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "freeze_name": "FINAL_SCIENTIFIC_CAMPAIGN_FREEZE",
        "generated_at": generated_at,
        "campaign_role": CAMPAIGN_ROLE,
        "environment": environment_record(repo_root),
        "scientific_source_sha256": scientific_source_sha256(repo_root),
        "replay": {
            "implemented_at_freeze": True,
            "replay_source_sha256": replay_source_sha256(repo_root),
            "note": (
                "The synchronized before/after replay system exists at the frozen implementation. "
                "Replay outputs are illustrative and are NOT part of the 290 scientific runs."
            ),
        },
        "seeds": {
            "final": list(FINAL_SEEDS),
            "count": len(FINAL_SEEDS),
            "pilot_v2": list(PILOT_V2_SEEDS),
            "extension_pool": list(EXTENSION_SEEDS),
            "provenance": SEED_PROVENANCE,
        },
        "controllers": {
            "final": list(FINAL_CONTROLLERS),
            "historical_not_final": list(HISTORICAL_CONTROLLERS),
            "b0_final": B0_FINAL,
        },
        "scenarios": list(MAIN_SCENARIOS),
        "b0_identity": B0_IDENTITY
        | {
            "plan_file": B0_PLAN_RELATIVE_PATH.as_posix(),
            "plan_file_sha256": file_sha256(plan_path),
            "plan_canonical_sha256": load_plan(plan_path).sha256(),
            "provenance": plan_payload["provenance"],
        },
        "main_matrix": {
            "experiment_id": MAIN_EXPERIMENT_ID,
            "config": MAIN_CONFIG_RELATIVE_PATH.as_posix(),
            "config_sha256": file_sha256(repo_root / MAIN_CONFIG_RELATIVE_PATH),
            "scenarios": list(MAIN_SCENARIOS),
            "controllers": list(FINAL_CONTROLLERS),
            "seeds": list(FINAL_SEEDS),
            "expected_runs": EXPECTED_MAIN_RUNS,
        },
        "s5_matrix": {
            "experiment_id": S5_EXPERIMENT_ID,
            "config": S5_CONFIG_RELATIVE_PATH.as_posix(),
            "config_sha256": file_sha256(repo_root / S5_CONFIG_RELATIVE_PATH),
            "traffic_base": S5_BASE_SCENARIO,
            "note": "S5 is a communication experiment, not a new traffic-demand pattern.",
            "delay_steps": [S5_DELAY_STEPS],
            "drop_probability": list(S5_DROP_PROBABILITIES),
            "cooperative_controllers": list(S5_COOPERATIVE_CONTROLLERS),
            "local_reference": S5_LOCAL_REFERENCE,
            "local_reference_runs_per_seed": 1,
            "expected_runs": EXPECTED_S5_RUNS,
        },
        "expected_run_counts": {
            "main": EXPECTED_MAIN_RUNS,
            "s5": EXPECTED_S5_RUNS,
            "total": EXPECTED_TOTAL_RUNS,
            "excluded": [
                "Pilot V2",
                "calibration",
                "calibration validation",
                "reference-route pre-final runs",
                "smokes",
                "visual replay",
            ],
        },
        "reference_route": reference | {"definition_sha256": json_sha256(reference)},
        "intersection_terminology": {
            "academic_ids": [f"A{i}" for i in range(1, 10)],
            "sumo_ids_are_implementation_only": True,
            "glossary": GLOSSARY_RELATIVE_PATH.as_posix(),
            "glossary_sha256": file_sha256(repo_root / GLOSSARY_RELATIVE_PATH),
        },
        "scenario_freeze": {
            "warmup_seconds": float(first_config.warmup_seconds),
            "measurement_duration_seconds": float(first_config.measurement_duration_seconds),
            "step_length": float(first_config.step_length),
            "s3_shock_start_seconds": load_scenario_config(
                scenario_dir / scenario_file_name("S3_DEMAND_SHIFT", 42)
            ).traffic.shock_start_seconds,
            "s3_post_shock_metric": "post_shock_queue_auc_vehicle_seconds",
            "s3_gate_note": (
                "The revised composite S3 validity gate was formalized after Pilot V2 diagnostic "
                "inspection and is therefore a post-hoc methodological refinement. No further S3 "
                "gate changes after freeze."
            ),
            "s4_teleport_policy": S4_TELEPORT_POLICY,
            "s4_teleport_note": (
                "sumo_teleports_total is always preserved; a teleport does not by itself "
                "invalidate a run."
            ),
            "s5_traffic_base": S5_BASE_SCENARIO,
            "validity_gates_doc_sha256": file_sha256(
                repo_root / "docs/methodology/scenario-validity-gates.md"
            ),
        },
        "canonical_metrics": {
            "definitions_sha256": metric_definitions_sha256(),
            "required": list(REQUIRED_CANONICAL_METRICS),
            "metrics_doc_sha256": file_sha256(repo_root / "docs/methodology/metrics.md"),
        },
        "statistical_plan": plan | {"plan_sha256": json_sha256(plan)},
        "scientific_input_hashes": {
            "network_sha256": network_sha,
            "scenario_configs_digest": digest("scenario_file_sha256"),
            "route_files_digest": digest("route_file_sha256"),
            "route_generation_configs_digest": digest("route_generator_config_sha256"),
            "turning_config_digest": digest("turning_config_sha256"),
            "movement_definitions_digest": digest("movement_model_sha256"),
            "phase_topology_digest": digest("phase_plan_sha256"),
            "scenario_neutral_digest": digest("scenario_neutral_sha256"),
            "controller_configs": {
                controller: json_sha256(build_controller(controller).manifest_metadata())
                for controller in FINAL_CONTROLLERS
            },
            "b0_plan_sha256": file_sha256(plan_path),
            "communication_topology_sha256": grid_3x3_communication_topology().topology_hash,
            "metric_definitions_sha256": metric_definitions_sha256(),
            "seed_list_sha256": json_sha256(list(FINAL_SEEDS)),
            "reference_route_definition_sha256": json_sha256(reference),
            "main_campaign_config_sha256": file_sha256(repo_root / MAIN_CONFIG_RELATIVE_PATH),
            "s5_campaign_config_sha256": file_sha256(repo_root / S5_CONFIG_RELATIVE_PATH),
            "statistical_plan_sha256": json_sha256(plan),
            "run_matrix_sha256": json_sha256(matrix_rows),
            "fairness_rule": (
                "Cross-controller fairness uses the controller-neutral scenario hash "
                "(scenario_neutral_sha256), never the controller-dependent scenario_sha256."
            ),
        },
        "change_policy": {
            "immutable_after_freeze": [
                "controllers",
                "controller parameters",
                "B0 plan",
                "scenario demand",
                "routes",
                "seeds",
                "phase topology",
                "packet-loss levels",
                "warmup",
                "measurement duration",
                "shock time",
                "metric definitions",
                "reference route",
                "statistical plan",
            ],
            "on_correctness_defect": [
                "STOP campaign",
                "document defect",
                "fix defect",
                "commit",
                "create NEW freeze",
                "rerun affected final evidence",
            ],
        },
    }


def write_freeze_evidence(repo_root: Path, manifest: Mapping[str, Any]) -> list[Path]:
    """Write the manifest (artifacts + versioned copy) and the lightweight evidence tables."""

    written: list[Path] = []
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    for relative in (FREEZE_ARTIFACT_RELATIVE_PATH, FREEZE_DOCS_DIR / "final-freeze-manifest.json"):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    docs = repo_root / FREEZE_DOCS_DIR
    write_csv(docs / "run-matrix.csv", RUN_MATRIX_COLUMNS, run_matrix_rows(repo_root))
    write_csv(docs / "scenario-inputs.csv", SCENARIO_INPUT_COLUMNS, scenario_input_rows(repo_root))
    plan_path = docs / "statistical-plan.json"
    plan_path.write_text(
        json.dumps(statistical_plan(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    written.extend([docs / "run-matrix.csv", docs / "scenario-inputs.csv", plan_path])
    return written


def verify_freeze_manifest(repo_root: Path, manifest_path: Path | None = None) -> list[str]:
    """Recompute hashes and compare them with the manifest. Returns the list of mismatches."""

    path = manifest_path or repo_root / FREEZE_DOCS_DIR / "final-freeze-manifest.json"
    recorded = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    def check(label: str, recorded_value: object, actual: object) -> None:
        if recorded_value != actual:
            problems.append(f"{label}: manifest={recorded_value!r} actual={actual!r}")

    check(
        "scientific_source_sha256",
        recorded["scientific_source_sha256"],
        scientific_source_sha256(repo_root),
    )
    hashes = recorded["scientific_input_hashes"]
    plan_path = repo_root / B0_PLAN_RELATIVE_PATH
    check("b0_plan_sha256", hashes["b0_plan_sha256"], file_sha256(plan_path))
    check(
        "main_campaign_config_sha256",
        hashes["main_campaign_config_sha256"],
        file_sha256(repo_root / MAIN_CONFIG_RELATIVE_PATH),
    )
    check(
        "s5_campaign_config_sha256",
        hashes["s5_campaign_config_sha256"],
        file_sha256(repo_root / S5_CONFIG_RELATIVE_PATH),
    )
    check(
        "metric_definitions_sha256",
        hashes["metric_definitions_sha256"],
        metric_definitions_sha256(),
    )
    check("seed_list_sha256", hashes["seed_list_sha256"], json_sha256(list(FINAL_SEEDS)))
    check("run_matrix_sha256", hashes["run_matrix_sha256"], json_sha256(run_matrix_rows(repo_root)))
    check(
        "statistical_plan_sha256",
        hashes["statistical_plan_sha256"],
        json_sha256(statistical_plan()),
    )
    check(
        "reference_route_definition_sha256",
        hashes["reference_route_definition_sha256"],
        json_sha256(reference_route_definition()),
    )
    rows = scenario_input_rows(repo_root)
    for key, column in (
        ("scenario_configs_digest", "scenario_file_sha256"),
        ("route_files_digest", "route_file_sha256"),
        ("route_generation_configs_digest", "route_generator_config_sha256"),
        ("turning_config_digest", "turning_config_sha256"),
        ("movement_definitions_digest", "movement_model_sha256"),
        ("phase_topology_digest", "phase_plan_sha256"),
        ("scenario_neutral_digest", "scenario_neutral_sha256"),
    ):
        check(key, hashes[key], json_sha256([row[column] for row in rows]))
    for controller, recorded_hash in hashes["controller_configs"].items():
        check(
            f"controller_config[{controller}]",
            recorded_hash,
            json_sha256(build_controller(controller).manifest_metadata()),
        )
    check(
        "communication_topology_sha256",
        hashes["communication_topology_sha256"],
        grid_3x3_communication_topology().topology_hash,
    )
    check(
        "uv_lock_sha256",
        recorded["environment"]["uv_lock_sha256"],
        file_sha256(repo_root / "uv.lock"),
    )
    return problems
