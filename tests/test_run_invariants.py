from __future__ import annotations

import json
from pathlib import Path

import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments import (
    RunInvariantFingerprint,
    RunInvariantValidationError,
    assert_comparable_manifests,
    assert_comparable_run_fingerprints,
    build_run_invariant_fingerprint,
    file_sha256,
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
    validate_run_inputs,
)
from traffic_agents.traffic_model import MOVEMENT_MODEL_VERSION, PHASE_PLAN_VERSION


def test_run_fingerprint_records_required_comparison_invariants(tmp_path: Path) -> None:
    scenario_dir = _write_scenario_dir(tmp_path)
    scenario_config = _scenario_config()

    fingerprint = build_run_invariant_fingerprint(
        scenario_config=scenario_config,
        scenario_dir=scenario_dir,
    )

    assert len(fingerprint.network_sha256) == 64
    assert len(fingerprint.route_sha256) == 64
    assert fingerprint.phase_plan_version == PHASE_PLAN_VERSION
    assert len(fingerprint.phase_plan_sha256) == 64
    assert fingerprint.movement_model_version == MOVEMENT_MODEL_VERSION
    assert len(fingerprint.movement_model_sha256) == 64
    assert fingerprint.turning_ratios == {"straight": 0.7, "left": 0.15, "right": 0.15}
    assert len(fingerprint.turning_config_sha256) == 64
    assert len(fingerprint.communication_topology_sha256) == 64


def test_validate_run_inputs_validates_phase_plan_before_run(tmp_path: Path) -> None:
    scenario_dir = _write_scenario_dir(tmp_path)

    fingerprint = validate_run_inputs(
        scenario_config=_scenario_config(),
        scenario_dir=scenario_dir,
    )

    assert fingerprint.phase_plan_version == PHASE_PLAN_VERSION


def test_validate_run_inputs_rejects_invalid_phase_plan(tmp_path: Path) -> None:
    scenario_dir = _write_scenario_dir(
        tmp_path,
        phase_metadata={
            "phase_min_green_seconds": 10.0,
            "phase_yellow_seconds": 4.0,
            "phase_all_red_seconds": 2.0,
            "phase_max_green_seconds": 60.0,
            "traffic_light_ids": {"A1": "J1"},
        },
    )

    with pytest.raises(RunInvariantValidationError, match=r"too short"):
        validate_run_inputs(
            scenario_config=_scenario_config(),
            scenario_dir=scenario_dir,
        )


def test_controller_comparison_requires_identical_invariant_inputs() -> None:
    reference = _fingerprint()
    candidate = _fingerprint(route_sha256="b" * 64)

    with pytest.raises(RunInvariantValidationError, match="route_sha256"):
        assert_comparable_run_fingerprints([reference, candidate])


def test_controller_comparison_rejects_changed_turning_ratios() -> None:
    reference = _fingerprint()
    candidate = _fingerprint(turning_ratios={"straight": 0.7, "left": 0.1, "right": 0.2})

    with pytest.raises(RunInvariantValidationError, match="turning_ratios"):
        assert_comparable_run_fingerprints([reference, candidate])


def test_controller_comparison_accepts_identical_manifests_with_different_controllers() -> None:
    reference = _fingerprint()
    manifest_b2 = reference.manifest_fields() | {
        "controller": {"controller_id": "B2_LOCAL_PRESSURE"}
    }
    manifest_c1 = reference.manifest_fields() | {
        "controller": {"controller_id": "C1_COOPERATIVE_COMPACT"}
    }

    assert_comparable_manifests([manifest_b2, manifest_c1])


def _scenario_config() -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=2,
        warmup_seconds=0,
        step_length=1.0,
        seed=42,
        controller_id="B0_FIXED",
        traffic={
            "demand_profile": "S1_BALANCED",
            "demand_level": "MEDIUM",
            "flows": [
                {
                    "flow_id": "west_to_east_middle",
                    "origin_edge_id": "left1A1",
                    "destination_edge_id": "C1right1",
                    "begin_seconds": 0,
                    "end_seconds": 2,
                    "vehicles_per_hour": {
                        "LOW": 1,
                        "MEDIUM": 2,
                        "HIGH": 3,
                    },
                }
            ],
        },
        intersections=[
            {
                "intersection_id": "A1",
                "incoming_lanes": [
                    "top1A1_0",
                    "right1A1_0",
                    "bottom1A1_0",
                    "left1A1_0",
                ],
                "outgoing_lanes": [
                    "A1top1_0",
                    "A1right1_0",
                    "A1bottom1_0",
                    "A1left1_0",
                ],
                "phases": ["north_south", "east_west"],
            }
        ],
    )


def _write_scenario_dir(
    tmp_path: Path,
    *,
    phase_metadata: dict[str, object] | None = None,
) -> Path:
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text(
        """
<net>
  <junction id="J1"/>
  <tlLogic id="J1" type="static" programID="0" offset="0">
    <phase duration="10" state="G"/>
    <phase duration="3" state="y"/>
    <phase duration="2" state="r"/>
  </tlLogic>
</net>
""".strip(),
        encoding="utf-8",
    )
    metadata = phase_metadata or {
        "phase_min_green_seconds": 10.0,
        "phase_yellow_seconds": 3.0,
        "phase_all_red_seconds": 2.0,
        "phase_max_green_seconds": 60.0,
        "traffic_light_ids": {"A1": "J1"},
    }
    (scenario_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (scenario_dir / "routes_s1_seed_42.rou.xml").write_text("<routes/>", encoding="utf-8")
    scenario_config = _scenario_config()
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text(
        json.dumps(
            {
                "scenario_id": scenario_config.scenario_id,
                "seed": scenario_config.seed,
                "config_hash": route_generator_config_sha256(scenario_config),
                "scenario_hash": route_artifact_scenario_sha256(scenario_config),
                "route_hash": file_sha256(scenario_dir / "routes_s1_seed_42.rou.xml"),
                "network_hash": file_sha256(scenario_dir / "network.net.xml"),
                "generated_at": "2026-01-01T00:00:00Z",
                "generator_version": "test",
            }
        ),
        encoding="utf-8",
    )
    return scenario_dir


def _fingerprint(
    *,
    scenario_sha256: str = "a" * 64,
    network_sha256: str = "a" * 64,
    route_sha256: str = "a" * 64,
    phase_plan_version: str = PHASE_PLAN_VERSION,
    phase_plan_sha256: str = "a" * 64,
    movement_model_version: str = MOVEMENT_MODEL_VERSION,
    movement_model_sha256: str = "a" * 64,
    turning_ratios: dict[str, float] | None = None,
    turning_config_sha256: str = "a" * 64,
    communication_topology_sha256: str = "a" * 64,
) -> RunInvariantFingerprint:
    return RunInvariantFingerprint(
        scenario_sha256=scenario_sha256,
        network_sha256=network_sha256,
        route_sha256=route_sha256,
        phase_plan_version=phase_plan_version,
        phase_plan_sha256=phase_plan_sha256,
        movement_model_version=movement_model_version,
        movement_model_sha256=movement_model_sha256,
        turning_ratios=turning_ratios or {"straight": 0.6, "left": 0.2, "right": 0.2},
        turning_config_sha256=turning_config_sha256,
        communication_topology_sha256=communication_topology_sha256,
    )
