"""Roteamento determinístico com seed por razões de conversão para demanda de entrada de borda.

Os veículos entram na rede em uma aresta de entrada de borda e, em cada junção semaforizada,
escolhem ``straight``/``left``/``right`` com as razões de conversão configuradas até
alcançarem uma aresta de saída de borda. Apenas movimentos legais da rede SUMO (conexões com
``dir`` em ``s``, ``l``, ``r``; retornos em U nunca são criados) são considerados, portanto
conversões ilegais nunca são forçadas para satisfazer uma razão.

Toda a aleatoriedade vem de instâncias de ``random.Random`` com seed derivada de
``(seed, demand_id)``; a mesma seed e configuração sempre reproduzem rotas e horários de
partida idênticos.
"""

from __future__ import annotations

import hashlib
import math
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Literal, get_args

from traffic_agents.config.scenario import (
    DemandLevel,
    EntryDemandConfig,
    TurningRatiosConfig,
)

Movement = Literal["straight", "left", "right"]
MOVEMENTS: tuple[Movement, ...] = get_args(Movement)
_DIRECTION_TO_MOVEMENT: Mapping[str, Movement] = {
    "s": "straight",
    "l": "left",
    "r": "right",
}
MAX_ROUTE_JUNCTIONS = 64


class RouteWalkError(ValueError):
    """Lançada quando o roteamento por razões de conversão não pode ser construído a partir da rede
    ou da config.
    """


@dataclass(frozen=True)
class RoutingGraph:
    """Grafo de movimentos legais extraído de um arquivo de rede SUMO."""

    successors: Mapping[str, Mapping[Movement, str]]
    entry_edges: frozenset[str]
    exit_edges: frozenset[str]
    edge_to_node: Mapping[str, str]
    signalized_nodes: frozenset[str]

    @classmethod
    def from_network(cls, network_path: Path) -> RoutingGraph:
        root = ET.parse(network_path).getroot()
        node_types = {
            str(junction.attrib["id"]): str(junction.attrib.get("type", ""))
            for junction in root.findall("junction")
            if not str(junction.attrib["id"]).startswith(":")
        }
        edges = {
            str(edge.attrib["id"]): (str(edge.attrib["from"]), str(edge.attrib["to"]))
            for edge in root.findall("edge")
            if not str(edge.attrib["id"]).startswith(":") and "from" in edge.attrib
        }
        successors: dict[str, dict[Movement, str]] = defaultdict(dict)
        for connection in root.findall("connection"):
            source = str(connection.attrib["from"])
            if source.startswith(":") or source not in edges:
                continue
            movement = _DIRECTION_TO_MOVEMENT.get(str(connection.attrib.get("dir", "")))
            if movement is None:
                continue
            target = str(connection.attrib["to"])
            if target in edges:
                successors[source][movement] = target
        entry_edges = frozenset(
            edge_id for edge_id, (start, _) in edges.items() if node_types.get(start) == "dead_end"
        )
        exit_edges = frozenset(
            edge_id for edge_id, (_, end) in edges.items() if node_types.get(end) == "dead_end"
        )
        if not entry_edges or not exit_edges:
            msg = f"network has no border entry/exit edges: {network_path}"
            raise RouteWalkError(msg)
        return cls(
            successors={edge_id: dict(options) for edge_id, options in successors.items()},
            entry_edges=entry_edges,
            exit_edges=exit_edges,
            edge_to_node={edge_id: end for edge_id, (_, end) in edges.items()},
            signalized_nodes=frozenset(
                node_id for node_id, node_type in node_types.items() if node_type == "traffic_light"
            ),
        )

    def options(self, edge_id: str) -> Mapping[Movement, str]:
        return self.successors.get(edge_id, {})

    def movement_between(self, edge_id: str, next_edge_id: str) -> Movement:
        for movement, target in self.options(edge_id).items():
            if target == next_edge_id:
                return movement
        msg = f"no legal movement from {edge_id} to {next_edge_id}"
        raise RouteWalkError(msg)


@dataclass(frozen=True)
class GeneratedVehicle:
    vehicle_id: str
    demand_id: str
    entry_edge_id: str
    group: str
    depart_seconds: float
    route: tuple[str, ...]


def entry_rng(seed: int, demand_id: str) -> random.Random:
    digest = hashlib.sha256(f"{int(seed)}|{demand_id}".encode()).hexdigest()
    return random.Random(int(digest, 16))


def effective_ratios(
    entry: EntryDemandConfig,
    default_ratios: TurningRatiosConfig,
) -> dict[Movement, float]:
    ratios = entry.turning_ratios or default_ratios
    return {
        "straight": float(ratios.straight),
        "left": float(ratios.left),
        "right": float(ratios.right),
    }


def shortest_paths_to_node(
    graph: RoutingGraph,
    entry_edge_id: str,
    via_node_id: str,
) -> tuple[tuple[str, ...], ...]:
    """Todos os caminhos legais mais curtos da entrada até uma aproximação de ``via_node_id``.

    Um caminho termina na primeira aresta cujo nó final é ``via_node_id``. Os resultados são
    ordenados para que a escolha entre caminhos igualmente curtos seja determinística.
    """

    if entry_edge_id not in graph.entry_edges:
        msg = f"not a border entry edge: {entry_edge_id}"
        raise RouteWalkError(msg)
    frontier: list[tuple[str, ...]] = [(entry_edge_id,)]
    visited = {entry_edge_id}
    for _ in range(MAX_ROUTE_JUNCTIONS):
        found = sorted(path for path in frontier if graph.edge_to_node.get(path[-1]) == via_node_id)
        if found:
            return tuple(found)
        following: list[tuple[str, ...]] = []
        level_visited: set[str] = set()
        for path in frontier:
            if path[-1] in graph.exit_edges:
                continue
            options = graph.options(path[-1])
            for movement in MOVEMENTS:
                target = options.get(movement)
                if target is None or target in visited:
                    continue
                level_visited.add(target)
                following.append((*path, target))
        visited |= level_visited
        frontier = following
        if not frontier:
            break
    msg = f"no legal path from {entry_edge_id} to intersection node {via_node_id}"
    raise RouteWalkError(msg)


def sample_route(
    graph: RoutingGraph,
    entry_edge_id: str,
    ratios: Mapping[Movement, float],
    rng: random.Random,
    via_node_id: str | None = None,
) -> tuple[str, ...]:
    """Sorteia uma rota de ``entry_edge_id`` até uma aresta de saída de borda."""

    if entry_edge_id not in graph.entry_edges:
        msg = f"not a border entry edge: {entry_edge_id}"
        raise RouteWalkError(msg)
    route = [entry_edge_id]
    if via_node_id is not None:
        candidates = shortest_paths_to_node(graph, entry_edge_id, via_node_id)
        route = list(candidates[rng.randrange(len(candidates))])
    current = route[-1]
    for _ in range(MAX_ROUTE_JUNCTIONS):
        if current in graph.exit_edges:
            return tuple(route)
        options = graph.options(current)
        legal = [movement for movement in MOVEMENTS if movement in options]
        weights = [max(float(ratios.get(movement, 0.0)), 0.0) for movement in legal]
        total = sum(weights)
        if not legal or total <= 0:
            msg = f"no legal positive-probability movement at edge {current}"
            raise RouteWalkError(msg)
        draw = rng.random() * total
        chosen = legal[-1]
        cumulative = 0.0
        for movement, weight in zip(legal, weights, strict=True):
            cumulative += weight
            if draw < cumulative:
                chosen = movement
                break
        current = options[chosen]
        route.append(current)
    msg = f"route from {entry_edge_id} exceeded {MAX_ROUTE_JUNCTIONS} junctions"
    raise RouteWalkError(msg)


def route_movements(graph: RoutingGraph, route: Sequence[str]) -> tuple[Movement, ...]:
    return tuple(
        graph.movement_between(edge_id, next_edge_id) for edge_id, next_edge_id in pairwise(route)
    )


def departure_times(
    *,
    begin_seconds: float,
    end_seconds: float,
    vehicles_per_hour: float,
    rng: random.Random,
) -> tuple[float, ...]:
    """Partidas uniformemente espaçadas (semântica ``vehsPerHour`` do SUMO) com fase definida por
    seed.
    """

    if vehicles_per_hour <= 0:
        return ()
    count = math.floor((end_seconds - begin_seconds) * vehicles_per_hour / 3600.0 + 1e-9)
    period = 3600.0 / vehicles_per_hour
    phase = rng.random()
    return tuple(round(begin_seconds + (index + phase) * period, 2) for index in range(count))


def generate_vehicles(
    *,
    graph: RoutingGraph,
    entries: Iterable[EntryDemandConfig],
    demand_level: DemandLevel,
    default_ratios: TurningRatiosConfig,
    seed: int,
    via_nodes: Mapping[str, str] | None = None,
) -> tuple[GeneratedVehicle, ...]:
    vehicles: list[GeneratedVehicle] = []
    for entry in entries:
        rng = entry_rng(seed, entry.demand_id)
        times = departure_times(
            begin_seconds=float(entry.begin_seconds),
            end_seconds=float(entry.end_seconds),
            vehicles_per_hour=entry.rate_for(demand_level),
            rng=rng,
        )
        ratios = effective_ratios(entry, default_ratios)
        via_node_id = resolve_via_node(entry, via_nodes)
        for index, depart in enumerate(times):
            vehicles.append(
                GeneratedVehicle(
                    vehicle_id=f"{entry.demand_id}.{index}",
                    demand_id=entry.demand_id,
                    entry_edge_id=entry.entry_edge_id,
                    group=entry.group,
                    depart_seconds=depart,
                    route=sample_route(graph, entry.entry_edge_id, ratios, rng, via_node_id),
                )
            )
    vehicles.sort(key=lambda vehicle: (vehicle.depart_seconds, vehicle.vehicle_id))
    return tuple(vehicles)


def resolve_via_node(
    entry: EntryDemandConfig,
    via_nodes: Mapping[str, str] | None,
) -> str | None:
    if entry.via_intersection_id is None:
        return None
    label = entry.via_intersection_id
    if via_nodes is not None and label in via_nodes:
        return via_nodes[label]
    if via_nodes is not None and label not in via_nodes.values():
        msg = f"unknown via_intersection_id for demand {entry.demand_id}: {label}"
        raise RouteWalkError(msg)
    return label


def expected_edge_flows(
    graph: RoutingGraph,
    entry_rates: Mapping[str, float],
    ratios_by_entry: Mapping[str, Mapping[Movement, float]],
    *,
    via_node_by_entry: Mapping[str, str | None] | None = None,
    max_steps: int = 80,
) -> tuple[dict[str, float], dict[Movement, float]]:
    """Veículos/hora esperados em cada aresta e volume esperado de movimentos (cadeia de Markov).

    Entradas com nó intermediário (via) primeiro seguem os caminhos mais curtos, escolhidos
    uniformemente, até ele.
    """

    flows: dict[str, float] = defaultdict(float)
    movement_volume: dict[Movement, float] = defaultdict(float)
    for entry_edge_id, rate in entry_rates.items():
        ratios = ratios_by_entry[entry_edge_id]
        via_node_id = (via_node_by_entry or {}).get(entry_edge_id)
        current: dict[str, float] = {entry_edge_id: float(rate)}
        if via_node_id is not None:
            paths = shortest_paths_to_node(graph, entry_edge_id, via_node_id)
            share = float(rate) / len(paths)
            for path in paths:
                for edge_id, next_edge_id in pairwise(path):
                    flows[edge_id] += share
                    movement_volume[graph.movement_between(edge_id, next_edge_id)] += share
            current = defaultdict(float)
            for path in paths:
                current[path[-1]] += share
        for _ in range(max_steps):
            following: dict[str, float] = defaultdict(float)
            for edge_id, volume in current.items():
                flows[edge_id] += volume
                if edge_id in graph.exit_edges:
                    continue
                options = graph.options(edge_id)
                legal = [movement for movement in MOVEMENTS if movement in options]
                total = sum(max(ratios.get(movement, 0.0), 0.0) for movement in legal)
                for movement in legal:
                    share = max(ratios.get(movement, 0.0), 0.0) / total
                    following[options[movement]] += volume * share
                    movement_volume[movement] += volume * share
            current = following
            if sum(current.values()) < 1e-9:
                break
    return dict(flows), dict(movement_volume)


def summarize_vehicles(
    *,
    graph: RoutingGraph,
    vehicles: Sequence[GeneratedVehicle],
    measurement_start_seconds: float,
    measurement_end_seconds: float,
) -> dict[str, object]:
    """Demanda ofertada, mistura de movimentos realizada e cobertura de junções dos veículos
    gerados.
    """

    by_entry: dict[str, int] = defaultdict(int)
    by_group: dict[str, int] = defaultdict(int)
    by_demand: dict[str, int] = defaultdict(int)
    movement_counts: dict[str, int] = {movement: 0 for movement in MOVEMENTS}
    movement_counts_by_group: dict[str, dict[str, int]] = defaultdict(
        lambda: {movement: 0 for movement in MOVEMENTS}
    )
    passes_by_node: dict[str, int] = defaultdict(int)
    in_window = 0
    for vehicle in vehicles:
        by_entry[vehicle.entry_edge_id] += 1
        by_group[vehicle.group] += 1
        by_demand[vehicle.demand_id] += 1
        if measurement_start_seconds <= vehicle.depart_seconds < measurement_end_seconds:
            in_window += 1
        for movement in route_movements(graph, vehicle.route):
            movement_counts[movement] += 1
            movement_counts_by_group[vehicle.group][movement] += 1
        for edge_id in vehicle.route[:-1]:
            node_id = graph.edge_to_node[edge_id]
            if node_id in graph.signalized_nodes:
                passes_by_node[node_id] += 1
    total_movements = sum(movement_counts.values())
    proportions = {
        movement: (count / total_movements if total_movements else 0.0)
        for movement, count in movement_counts.items()
    }
    total_passes = sum(passes_by_node.values())
    return {
        "offered_vehicle_count": len(vehicles),
        "offered_in_measurement_window": in_window,
        "offered_by_entry": dict(sorted(by_entry.items())),
        "offered_by_group": dict(sorted(by_group.items())),
        "offered_by_demand": dict(sorted(by_demand.items())),
        "realized_movement_counts": movement_counts,
        "realized_movement_proportions": proportions,
        "realized_movement_counts_by_group": {
            group: dict(counts) for group, counts in sorted(movement_counts_by_group.items())
        },
        "junction_passes_by_node": dict(sorted(passes_by_node.items())),
        "junction_pass_share_by_node": {
            node_id: (count / total_passes if total_passes else 0.0)
            for node_id, count in sorted(passes_by_node.items())
        },
    }
