"""Experiment orchestration."""

from typing import TYPE_CHECKING, Any

from traffic_agents.experiments.run_invariants import (
    COMPARISON_INVARIANT_FIELDS,
    RunInvariantFingerprint,
    RunInvariantValidationError,
    assert_comparable_manifests,
    assert_comparable_run_fingerprints,
    build_run_invariant_fingerprint,
    file_sha256,
    load_phase_timing_config,
    phase_plan_sha256,
    run_invariant_fingerprint_from_manifest,
    scenario_config_sha256,
    validate_phase_plan,
    validate_run_inputs,
)

if TYPE_CHECKING:
    from traffic_agents.experiments.runner import (
        ExperimentConfig,
        ExperimentRunner,
        ExperimentRunSummary,
        load_experiment_config,
    )

__all__ = [
    "COMPARISON_INVARIANT_FIELDS",
    "ExperimentConfig",
    "ExperimentRunSummary",
    "ExperimentRunner",
    "RunInvariantFingerprint",
    "RunInvariantValidationError",
    "assert_comparable_manifests",
    "assert_comparable_run_fingerprints",
    "build_run_invariant_fingerprint",
    "file_sha256",
    "load_experiment_config",
    "load_phase_timing_config",
    "phase_plan_sha256",
    "run_invariant_fingerprint_from_manifest",
    "scenario_config_sha256",
    "validate_phase_plan",
    "validate_run_inputs",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ExperimentConfig",
        "ExperimentRunner",
        "ExperimentRunSummary",
        "load_experiment_config",
    }:
        from traffic_agents.experiments.runner import (
            ExperimentConfig,
            ExperimentRunner,
            ExperimentRunSummary,
            load_experiment_config,
        )

        exports: dict[str, Any] = {
            "ExperimentConfig": ExperimentConfig,
            "ExperimentRunner": ExperimentRunner,
            "ExperimentRunSummary": ExperimentRunSummary,
            "load_experiment_config": load_experiment_config,
        }
        return exports[name]

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
