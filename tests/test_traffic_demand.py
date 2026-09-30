from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.simulation import SumoEnvironmentInfo, TrafficDemandGenerator
from traffic_agents.simulation.traffic_demand import apply_visual_vehicle_style


def scenario_config() -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=3600,
        warmup_seconds=300,
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
    assert 'guiShape="passenger"' in route_content
    assert 'color="#1971c2"' in route_content
    assert 'width="1.80"' in route_content
    assert metadata["seed"] == 42
    assert metadata["generated_at"]
    assert metadata["flows"]
    assert metadata["flows"][0]["vehicles_per_hour"] == 600
    assert metadata["turning_ratios"] == {"straight": 0.7, "left": 0.15, "right": 0.15}
    assert metadata["schedule"] == []
    assert metadata["config_hash"]
    assert metadata["scenario_hash"] == generated.scenario_hash
    assert metadata["route_hash"] == generated.route_hash
    assert metadata["network_hash"]
    assert metadata["generator_version"]
    assert len(metadata["scenario_hash"]) == 64
    assert len(metadata["route_hash"]) == 64
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
    second = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=scenario_dir,
        seed=42,
        demand_profile="S1_BALANCED",
        sumo_info=info,
    ).generate()
    assert first.config_hash == second.config_hash
    assert first.route_hash == second.route_hash


def test_traffic_demand_generator_rejects_profile_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="demand_profile must match"):
        TrafficDemandGenerator(
            scenario_config=scenario_config(),
            scenario_dir=tmp_path,
            seed=42,
            demand_profile="S1_BALANCED_WRONG",  # type: ignore[arg-type]
        )


def test_apply_visual_vehicle_style_adds_passenger_type_when_missing(tmp_path: Path) -> None:
    route_path = tmp_path / "routes.rou.xml"
    route_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <flow id="flow-a" begin="0" end="10" route="route0"/>
</routes>
""",
        encoding="utf-8",
    )

    apply_visual_vehicle_style(route_path)

    route_content = route_path.read_text(encoding="utf-8")
    assert '<vType id="passenger"' in route_content
    assert 'guiShape="passenger"' in route_content
    assert 'color="#2f80ed"' in route_content


def test_apply_visual_vehicle_style_colors_known_flows(tmp_path: Path) -> None:
    route_path = tmp_path / "routes.rou.xml"
    route_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <flow id="west_to_east_middle" begin="0" end="10" route="route0">
        <route edges="left1A1 A1B1 B1C1 C1right1"/>
    </flow>
    <flow id="east_to_west_middle" begin="0" end="10" route="route1">
        <route edges="right1C1 C1B1 B1A1 A1left1"/>
    </flow>
</routes>
""",
        encoding="utf-8",
    )

    apply_visual_vehicle_style(route_path)

    root = ET.parse(route_path).getroot()
    west_flow = root.find("./flow[@id='west_to_east_middle']")
    east_flow = root.find("./flow[@id='east_to_west_middle']")
    assert west_flow is not None
    assert east_flow is not None
    assert west_flow.attrib["color"] == "#1971c2"
    assert east_flow.attrib["color"] == "#e03131"
    west_route = west_flow.find("route")
    assert west_route is not None
    assert west_route.attrib["color"] == "#1971c2"


def test_apply_visual_vehicle_style_colors_windowed_known_flows(tmp_path: Path) -> None:
    route_path = tmp_path / "routes.rou.xml"
    route_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <flow id="s3_w1_west_to_east_middle" begin="0" end="10" route="route0"/>
</routes>
""",
        encoding="utf-8",
    )

    apply_visual_vehicle_style(route_path)

    root = ET.parse(route_path).getroot()
    flow = root.find("./flow[@id='s3_w1_west_to_east_middle']")
    assert flow is not None
    assert flow.attrib["color"] == "#1971c2"
