from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.simulation import SumoEnvironmentInfo, TrafficDemandGenerator


def scenario_config() -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=3600,
        warmup_seconds=300,
        step_length=1.0,
        seed=42,
        controller_id="fixed_time",
        traffic={
            "demand_profile": "S1_BALANCED",
            "demand_level": "MEDIUM",
            "flows": [
                {
                    "flow_id": "west_to_east_middle",
                    "origin_edge_id": "left1A1",
                    "destination_edge_id": "C1right1",
                    "begin_seconds": 0,
                    "end_seconds": 3600,
                    "vehicles_per_hour": {
                        "LOW": 300,
                        "MEDIUM": 600,
                        "HIGH": 900,
                    },
                }
            ],
        },
        intersections=[
            {
                "intersection_id": "A1",
                "incoming_lanes": ["left1A1_0"],
                "outgoing_lanes": ["A1left1_0"],
                "phases": ["north_south", "east_west"],
            }
        ],
    )


def sumo_info(tmp_path: Path) -> SumoEnvironmentInfo:
    sumo_home = tmp_path / "sumo"
    bin_dir = sumo_home / "bin"
    bin_dir.mkdir(parents=True)
    duarouter = bin_dir / "duarouter.exe"
    duarouter.write_text("", encoding="utf-8")
    return SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=bin_dir / "sumo.exe",
        sumo_gui_binary=bin_dir / "sumo-gui.exe",
        version="1.27.1",
    )


def write_mock_route_file(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>

<!-- generated on 2026-09-01T22:00:00 by Eclipse SUMO duarouter 1.27.1
<duarouterConfiguration>
</duarouterConfiguration>
-->
<routes>
    <flow id="west_to_east_middle" begin="0.00" end="3600.00" route="route0"/>
</routes>
""",
        encoding="utf-8",
    )


def test_traffic_demand_generator_writes_routes_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = scenario_config()
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text("<net/>", encoding="utf-8")
    info = sumo_info(tmp_path)
    calls: list[list[str]] = []

    def run(
        args: list[str],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert check is True
        assert env["SUMO_HOME"] == str(info.sumo_home)
        write_mock_route_file(scenario_dir / "routes_s1_seed_42.rou.xml")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", run)

    generated = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=scenario_dir,
        seed=42,
        demand_profile="S1_BALANCED",
        sumo_info=info,
    ).generate()

    route_content = generated.route_path.read_text(encoding="utf-8")
    metadata = json.loads(generated.metadata_path.read_text(encoding="utf-8"))

    assert generated.route_path.exists()
    assert "<flow" in route_content
    assert metadata["seed"] == 42
    assert metadata["generated_at"]
    assert metadata["flows"]
    assert metadata["flows"][0]["vehicles_per_hour"] == 600
    assert metadata["config_hash"]
    assert "--seed" in calls[0]
    assert "42" in calls[0]


def test_same_seed_and_config_keep_metadata_hash_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = scenario_config()
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text("<net/>", encoding="utf-8")
    info = sumo_info(tmp_path)

    def run(
        args: list[str],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        write_mock_route_file(scenario_dir / "routes_s1_seed_42.rou.xml")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", run)

    first = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=scenario_dir,
        seed=42,
        demand_profile="S1_BALANCED",
        sumo_info=info,
    ).generate()
    first_metadata = json.loads(first.metadata_path.read_text(encoding="utf-8"))

    second = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=scenario_dir,
        seed=42,
        demand_profile="S1_BALANCED",
        sumo_info=info,
    ).generate()
    second_metadata = json.loads(second.metadata_path.read_text(encoding="utf-8"))

    assert first.config_hash == second.config_hash
    assert first_metadata["generated_at"] == second_metadata["generated_at"]


def test_traffic_demand_generator_rejects_profile_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="demand_profile must match"):
        TrafficDemandGenerator(
            scenario_config=scenario_config(),
            scenario_dir=tmp_path,
            seed=42,
            demand_profile="S1_BALANCED_WRONG",  # type: ignore[arg-type]
        )
