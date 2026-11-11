"""Finalização canônica das métricas por execução.

``finalize_run_metrics`` transforma os artefatos brutos de uma execução concluída (arquivo de
rotas, ``tripinfo.xml``/``statistics.xml`` do SUMO, telemetria Parquet canônica, manifesto) em
um único ``run_metrics.json`` legível por máquina. Nada nos resultados científicos depende de
scripts de análise ad hoc nem de rastros de depuração opcionais.

Política de população (documentada em ``docs/methodology/metrics.md``):

* A *coorte de medição* é o conjunto de veículos ofertados cujo tempo de partida PROGRAMADO está
  na janela de medição ``[warmup, warmup + measurement_duration)``. As contagens (ofertados,
  partiram, chegaram, nunca inseridos, não finalizados) e todas as métricas de viagens
  concluídas usam essa coorte, de modo que a demanda de warmup nunca contamina as populações de
  medição.
* ``throughput`` é uma contagem de fluxo: veículos que CHEGAM dentro da janela de medição.
* As métricas de fila usam apenas lanes de entrada únicas e apenas passos da janela de medição.
* As contagens ``full_run_*`` cobrem todo veículo ofertado da execução inteira.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.config import ScenarioConfig
from traffic_agents.metrics.network_telemetry import (
    JUNCTION_TELEMETRY_FILE,
    LANE_TELEMETRY_FILE,
)

RUN_METRICS_FILE = "run_metrics.json"
RUN_METRICS_SCHEMA_VERSION = "run-metrics-v1"
COMMUNICATION_METRIC_KEYS = (
    "messages_sent",
    "messages_delivered",
    "messages_dropped",
    "messages_stale",
    "bytes_sent",
    "bytes_delivered",
    "mean_message_age_steps",
    "max_message_age_steps",
)
CORRIDOR_EDGES = ("A1B1", "B1C1")


class MetricsFinalizationError(RuntimeError):
    """Lançada quando uma execução não pode ser finalizada cientificamente."""


@dataclass(frozen=True)
class OfferedVehicle:
    vehicle_id: str
    demand_id: str
    scheduled_depart: float
    entry_edge_id: str
    route: tuple[str, ...]


@dataclass(frozen=True)
class TripRecord:
    vehicle_id: str
    depart: float
    depart_delay: float
    arrival: float
    duration: float
    waiting_time: float
    time_loss: float
    waiting_count: float

    @property
    def arrived(self) -> bool:
        return self.arrival >= 0.0


def load_offered_vehicles(route_path: Path) -> tuple[OfferedVehicle, ...]:
    """Todo veículo que o arquivo de rotas oferece, com seu tempo de partida programado.

    Trata elementos ``<vehicle>`` explícitos (demanda por razões de conversão, ``<route id>``
    compartilhado opcional) e elementos ``<flow>`` (demanda legada do ``duarouter``, expandida
    com a taxa do fluxo).
    """

    try:
        root = ET.parse(route_path).getroot()
    except (ET.ParseError, OSError) as exc:
        msg = f"cannot read route file: {route_path}"
        raise MetricsFinalizationError(msg) from exc
    shared_routes = {
        str(route.attrib["id"]): tuple(str(route.attrib["edges"]).split())
        for route in root.findall("route")
        if "id" in route.attrib and "edges" in route.attrib
    }
    offered: list[OfferedVehicle] = []
    for vehicle in root.findall("vehicle"):
        vehicle_id = str(vehicle.attrib["id"])
        route = _vehicle_route(vehicle, shared_routes)
        offered.append(
            OfferedVehicle(
                vehicle_id=vehicle_id,
                demand_id=vehicle_id.rsplit(".", maxsplit=1)[0],
                scheduled_depart=float(vehicle.attrib["depart"]),
                entry_edge_id=route[0],
                route=route,
            )
        )
    for flow in root.findall("flow"):
        flow_id = str(flow.attrib["id"])
        route = _vehicle_route(flow, shared_routes)
        begin = float(flow.attrib.get("begin", "0"))
        end = float(flow.attrib.get("end", "0"))
        rate = float(flow.attrib.get("vehsPerHour", flow.attrib.get("perHour", "0")))
        if rate <= 0:
            continue
        period = 3600.0 / rate
        for index in range(math.floor((end - begin) / period + 1e-9)):
            offered.append(
                OfferedVehicle(
                    vehicle_id=f"{flow_id}.{index}",
                    demand_id=flow_id,
                    scheduled_depart=begin + index * period,
                    entry_edge_id=route[0],
                    route=route,
                )
            )
    if not offered:
        msg = f"route file offers no vehicles: {route_path}"
        raise MetricsFinalizationError(msg)
    return tuple(offered)


def _vehicle_route(
    element: ET.Element, shared_routes: Mapping[str, tuple[str, ...]]
) -> tuple[str, ...]:
    route_id = element.attrib.get("route")
    if route_id is not None:
        if route_id not in shared_routes:
            msg = f"vehicle references unknown route: {route_id}"
            raise MetricsFinalizationError(msg)
        return shared_routes[route_id]
    nested = element.find("route")
    if nested is None or "edges" not in nested.attrib:
        msg = f"vehicle/flow without route edges: {element.attrib.get('id')}"
        raise MetricsFinalizationError(msg)
    return tuple(str(nested.attrib["edges"]).split())


def parse_tripinfo_records(tripinfo_path: Path) -> dict[str, TripRecord]:
    """Todos os registros de tripinfo; veículos inseridos e não finalizados têm ``arrival < 0``."""

    if not tripinfo_path.exists():
        msg = f"SUMO tripinfo file not found: {tripinfo_path}"
        raise MetricsFinalizationError(msg)
    records: dict[str, TripRecord] = {}
    try:
        for _, element in ET.iterparse(tripinfo_path):
            if element.tag != "tripinfo":
                continue
            attributes = element.attrib
            depart = float(attributes["depart"])
            records[str(attributes["id"])] = TripRecord(
                vehicle_id=str(attributes["id"]),
                depart=depart,
                depart_delay=float(attributes.get("departDelay", "0")),
                arrival=float(attributes.get("arrival", "-1")),
                duration=float(attributes.get("duration", "-1")),
                waiting_time=float(attributes.get("waitingTime", "0")),
                time_loss=float(attributes.get("timeLoss", "0")),
                waiting_count=float(attributes.get("waitingCount", "0")),
            )
            element.clear()
    except (ET.ParseError, KeyError, ValueError) as exc:
        msg = f"malformed SUMO tripinfo: {tripinfo_path}"
        raise MetricsFinalizationError(msg) from exc
    return records


def parse_statistics_counts(statistics_path: Path) -> dict[str, float]:
    if not statistics_path.exists():
        msg = f"SUMO statistics file not found: {statistics_path}"
        raise MetricsFinalizationError(msg)
    try:
        root = ET.parse(statistics_path).getroot()
    except ET.ParseError as exc:
        msg = f"malformed SUMO statistics: {statistics_path}"
        raise MetricsFinalizationError(msg) from exc
    vehicles = root.find("vehicles")
    teleports = root.find("teleports")
    counts: dict[str, float] = {}
    if vehicles is not None:
        for key in ("loaded", "inserted", "running", "waiting"):
            if key in vehicles.attrib:
                counts[f"sumo_vehicles_{key}"] = float(vehicles.attrib[key])
    if teleports is not None and "total" in teleports.attrib:
        counts["sumo_teleports_total"] = float(teleports.attrib["total"])
    return counts


def finalize_run_metrics(
    *,
    run_dir: Path,
    manifest: Mapping[str, Any],
    scenario_config: ScenarioConfig,
    route_path: Path,
    route_metadata_path: Path | None,
    steps_executed: int,
    performance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula as métricas canônicas de uma execução e retorna o payload de ``run_metrics.json``."""

    step_length = float(scenario_config.step_length)
    measurement_start_step = int(scenario_config.measurement_start_step)
    measurement_end_step = int(scenario_config.measurement_end_step)
    effective_end_step = min(measurement_end_step, int(steps_executed))
    if effective_end_step <= measurement_start_step:
        msg = "run ended before the measurement window; metrics cannot be finalized"
        raise MetricsFinalizationError(msg)
    window_start_seconds = measurement_start_step * step_length
    window_end_seconds = effective_end_step * step_length
    run_end_seconds = int(steps_executed) * step_length
    horizon_complete = effective_end_step == measurement_end_step

    offered_vehicles = load_offered_vehicles(route_path)
    trips = parse_tripinfo_records(run_dir / "sumo" / "tripinfo.xml")
    statistics = parse_statistics_counts(run_dir / "sumo" / "statistics.xml")
    entry_group = _entry_group_lookup(route_metadata_path)

    metrics: dict[str, float] = {}
    populations: dict[str, dict[str, int]] = {}

    full_run = _population_counts(offered_vehicles, trips)
    cohort_vehicles = tuple(
        vehicle
        for vehicle in offered_vehicles
        if window_start_seconds <= vehicle.scheduled_depart < window_end_seconds
    )
    measurement = _population_counts(cohort_vehicles, trips)
    populations["full_run"] = full_run
    populations["measurement"] = measurement
    for name, value in full_run.items():
        metrics[f"full_run_{_count_metric_name(name)}"] = float(value)
    for name, value in measurement.items():
        metrics[f"measurement_{_count_metric_name(name)}"] = float(value)
        metrics[_count_metric_name(name)] = float(value)
    metrics["departure_ratio"] = _ratio(measurement["departed"], measurement["offered"])
    metrics["completion_ratio_offered"] = _ratio(measurement["arrived"], measurement["offered"])
    metrics["completion_ratio_departed"] = _ratio(measurement["arrived"], measurement["departed"])
    metrics["full_run_departure_ratio"] = _ratio(full_run["departed"], full_run["offered"])
    metrics["full_run_completion_ratio_offered"] = _ratio(full_run["arrived"], full_run["offered"])
    metrics["full_run_completion_ratio_departed"] = _ratio(
        full_run["arrived"], full_run["departed"]
    )

    # Throughput: chegadas dentro da janela de medição (contagem de fluxo).
    arrivals_in_window = [
        trip
        for trip in trips.values()
        if trip.arrived and window_start_seconds <= trip.arrival < window_end_seconds
    ]
    metrics["throughput"] = float(len(arrivals_in_window))
    metrics["measurement_arrivals_from_warmup_offered_count"] = float(
        sum(1 for trip in arrivals_in_window if _scheduled_depart(trip) < window_start_seconds)
    )

    # Atraso de inserção dos veículos da coorte que de fato partiram.
    cohort_ids = {vehicle.vehicle_id for vehicle in cohort_vehicles}
    cohort_trips = [trips[vehicle_id] for vehicle_id in sorted(cohort_ids) if vehicle_id in trips]
    delays = [trip.depart_delay for trip in cohort_trips]
    metrics["total_depart_delay_seconds"] = float(sum(delays))
    if delays:
        metrics["mean_depart_delay_seconds"] = float(sum(delays) / len(delays))
    never_inserted = [vehicle for vehicle in cohort_vehicles if vehicle.vehicle_id not in trips]
    backlog_lower_bound = sum(
        max(run_end_seconds - vehicle.scheduled_depart, 0.0) for vehicle in never_inserted
    )
    metrics["never_inserted_backlog_delay_lower_bound_seconds"] = float(backlog_lower_bound)
    if never_inserted:
        metrics["never_inserted_mean_backlog_delay_lower_bound_seconds"] = float(
            backlog_lower_bound / len(never_inserted)
        )

    # Métricas de viagens concluídas (condicionais à conclusão) sobre a coorte de medição.
    completed = [trip for trip in cohort_trips if trip.arrived]
    metrics["completed_trip_count"] = float(len(completed))
    if completed:
        metrics["mean_travel_time"] = _mean(trip.duration for trip in completed)
        metrics["mean_waiting_time"] = _mean(trip.waiting_time for trip in completed)
        metrics["mean_time_loss"] = _mean(trip.time_loss for trip in completed)
        metrics["mean_stops"] = _mean(trip.waiting_count for trip in completed)
        metrics["mean_time_in_system_seconds"] = _mean(
            trip.duration + trip.depart_delay for trip in completed
        )

    # Métricas do corredor (S2): veículos que atravessam a linha central no sentido leste.
    offered_by_id = {vehicle.vehicle_id: vehicle for vehicle in offered_vehicles}
    corridor_ids = {
        vehicle.vehicle_id for vehicle in offered_vehicles if _uses_corridor(vehicle.route)
    }
    metrics["corridor_throughput"] = float(
        sum(1 for trip in arrivals_in_window if trip.vehicle_id in corridor_ids)
    )
    corridor_completed = [trip for trip in completed if trip.vehicle_id in corridor_ids]
    if corridor_completed:
        metrics["corridor_mean_travel_time"] = _mean(trip.duration for trip in corridor_completed)
        metrics["corridor_mean_stops"] = _mean(trip.waiting_count for trip in corridor_completed)

    # Perda de tempo pós-choque (S3): veículos da coorte PROGRAMADOS no choque ou depois dele.
    shock_start_seconds = scenario_config.traffic.shock_start_seconds
    if shock_start_seconds is not None:
        post_shock_completed = [
            trip
            for trip in completed
            if offered_by_id[trip.vehicle_id].scheduled_depart >= shock_start_seconds
        ]
        metrics["post_shock_completed_trip_count"] = float(len(post_shock_completed))
        if post_shock_completed:
            metrics["post_shock_time_loss"] = _mean(trip.time_loss for trip in post_shock_completed)
        pre_shock_completed = [
            trip
            for trip in completed
            if offered_by_id[trip.vehicle_id].scheduled_depart < shock_start_seconds
        ]
        if pre_shock_completed:
            metrics["pre_shock_time_loss"] = _mean(trip.time_loss for trip in pre_shock_completed)

    # Contabilização por entrada / grupo.
    by_entry = _entry_accounting(cohort_vehicles, trips, key=lambda vehicle: vehicle.entry_edge_id)
    by_group = _entry_accounting(
        cohort_vehicles,
        trips,
        key=lambda vehicle: entry_group.get(vehicle.demand_id, "unknown"),
    )
    for entry_edge, entry_row in by_entry.items():
        metrics[f"offered_by_entry__{entry_edge}"] = float(entry_row["offered"])
        metrics[f"departed_by_entry__{entry_edge}"] = float(entry_row["departed"])
        metrics[f"arrived_by_entry__{entry_edge}"] = float(entry_row["arrived"])
        metrics[f"entry_departure_ratio__{entry_edge}"] = entry_row["entry_departure_ratio"]
    if by_entry:
        metrics["min_entry_departure_ratio"] = min(
            row["entry_departure_ratio"] for row in by_entry.values()
        )
    for group, row in by_group.items():
        metrics[f"group_{group}_offered_share"] = _ratio(
            row["offered"], sum(item["offered"] for item in by_group.values())
        )
        metrics[f"group_{group}_departure_ratio"] = row["entry_departure_ratio"]

    # Métricas canônicas de fila e de junção a partir da telemetria unificada.
    _add_telemetry_metrics(
        metrics,
        run_dir=run_dir,
        scenario_config=scenario_config,
        measurement_start_step=measurement_start_step,
        effective_end_step=effective_end_step,
        step_length=step_length,
    )

    communication = manifest.get("communication_metrics")
    if isinstance(communication, dict):
        for key in COMMUNICATION_METRIC_KEYS:
            communication_value = communication.get(key)
            if isinstance(communication_value, int | float):
                metrics[key] = float(communication_value)

    simulation = manifest.get("simulation")
    wall_time = (
        float(simulation["wall_time_seconds"])
        if isinstance(simulation, dict) and "wall_time_seconds" in simulation
        else None
    )
    if wall_time is not None:
        metrics["wall_time_seconds"] = wall_time
        metrics["steps_per_second"] = (steps_executed / wall_time) if wall_time > 0 else 0.0
    if performance is not None:
        for key in (
            "controller_decision_mean_ms",
            "controller_decision_p95_ms",
            "result_collector_time_ms",
        ):
            performance_value = performance.get(key)
            if isinstance(performance_value, int | float):
                metrics[key] = float(performance_value)
    metrics.update(statistics)

    finite_metrics = {
        name: float(value) for name, value in sorted(metrics.items()) if math.isfinite(value)
    }
    return {
        "schema_version": RUN_METRICS_SCHEMA_VERSION,
        "run_id": manifest.get("run_id"),
        "scenario_id": manifest.get("scenario_id"),
        "demand_profile": manifest.get("demand_profile"),
        "seed": manifest.get("seed"),
        "controller_id": _controller_id(manifest),
        "status": "COMPLETED",
        "windows": {
            "warmup_seconds": float(scenario_config.warmup_seconds),
            "measurement_start_seconds": window_start_seconds,
            "measurement_end_seconds": measurement_end_step * step_length,
            "effective_measurement_end_seconds": window_end_seconds,
            "shock_start_seconds": shock_start_seconds,
            "step_length": step_length,
            "steps_executed": int(steps_executed),
            "horizon_complete": bool(horizon_complete),
        },
        "population_policy": {
            "measurement_cohort": (
                "offered vehicles whose scheduled departure lies in the measurement window"
            ),
            "counts": (
                "offered/departed/arrived/never_inserted/unfinished_in_network use the cohort"
            ),
            "completed_trip_metrics": (
                "conditional on completion: cohort vehicles that arrived before the run ended"
            ),
            "throughput": "vehicles arriving inside the measurement window (flow count)",
            "queues": "unique incoming lanes, measurement-window steps only",
        },
        "populations": populations,
        "by_entry": by_entry,
        "by_group": by_group,
        "metrics": finite_metrics,
        "invariants": {
            key: manifest.get(key)
            for key in (
                "network_sha256",
                "route_sha256",
                "phase_plan_sha256",
                "movement_model_sha256",
                "turning_config_sha256",
                "communication_topology_sha256",
            )
        },
    }


def write_run_metrics(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _controller_id(manifest: Mapping[str, Any]) -> str | None:
    controller = manifest.get("controller")
    if isinstance(controller, dict):
        value = controller.get("controller_id")
        return str(value) if value is not None else None
    return None


def _scheduled_depart(trip: TripRecord) -> float:
    return trip.depart - trip.depart_delay


def _population_counts(
    vehicles: Sequence[OfferedVehicle],
    trips: Mapping[str, TripRecord],
) -> dict[str, int]:
    offered = len(vehicles)
    departed = sum(1 for vehicle in vehicles if vehicle.vehicle_id in trips)
    arrived = sum(
        1
        for vehicle in vehicles
        if vehicle.vehicle_id in trips and trips[vehicle.vehicle_id].arrived
    )
    return {
        "offered": offered,
        "departed": departed,
        "arrived": arrived,
        "never_inserted": offered - departed,
        "unfinished_in_network": departed - arrived,
    }


def _entry_accounting(
    vehicles: Sequence[OfferedVehicle],
    trips: Mapping[str, TripRecord],
    *,
    key: Any,
) -> dict[str, dict[str, float]]:
    offered: dict[str, int] = defaultdict(int)
    departed: dict[str, int] = defaultdict(int)
    arrived: dict[str, int] = defaultdict(int)
    for vehicle in vehicles:
        name = str(key(vehicle))
        offered[name] += 1
        trip = trips.get(vehicle.vehicle_id)
        if trip is not None:
            departed[name] += 1
            if trip.arrived:
                arrived[name] += 1
    return {
        name: {
            "offered": offered[name],
            "departed": departed[name],
            "arrived": arrived[name],
            "entry_departure_ratio": _ratio(departed[name], offered[name]),
        }
        for name in sorted(offered)
    }


def _entry_group_lookup(route_metadata_path: Path | None) -> dict[str, str]:
    if route_metadata_path is None or not route_metadata_path.exists():
        return {}
    payload = json.loads(route_metadata_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return {}
    return {
        str(entry["demand_id"]): str(entry.get("group", "base"))
        for entry in entries
        if isinstance(entry, dict) and "demand_id" in entry
    }


def _uses_corridor(route: Sequence[str]) -> bool:
    first, second = CORRIDOR_EDGES
    for index in range(len(route) - 1):
        if route[index] == first and route[index + 1] == second:
            return True
    return False


def _add_telemetry_metrics(
    metrics: dict[str, float],
    *,
    run_dir: Path,
    scenario_config: ScenarioConfig,
    measurement_start_step: int,
    effective_end_step: int,
    step_length: float,
) -> None:
    lane_path = run_dir / LANE_TELEMETRY_FILE
    junction_path = run_dir / JUNCTION_TELEMETRY_FILE
    if not lane_path.exists() or not junction_path.exists():
        msg = f"canonical telemetry files are missing in {run_dir}"
        raise MetricsFinalizationError(msg)
    lane_table = pq.read_table(lane_path, columns=["step_index", "queue"])
    junction_table = pq.read_table(
        junction_path,
        columns=[
            "step_index",
            "intersection_total_queue",
            "internal_lane_persistence_events",
        ],
    )
    lane_steps = lane_table.column("step_index").to_numpy()
    lane_queue = lane_table.column("queue").to_numpy().astype(np.int64)
    lanes_per_step = int(np.sum(lane_steps == lane_steps[0]))
    if lanes_per_step <= 0 or lane_steps.size % lanes_per_step != 0:
        msg = "lane telemetry is not rectangular (steps x lanes)"
        raise MetricsFinalizationError(msg)
    lane_matrix = lane_queue.reshape(-1, lanes_per_step)
    steps = lane_steps[::lanes_per_step]

    junction_steps = junction_table.column("step_index").to_numpy()
    junction_total = junction_table.column("intersection_total_queue").to_numpy().astype(np.int64)
    persistence = junction_table.column("internal_lane_persistence_events").to_numpy()
    junctions_per_step = int(np.sum(junction_steps == junction_steps[0]))
    junction_matrix = junction_total.reshape(-1, junctions_per_step)

    in_window = (steps >= measurement_start_step) & (steps < effective_end_step)
    if not bool(in_window.any()):
        msg = "no telemetry samples inside the measurement window"
        raise MetricsFinalizationError(msg)
    network_total = lane_matrix.sum(axis=1)
    metrics["mean_network_queue_vehicles"] = float(network_total[in_window].mean())
    metrics["max_network_queue_vehicles"] = float(network_total[in_window].max())
    metrics["mean_intersection_queue_vehicles"] = float(junction_matrix[in_window].mean())
    metrics["max_intersection_queue_vehicles"] = float(junction_matrix[in_window].max())
    metrics["mean_lane_queue_vehicles"] = float(lane_matrix[in_window].mean())
    metrics["max_lane_queue_vehicles"] = float(lane_matrix[in_window].max())
    window_junction_mask = (junction_steps >= measurement_start_step) & (
        junction_steps < effective_end_step
    )
    metrics["internal_lane_persistence_events"] = float(persistence[window_junction_mask].sum())

    shock_step = scenario_config.shock_start_step
    if shock_step is not None:
        post = in_window & (steps >= shock_step)
        pre = in_window & (steps < shock_step)
        if bool(pre.any()):
            metrics["pre_shock_mean_network_queue_vehicles"] = float(network_total[pre].mean())
            metrics["pre_shock_max_network_queue_vehicles"] = float(network_total[pre].max())
        if bool(post.any()):
            metrics["post_shock_mean_network_queue_vehicles"] = float(network_total[post].mean())
            metrics["post_shock_max_network_queue_vehicles"] = float(network_total[post].max())
            times = (steps[post].astype(np.float64) + 1.0) * step_length
            metrics["post_shock_queue_auc_vehicle_seconds"] = (
                float(np.trapezoid(network_total[post].astype(np.float64), times))
                if int(post.sum()) > 1
                else 0.0
            )


def _mean(values: Any) -> float:
    items = list(values)
    return float(sum(items) / len(items)) if items else math.nan


def _ratio(numerator: float, denominator: float) -> float:
    """Razão com tratamento seguro de denominador zero: 0.0 quando o denominador é 0."""

    return float(numerator / denominator) if denominator > 0 else 0.0


def _count_metric_name(population_key: str) -> str:
    if population_key == "unfinished_in_network":
        return "unfinished_in_network_count"
    return f"{population_key}_vehicle_count"
