from __future__ import annotations

import json
from pathlib import Path

import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments.route_artifacts import (
    RouteArtifactValidationError,
    validate_route_artifacts,
)
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
)


def test_valid_route_metadata_passes(tmp_path: Path) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(tmp_path, scenario_config=scenario_config)

    validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("config_hash", "stale", "config_hash"),
        ("scenario_hash", "stale", "scenario_hash"),
        ("seed", 7, "seed"),
        ("scenario_id", "wrong", "scenario_id"),
        ("network_hash", "0" * 64, "network_hash"),
    ],
)
def test_stale_or_wrong_route_metadata_fails(
    tmp_path: Path,
    field: str,
    value: object,
    match: str,
) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(
        tmp_path,
        scenario_config=scenario_config,
        metadata_overrides={field: value},
    )

    with pytest.raises(RouteArtifactValidationError, match=match):
        validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


def test_route_file_modified_after_metadata_fails(tmp_path: Path) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(tmp_path, scenario_config=scenario_config)
    (scenario_dir / scenario_config.route_file).write_text(
        "<routes><flow id='changed' begin='0' end='2' vehsPerHour='2'/></routes>",
        encoding="utf-8",
    )

    with pytest.raises(RouteArtifactValidationError, match="route_hash"):
        validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


def test_missing_route_metadata_fails(tmp_path: Path) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(tmp_path, scenario_config=scenario_config)
    (scenario_dir / "routes_s1_seed_42.metadata.json").unlink()

    with pytest.raises(FileNotFoundError, match="route metadata"):
        validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


def test_malformed_route_metadata_fails(tmp_path: Path) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(tmp_path, scenario_config=scenario_config)
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text("{", encoding="utf-8")

    with pytest.raises(RouteArtifactValidationError, match="malformed"):
        validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


def test_route_windows_must_match_scenario_config(tmp_path: Path) -> None:
    scenario_config = _scenario_config()
    scenario_dir = _write_artifacts(tmp_path, scenario_config=scenario_config)
    route_path = scenario_dir / scenario_config.route_file
    route_path.write_text(
        "<routes><flow id='west_to_east_middle' begin='0' end='1' vehsPerHour='2'/></routes>",
        encoding="utf-8",
    )
    _write_metadata(scenario_dir, scenario_config)

    with pytest.raises(RouteArtifactValidationError, match="flow begin/end/rate"):
        validate_route_artifacts(scenario_config=scenario_config, scenario_dir=scenario_dir)


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
                    "vehicles_per_hour": {"LOW": 1, "MEDIUM": 2, "HIGH": 3},
                }
            ],
        },
        intersections=[
            {
                "intersection_id": "A1",
                "incoming_lanes": ["top1A1_0"],
                "outgoing_lanes": ["A1top1_0"],
                "phases": ["north_south"],
            }
        ],
    )


def _write_artifacts(
    tmp_path: Path,
    *,
    scenario_config: ScenarioConfig,
    metadata_overrides: dict[str, object] | None = None,
) -> Path:
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text("<net/>", encoding="utf-8")
    (scenario_dir / "routes_s1_seed_42.rou.xml").write_text(
        "<routes><flow id='west_to_east_middle' begin='0' end='2' vehsPerHour='2'/></routes>",
        encoding="utf-8",
    )
    _write_metadata(scenario_dir, scenario_config, metadata_overrides)
    return scenario_dir


def _write_metadata(
    scenario_dir: Path,
    scenario_config: ScenarioConfig,
    metadata_overrides: dict[str, object] | None = None,
) -> None:
    route_path = scenario_dir / scenario_config.route_file
    payload = {
        "scenario_id": scenario_config.scenario_id,
        "seed": scenario_config.seed,
        "config_hash": route_generator_config_sha256(scenario_config),
        "scenario_hash": route_artifact_scenario_sha256(scenario_config),
        "route_hash": file_sha256(route_path),
        "network_hash": file_sha256(scenario_dir / scenario_config.network_file),
        "generated_at": "2026-01-01T00:00:00Z",
        "generator_version": "test",
    }
    if metadata_overrides:
        payload.update(metadata_overrides)
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
