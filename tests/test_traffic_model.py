from __future__ import annotations

import ast
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from traffic_agents.config import load_scenario_config
from traffic_agents.traffic_model import (
    DIRECTION_ORDER,
    PhaseTimingConfig,
    load_grid_traffic_models,
    validate_traffic_models,
)

SCENARIO_PATH = Path("scenarios/grid_3x3/scenario.yaml")
SCENARIO_DIR = SCENARIO_PATH.parent


def test_grid_3x3_defines_all_non_uturn_movements() -> None:
    scenario_config = load_scenario_config(SCENARIO_PATH)
    models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=SCENARIO_DIR,
    )
    expected_suffixes = {
        f"{from_direction}_to_{to_direction}"
        for from_direction in DIRECTION_ORDER
        for to_direction in DIRECTION_ORDER
        if from_direction != to_direction
    }

    assert set(models) == {f"A{index}" for index in range(1, 10)}
    for intersection_id, model in models.items():
        assert {movement.movement_id for movement in model.movements} == {
            f"{intersection_id}:{suffix}" for suffix in expected_suffixes
        }


def test_grid_3x3_phase_plan_has_no_conflicting_green_movements() -> None:
    scenario_config = load_scenario_config(SCENARIO_PATH)
    models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=SCENARIO_DIR,
    )

    validate_traffic_models(
        models,
        timing=PhaseTimingConfig(
            min_green_seconds=10.0,
            yellow_seconds=3.0,
            all_red_seconds=2.0,
            max_green_seconds=60.0,
        ),
    )


def test_each_grid_3x3_intersection_has_valid_phase_plan() -> None:
    scenario_config = load_scenario_config(SCENARIO_PATH)
    models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=SCENARIO_DIR,
    )

    for model in models.values():
        green_phases = [phase for phase in model.phase_plan if phase.kind == "GREEN"]
        assert len(green_phases) == 4
        assert {phase.phase_name for phase in green_phases} == {
            "PHASE_NORTH_APPROACH",
            "PHASE_EAST_APPROACH",
            "PHASE_SOUTH_APPROACH",
            "PHASE_WEST_APPROACH",
        }
        assert all(phase.movement_ids for phase in green_phases)
        assert all(len(phase.movement_ids) == 3 for phase in green_phases)


def test_turning_routes_exist_and_ratios_are_configured() -> None:
    scenario_config = load_scenario_config(SCENARIO_PATH)

    assert scenario_config.traffic.turning_ratios.straight == pytest.approx(0.70)
    assert scenario_config.traffic.turning_ratios.left == pytest.approx(0.15)
    assert scenario_config.traffic.turning_ratios.right == pytest.approx(0.15)
    assert scenario_config.traffic.uses_turning_ratio_routing

    route_tree = ET.parse(SCENARIO_DIR / scenario_config.route_file)
    route_edges = {
        route.attrib["edges"]
        for route in route_tree.getroot().findall("./route")
        if "edges" in route.attrib
    }
    assert any(" B1C1 " in f" {edges} " for edges in route_edges)
    assert any(" B1B2 " in f" {edges} " for edges in route_edges)
    assert any(" B1A1 " in f" {edges} " for edges in route_edges)


def test_controllers_do_not_command_raw_signal_states() -> None:
    controller_dir = Path("src/traffic_agents/controllers")
    forbidden_calls = {"setRedYellowGreenState", "setLinkState"}

    for path in controller_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in forbidden_calls:
                pytest.fail(f"{path} commands raw signal state via {node.attr}")


def test_grid_3x3_incoming_edges_have_passenger_stop_offsets() -> None:
    scenario_config = load_scenario_config(SCENARIO_PATH)
    network_tree = ET.parse(SCENARIO_DIR / scenario_config.network_file)
    root = network_tree.getroot()
    traffic_light_ids = {
        intersection.intersection_id for intersection in scenario_config.intersections
    }
    incoming_lane_ids = {
        lane_id
        for intersection in scenario_config.intersections
        for lane_id in intersection.incoming_lanes
    }
    incoming_edge_ids = {lane_id.rsplit("_", 1)[0] for lane_id in incoming_lane_ids}

    assert traffic_light_ids == {f"A{index}" for index in range(1, 10)}
    for edge_id in incoming_edge_ids:
        edge = root.find(f"./edge[@id='{edge_id}']")
        assert edge is not None
        stop_offset = edge.find("stopOffset")
        assert stop_offset is not None
        assert stop_offset.attrib == {"value": "7", "vClasses": "passenger"}
