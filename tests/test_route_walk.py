from __future__ import annotations

import json
import shutil
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from traffic_agents.config import (
    EntryDemandConfig,
    ScenarioConfig,
    TurningRatiosConfig,
    load_scenario_config,
)
from traffic_agents.simulation import TrafficDemandGenerator
from traffic_agents.simulation.route_walk import (
    RouteWalkError,
    RoutingGraph,
    entry_rng,
    expected_edge_flows,
    generate_vehicles,
    route_movements,
    sample_route,
    shortest_paths_to_node,
    summarize_vehicles,
)

SCENARIO_DIR = Path("scenarios/grid_3x3")
NETWORK_PATH = SCENARIO_DIR / "network.net.xml"
ALL_ENTRIES = (
    "left0A0",
    "left1A1",
    "left2A2",
    "right0C0",
    "right1C1",
    "right2C2",
    "top0A2",
    "top1B2",
    "top2C2",
    "bottom0A0",
    "bottom1B0",
    "bottom2C0",
)


@pytest.fixture(scope="module")
def graph() -> RoutingGraph:
    return RoutingGraph.from_network(NETWORK_PATH)


def entry(
    demand_id: str,
    edge: str,
    rate: float,
    *,
    ratios: dict[str, float] | None = None,
    via: str | None = None,
) -> EntryDemandConfig:
    return EntryDemandConfig(
        demand_id=demand_id,
        entry_edge_id=edge,
        begin_seconds=0,
        end_seconds=3600,
        vehicles_per_hour={"LOW": rate, "MEDIUM": rate, "HIGH": rate},
        turning_ratios=TurningRatiosConfig(**ratios) if ratios else None,
        via_intersection_id=via,
    )


def test_routing_graph_contains_only_legal_movements(graph: RoutingGraph) -> None:
    assert len(graph.entry_edges) == 12
    assert len(graph.exit_edges) == 12
    assert len(graph.signalized_nodes) == 9
    for edge_id, options in graph.successors.items():
        assert set(options) == {"straight", "left", "right"}, edge_id
        assert edge_id not in graph.exit_edges
        # no movement returns onto the edge itself and every movement has a distinct target
        assert edge_id not in options.values()
        assert len(set(options.values())) == 3
    for edge_id in graph.entry_edges | graph.exit_edges:
        assert edge_id in graph.edge_to_node


def test_sampled_routes_end_at_border_exits_and_follow_legal_connections(
    graph: RoutingGraph,
) -> None:
    rng = entry_rng(42, "probe")
    for entry_edge in sorted(graph.entry_edges):
        for _ in range(20):
            route = sample_route(
                graph, entry_edge, {"straight": 0.7, "left": 0.15, "right": 0.15}, rng
            )
            assert route[0] == entry_edge
            assert route[-1] in graph.exit_edges
            for current, following in pairwise(route):
                assert following in graph.options(current).values()


def test_sample_route_rejects_non_entry_edges(graph: RoutingGraph) -> None:
    with pytest.raises(RouteWalkError, match="not a border entry"):
        sample_route(graph, "A1B1", {"straight": 1.0}, entry_rng(1, "x"))


def test_generation_is_deterministic_for_the_same_seed(graph: RoutingGraph) -> None:
    entries = [entry(f"base_{edge}", edge, 150) for edge in ALL_ENTRIES]
    ratios = TurningRatiosConfig()

    first = generate_vehicles(
        graph=graph, entries=entries, demand_level="MEDIUM", default_ratios=ratios, seed=42
    )
    second = generate_vehicles(
        graph=graph, entries=entries, demand_level="MEDIUM", default_ratios=ratios, seed=42
    )
    other = generate_vehicles(
        graph=graph, entries=entries, demand_level="MEDIUM", default_ratios=ratios, seed=2027
    )

    assert first == second
    assert [vehicle.route for vehicle in first] != [vehicle.route for vehicle in other]
    departures = [vehicle.depart_seconds for vehicle in first]
    assert departures == sorted(departures)
    assert len({vehicle.vehicle_id for vehicle in first}) == len(first)


@pytest.mark.parametrize(
    "ratios",
    [
        {"straight": 0.70, "left": 0.15, "right": 0.15},
        {"straight": 0.40, "left": 0.30, "right": 0.30},
        {"straight": 0.50, "left": 0.10, "right": 0.40},
    ],
)
def test_configured_turning_ratios_shape_realized_movements(
    graph: RoutingGraph,
    ratios: dict[str, float],
) -> None:
    entries = [entry(f"base_{edge}", edge, 300) for edge in ALL_ENTRIES]
    vehicles = generate_vehicles(
        graph=graph,
        entries=entries,
        demand_level="MEDIUM",
        default_ratios=TurningRatiosConfig(**ratios),
        seed=42,
    )

    summary = summarize_vehicles(
        graph=graph,
        vehicles=vehicles,
        measurement_start_seconds=300,
        measurement_end_seconds=3600,
    )

    proportions: dict[str, float] = summary["realized_movement_proportions"]  # type: ignore[assignment]
    total_movements = sum(summary["realized_movement_counts"].values())  # type: ignore[attr-defined]
    assert total_movements > 5000
    for movement, expected in ratios.items():
        assert abs(proportions[movement] - expected) <= 0.03, (movement, proportions)


def test_zero_probability_movements_are_never_created(graph: RoutingGraph) -> None:
    entries = [entry(f"base_{edge}", edge, 120) for edge in ALL_ENTRIES]
    vehicles = generate_vehicles(
        graph=graph,
        entries=entries,
        demand_level="MEDIUM",
        default_ratios=TurningRatiosConfig(straight=1.0, left=0.0, right=0.0),
        seed=7,
    )

    movements = {
        movement for vehicle in vehicles for movement in route_movements(graph, vehicle.route)
    }
    assert movements == {"straight"}
    assert all(len(vehicle.route) == 4 for vehicle in vehicles)


def test_per_entry_turning_override_applies_only_to_that_entry(graph: RoutingGraph) -> None:
    entries = [
        entry("biased", "left1A1", 400, ratios={"straight": 0.0, "left": 1.0, "right": 0.0}),
        entry("plain", "right1C1", 400),
    ]
    vehicles = generate_vehicles(
        graph=graph,
        entries=entries,
        demand_level="MEDIUM",
        default_ratios=TurningRatiosConfig(),
        seed=3,
    )

    biased = {
        movement
        for vehicle in vehicles
        if vehicle.demand_id == "biased"
        for movement in route_movements(graph, vehicle.route)
    }
    plain = {
        movement
        for vehicle in vehicles
        if vehicle.demand_id == "plain"
        for movement in route_movements(graph, vehicle.route)
    }
    assert biased == {"left"}
    assert plain == {"straight", "left", "right"}


def test_via_intersection_routes_pass_through_that_intersection(graph: RoutingGraph) -> None:
    b1 = "B1"  # SUMO id of project intersection A5
    entries = [
        entry(
            f"via_{edge}",
            edge,
            100,
            via="A5",
            ratios={"straight": 0.9, "left": 0.05, "right": 0.05},
        )
        for edge in ALL_ENTRIES
    ]
    vehicles = generate_vehicles(
        graph=graph,
        entries=entries,
        demand_level="MEDIUM",
        default_ratios=TurningRatiosConfig(),
        seed=5,
        via_nodes={"A5": b1},
    )

    for vehicle in vehicles:
        assert any(graph.edge_to_node[edge_id] == b1 for edge_id in vehicle.route), vehicle
    paths = shortest_paths_to_node(graph, "left2A2", b1)
    assert all(graph.edge_to_node[path[-1]] == b1 for path in paths)
    assert len({len(path) for path in paths}) == 1


def test_expected_flows_conserve_entry_volume(graph: RoutingGraph) -> None:
    flows, movements = expected_edge_flows(
        graph,
        {"left1A1": 100.0},
        {"left1A1": {"straight": 0.7, "left": 0.15, "right": 0.15}},
    )

    exits = sum(volume for edge_id, volume in flows.items() if edge_id in graph.exit_edges)
    assert exits == pytest.approx(100.0, rel=1e-6)
    assert sum(movements.values()) > 100.0


def _scenario_copy(tmp_path: Path, scenario_name: str) -> tuple[Path, ScenarioConfig]:
    directory = tmp_path / "scenario"
    directory.mkdir()
    shutil.copy(NETWORK_PATH, directory / "network.net.xml")
    shutil.copy(SCENARIO_DIR / "metadata.json", directory / "metadata.json")
    config = load_scenario_config(SCENARIO_DIR / scenario_name)
    return directory, config


def test_generator_writes_reproducible_route_artifacts(tmp_path: Path) -> None:
    directory, config = _scenario_copy(tmp_path, "scenario_s1_balanced_seed_42.yaml")

    first = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=directory,
        seed=config.seed,
        demand_profile=config.traffic.demand_profile,
    ).generate()
    first_bytes = first.route_path.read_bytes()
    second = TrafficDemandGenerator(
        scenario_config=config,
        scenario_dir=directory,
        seed=config.seed,
        demand_profile=config.traffic.demand_profile,
    ).generate()

    assert first.route_hash == second.route_hash
    assert second.route_path.read_bytes() == first_bytes
    metadata = json.loads(first.metadata_path.read_text(encoding="utf-8"))
    assert metadata["routing"] == "turning_ratio_walk"
    assert metadata["turning"]["configured"] == {"straight": 0.7, "left": 0.15, "right": 0.15}
    assert set(metadata["turning"]["realized_movement_counts"]) == {"straight", "left", "right"}
    assert metadata["offered"]["offered_vehicle_count"] == sum(
        metadata["offered"]["offered_by_entry"].values()
    )
    # the checked-in artifact for the same scenario is byte-identical (deterministic seed).
    assert first_bytes == (SCENARIO_DIR / config.route_file).read_bytes()


# ---------------------------------------------------------------------------------------
# Structure of the versioned V1 scenarios (checked-in YAMLs and route artifacts).
# ---------------------------------------------------------------------------------------

SEEDS = (42, 2027, 3253, 4517, 5791)
SCENARIO_FILES = {
    "S1_BALANCED": "scenario_s1_balanced_seed_{seed}.yaml",
    "S2_DIRECTIONAL_PEAK": "scenario_s2_directional_peak_seed_{seed}.yaml",
    "S3_DEMAND_SHIFT": "scenario_s3_demand_shift_seed_{seed}.yaml",
    "S4_LOCAL_SATURATION": "scenario_s4_local_saturation_seed_{seed}.yaml",
}
NOMINAL_APPROACH_CAPACITY_VEH_PER_HOUR = 320.0  # measured B0 discharge per approach in Pilot V1


def metadata_for(profile: str, seed: int = 42) -> dict[str, Any]:
    config = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES[profile].format(seed=seed))
    route_path = SCENARIO_DIR / config.route_file
    metadata_path = route_path.with_name(route_path.name.replace(".rou.xml", ".metadata.json"))
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def pass_shares(metadata: dict[str, Any]) -> dict[str, float]:
    labels = metadata["coverage"]["intersection_labels"]
    shares = metadata["coverage"]["junction_pass_share_by_node"]
    return {labels[node]: share for node, share in shares.items()}


@pytest.mark.parametrize("profile", sorted(SCENARIO_FILES))
def test_all_scenarios_share_timing_and_protocol_turning_ratios(profile: str) -> None:
    for seed in SEEDS:
        config = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES[profile].format(seed=seed))
        assert config.traffic.demand_profile == profile
        assert config.seed == seed
        assert config.simulation.warmup_seconds == 300
        assert config.simulation.measurement_duration_seconds == 3600
        assert config.simulation.step_length == 1.0
        assert config.total_simulation_steps == 3900
        assert config.measurement_start_step == 300
        assert config.measurement_end_step == 3900
        assert config.traffic.turning_ratios == TurningRatiosConfig(
            straight=0.70, left=0.15, right=0.15
        )
        assert config.traffic.uses_turning_ratio_routing


@pytest.mark.parametrize("profile", sorted(SCENARIO_FILES))
def test_versioned_route_artifacts_are_valid_and_seeded(profile: str) -> None:
    from traffic_agents.experiments.route_artifacts import validate_route_artifacts

    route_hashes = set()
    for seed in SEEDS:
        config = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES[profile].format(seed=seed))
        validate_route_artifacts(scenario_config=config, scenario_dir=SCENARIO_DIR)
        route_hashes.add(metadata_for(profile, seed)["route_hash"])
    assert len(route_hashes) == len(SEEDS)


def test_s1_uses_the_full_grid_with_balanced_border_demand() -> None:
    config = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES["S1_BALANCED"].format(seed=42))
    metadata = metadata_for("S1_BALANCED")

    assert {item.entry_edge_id for item in config.traffic.entries} == set(ALL_ENTRIES)
    rates = {item.vehicles_per_hour["MEDIUM"] for item in config.traffic.entries}
    assert len(rates) == 1
    offered_by_entry = metadata["offered"]["offered_by_entry"]
    assert set(offered_by_entry) == set(ALL_ENTRIES)
    assert max(offered_by_entry.values()) - min(offered_by_entry.values()) <= 1
    shares = pass_shares(metadata)
    assert set(shares) == {f"A{index}" for index in range(1, 10)}
    # no unused corners and no single intersection forced into every route
    assert all(0.08 <= share <= 0.15 for share in shares.values()), shares
    realized = metadata["turning"]["realized_movement_proportions"]
    for movement, expected in {"straight": 0.70, "left": 0.15, "right": 0.15}.items():
        assert abs(realized[movement] - expected) <= 0.03
    # provisional S1 intensity must stay well below one approach's nominal capacity
    assert (
        metadata["max_expected_approach_load_veh_per_hour"]
        <= 0.6 * NOMINAL_APPROACH_CAPACITY_VEH_PER_HOUR
    )


def test_s2_offers_about_80_percent_from_the_west_dominant_profile() -> None:
    config = load_scenario_config(
        SCENARIO_DIR / SCENARIO_FILES["S2_DIRECTIONAL_PEAK"].format(seed=42)
    )
    metadata = metadata_for("S2_DIRECTIONAL_PEAK")

    dominant = [item for item in config.traffic.entries if item.group == "dominant"]
    assert {item.entry_edge_id for item in dominant} == {"left0A0", "left1A1", "left2A2"}
    by_group = metadata["offered"]["offered_by_group"]
    dominant_share = by_group["dominant"] / sum(by_group.values())
    assert 0.78 <= dominant_share <= 0.82
    # the dominant demand is offered below entry capacity so it is not starved at the entry
    dominant_rate = dominant[0].vehicles_per_hour["MEDIUM"]
    assert dominant_rate <= 0.8 * NOMINAL_APPROACH_CAPACITY_VEH_PER_HOUR
    counts = metadata["turning"]["realized_movement_counts_by_group"]["dominant"]
    assert counts["left"] > 0 and counts["right"] > 0 and counts["straight"] > counts["left"]
    # corridor traffic is visible: some routes traverse the middle row eastbound (A1B1 -> B1C1)
    route_text = (SCENARIO_DIR / "routes_s2_seed_42.rou.xml").read_text(encoding="utf-8")
    assert "A1B1 B1C1" in route_text


def test_s3_structure_balanced_first_half_then_west_shock_through_a5() -> None:
    config = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES["S3_DEMAND_SHIFT"].format(seed=42))
    s1 = load_scenario_config(SCENARIO_DIR / SCENARIO_FILES["S1_BALANCED"].format(seed=42))
    shock_start = (
        config.simulation.warmup_seconds + config.simulation.measurement_duration_seconds / 2
    )

    assert config.traffic.shock_start_seconds == shock_start == 2100
    assert config.shock_start_measurement_offset_seconds == 1800
    base = [item for item in config.traffic.entries if item.group == "base"]
    shock = [item for item in config.traffic.entries if item.group == "shock"]
    # first half equals the S1 balanced base (same entries, same rates, from t=0)
    assert {item.entry_edge_id for item in base} == set(ALL_ENTRIES)
    assert all(item.begin_seconds == 0 for item in base)
    s1_rates = {item.entry_edge_id: item.vehicles_per_hour for item in s1.traffic.entries}
    assert {item.entry_edge_id: item.vehicles_per_hour for item in base} == s1_rates
    # the shock: one border only, abrupt at 50% of the measurement window, routed through A5
    assert shock
    assert all(item.begin_seconds == shock_start for item in shock)
    assert {item.entry_edge_id for item in shock} <= {"left0A0", "left1A1", "left2A2"}
    assert all(item.via_intersection_id == "A5" for item in shock)
    assert all(item.turning_ratios is not None for item in shock)

    graph = RoutingGraph.from_network(NETWORK_PATH)
    route_text = (SCENARIO_DIR / "routes_s3_seed_42.rou.xml").read_text(encoding="utf-8")
    import xml.etree.ElementTree as ET

    root = ET.fromstring(route_text)
    routes = {route.attrib["id"]: route.attrib["edges"].split() for route in root.findall("route")}
    shock_vehicles = [v for v in root.findall("vehicle") if v.attrib["id"].startswith("shock_")]
    assert shock_vehicles
    assert all(float(v.attrib["depart"]) >= shock_start for v in shock_vehicles)
    assert all(
        any(graph.edge_to_node[edge_id] == "B1" for edge_id in routes[v.attrib["route"]])
        for v in shock_vehicles
    )
    first_half = [v for v in root.findall("vehicle") if float(v.attrib["depart"]) < shock_start]
    assert first_half
    assert not any(v.attrib["id"].startswith("shock_") for v in first_half)
    # the base phase is not structurally saturated: S3 base demand equals the provisional S1 level
    assert (
        metadata_for("S1_BALANCED")["max_expected_approach_load_veh_per_hour"]
        <= 0.6 * NOMINAL_APPROACH_CAPACITY_VEH_PER_HOUR
    )


def test_s3_shock_time_must_be_at_half_of_the_measurement_window() -> None:
    payload = load_scenario_config(
        SCENARIO_DIR / SCENARIO_FILES["S3_DEMAND_SHIFT"].format(seed=42)
    ).model_dump(mode="json")
    payload["traffic"]["shock_start_seconds"] = 1950  # 50% of TOTAL time, not of measurement

    with pytest.raises(ValueError, match="50% of the measurement"):
        ScenarioConfig.model_validate(payload)

    payload["traffic"]["shock_start_seconds"] = None
    with pytest.raises(ValueError, match=r"requires traffic\.shock_start_seconds"):
        ScenarioConfig.model_validate(payload)


def test_shock_is_rejected_outside_s3() -> None:
    payload = load_scenario_config(
        SCENARIO_DIR / SCENARIO_FILES["S1_BALANCED"].format(seed=42)
    ).model_dump(mode="json")
    payload["traffic"]["shock_start_seconds"] = 2100

    with pytest.raises(ValueError, match="only valid for S3"):
        ScenarioConfig.model_validate(payload)


def test_s4_hotspot_concentrates_traffic_around_a5() -> None:
    metadata = metadata_for("S4_LOCAL_SATURATION")
    config = load_scenario_config(
        SCENARIO_DIR / SCENARIO_FILES["S4_LOCAL_SATURATION"].format(seed=42)
    )

    hotspot = [item for item in config.traffic.entries if item.group == "hotspot"]
    assert hotspot
    assert all(item.via_intersection_id == "A5" for item in hotspot)
    shares = pass_shares(metadata)
    neighbours = ("A2", "A4", "A6", "A8")
    corners = ("A1", "A3", "A7", "A9")
    # congestion is concentrated around A5 ...
    assert shares["A5"] >= 0.20
    assert shares["A5"] >= 1.5 * max(shares[node] for node in neighbours)
    # ... and propagates to A2/A4/A6/A8 rather than to the corners.
    assert min(shares[node] for node in neighbours) > max(shares[node] for node in corners)
    loads = metadata["expected_approach_load_veh_per_hour"]
    a5_incoming = [loads[edge] for edge in ("A1B1", "C1B1", "B0B1", "B2B1")]
    assert min(a5_incoming) > loads["left1A1"]
    assert metadata["max_expected_approach_load_veh_per_hour"] == pytest.approx(max(a5_incoming))
    # every hotspot vehicle traverses A5 (checked on the generated route file).
    import xml.etree.ElementTree as ET

    root = ET.parse(SCENARIO_DIR / "routes_s4_seed_42.rou.xml").getroot()
    routes = {route.attrib["id"]: route.attrib["edges"].split() for route in root.findall("route")}
    hotspot_vehicles = [v for v in root.findall("vehicle") if v.attrib["id"].startswith("hotspot_")]
    assert hotspot_vehicles
    assert all(
        any(edge_id.endswith("B1") for edge_id in routes[v.attrib["route"]])
        for v in hotspot_vehicles
    )
