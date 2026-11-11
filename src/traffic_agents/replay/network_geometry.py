"""Geometria estática de uma rede SUMO, lida diretamente de ``network.net.xml``.

A ferramenta de replay precisa das coordenadas das junções (enquadramento da câmera, rótulos de
interseção) e do mapeamento dos rótulos de interseção do projeto (``A1``..``A9``) para os ids de
junção do SUMO (``A0``..``C2``). Ambos são derivados dos arquivos congelados de rede e cenário,
nunca fixados no código.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from traffic_agents.config import ScenarioConfig


class NetworkGeometryError(ValueError):
    """Lançada quando o arquivo de rede não consegue fornecer a geometria solicitada."""


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
    """Mapeia cada rótulo de interseção (``A5``) para seu id de junção do SUMO (``B1``).

    Uma junção é onde termina toda lane de entrada da interseção.
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
