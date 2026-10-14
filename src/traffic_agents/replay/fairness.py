"""Scenario resolution and BEFORE/AFTER fairness verification.

Both sides of a replay must share every scientific input; only the controller may differ. The
manifest ``scenario_sha256`` is NOT used for the comparison because it incorporates
``controller_id`` and therefore differs between controllers by design. A controller-neutral hash
(``scenario_neutral_sha256``, the scenario config with the controller id neutralised) is used
instead, exactly like the reference-route pairing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from traffic_agents.config import ScenarioConfig, load_scenario_config
from traffic_agents.controllers import build_controller
from traffic_agents.experiments.route_artifacts import route_metadata_path
from traffic_agents.experiments.run_invariants import (
    RunInvariantFingerprint,
    file_sha256,
    json_sha256,
    scenario_config_sha256,
    validate_run_inputs,
)
from traffic_agents.metrics.run_metrics import load_offered_vehicles

DEMO_SEED = 42
KNOWN_SCENARIOS: tuple[str, ...] = (
    "S1_BALANCED",
    "S2_DIRECTIONAL_PEAK",
    "S3_DEMAND_SHIFT",
    "S4_LOCAL_SATURATION",
)
NEUTRAL_CONTROLLER_ID = "NEUTRAL"

# Every field below must be identical on both sides. Order is only for readable reports.
FAIRNESS_FIELDS: tuple[str, ...] = (
    "scenario_id",
    "demand_profile",
    "seed",
    "network_file",
    "route_file",
    "network_sha256",
    "route_sha256",
    "route_metadata_sha256",
    "turning_config_sha256",
    "scenario_neutral_sha256",
    "phase_plan_sha256",
    "movement_model_sha256",
    "communication_topology_sha256",
    "vehicle_population_sha256",
    "vehicle_population_count",
    "step_length",
    "warmup_seconds",
    "measurement_duration_seconds",
    "measurement_start_step",
    "measurement_end_step",
    "total_simulation_steps",
)


class ReplayFairnessError(ValueError):
    """Raised when BEFORE and AFTER differ in a scientific input (or are otherwise invalid)."""


@dataclass(frozen=True)
class ReplaySide:
    controller_id: str
    scenario_path: Path
    scenario_dir: Path
    config: ScenarioConfig
    fingerprint: RunInvariantFingerprint
    fairness: Mapping[str, object]


def resolve_scenario_path(scenario: str, seed: int, scenario_dir: Path) -> Path:
    """Frozen scenario YAML for ``(scenario, seed)``; ``scenario`` may also be a YAML path."""

    candidate = Path(scenario)
    if candidate.suffix in {".yaml", ".yml"}:
        if not candidate.exists():
            msg = f"scenario file not found: {candidate}"
            raise ReplayFairnessError(msg)
        return candidate
    name = scenario.upper()
    if name not in KNOWN_SCENARIOS:
        msg = f"unknown scenario {scenario!r}; valid scenarios: {', '.join(KNOWN_SCENARIOS)}"
        raise ReplayFairnessError(msg)
    path = scenario_dir / f"scenario_{name.lower()}_seed_{seed}.yaml"
    if not path.exists():
        msg = (
            f"no frozen scenario artifact for {name} with seed {seed}: {path} "
            "(the replay tool never generates routes; use a seed that already has artifacts)"
        )
        raise ReplayFairnessError(msg)
    return path


def build_replay_side(
    *,
    scenario_path: Path,
    controller_id: str,
    seed: int,
) -> ReplaySide:
    """Run configuration of one side, built like the experiment runner builds a run."""

    base = load_scenario_config(scenario_path)
    if base.seed != seed:
        msg = (
            f"scenario artifact {scenario_path.name} is frozen with seed {base.seed}, "
            f"requested seed {seed}"
        )
        raise ReplayFairnessError(msg)
    try:
        build_controller(controller_id)
    except Exception as exc:
        msg = f"unsupported controller {controller_id!r}: {exc}"
        raise ReplayFairnessError(msg) from exc
    config = base.model_copy(
        update={
            "controller_id": controller_id,
            "simulation": base.simulation.model_copy(update={"seed": int(seed)}),
        }
    )
    scenario_dir = scenario_path.parent
    fingerprint = validate_run_inputs(scenario_config=config, scenario_dir=scenario_dir)
    return ReplaySide(
        controller_id=controller_id,
        scenario_path=scenario_path,
        scenario_dir=scenario_dir,
        config=config,
        fingerprint=fingerprint,
        fairness=fairness_inputs(config, scenario_dir, fingerprint),
    )


def neutral_scenario_sha256(config: ScenarioConfig) -> str:
    return scenario_config_sha256(
        config.model_copy(update={"controller_id": NEUTRAL_CONTROLLER_ID})
    )


def vehicle_population_sha256(route_path: Path) -> tuple[str, int]:
    offered = load_offered_vehicles(route_path)
    digest = json_sha256(
        [
            [vehicle.vehicle_id, vehicle.scheduled_depart, list(vehicle.route)]
            for vehicle in sorted(offered, key=lambda v: v.vehicle_id)
        ]
    )
    return digest, len(offered)


def fairness_inputs(
    config: ScenarioConfig,
    scenario_dir: Path,
    fingerprint: RunInvariantFingerprint,
) -> dict[str, object]:
    route_path = scenario_dir / config.route_file
    population_hash, population_count = vehicle_population_sha256(route_path)
    metadata_path = route_metadata_path(route_path)
    return {
        "scenario_id": config.scenario_id,
        "demand_profile": config.traffic.demand_profile,
        "seed": int(config.seed),
        "network_file": config.network_file.as_posix(),
        "route_file": config.route_file.as_posix(),
        "network_sha256": fingerprint.network_sha256,
        "route_sha256": fingerprint.route_sha256,
        "route_metadata_sha256": file_sha256(metadata_path),
        "turning_config_sha256": fingerprint.turning_config_sha256,
        "scenario_neutral_sha256": neutral_scenario_sha256(config),
        "phase_plan_sha256": fingerprint.phase_plan_sha256,
        "movement_model_sha256": fingerprint.movement_model_sha256,
        "communication_topology_sha256": fingerprint.communication_topology_sha256,
        "vehicle_population_sha256": population_hash,
        "vehicle_population_count": population_count,
        "step_length": float(config.step_length),
        "warmup_seconds": float(config.warmup_seconds),
        "measurement_duration_seconds": float(config.measurement_duration_seconds),
        "measurement_start_step": int(config.measurement_start_step),
        "measurement_end_step": int(config.measurement_end_step),
        "total_simulation_steps": int(config.total_simulation_steps),
    }


def fairness_mismatches(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> list[str]:
    mismatches = []
    for name in FAIRNESS_FIELDS:
        if name not in before or name not in after:
            mismatches.append(
                f"{name}: missing (before={before.get(name)}, after={after.get(name)})"
            )
        elif before[name] != after[name]:
            mismatches.append(f"{name}: before={before[name]!r} after={after[name]!r}")
    return mismatches


def verify_fairness(before: ReplaySide, after: ReplaySide, *, requested_seed: int) -> None:
    """Fail immediately on any scientific-input mismatch between the two sides."""

    mismatches = fairness_mismatches(before.fairness, after.fairness)
    for label, side in (("before", before), ("after", after)):
        if int(side.config.seed) != int(requested_seed):
            mismatches.append(
                f"seed: {label} runs seed {side.config.seed}, requested seed {requested_seed}"
            )
    if mismatches:
        msg = "BEFORE/AFTER scientific inputs differ: " + "; ".join(mismatches)
        raise ReplayFairnessError(msg)


def fairness_report(before: ReplaySide, after: ReplaySide) -> dict[str, object]:
    """Verified, controller-independent inputs shared by both sides (for comparison.json)."""

    shared = {name: before.fairness[name] for name in FAIRNESS_FIELDS}
    shared["fairness_digest"] = json_sha256(shared)
    return shared
