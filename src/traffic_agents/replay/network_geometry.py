"""Static geometry of a SUMO network, read straight from ``network.net.xml``.

The replay tool needs junction coordinates (camera framing, intersection labels) and the
mapping from the project's intersection labels (``A1``..``A9``) to SUMO junction ids
(``A0``..``C2``). Both are derived from the frozen network and scenario files, never hard-coded.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from traffic_agents.config import ScenarioConfig


class NetworkGeometryError(ValueError):
    """Raised when the network file cannot provide the requested geometry."""


@dataclass(frozen=True)
class NetworkGeometry:
    junctions: Mapping[str, tuple[float, float]]
    edges: Mapping[str, tuple[str, str]]

    def junction_position(self, junction_id: str) -> tuple[float, float]:
        try:
            return self.junctions[junction_id]
        except KeyError:
            msg = f"unknown junction id: {junction_id}"
            raise NetworkGeometryError(msg) from None

    def edge_endpoints(self, edge_id: str) -> tuple[str, str]:
        try:
            return self.edges[edge_id]
        except KeyError:
            msg = f"unknown edge id: {edge_id}"
            raise NetworkGeometryError(msg) from None

    @property
    def edge_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.edges))


def load_network_geometry(network_path: Path) -> NetworkGeometry:
    try:
        root = ET.parse(network_path).getroot()
    except (ET.ParseError, OSError) as exc:
        msg = f"cannot read network file: {network_path}"
        raise NetworkGeometryError(msg) from exc

    junctions: dict[str, tuple[float, float]] = {}
    for junction in root.findall("junction"):
        if junction.attrib.get("type") == "internal":
            continue
        junctions[str(junction.attrib["id"])] = (
            float(junction.attrib["x"]),
            float(junction.attrib["y"]),
        )
    edges: dict[str, tuple[str, str]] = {}
    for edge in root.findall("edge"):
        if edge.attrib.get("function") == "internal":
            continue
        edges[str(edge.attrib["id"])] = (str(edge.attrib["from"]), str(edge.attrib["to"]))
    if not junctions or not edges:
        msg = f"network has no junctions or edges: {network_path}"
        raise NetworkGeometryError(msg)
    return NetworkGeometry(junctions=junctions, edges=edges)


def intersection_junctions(
    scenario_config: ScenarioConfig,
    geometry: NetworkGeometry,
) -> dict[str, str]:
    """Map each intersection label (``A5``) to its SUMO junction id (``B1``).

    A junction is where every incoming lane of the intersection ends.
    """

    mapping: dict[str, str] = {}
    for intersection in scenario_config.intersections:
        targets = {
            geometry.edge_endpoints(lane_id.rsplit("_", maxsplit=1)[0])[1]
            for lane_id in intersection.incoming_lanes
        }
        if len(targets) != 1:
            msg = (
                f"incoming lanes of {intersection.intersection_id} do not end in a single "
                f"junction: {sorted(targets)}"
            )
            raise NetworkGeometryError(msg)
        mapping[str(intersection.intersection_id)] = next(iter(targets))
    return mapping
