from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from traffic_agents.communication import grid_3x3_communication_topology
from traffic_agents.config import ScenarioConfig
from traffic_agents.traffic_model import (
    MOVEMENT_MODEL_VERSION,
    PHASE_PLAN_VERSION,
    PhaseTimingConfig,
    load_grid_traffic_models,
    validate_traffic_models,
)

TURNING_RATIO_TOLERANCE = 0.000001

COMPARISON_INVARIANT_FIELDS: tuple[str, ...] = (
    "network_sha256",
    "route_sha256",
    "phase_plan_version",
    "movement_model_version",
    "turning_ratios",
    "communication_topology_sha256",
)


class RunInvariantValidationError(ValueError):
    """Raised when a scenario run is not scientifically comparable or valid."""


@dataclass(frozen=True)
class RunInvariantFingerprint:
    network_sha256: str
    route_sha256: str
    phase_plan_version: str
    movement_model_version: str
    turning_ratios: Mapping[str, float]
    communication_topology_sha256: str

    def manifest_fields(self) -> dict[str, object]:
        return {
            "network_sha256": self.network_sha256,
            "route_sha256": self.route_sha256,
            "phase_plan_version": self.phase_plan_version,
            "movement_model_version": self.movement_model_version,
            "turning_ratios": dict(self.turning_ratios),
            "communication_topology_sha256": self.communication_topology_sha256,
        }


def validate_run_inputs(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
) -> RunInvariantFingerprint:
    """Validate invariant inputs before starting a SUMO run."""

    fingerprint = build_run_invariant_fingerprint(
        scenario_config=scenario_config,
        scenario_dir=scenario_dir,
    )
    validate_phase_plan(scenario_config=scenario_config, scenario_dir=scenario_dir)
    return fingerprint


def build_run_invariant_fingerprint(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
) -> RunInvariantFingerprint:
    network_path = scenario_dir / scenario_config.network_file
    route_path = scenario_dir / scenario_config.route_file

    _require_file(network_path, label="Network")
    _require_file(route_path, label="Route")

    turning_ratios = _turning_ratios_payload(scenario_config)
    _validate_turning_ratios(turning_ratios)

    return RunInvariantFingerprint(
        network_sha256=file_sha256(network_path),
        route_sha256=file_sha256(route_path),
        phase_plan_version=PHASE_PLAN_VERSION,
        movement_model_version=MOVEMENT_MODEL_VERSION,
        turning_ratios=turning_ratios,
        communication_topology_sha256=grid_3x3_communication_topology().topology_hash,
    )


def validate_phase_plan(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
) -> None:
    metadata_path = scenario_dir / "metadata.json"
    _require_file(metadata_path, label="Scenario metadata")

    try:
        traffic_models = load_grid_traffic_models(
            scenario_config=scenario_config,
            scenario_dir=scenario_dir,
        )
        validate_traffic_models(
            traffic_models,
            timing=load_phase_timing_config(metadata_path),
        )
    except ValueError as exc:
        msg = f"invalid phase plan for {scenario_config.scenario_id}: {exc}"
        raise RunInvariantValidationError(msg) from exc


def load_phase_timing_config(metadata_path: Path) -> PhaseTimingConfig:
    _require_file(metadata_path, label="Scenario metadata")
    with metadata_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        msg = f"phase timing metadata must be a JSON object: {metadata_path}"
        raise RunInvariantValidationError(msg)

    try:
        return PhaseTimingConfig(
            min_green_seconds=_required_number(payload, "phase_min_green_seconds"),
            yellow_seconds=_required_number(payload, "phase_yellow_seconds"),
            all_red_seconds=_required_number(payload, "phase_all_red_seconds"),
            max_green_seconds=_required_number(payload, "phase_max_green_seconds"),
        )
    except ValueError as exc:
        msg = f"invalid phase timing metadata in {metadata_path}: {exc}"
        raise RunInvariantValidationError(msg) from exc


def assert_comparable_run_fingerprints(
    fingerprints: Iterable[RunInvariantFingerprint],
) -> None:
    items = tuple(fingerprints)
    if len(items) < 2:
        return

    reference = items[0]
    for index, candidate in enumerate(items[1:], start=1):
        mismatches = _fingerprint_mismatches(reference, candidate)
        if mismatches:
            details = ", ".join(mismatches)
            msg = (
                "invalid controller comparison; invariant inputs differ before run "
                f"at comparison index {index}: {details}"
            )
            raise RunInvariantValidationError(msg)


def assert_comparable_manifests(manifests: Iterable[Mapping[str, object]]) -> None:
    assert_comparable_run_fingerprints(
        run_invariant_fingerprint_from_manifest(manifest) for manifest in manifests
    )


def run_invariant_fingerprint_from_manifest(
    manifest: Mapping[str, object],
) -> RunInvariantFingerprint:
    return RunInvariantFingerprint(
        network_sha256=_required_string(manifest, "network_sha256"),
        route_sha256=_required_string(manifest, "route_sha256"),
        phase_plan_version=_required_string(manifest, "phase_plan_version"),
        movement_model_version=_required_string(manifest, "movement_model_version"),
        turning_ratios=_required_turning_ratios(manifest),
        communication_topology_sha256=_required_string(
            manifest,
            "communication_topology_sha256",
        ),
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, *, label: str) -> None:
    if not path.exists():
        msg = f"{label} file not found: {path}"
        raise FileNotFoundError(msg)
    if not path.is_file():
        msg = f"{label} path is not a file: {path}"
        raise RunInvariantValidationError(msg)


def _turning_ratios_payload(scenario_config: ScenarioConfig) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in scenario_config.traffic.turning_ratios.model_dump().items()
    }


def _validate_turning_ratios(turning_ratios: Mapping[str, float]) -> None:
    expected_fields = {"straight", "left", "right"}
    actual_fields = set(turning_ratios)
    if actual_fields != expected_fields:
        msg = f"turning ratios must define exactly {tuple(sorted(expected_fields))}"
        raise RunInvariantValidationError(msg)
    if any(value < 0 for value in turning_ratios.values()):
        msg = "turning ratios must be non-negative"
        raise RunInvariantValidationError(msg)
    total = sum(turning_ratios.values())
    if abs(total - 1.0) > TURNING_RATIO_TOLERANCE:
        msg = "turning ratios must sum to 1.0"
        raise RunInvariantValidationError(msg)


def _required_number(payload: Mapping[str, Any], field: str) -> float:
    value = payload.get(field)
    if not isinstance(value, int | float):
        msg = f"{field} must be numeric"
        raise ValueError(msg)
    return float(value)


def _required_string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        msg = f"manifest missing required invariant field: {field}"
        raise RunInvariantValidationError(msg)
    return value


def _required_turning_ratios(payload: Mapping[str, object]) -> dict[str, float]:
    value = payload.get("turning_ratios")
    if not isinstance(value, dict):
        msg = "manifest missing required invariant field: turning_ratios"
        raise RunInvariantValidationError(msg)
    turning_ratios: dict[str, float] = {}
    for key, raw_ratio in value.items():
        if not isinstance(key, str) or not isinstance(raw_ratio, int | float):
            msg = "manifest turning_ratios must be a string-to-number object"
            raise RunInvariantValidationError(msg)
        turning_ratios[key] = float(raw_ratio)
    _validate_turning_ratios(turning_ratios)
    return turning_ratios


def _fingerprint_mismatches(
    reference: RunInvariantFingerprint,
    candidate: RunInvariantFingerprint,
) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in COMPARISON_INVARIANT_FIELDS:
        reference_value = getattr(reference, field)
        candidate_value = getattr(candidate, field)
        if reference_value != candidate_value:
            mismatches.append(f"{field}={candidate_value!r} != {reference_value!r}")
    return tuple(mismatches)
