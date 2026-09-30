from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from traffic_agents.config import DemandLevel, DemandProfileId, ScenarioConfig
from traffic_agents.config.scenario import FlowDefinitionConfig
from traffic_agents.experiments.run_invariants import (
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
)
from traffic_agents.simulation.route_walk import (
    GeneratedVehicle,
    RoutingGraph,
    effective_ratios,
    expected_edge_flows,
    generate_vehicles,
    resolve_via_node,
    summarize_vehicles,
)
from traffic_agents.simulation.sumo_environment import SumoEnvironmentInfo, detect_sumo_environment

GENERATED_COMMENT_PATTERN = re.compile(
    r"\n?<!-- generated on .*?</duarouterConfiguration>\s*-->\s*",
    re.DOTALL,
)
PASSENGER_VEHICLE_VISUAL_STYLE: Mapping[str, str] = {
    "color": "#2f80ed",
    "guiShape": "passenger",
    "height": "1.50",
    "length": "5.00",
    "width": "1.80",
}
DEFAULT_FLOW_COLOR = "#2f80ed"
TRAFFIC_DEMAND_GENERATOR_VERSION = "2.0.0"
ENTRY_GROUP_COLORS: Mapping[str, str] = {
    "base": "#2f80ed",
    "dominant": "#1971c2",
    "residual": "#74c0fc",
    "shock": "#e03131",
    "hotspot": "#f59f00",
}
FLOW_VISUAL_COLORS: Mapping[str, str] = {
    "east_to_north_turn": "#ff6b6b",
    "east_to_south_turn": "#f59f00",
    "east_to_west_middle": "#e03131",
    "north_to_east_turn": "#20c997",
    "north_to_south_middle": "#2f9e44",
    "north_to_west_turn": "#94d82d",
    "south_to_east_turn": "#748ffc",
    "south_to_north_middle": "#364fc7",
    "south_to_west_turn": "#15aabf",
    "west_to_east_middle": "#1971c2",
    "west_to_north_turn": "#9c36b5",
    "west_to_south_turn": "#d6336c",
}


@dataclass(frozen=True)
class GeneratedTrafficDemandInfo:
    route_path: Path
    metadata_path: Path
    seed: int
    demand_profile: DemandProfileId
    config_hash: str
    scenario_hash: str
    route_hash: str
    flow_count: int


@dataclass(frozen=True)
class SelectedFlow:
    flow_id: str
    origin_edge_id: str
    destination_edge_id: str
    begin_seconds: float
    end_seconds: float
    vehicles_per_hour: float


class TrafficDemandGenerator:
    def __init__(
        self,
        *,
        scenario_config: ScenarioConfig,
        scenario_dir: Path,
        seed: int,
        demand_profile: DemandProfileId,
        sumo_info: SumoEnvironmentInfo | None = None,
    ) -> None:
        if seed < 0:
            msg = "seed must be non-negative"
            raise ValueError(msg)
        if scenario_config.traffic.demand_profile != demand_profile:
            msg = (
                "demand_profile must match scenario_config.traffic.demand_profile: "
                f"{scenario_config.traffic.demand_profile}"
            )
            raise ValueError(msg)

        self._scenario_config = scenario_config
        self._scenario_dir = scenario_dir
        self._seed = seed
        self._demand_profile = demand_profile
        self._sumo_info = sumo_info

    def generate(self) -> GeneratedTrafficDemandInfo:
        if self._scenario_config.traffic.uses_turning_ratio_routing:
            return self._generate_turning_ratio_demand()
        sumo_info = self._sumo_info or detect_sumo_environment()
        route_path = self._scenario_dir / self._scenario_config.route_file
        metadata_path = _metadata_path_for(route_path)
        network_path = self._scenario_dir / self._scenario_config.network_file
        route_path.parent.mkdir(parents=True, exist_ok=True)
        selected_flows = self._selected_flows()
        config_hash = self._config_hash(selected_flows)
        scenario_hash = self._scenario_hash()

        with tempfile.TemporaryDirectory() as temp_dir:
            flow_input_path = Path(temp_dir) / "demand.flows.xml"
            self._write_flow_input(flow_input_path, selected_flows)
            self._run_duarouter(sumo_info, network_path, flow_input_path, route_path)

        _remove_duarouter_alternatives(route_path)
        normalize_generated_route_header(route_path)
        apply_visual_vehicle_style(route_path)
        _validate_route_file(route_path)
        route_hash = _file_sha256(route_path)
        network_hash = _file_sha256(network_path)
        self._write_metadata(
            metadata_path,
            selected_flows,
            config_hash,
            scenario_hash,
            route_hash,
            network_hash,
        )

        return GeneratedTrafficDemandInfo(
            route_path=route_path,
            metadata_path=metadata_path,
            seed=self._seed,
            demand_profile=self._demand_profile,
            config_hash=config_hash,
            scenario_hash=scenario_hash,
            route_hash=route_hash,
            flow_count=len(selected_flows),
        )

    def _generate_turning_ratio_demand(self) -> GeneratedTrafficDemandInfo:
        config = self._scenario_config
        traffic = config.traffic
        route_path = self._scenario_dir / config.route_file
        metadata_path = _metadata_path_for(route_path)
        network_path = self._scenario_dir / config.network_file
        route_path.parent.mkdir(parents=True, exist_ok=True)

        graph = RoutingGraph.from_network(network_path)
        via_nodes = _via_node_lookup(self._scenario_dir)
        vehicles = generate_vehicles(
            graph=graph,
            entries=traffic.entries,
            demand_level=traffic.demand_level,
            default_ratios=traffic.turning_ratios,
            seed=self._seed,
            via_nodes=via_nodes,
        )
        _write_vehicle_routes(route_path, vehicles)
        _validate_route_file(route_path)

        config_hash = route_generator_config_sha256(config)
        scenario_hash = self._scenario_hash()
        route_hash = _file_sha256(route_path)
        network_hash = _file_sha256(network_path)
        summary = summarize_vehicles(
            graph=graph,
            vehicles=vehicles,
            measurement_start_seconds=float(config.warmup_seconds),
            measurement_end_seconds=float(config.total_duration_seconds),
        )
        expected_flows: dict[str, float] = {}
        expected_movements: dict[str, float] = {}
        for entry in traffic.entries:
            entry_flows, entry_movements = expected_edge_flows(
                graph,
                {entry.entry_edge_id: entry.rate_for(traffic.demand_level)},
                {entry.entry_edge_id: effective_ratios(entry, traffic.turning_ratios)},
                via_node_by_entry={entry.entry_edge_id: resolve_via_node(entry, via_nodes)},
            )
            for edge_id, volume in entry_flows.items():
                expected_flows[edge_id] = expected_flows.get(edge_id, 0.0) + volume
            for movement, volume in entry_movements.items():
                expected_movements[movement] = expected_movements.get(movement, 0.0) + volume
        approach_loads = {
            edge_id: round(volume, 3)
            for edge_id, volume in sorted(expected_flows.items())
            if edge_id not in graph.exit_edges
        }
        total_expected = sum(expected_movements.values())
        payload = {
            "scenario_id": config.scenario_id,
            "route_file": config.route_file.as_posix(),
            "seed": self._seed,
            "demand_profile": self._demand_profile,
            "demand_level": traffic.demand_level,
            "routing": "turning_ratio_walk",
            "turning_ratios": traffic.turning_ratios.model_dump(),
            "schedule": [window.model_dump(mode="json") for window in traffic.schedule],
            "shock_start_seconds": traffic.shock_start_seconds,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "generator_version": TRAFFIC_DEMAND_GENERATOR_VERSION,
            "config_hash": config_hash,
            "scenario_hash": scenario_hash,
            "route_hash": route_hash,
            "network_hash": network_hash,
            "entries": [
                {
                    "demand_id": entry.demand_id,
                    "entry_edge_id": entry.entry_edge_id,
                    "group": entry.group,
                    "begin_seconds": float(entry.begin_seconds),
                    "end_seconds": float(entry.end_seconds),
                    "vehicles_per_hour": entry.rate_for(traffic.demand_level),
                    "turning_ratios": effective_ratios(entry, traffic.turning_ratios),
                    "via_intersection_id": entry.via_intersection_id,
                }
                for entry in traffic.entries
            ],
            "turning": {
                "configured": traffic.turning_ratios.model_dump(),
                "expected_movement_proportions": {
                    movement: (volume / total_expected if total_expected else 0.0)
                    for movement, volume in sorted(expected_movements.items())
                },
                "realized_movement_counts": summary["realized_movement_counts"],
                "realized_movement_proportions": summary["realized_movement_proportions"],
                "realized_movement_counts_by_group": summary["realized_movement_counts_by_group"],
            },
            "offered": {
                "offered_vehicle_count": summary["offered_vehicle_count"],
                "offered_in_measurement_window": summary["offered_in_measurement_window"],
                "offered_by_entry": summary["offered_by_entry"],
                "offered_by_group": summary["offered_by_group"],
                "offered_by_demand": summary["offered_by_demand"],
            },
            "coverage": {
                "junction_passes_by_node": summary["junction_passes_by_node"],
                "junction_pass_share_by_node": summary["junction_pass_share_by_node"],
                "intersection_labels": _intersection_labels(self._scenario_dir),
            },
            "expected_approach_load_veh_per_hour": approach_loads,
            "max_expected_approach_load_veh_per_hour": max(approach_loads.values(), default=0.0),
        }
        metadata_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GeneratedTrafficDemandInfo(
            route_path=route_path,
            metadata_path=metadata_path,
            seed=self._seed,
            demand_profile=self._demand_profile,
            config_hash=config_hash,
            scenario_hash=scenario_hash,
            route_hash=route_hash,
            flow_count=len(traffic.entries),
        )

    def _selected_flows(self) -> tuple[SelectedFlow, ...]:
        return tuple(
            _select_flow(flow, self._scenario_config.traffic.demand_level)
            for flow in self._scenario_config.traffic.flows
        )

    def _write_flow_input(
        self,
        flow_input_path: Path,
        selected_flows: tuple[SelectedFlow, ...],
    ) -> None:
        root = ET.Element("routes")
        ET.SubElement(
            root,
            "vType",
            {
                "id": "passenger",
                "vClass": "passenger",
                "accel": "2.6",
                "decel": "4.5",
                "sigma": "0.5",
                "length": PASSENGER_VEHICLE_VISUAL_STYLE["length"],
                "width": PASSENGER_VEHICLE_VISUAL_STYLE["width"],
                "height": PASSENGER_VEHICLE_VISUAL_STYLE["height"],
                "minGap": "2.5",
                "maxSpeed": "13.89",
                "color": PASSENGER_VEHICLE_VISUAL_STYLE["color"],
                "guiShape": PASSENGER_VEHICLE_VISUAL_STYLE["guiShape"],
            },
        )

        for flow in selected_flows:
            ET.SubElement(
                root,
                "flow",
                {
                    "id": flow.flow_id,
                    "type": "passenger",
                    "begin": _format_number(flow.begin_seconds),
                    "end": _format_number(flow.end_seconds),
                    "vehsPerHour": _format_number(flow.vehicles_per_hour),
                    "from": flow.origin_edge_id,
                    "to": flow.destination_edge_id,
                    "departLane": "best",
                    "departSpeed": "max",
                    "color": _flow_color(flow.flow_id),
                },
            )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        tree.write(flow_input_path, encoding="utf-8", xml_declaration=True)

    def _run_duarouter(
        self,
        sumo_info: SumoEnvironmentInfo,
        network_path: Path,
        flow_input_path: Path,
        route_path: Path,
    ) -> None:
        duarouter_binary = _sumo_tool_binary(sumo_info, "duarouter")
        subprocess.run(
            [
                str(duarouter_binary),
                "--net-file",
                str(network_path),
                "--route-files",
                str(flow_input_path),
                "--output-file",
                str(route_path),
                "--keep-flows",
                "--seed",
                str(self._seed),
                "--no-step-log",
            ],
            check=True,
            env=_subprocess_env(sumo_info),
        )

    def _config_hash(self, selected_flows: tuple[SelectedFlow, ...]) -> str:
        payload = {
            "scenario": {
                key: value
                for key, value in self._scenario_config.model_dump(mode="json").items()
                if key not in {"controller_id", "communication", "tracing"}
            },
            "seed": self._seed,
            "demand_profile": self._demand_profile,
            "selected_flows": [flow.__dict__ for flow in selected_flows],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _scenario_hash(self) -> str:
        return route_artifact_scenario_sha256(self._scenario_config)

    def _write_metadata(
        self,
        metadata_path: Path,
        selected_flows: tuple[SelectedFlow, ...],
        config_hash: str,
        scenario_hash: str,
        route_hash: str,
        network_hash: str,
    ) -> None:
        payload = {
            "scenario_id": self._scenario_config.scenario_id,
            "route_file": self._scenario_config.route_file.as_posix(),
            "seed": self._seed,
            "demand_profile": self._demand_profile,
            "demand_level": self._scenario_config.traffic.demand_level,
            "turning_ratios": self._scenario_config.traffic.turning_ratios.model_dump(),
            "schedule": [
                window.model_dump(mode="json") for window in self._scenario_config.traffic.schedule
            ],
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "generator_version": TRAFFIC_DEMAND_GENERATOR_VERSION,
            "config_hash": config_hash,
            "scenario_hash": scenario_hash,
            "route_hash": route_hash,
            "network_hash": network_hash,
            "flows": [flow.__dict__ for flow in selected_flows],
        }
        metadata_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _write_vehicle_routes(route_path: Path, vehicles: tuple[GeneratedVehicle, ...]) -> None:
    root = ET.Element("routes")
    ET.SubElement(
        root,
        "vType",
        {
            "id": "passenger",
            "vClass": "passenger",
            "accel": "2.6",
            "decel": "4.5",
            "sigma": "0.5",
            "length": PASSENGER_VEHICLE_VISUAL_STYLE["length"],
            "width": PASSENGER_VEHICLE_VISUAL_STYLE["width"],
            "height": PASSENGER_VEHICLE_VISUAL_STYLE["height"],
            "minGap": "2.5",
            "maxSpeed": "13.89",
            "color": PASSENGER_VEHICLE_VISUAL_STYLE["color"],
            "guiShape": PASSENGER_VEHICLE_VISUAL_STYLE["guiShape"],
        },
    )
    route_ids: dict[tuple[str, ...], str] = {}
    for vehicle in vehicles:
        if vehicle.route not in route_ids:
            route_ids[vehicle.route] = f"r{len(route_ids)}"
            ET.SubElement(
                root,
                "route",
                {"id": route_ids[vehicle.route], "edges": " ".join(vehicle.route)},
            )
    for vehicle in vehicles:
        ET.SubElement(
            root,
            "vehicle",
            {
                "id": vehicle.vehicle_id,
                "type": "passenger",
                "route": route_ids[vehicle.route],
                "depart": f"{vehicle.depart_seconds:.2f}",
                "departLane": "best",
                "departSpeed": "max",
                "color": ENTRY_GROUP_COLORS.get(vehicle.group, DEFAULT_FLOW_COLOR),
            },
        )
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(route_path, encoding="utf-8", xml_declaration=True)


def _via_node_lookup(scenario_dir: Path) -> dict[str, str]:
    metadata_path = scenario_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    traffic_light_ids = payload.get("traffic_light_ids", {})
    if not isinstance(traffic_light_ids, dict):
        return {}
    return {str(label): str(tls_id) for label, tls_id in traffic_light_ids.items()}


def _intersection_labels(scenario_dir: Path) -> dict[str, str]:
    metadata_path = scenario_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    traffic_light_ids = payload.get("traffic_light_ids", {})
    if not isinstance(traffic_light_ids, dict):
        return {}
    return {str(tls_id): str(label) for label, tls_id in sorted(traffic_light_ids.items())}


def normalize_generated_route_header(route_path: Path) -> None:
    content = route_path.read_text(encoding="utf-8")
    normalized = GENERATED_COMMENT_PATTERN.sub(
        "\n<!-- generated by Eclipse SUMO duarouter via TrafficDemandGenerator -->\n\n",
        content,
        count=1,
    )
    route_path.write_text(normalized, encoding="utf-8")


def apply_visual_vehicle_style(route_path: Path) -> None:
    tree = ET.parse(route_path)
    root = tree.getroot()
    passenger_type = root.find("./vType[@id='passenger']")
    if passenger_type is None:
        passenger_type = ET.Element("vType", {"id": "passenger", "vClass": "passenger"})
        root.insert(0, passenger_type)

    for attribute, value in PASSENGER_VEHICLE_VISUAL_STYLE.items():
        passenger_type.set(attribute, value)
    for flow in root.findall("flow"):
        flow_color = _flow_color(flow.attrib.get("id", ""))
        flow.set("color", flow_color)
        route = flow.find("route")
        if route is not None:
            route.set("color", flow_color)

    ET.indent(tree, space="    ")
    tree.write(route_path, encoding="utf-8", xml_declaration=True)


def _select_flow(flow: FlowDefinitionConfig, demand_level: DemandLevel) -> SelectedFlow:
    return SelectedFlow(
        flow_id=flow.flow_id,
        origin_edge_id=flow.origin_edge_id,
        destination_edge_id=flow.destination_edge_id,
        begin_seconds=float(flow.begin_seconds),
        end_seconds=float(flow.end_seconds),
        vehicles_per_hour=flow.rate_for(demand_level),
    )


def _validate_route_file(route_path: Path) -> None:
    tree = ET.parse(route_path)
    root = tree.getroot()
    route_elements = root.findall("vehicle") + root.findall("flow")
    if not route_elements:
        msg = f"Generated route file is empty: {route_path}"
        raise ValueError(msg)


def _metadata_path_for(route_path: Path) -> Path:
    if route_path.name.endswith(".rou.xml"):
        return route_path.with_name(route_path.name.replace(".rou.xml", ".metadata.json"))
    return route_path.with_suffix(".metadata.json")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _remove_duarouter_alternatives(route_path: Path) -> None:
    alternatives_path = route_path.with_suffix(".alt.xml")
    if alternatives_path.exists():
        alternatives_path.unlink()


def _sumo_tool_binary(sumo_info: SumoEnvironmentInfo, tool_name: str) -> Path:
    if sumo_info.sumo_home is None:
        msg = f"SUMO_HOME is required to locate {tool_name}"
        raise ValueError(msg)

    candidates = [
        sumo_info.sumo_home / "bin" / tool_name,
        sumo_info.sumo_home / "bin" / f"{tool_name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    msg = f"SUMO tool not found: {tool_name}"
    raise FileNotFoundError(msg)


def _subprocess_env(sumo_info: SumoEnvironmentInfo) -> Mapping[str, str]:
    env = os.environ.copy()
    if sumo_info.sumo_home is not None:
        env["SUMO_HOME"] = str(sumo_info.sumo_home)
    return env


def _format_number(value: float) -> str:
    return f"{value:g}"


def _flow_color(flow_id: str) -> str:
    if flow_id in FLOW_VISUAL_COLORS:
        return FLOW_VISUAL_COLORS[flow_id]
    for known_flow_id, color in FLOW_VISUAL_COLORS.items():
        if flow_id.endswith(known_flow_id):
            return color
    return DEFAULT_FLOW_COLOR
