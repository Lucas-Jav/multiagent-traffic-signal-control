"""Freeze da campanha científica final (Prompt 59).

Fonte única da verdade para a especificação imutável da campanha FINAL do TCC: seeds,
controladores, as matrizes principal (200 execuções) e S5 (90 execuções), as comparações
primárias/secundárias e o plano estatístico. As duas configs canônicas em
``experiments/configs`` são GERADAS a partir deste módulo e verificadas contra ele, de modo que
uma edição manual de uma config congelada é detectada.

Nada aqui executa simulação. Após o freeze, nenhum dos valores abaixo pode mudar; um defeito de
correção exige um NOVO freeze (ver ``docs/methodology/final-campaign-freeze.md``).
"""

from __future__ import annotations

import csv
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
from traffic_agents.experiments.freeze_hashing import (
    CANONICAL_TEXT_SCHEMA,
    SCIENTIFIC_TREE_SCHEMA,
    SEMANTIC_METADATA_SCHEMA,
    FileHashes,
    FreezePreconditions,
    ScientificSpec,
    ScientificTree,
    TreeRoot,
    WorkingTreeSource,
    canonical_sha256,
    check_freeze_preconditions,
    compute_scientific_tree,
    fingerprint_entries,
    git_resolve_commit,
    hash_file_bytes,
    historical_controller_labels,
    write_manifest_checksum,
)
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

FREEZE_SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
# NOTA: o SHA do commit-fonte científico NÃO é uma constante. Ele não pode ser conhecido antes de
# esse commit existir, então é informado explicitamente (``--scientific-source-sha``) e validado:
# deve existir, ser ancestral de HEAD (o próprio HEAD é permitido) e ter a mesma árvore científica
# atual.
MANIFEST_FILE_NAME = "final-freeze-manifest.json"
CAMPAIGN_ROLE = "FINAL_SCIENTIFIC"

# --- Seeds (sementes)
# --------------------------------------------------------------------------------------
PILOT_V2_SEEDS: tuple[int, ...] = (42, 2027, 3253, 4517, 5791)
EXTENSION_SEEDS: tuple[int, ...] = (6841, 8089, 10007, 12011, 16001)
FINAL_SEEDS: tuple[int, ...] = PILOT_V2_SEEDS + EXTENSION_SEEDS
SEED_PROVENANCE = (
    "First five seeds are the Pilot V2 seeds; the next five are a pre-reserved extension pool. "
    "No seed was selected according to controller performance."
)

# --- Controladores --------------------------------------------------------------------------------
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
# Autoridade multiplataforma (CANONICAL_TEXT_LF_V1). O hash bruto depende das quebras de linha do
# checkout (a950d82d... neste checkout Windows CRLF; igual ao canônico em um checkout LF).
B0_CANONICAL_SHA256 = "4ebbed94ef4feae63f7af62bc70944634bc5cbf399d0cd7856693d6758e6da19"
B0_EVIDENCE_RELATIVE_PATH = Path("docs/evidencias/fixed-time-calibration/b0_fixed_calibrated.json")

# --- Cenários e matrizes ---------------------------------------------------------------------
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

# --- Comparações --------------------------------------------------------------------------------
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

# --- Estatística ---------------------------------------------------------------------------------
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

# Arquivos-fonte que definem o comportamento científico. O pacote replay (apenas apresentação) e
# este módulo de ferramentas são rastreados separadamente.


class FinalFreezeError(ValueError):
    """Lançada quando a especificação da campanha final é inconsistente."""


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
        # B2 não usa comunicação: UMA execução de referência por seed.
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


# --- Plano estatístico ---------------------------------------------------------------------------
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


# --- Validação (sem simulação) -----------------------------------------------------------------
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
    """Verifica as configs congeladas contra este módulo sem executar nenhuma simulação."""

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
    if _canonical(plan_path) != B0_CANONICAL_SHA256:
        problems.append("B0 plan canonical sha256 differs from the frozen calibration plan")
    evidence = repo_root / B0_EVIDENCE_RELATIVE_PATH
    if not evidence.exists() or _canonical(evidence) != _canonical(plan_path):
        problems.append("B0 plan differs from its calibration evidence copy")
    return problems


def _validate_metric_identity() -> list[str]:
    missing = [
        name
        for name in REQUIRED_CANONICAL_METRICS
        if name not in METRIC_DEFINITIONS and name not in METRIC_DEFINITION_ALIASES
    ]
    return [f"canonical metric not defined: {name}" for name in missing]


# --- Hashes (resumos criptográficos)
# -------------------------------------------------------------------------------------
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


def _canonical(path: Path) -> str:
    return canonical_sha256(path.read_bytes())


def _file_hashes(repo_root: Path, relative: Path | str, *, semantic: bool = False) -> FileHashes:
    posix = Path(relative).as_posix()
    return hash_file_bytes(posix, (repo_root / posix).read_bytes(), semantic=semantic)


def replay_tree_sha256(repo_root: Path) -> str:
    """Impressão digital canônica das ferramentas de replay (só apresentação, fora da ciência)."""

    files = sorted(
        {
            *WorkingTreeSource(repo_root).list_dir("src/traffic_agents/replay"),
            "scripts/record_before_after.py",
            *(
                f"config/{path.name}"
                for path in sorted((repo_root / "config").glob("demo_*"))
                if path.is_file()
            ),
        }
    )
    return fingerprint_entries(_file_hashes(repo_root, path) for path in files)


# --- Conjunto de arquivos científicos (SCIENTIFIC_TREE_SHA256) -----------------------------------
# As ferramentas de freeze/replay são excluídas para que a impressão digital científica nunca
# dependa do seu verificador.
FREEZE_TOOLING_FILES: tuple[str, ...] = (
    "src/traffic_agents/experiments/final_freeze.py",
    "src/traffic_agents/experiments/freeze_hashing.py",
)
REPLAY_PREFIX = "src/traffic_agents/replay/"
SCENARIO_GENERATION_SCRIPTS: tuple[str, ...] = (
    "scripts/generate_grid.py",
    "scripts/generate_routes.py",
    "scripts/generate_scenarios.py",
)


def route_file_name(scenario_base: str, seed: int) -> str:
    return f"routes_{scenario_base.split('_', maxsplit=1)[0].lower()}_seed_{seed}.rou.xml"


def route_metadata_file_name(scenario_base: str, seed: int) -> str:
    return route_file_name(scenario_base, seed).removesuffix(".rou.xml") + ".metadata.json"


def scientific_spec() -> ScientificSpec:
    """Exatamente quais arquivos compõem a árvore científica (regras de inclusão autoritativas).

    Incluídos: todo o código-fonte científico (``src/traffic_agents`` e ``analysis``), as duas
    configs finais, o plano B0, a rede e seus metadados, o template de cenário, todo YAML de
    cenário x seed final / arquivo de rotas (hash de texto canônico) e metadados de rota (hash
    semântico, ``generated_at`` excluído), os geradores de cenário/rota, ``pyproject.toml`` e
    ``uv.lock``.

    Excluídos: pacote replay, módulos de ferramentas de freeze, testes, docs, evidências,
    ``artifacts/``, caches, arquivos apenas de GUI (``viewsettings.xml``) e todo arquivo não
    usado por uma execução final.
    """

    scenario_dir = SCENARIO_DIR_RELATIVE.as_posix()
    scenario_files: list[str] = []
    semantic: list[str] = []
    for scenario in MAIN_SCENARIOS:
        for seed in FINAL_SEEDS:
            scenario_files.append(f"{scenario_dir}/{scenario_file_name(scenario, seed)}")
            scenario_files.append(f"{scenario_dir}/{route_file_name(scenario, seed)}")
            semantic.append(f"{scenario_dir}/{route_metadata_file_name(scenario, seed)}")
    fixed = (
        MAIN_CONFIG_RELATIVE_PATH.as_posix(),
        S5_CONFIG_RELATIVE_PATH.as_posix(),
        B0_PLAN_RELATIVE_PATH.as_posix(),
        f"{scenario_dir}/network.net.xml",
        f"{scenario_dir}/metadata.json",
        f"{scenario_dir}/scenario.yaml",
        "pyproject.toml",
        "uv.lock",
        *SCENARIO_GENERATION_SCRIPTS,
        *scenario_files,
    )
    return ScientificSpec(
        tree_roots=(
            TreeRoot(
                "src/traffic_agents",
                (".py",),
                excluded_prefixes=(REPLAY_PREFIX,),
                excluded_files=FREEZE_TOOLING_FILES,
            ),
            TreeRoot("analysis", (".py",)),
        ),
        fixed_files=fixed,
        semantic_files=tuple(semantic),
        description={
            "included": "src/traffic_agents/**/*.py, analysis/**/*.py, final configs, B0 plan, "
            "network + metadata + scenario template, 40 final scenario YAML + route files, 40 "
            "route metadata (semantic), scenario generators, pyproject.toml, uv.lock",
            "excluded": "replay package, freeze tooling (final_freeze.py, freeze_hashing.py), "
            "tests, docs, evidence, artifacts/, caches, viewsettings.xml, unused scenario files",
        },
    )


SCENARIO_INPUT_COLUMNS: tuple[str, ...] = (
    "scenario_base",
    "seed",
    "scenario_file_raw_sha256",
    "scenario_file_canonical_sha256",
    "route_file_raw_sha256",
    "route_file_canonical_sha256",
    "route_metadata_raw_sha256",
    "route_metadata_canonical_sha256",
    "route_metadata_semantic_sha256",
    "route_generator_config_sha256",
    "turning_config_sha256",
    "movement_model_sha256",
    "phase_plan_sha256",
    "scenario_neutral_sha256",
)


def scenario_input_rows(repo_root: Path) -> list[dict[str, object]]:
    """Hashes por cenário x seed. Os canônicos/semânticos são as autoridades multiplataforma."""

    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    rows: list[dict[str, object]] = []
    for scenario in MAIN_SCENARIOS:
        for seed in FINAL_SEEDS:
            path = scenario_dir / scenario_file_name(scenario, seed)
            config = load_scenario_config(path)
            models = load_grid_traffic_models(scenario_config=config, scenario_dir=scenario_dir)
            neutral = config.model_copy(update={"controller_id": "NEUTRAL"})
            scenario_hashes = _file_hashes(repo_root, path.relative_to(repo_root))
            route_hashes = _file_hashes(repo_root, scenario_dir / config.route_file)
            meta_hashes = _file_hashes(
                repo_root,
                SCENARIO_DIR_RELATIVE / route_metadata_file_name(scenario, seed),
                semantic=True,
            )
            rows.append(
                {
                    "scenario_base": scenario,
                    "seed": seed,
                    "scenario_file_raw_sha256": scenario_hashes.raw_byte_sha256,
                    "scenario_file_canonical_sha256": scenario_hashes.canonical_sha256,
                    "route_file_raw_sha256": route_hashes.raw_byte_sha256,
                    "route_file_canonical_sha256": route_hashes.canonical_sha256,
                    "route_metadata_raw_sha256": meta_hashes.raw_byte_sha256,
                    "route_metadata_canonical_sha256": meta_hashes.canonical_sha256,
                    "route_metadata_semantic_sha256": meta_hashes.semantic_sha256,
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
    "route_file_canonical_sha256",
)

SCIENTIFIC_TREE_COLUMNS: tuple[str, ...] = (
    "path",
    "hash_mode",
    "authoritative_sha256",
    "raw_byte_sha256",
    "canonical_sha256",
    "semantic_sha256",
)


def run_matrix_rows(repo_root: Path) -> list[dict[str, object]]:
    """Uma linha por execução final; ``scenario_neutral_sha256`` ignora o id do controlador."""

    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    route_hash_cache: dict[str, str | None] = {}
    rows: list[dict[str, object]] = []
    for run in (*main_runs(), *s5_runs()):
        config = _scenario_config_for(run, scenario_dir)
        neutral = config.model_copy(update={"controller_id": "NEUTRAL"})
        route_key = config.route_file.as_posix()
        if route_key not in route_hash_cache:
            route_hash_cache[route_key] = _file_hashes(
                repo_root, scenario_dir / config.route_file
            ).canonical_sha256
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
                "route_file_canonical_sha256": route_hash_cache[route_key],
            }
        )
    return rows


def scientific_tree_rows(tree: ScientificTree) -> list[dict[str, object]]:
    return [
        {
            "path": entry.path,
            "hash_mode": entry.mode,
            "authoritative_sha256": entry.authoritative,
            "raw_byte_sha256": entry.raw_byte_sha256,
            "canonical_sha256": entry.canonical_sha256,
            "semantic_sha256": entry.semantic_sha256,
        }
        for entry in tree.entries
    ]


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# --- Ambiente / git --------------------------------------------------------------------------
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
    return {
        "python_version": platform.python_version(),
        "sumo_version": sumo.version,
        "traci_version": _package_version("traci"),
        "sumolib_version": _package_version("sumolib"),
        "uv_version": _uv_version(),
        "uv_lock_sha256": _file_hashes(repo_root, "uv.lock").canonical_sha256,
        "uv_lock_raw_sha256": _file_hashes(repo_root, "uv.lock").raw_byte_sha256,
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


# --- Manifesto -----------------------------------------------------------------------------------
def build_freeze_manifest(
    repo_root: Path,
    *,
    generated_at: str,
    preconditions: FreezePreconditions,
) -> dict[str, Any]:
    """Monta o manifesto do freeze a partir de entradas inspecionadas sob ``preconditions``.

    O chamador (``generate_definitive_freeze``) deve ter verificado ``preconditions.ok``; o
    manifesto registra o estado observado em qualquer caso, de modo que nunca pode alegar uma
    inspeção limpa que não ocorreu.
    """

    scenario_dir = repo_root / SCENARIO_DIR_RELATIVE
    plan_path = repo_root / B0_PLAN_RELATIVE_PATH
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    from traffic_agents.controllers.fixed_time_plan import load_plan

    scenario_rows = scenario_input_rows(repo_root)
    matrix_rows = run_matrix_rows(repo_root)
    reference = reference_route_definition()
    plan = statistical_plan()
    first_config = load_scenario_config(scenario_dir / scenario_file_name(MAIN_SCENARIOS[0], 42))
    network_hashes_obj = _file_hashes(repo_root, scenario_dir / first_config.network_file)
    network_sha = network_hashes_obj.canonical_sha256
    network_hashes = {
        _file_hashes(
            repo_root, scenario_dir / load_scenario_config(scenario_dir / row_path).network_file
        ).canonical_sha256
        for row_path in (
            scenario_file_name(s, seed) for s in MAIN_SCENARIOS for seed in FINAL_SEEDS
        )
    }
    if network_hashes != {network_sha}:
        msg = "all scenarios must share one network file"
        raise FinalFreezeError(msg)

    b0_hashes = _file_hashes(repo_root, B0_PLAN_RELATIVE_PATH)
    main_cfg = _file_hashes(repo_root, MAIN_CONFIG_RELATIVE_PATH)
    s5_cfg = _file_hashes(repo_root, S5_CONFIG_RELATIVE_PATH)

    def digest(column: str) -> str:
        return json_sha256([row[column] for row in scenario_rows])

    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "freeze_name": "FINAL_SCIENTIFIC_CAMPAIGN_FREEZE",
        "generated_at": generated_at,
        "campaign_role": CAMPAIGN_ROLE,
        "environment": environment_record(repo_root),
        "identity": {
            "scientific_source_git_sha": preconditions.scientific_source_git_sha,
            "freeze_tooling_git_sha": preconditions.head_sha,
            "scientific_source_is_ancestor_of_head": preconditions.source_is_ancestor_of_head,
            "git_working_tree_dirty_at_input_inspection": (
                preconditions.working_tree_dirty_at_input_inspection
            ),
            "scientific_tree_sha256": preconditions.scientific_tree_sha256,
            "source_scientific_tree_sha256": preconditions.source_scientific_tree_sha256,
            "scientific_tree_unchanged_from_source": (
                not preconditions.scientific_changes_since_source
            ),
            "scientific_tree_file_count": len(preconditions.tree.entries),
            "note": (
                "git_working_tree_dirty_at_input_inspection describes the tree while the "
                "scientific inputs were inspected; evidence written afterwards does not "
                "retroactively make that inspection dirty."
            ),
        },
        "scientific_hash_schema": {
            "text": CANONICAL_TEXT_SCHEMA,
            "metadata": SEMANTIC_METADATA_SCHEMA,
            "tree": SCIENTIFIC_TREE_SCHEMA,
            "authoritative_for_cross_platform_verification": (
                "canonical_sha256 for text, semantic_sha256 for route metadata, raw_byte_sha256 "
                "for binary files; raw hashes of text files are forensic/local evidence only"
            ),
            "tree_record_format": "<relative_path>\t<hash_mode>\t<authoritative_hash>\n",
            "tree_file_set": dict(scientific_spec().description),
            "tree_evidence_file": (FREEZE_DOCS_DIR / "scientific-tree.csv").as_posix(),
        },
        "replay": {
            "implemented_at_freeze": True,
            "replay_tree_sha256": replay_tree_sha256(repo_root),
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
            "plan_file_raw_sha256": b0_hashes.raw_byte_sha256,
            "plan_file_canonical_sha256": b0_hashes.canonical_sha256,
            "plan_semantic_sha256": load_plan(plan_path).sha256(),
            "provenance": plan_payload["provenance"],
        },
        "main_matrix": {
            "experiment_id": MAIN_EXPERIMENT_ID,
            "config": MAIN_CONFIG_RELATIVE_PATH.as_posix(),
            "config_raw_sha256": main_cfg.raw_byte_sha256,
            "config_canonical_sha256": main_cfg.canonical_sha256,
            "scenarios": list(MAIN_SCENARIOS),
            "controllers": list(FINAL_CONTROLLERS),
            "seeds": list(FINAL_SEEDS),
            "expected_runs": EXPECTED_MAIN_RUNS,
        },
        "s5_matrix": {
            "experiment_id": S5_EXPERIMENT_ID,
            "config": S5_CONFIG_RELATIVE_PATH.as_posix(),
            "config_raw_sha256": s5_cfg.raw_byte_sha256,
            "config_canonical_sha256": s5_cfg.canonical_sha256,
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
            "glossary_sha256": _canonical(repo_root / GLOSSARY_RELATIVE_PATH),
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
            "validity_gates_doc_sha256": _canonical(
                repo_root / "docs/methodology/scenario-validity-gates.md"
            ),
        },
        "canonical_metrics": {
            "definitions_sha256": metric_definitions_sha256(),
            "required": list(REQUIRED_CANONICAL_METRICS),
            "metrics_doc_sha256": _canonical(repo_root / "docs/methodology/metrics.md"),
        },
        "statistical_plan": plan | {"plan_sha256": json_sha256(plan)},
        "scientific_input_hashes": {
            "network_sha256": network_sha,
            "scenario_configs_digest": digest("scenario_file_canonical_sha256"),
            "route_files_digest": digest("route_file_canonical_sha256"),
            "route_generation_configs_digest": digest("route_generator_config_sha256"),
            "turning_config_digest": digest("turning_config_sha256"),
            "movement_definitions_digest": digest("movement_model_sha256"),
            "phase_topology_digest": digest("phase_plan_sha256"),
            "scenario_neutral_digest": digest("scenario_neutral_sha256"),
            "controller_configs": {
                controller: json_sha256(build_controller(controller).manifest_metadata())
                for controller in FINAL_CONTROLLERS
            },
            "b0_plan_sha256": b0_hashes.canonical_sha256,
            "b0_plan_raw_sha256": b0_hashes.raw_byte_sha256,
            "route_metadata_semantic_digest": digest("route_metadata_semantic_sha256"),
            "network_raw_sha256": network_hashes_obj.raw_byte_sha256,
            "communication_topology_sha256": grid_3x3_communication_topology().topology_hash,
            "metric_definitions_sha256": metric_definitions_sha256(),
            "seed_list_sha256": json_sha256(list(FINAL_SEEDS)),
            "reference_route_definition_sha256": json_sha256(reference),
            "main_campaign_config_sha256": main_cfg.canonical_sha256,
            "main_campaign_config_raw_sha256": main_cfg.raw_byte_sha256,
            "s5_campaign_config_sha256": s5_cfg.canonical_sha256,
            "s5_campaign_config_raw_sha256": s5_cfg.raw_byte_sha256,
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


def write_freeze_evidence(
    repo_root: Path,
    manifest: Mapping[str, Any],
    preconditions: FreezePreconditions,
) -> list[Path]:
    """Grava o manifesto (artefatos + cópia versionada), as tabelas de evidência e os checksums do
    manifesto.
    """

    written: list[Path] = []
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    for relative in (FREEZE_ARTIFACT_RELATIVE_PATH, FREEZE_DOCS_DIR / MANIFEST_FILE_NAME):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
        # O manifesto nunca contém o próprio hash; ele fica em um arquivo de checksum irmão.
        written.append(write_manifest_checksum(path))
    docs = repo_root / FREEZE_DOCS_DIR
    write_csv(docs / "run-matrix.csv", RUN_MATRIX_COLUMNS, run_matrix_rows(repo_root))
    write_csv(docs / "scenario-inputs.csv", SCENARIO_INPUT_COLUMNS, scenario_input_rows(repo_root))
    write_csv(
        docs / "scientific-tree.csv",
        SCIENTIFIC_TREE_COLUMNS,
        scientific_tree_rows(preconditions.tree),
    )
    plan_path = docs / "statistical-plan.json"
    plan_path.write_text(
        json.dumps(statistical_plan(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    written.extend(
        [
            docs / "run-matrix.csv",
            docs / "scenario-inputs.csv",
            docs / "scientific-tree.csv",
            plan_path,
        ]
    )
    return written


class FreezePreconditionError(FinalFreezeError):
    """Lançada quando o freeze definitivo não pode ser gerado a partir do estado atual do
    repositório.
    """


def reject_historical_b0(labels: Sequence[str]) -> None:
    """A análise final deve nomear ``B0_FIXED_CALIBRATED`` explicitamente.

    ``analysis/statistics.py`` ainda mapeia o alias simples ``B0`` para o histórico ``B0_FIXED``
    (esse arquivo faz parte do código-fonte científico congelado, portanto não é editado); as
    entradas e comparações finais são, por isso, verificadas aqui.
    """

    forbidden = [*HISTORICAL_CONTROLLERS, "B0"]
    found = historical_controller_labels(labels, forbidden)
    if found:
        msg = f"historical B0 label(s) {found} are not allowed in the final analysis"
        raise FinalFreezeError(msg)


def generate_definitive_freeze(
    repo_root: Path,
    *,
    generated_at: str,
    scientific_source_sha: str,
) -> tuple[list[Path], FreezePreconditions]:
    """Fluxo de geração definitivo. Nada é gravado a menos que todas as pré-condições valham.

    1. árvore de trabalho limpa; 2. SHA-fonte científico é ancestral de HEAD; 3. árvore científica
    calculada e comparada com a árvore do commit-fonte; 4. entradas inspecionadas enquanto
    limpa; 5. evidências gravadas depois.
    """

    preconditions = check_freeze_preconditions(repo_root, scientific_spec(), scientific_source_sha)
    if not preconditions.ok:
        msg = "cannot generate the final freeze: " + "; ".join(preconditions.failures())
        raise FreezePreconditionError(msg)
    validate_final_campaign(repo_root)
    reject_historical_b0([controller for pair in FINAL_CONTROLLER_PAIRS for controller in pair])
    manifest = build_freeze_manifest(
        repo_root, generated_at=generated_at, preconditions=preconditions
    )
    return write_freeze_evidence(repo_root, manifest, preconditions), preconditions


def verify_freeze_manifest(
    repo_root: Path,
    manifest_path: Path | None = None,
    *,
    scientific_source_sha: str | None = None,
) -> list[str]:
    """Verifica um manifesto schema 2: identidade git (SHA-fonte do manifesto ou do chamador)
    mais todo hash multiplataforma. Retorna a lista de divergências."""

    path = manifest_path or repo_root / FREEZE_DOCS_DIR / MANIFEST_FILE_NAME
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if recorded.get("schema_version") != FREEZE_SCHEMA_VERSION:
        return [
            f"manifest schema_version {recorded.get('schema_version')!r} is not "
            f"{FREEZE_SCHEMA_VERSION}; a legacy manifest must be regenerated"
        ]
    recorded_sha = recorded["identity"]["scientific_source_git_sha"]
    problems: list[str] = []
    if scientific_source_sha is not None:
        resolved = git_resolve_commit(repo_root, scientific_source_sha)
        if resolved != recorded_sha:
            problems.append(
                f"scientific_source_git_sha: manifest={recorded_sha!r} provided={resolved!r}"
            )
    source = check_freeze_preconditions(repo_root, scientific_spec(), recorded_sha)
    if not source.source_exists:
        problems.append(f"scientific source {recorded_sha} does not exist")
    elif not source.source_is_ancestor_of_head:
        problems.append("scientific source commit is not an ancestor of HEAD")
    problems.extend(
        f"scientific input changed since source commit: {change}"
        for change in source.scientific_changes_since_source
    )
    return problems + verify_manifest_hashes(repo_root, recorded)


def verify_manifest_hashes(repo_root: Path, recorded: Mapping[str, Any]) -> list[str]:
    """Recalcula os hashes multiplataforma de um manifesto schema 2 (sem acesso ao git)."""

    problems: list[str] = []

    def check(label: str, recorded_value: object, actual: object) -> None:
        if recorded_value != actual:
            problems.append(f"{label}: manifest={recorded_value!r} actual={actual!r}")

    identity = recorded["identity"]
    current_tree = compute_scientific_tree(scientific_spec(), WorkingTreeSource(repo_root))
    check("scientific_tree_sha256", identity["scientific_tree_sha256"], current_tree.sha256)

    hashes = recorded["scientific_input_hashes"]
    plan_hashes = _file_hashes(repo_root, B0_PLAN_RELATIVE_PATH)
    check("b0_plan_sha256", hashes["b0_plan_sha256"], plan_hashes.canonical_sha256)
    check(
        "main_campaign_config_sha256",
        hashes["main_campaign_config_sha256"],
        _file_hashes(repo_root, MAIN_CONFIG_RELATIVE_PATH).canonical_sha256,
    )
    check(
        "s5_campaign_config_sha256",
        hashes["s5_campaign_config_sha256"],
        _file_hashes(repo_root, S5_CONFIG_RELATIVE_PATH).canonical_sha256,
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
        ("scenario_configs_digest", "scenario_file_canonical_sha256"),
        ("route_files_digest", "route_file_canonical_sha256"),
        ("route_metadata_semantic_digest", "route_metadata_semantic_sha256"),
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
        _file_hashes(repo_root, "uv.lock").canonical_sha256,
    )
    return problems
