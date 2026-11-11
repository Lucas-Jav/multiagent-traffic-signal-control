"""Orquestração de experimentos."""

from typing import TYPE_CHECKING, Any

from traffic_agents.experiments.run_invariants import (
    COMPARISON_INVARIANT_FIELDS,
    RunInvariantFingerprint,
    RunInvariantValidationError,
    assert_comparable_manifests,
    assert_comparable_run_fingerprints,
    build_run_invariant_fingerprint,
    file_sha256,
    json_sha256,
    load_phase_timing_config,
    movement_model_sha256,
    phase_plan_sha256,
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
    run_invariant_fingerprint_from_manifest,
    scenario_config_sha256,
    scenario_turning_config_sha256,
    turning_config_sha256,
    validate_phase_plan,
    validate_run_inputs,
)

if TYPE_CHECKING:
    from traffic_agents.experiments.freeze import (
        ExperimentFreezeError,
        FreezeResult,
        FrozenExperimentConfig,
        freeze_experiment_config,
        load_frozen_experiment_config,
        load_frozen_experiment_config_from_dir,
    )
    from traffic_agents.experiments.runner import (
        ExperimentCommunicationMatrixConfig,
        ExperimentConfig,
        ExperimentRunConfig,
        ExperimentRunner,
        ExperimentRunSummary,
        load_experiment_config,
    )

__all__ = [
    "COMPARISON_INVARIANT_FIELDS",
    "ExperimentCommunicationMatrixConfig",
    "ExperimentConfig",
    "ExperimentFreezeError",
    "ExperimentRunConfig",
    "ExperimentRunSummary",
    "ExperimentRunner",
    "FreezeResult",
    "FrozenExperimentConfig",
    "RunInvariantFingerprint",
    "RunInvariantValidationError",
    "assert_comparable_manifests",
    "assert_comparable_run_fingerprints",
    "build_run_invariant_fingerprint",
    "file_sha256",
    "freeze_experiment_config",
    "json_sha256",
    "load_experiment_config",
    "load_frozen_experiment_config",
    "load_frozen_experiment_config_from_dir",
    "load_phase_timing_config",
    "movement_model_sha256",
    "phase_plan_sha256",
    "route_artifact_scenario_sha256",
    "route_generator_config_sha256",
    "run_invariant_fingerprint_from_manifest",
    "scenario_config_sha256",
    "scenario_turning_config_sha256",
    "turning_config_sha256",
    "validate_phase_plan",
    "validate_run_inputs",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ExperimentFreezeError",
        "FreezeResult",
        "FrozenExperimentConfig",
        "freeze_experiment_config",
        "load_frozen_experiment_config",
        "load_frozen_experiment_config_from_dir",
    }:
        from traffic_agents.experiments.freeze import (
            ExperimentFreezeError,
            FreezeResult,
            FrozenExperimentConfig,
            freeze_experiment_config,
            load_frozen_experiment_config,
            load_frozen_experiment_config_from_dir,
        )

        freeze_exports: dict[str, Any] = {
            "ExperimentFreezeError": ExperimentFreezeError,
            "FreezeResult": FreezeResult,
            "FrozenExperimentConfig": FrozenExperimentConfig,
            "freeze_experiment_config": freeze_experiment_config,
            "load_frozen_experiment_config": load_frozen_experiment_config,
            "load_frozen_experiment_config_from_dir": load_frozen_experiment_config_from_dir,
        }
        return freeze_exports[name]

    if name in {
        "ExperimentConfig",
        "ExperimentCommunicationMatrixConfig",
        "ExperimentRunConfig",
        "ExperimentRunner",
        "ExperimentRunSummary",
        "load_experiment_config",
    }:
        from traffic_agents.experiments.runner import (
            ExperimentCommunicationMatrixConfig,
            ExperimentConfig,
            ExperimentRunConfig,
            ExperimentRunner,
            ExperimentRunSummary,
            load_experiment_config,
        )

        runner_exports: dict[str, Any] = {
            "ExperimentCommunicationMatrixConfig": ExperimentCommunicationMatrixConfig,
            "ExperimentConfig": ExperimentConfig,
            "ExperimentRunConfig": ExperimentRunConfig,
            "ExperimentRunner": ExperimentRunner,
            "ExperimentRunSummary": ExperimentRunSummary,
            "load_experiment_config": load_experiment_config,
        }
        return runner_exports[name]

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
