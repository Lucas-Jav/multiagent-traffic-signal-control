from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from traffic_agents.config import ScenarioConfig, load_scenario_config


def valid_payload() -> dict[str, Any]:
    return {
        "scenario_id": "grid_3x3",
        "network_file": "grid_3x3.net.xml",
        "route_file": "grid_3x3.rou.xml",
        "duration_seconds": 3600,
        "warmup_seconds": 300,
        "step_length": 1.0,
        "seed": 42,
        "controller_id": "fixed_time",
        "traffic": {
            "demand_level": "medium",
            "flows": [
                {
                    "flow_id": "west_to_east_main",
                    "origin_edge_id": "west_in",
                    "destination_edge_id": "east_out",
                    "begin_seconds": 0,
                    "end_seconds": 3600,
                    "vehicles_per_hour": 900,
                }
            ],
        },
        "intersections": [
            {
                "intersection_id": "junction_1_1",
                "incoming_lanes": ["west_in_0", "north_in_0"],
                "outgoing_lanes": ["east_out_0", "south_out_0"],
                "phases": ["north_south", "east_west"],
            }
        ],
    }


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_load_valid_scenario_config(tmp_path: Path) -> None:
    path = tmp_path / "scenario.yaml"
    write_yaml(path, valid_payload())

    scenario = load_scenario_config(path)

    assert scenario.scenario_id == "grid_3x3"
    assert scenario.simulation.seed == 42
    assert scenario.traffic.demand_level == "medium"
    assert scenario.traffic.flows[0].vehicles_per_hour == 900
    assert scenario.intersections[0].intersection_id == "junction_1_1"


def test_versioned_grid_3x3_scenario_is_valid() -> None:
    scenario = load_scenario_config(Path("scenarios/grid_3x3/scenario.yaml"))

    assert scenario.scenario_id == "grid_3x3"


def test_scenario_config_rejects_missing_field() -> None:
    payload = valid_payload()
    del payload["duration_seconds"]

    with pytest.raises(ValidationError, match="duration_seconds"):
        ScenarioConfig.model_validate(payload)


def test_scenario_config_rejects_invalid_duration() -> None:
    payload = valid_payload()
    payload["duration_seconds"] = 0

    with pytest.raises(ValidationError, match="duration_seconds"):
        ScenarioConfig.model_validate(payload)


def test_scenario_config_rejects_invalid_seed() -> None:
    payload = valid_payload()
    payload["seed"] = -1

    with pytest.raises(ValidationError, match="seed"):
        ScenarioConfig.model_validate(payload)


def test_scenario_config_rejects_invalid_demand() -> None:
    payload = valid_payload()
    payload["traffic"]["demand_level"] = "rush_hour"

    with pytest.raises(ValidationError, match="demand_level"):
        ScenarioConfig.model_validate(payload)


def test_scenario_config_rejects_warmup_equal_to_duration() -> None:
    payload = valid_payload()
    payload["duration_seconds"] = 300
    payload["warmup_seconds"] = 300

    with pytest.raises(ValidationError, match="warmup_seconds must be lower"):
        ScenarioConfig.model_validate(payload)
