"""Definições operacionais das métricas finais V1.

Toda métrica exportada pela finalização canônica da execução (``run_metrics.json``) e consumida
pelo relatório/análise tem aqui uma entrada com sua unidade, fonte, população, agregação, janela
e política de casos-limite. ``docs/methodology/metrics.md`` espelha este módulo.

Vocabulário de populações:

* **coorte de medição** - veículos ofertados cuja partida PROGRAMADA está dentro da janela de
  medição ``[warmup, warmup + measurement_duration)``.
* **viagens concluídas** - veículos da coorte que chegaram antes do fim da execução. Métricas
  calculadas apenas sobre viagens concluídas são CONDICIONAIS à conclusão e devem sempre ser
  lidas junto com ``throughput``, as razões de conclusão e as métricas de fila/backlog.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

CORRIDOR_DEFINITION_VERSION = "west-east-middle-corridor-v2"
CORRIDOR_DEFINITION = {
    "label": "West -> A4 -> A5 -> A6 -> East",
    "sumo_tls_path": ("A1", "B1", "C1"),
    "entry_edge": "left1A1",
    "through_edges": ("A1B1", "B1C1"),
    "exit_edge": "C1right1",
    "membership_rule": "route traverses edge A1B1 immediately followed by edge B1C1",
}

_RUN_WINDOW = "Whole run, including warmup (offered/departed/arrived over every vehicle)."
_COHORT_WINDOW = (
    "Measurement window; cohort = vehicles scheduled to depart inside "
    "[warmup, warmup + measurement_duration)."
)
_QUEUE_WINDOW = "Measurement-window steps only (warmup excluded); one sample per simulation step."
_COMM_WINDOW = "Full simulated run, including warmup, unless report labels otherwise."


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    unit: str
    source: str
    aggregation: str
    measurement_window: str
    edge_case_policy: str
    population: str = "Not population dependent."
    completed_trips_only: bool = False

    def as_dict(self) -> dict[str, str]:
        payload = {key: str(value) for key, value in asdict(self).items()}
        payload["completed_trips_only"] = str(self.completed_trips_only).lower()
        return payload


def _count(
    name: str,
    description: str,
    window: str,
    population: str,
) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        unit="vehicles",
        source="Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived).",
        aggregation=description,
        measurement_window=window,
        edge_case_policy="Counts are 0 when the population is empty.",
        population=population,
    )


def _ratio(name: str, formula: str, population: str) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        unit="ratio",
        source="Population counts from route file and SUMO tripinfo.",
        aggregation=formula,
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="Reported as 0.0 when the denominator is 0.",
        population=population,
    )


def _completed(
    name: str,
    unit: str,
    source: str,
    *,
    population: str = "Completed trips of the measurement cohort (conditional on completion).",
    window: str = _COHORT_WINDOW,
    aggregation: str | None = None,
) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        unit=unit,
        source=source,
        aggregation=aggregation or "Arithmetic mean over completed trips of the cohort.",
        measurement_window=window,
        edge_case_policy="If no cohort vehicle completes its trip, omit the metric for that run.",
        population=population,
        completed_trips_only=True,
    )


def _queue(name: str, aggregation: str, *, window: str = _QUEUE_WINDOW) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        unit="vehicles",
        source=(
            "Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting "
            "vehicle count per UNIQUE incoming lane, sampled by the simulation runner for "
            "every controller)."
        ),
        aggregation=aggregation,
        measurement_window=window,
        edge_case_policy="Omitted only if no telemetry samples exist in the window (run fails).",
        population="All vehicles halting on incoming lanes; each physical lane counted once.",
    )


METRIC_DEFINITIONS: Mapping[str, MetricDefinition] = {
    # --- populações -----------------------------------------------------------------
    "offered_vehicle_count": _count(
        "offered_vehicle_count",
        "Count of offered vehicles in the measurement cohort (alias of "
        "measurement_offered_vehicle_count).",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "departed_vehicle_count": _count(
        "departed_vehicle_count",
        "Cohort vehicles that were inserted into the network before the run ended.",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "arrived_vehicle_count": _count(
        "arrived_vehicle_count",
        "Cohort vehicles that arrived before the run ended.",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "never_inserted_vehicle_count": _count(
        "never_inserted_vehicle_count",
        "Cohort vehicles that never entered the network (offered - departed).",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "unfinished_in_network_count": _count(
        "unfinished_in_network_count",
        "Cohort vehicles inserted but not arrived at the end of the run (departed - arrived).",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "full_run_offered_vehicle_count": _count(
        "full_run_offered_vehicle_count",
        "All vehicles offered by the route file over the whole run.",
        _RUN_WINDOW,
        "Every offered vehicle.",
    ),
    "full_run_departed_vehicle_count": _count(
        "full_run_departed_vehicle_count",
        "All vehicles inserted into the network over the whole run.",
        _RUN_WINDOW,
        "Every offered vehicle.",
    ),
    "full_run_arrived_vehicle_count": _count(
        "full_run_arrived_vehicle_count",
        "All vehicles that arrived over the whole run.",
        _RUN_WINDOW,
        "Every offered vehicle.",
    ),
    "full_run_never_inserted_vehicle_count": _count(
        "full_run_never_inserted_vehicle_count",
        "Offered vehicles that never entered the network over the whole run.",
        _RUN_WINDOW,
        "Every offered vehicle.",
    ),
    "full_run_unfinished_in_network_count": _count(
        "full_run_unfinished_in_network_count",
        "Vehicles inserted but not arrived at the end of the run.",
        _RUN_WINDOW,
        "Every offered vehicle.",
    ),
    "measurement_offered_vehicle_count": _count(
        "measurement_offered_vehicle_count",
        "Offered vehicles scheduled inside the measurement window.",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "measurement_departed_vehicle_count": _count(
        "measurement_departed_vehicle_count",
        "Cohort vehicles inserted before the run ended.",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "measurement_arrived_vehicle_count": _count(
        "measurement_arrived_vehicle_count",
        "Cohort vehicles that arrived before the run ended.",
        _COHORT_WINDOW,
        "Measurement cohort.",
    ),
    "departure_ratio": _ratio(
        "departure_ratio",
        "departed_vehicle_count / offered_vehicle_count.",
        "Measurement cohort.",
    ),
    "completion_ratio_offered": _ratio(
        "completion_ratio_offered",
        "arrived_vehicle_count / offered_vehicle_count.",
        "Measurement cohort.",
    ),
    "completion_ratio_departed": _ratio(
        "completion_ratio_departed",
        "arrived_vehicle_count / departed_vehicle_count.",
        "Measurement cohort.",
    ),
    "throughput": MetricDefinition(
        name="throughput",
        unit="vehicles",
        source="SUMO tripinfo arrival times (equals SUMO arrived counts per step).",
        aggregation="Count of vehicles that arrive during the measurement window.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no vehicles arrive, report 0.",
        population=(
            "Flow count: every vehicle arriving in the window, including vehicles scheduled "
            "during warmup."
        ),
    ),
    "completed_trip_count": _count(
        "completed_trip_count",
        "Cohort vehicles used for completed-trip metrics (arrived before the run ended).",
        _COHORT_WINDOW,
        "Measurement cohort, completed trips.",
    ),
    # --- atraso de inserção -------------------------------------------------------------
    "mean_depart_delay_seconds": MetricDefinition(
        name="mean_depart_delay_seconds",
        unit="seconds/vehicle",
        source="SUMO tripinfo departDelay (insertion time - scheduled departure).",
        aggregation="Arithmetic mean over cohort vehicles that were inserted.",
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="Omitted if no cohort vehicle was inserted.",
        population="Cohort vehicles that actually departed (never-inserted vehicles excluded).",
    ),
    "total_depart_delay_seconds": MetricDefinition(
        name="total_depart_delay_seconds",
        unit="seconds",
        source="SUMO tripinfo departDelay.",
        aggregation="Sum over cohort vehicles that were inserted.",
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0 when no cohort vehicle was inserted.",
        population="Cohort vehicles that actually departed.",
    ),
    "never_inserted_backlog_delay_lower_bound_seconds": MetricDefinition(
        name="never_inserted_backlog_delay_lower_bound_seconds",
        unit="seconds",
        source="Route file scheduled departure and the simulated run end.",
        aggregation=(
            "Sum over never-inserted cohort vehicles of (run end - scheduled departure); a "
            "LOWER BOUND of their backlog delay, never merged into completed-trip means."
        ),
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0 when every cohort vehicle was inserted.",
        population="Cohort vehicles that never entered the network.",
    ),
    # --- métricas de viagens concluídas (condicionais) ----------------------------------------
    "mean_travel_time": _completed(
        "mean_travel_time",
        "seconds/vehicle",
        "SUMO tripinfo duration (arrival - insertion; excludes insertion delay).",
    ),
    "mean_waiting_time": _completed(
        "mean_waiting_time",
        "seconds/vehicle",
        "SUMO tripinfo waitingTime for completed trips.",
    ),
    "mean_time_loss": _completed(
        "mean_time_loss",
        "seconds/vehicle",
        "SUMO tripinfo timeLoss for completed trips.",
    ),
    "mean_stops": _completed(
        "mean_stops",
        "stops/vehicle",
        "SUMO tripinfo waitingCount for completed trips.",
    ),
    "mean_time_in_system_seconds": _completed(
        "mean_time_in_system_seconds",
        "seconds/vehicle",
        "SUMO tripinfo duration + departDelay for completed trips.",
        aggregation="Arithmetic mean of (travel time + insertion delay) over completed trips.",
    ),
    "corridor_throughput": MetricDefinition(
        name="corridor_throughput",
        unit="vehicles",
        source=f"Route file corridor membership ({CORRIDOR_DEFINITION_VERSION}) and tripinfo.",
        aggregation="Count of corridor vehicles that arrive during the measurement window.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no corridor vehicles arrive, report 0.",
        population="Flow count of vehicles whose route traverses the middle-row corridor.",
    ),
    "corridor_mean_travel_time": _completed(
        "corridor_mean_travel_time",
        "seconds/vehicle",
        f"SUMO tripinfo duration filtered to {CORRIDOR_DEFINITION_VERSION}.",
        population="Completed corridor trips of the measurement cohort (conditional).",
    ),
    "corridor_mean_stops": _completed(
        "corridor_mean_stops",
        "stops/vehicle",
        f"SUMO tripinfo waitingCount filtered to {CORRIDOR_DEFINITION_VERSION}.",
        population="Completed corridor trips of the measurement cohort (conditional).",
    ),
    "post_shock_time_loss": _completed(
        "post_shock_time_loss",
        "seconds/vehicle",
        "SUMO tripinfo timeLoss of completed trips scheduled at or after the shock time.",
        population=(
            "Completed trips of cohort vehicles SCHEDULED at or after the shock start "
            "(conditional on completion; population defined by scheduled, not insertion, time)."
        ),
        window="Post-shock subset of the measurement window.",
    ),
    "pre_shock_time_loss": _completed(
        "pre_shock_time_loss",
        "seconds/vehicle",
        "SUMO tripinfo timeLoss of completed trips scheduled before the shock time.",
        population=(
            "Completed trips of cohort vehicles scheduled before the shock start "
            "(conditional on completion)."
        ),
        window="Pre-shock subset of the measurement window.",
    ),
    # --- filas ----------------------------------------------------------------------
    "mean_network_queue_vehicles": _queue(
        "mean_network_queue_vehicles",
        "Mean over measurement steps of network_total_queue (sum of unique incoming-lane "
        "halting counts).",
    ),
    "max_network_queue_vehicles": _queue(
        "max_network_queue_vehicles",
        "Maximum over measurement steps of network_total_queue.",
    ),
    "mean_intersection_queue_vehicles": _queue(
        "mean_intersection_queue_vehicles",
        "Mean over measurement steps and intersections of intersection_total_queue (sum of "
        "the unique incoming-lane halting counts of one intersection).",
    ),
    "max_intersection_queue_vehicles": _queue(
        "max_intersection_queue_vehicles",
        "Maximum over measurement steps and intersections of intersection_total_queue.",
    ),
    "mean_lane_queue_vehicles": _queue(
        "mean_lane_queue_vehicles",
        "Mean over measurement steps and lanes of lane_queue (diluted by idle lanes; "
        "diagnostic only).",
    ),
    "max_lane_queue_vehicles": _queue(
        "max_lane_queue_vehicles",
        "Maximum lane_queue over measurement steps and lanes. May saturate at the physical "
        "storage capacity of a lane (about 30 vehicles on a 235.6 m edge) in overloaded "
        "scenarios and then loses discriminatory power; use the network/intersection "
        "aggregates alongside it.",
    ),
    "post_shock_mean_network_queue_vehicles": _queue(
        "post_shock_mean_network_queue_vehicles",
        "Mean network_total_queue over post-shock measurement steps.",
        window="Post-shock subset of the measurement window (step >= shock start step).",
    ),
    "post_shock_max_network_queue_vehicles": _queue(
        "post_shock_max_network_queue_vehicles",
        "Maximum network_total_queue over post-shock measurement steps.",
        window="Post-shock subset of the measurement window (step >= shock start step).",
    ),
    "pre_shock_mean_network_queue_vehicles": _queue(
        "pre_shock_mean_network_queue_vehicles",
        "Mean network_total_queue over pre-shock measurement steps.",
        window="Pre-shock subset of the measurement window.",
    ),
    "pre_shock_max_network_queue_vehicles": _queue(
        "pre_shock_max_network_queue_vehicles",
        "Maximum network_total_queue over pre-shock measurement steps.",
        window="Pre-shock subset of the measurement window.",
    ),
    "post_shock_queue_auc_vehicle_seconds": MetricDefinition(
        name="post_shock_queue_auc_vehicle_seconds",
        unit="vehicle-seconds",
        source="Canonical lane_telemetry.parquet (unique-lane halting counts).",
        aggregation=(
            "Trapezoidal integral of network_total_queue over simulation time from the shock "
            "start step to the last measurement step: sum((Q_i + Q_{i+1}) / 2 * (t_{i+1} - t_i)) "
            "with t_i the telemetry timestamp of step i."
        ),
        measurement_window="Post-shock subset of the measurement window.",
        edge_case_policy="0 if fewer than two post-shock samples exist.",
        population="network_total_queue = sum over unique incoming lanes; never movement rows.",
    ),
    "internal_lane_persistence_events": MetricDefinition(
        name="internal_lane_persistence_events",
        unit="events",
        source=(
            "Canonical junction_telemetry.parquet: vehicles present on the internal lanes of an "
            "intersection in two consecutive steps."
        ),
        aggregation=(
            "Sum over measurement steps and intersections (one row per intersection and step). "
            "Proxy of internal-junction occupancy, not a spillback or gridlock measurement."
        ),
        measurement_window=_QUEUE_WINDOW,
        edge_case_policy="Report 0 when no persistence events are observed.",
        population="Vehicles on junction internal lanes.",
    ),
    "offered_by_entry": MetricDefinition(
        name="offered_by_entry",
        unit="vehicles",
        source="Route file entry edges (scheduled departures).",
        aggregation=(
            "Exported per entry edge as `offered_by_entry__<entry_edge>`: cohort vehicles "
            "offered at that border entry."
        ),
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0 for an entry without offered vehicles.",
        population="Measurement cohort grouped by entry edge.",
    ),
    "departed_by_entry": MetricDefinition(
        name="departed_by_entry",
        unit="vehicles",
        source="Route file entry edges joined with SUMO tripinfo.",
        aggregation=(
            "Exported per entry edge as `departed_by_entry__<entry_edge>`: cohort vehicles of "
            "that entry that were inserted."
        ),
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0 for an entry without departures.",
        population="Measurement cohort grouped by entry edge.",
    ),
    "arrived_by_entry": MetricDefinition(
        name="arrived_by_entry",
        unit="vehicles",
        source="Route file entry edges joined with SUMO tripinfo.",
        aggregation=(
            "Exported per entry edge as `arrived_by_entry__<entry_edge>`: cohort vehicles of "
            "that entry that arrived before the run ended."
        ),
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0 for an entry without arrivals.",
        population="Measurement cohort grouped by entry edge.",
    ),
    "entry_departure_ratio": MetricDefinition(
        name="entry_departure_ratio",
        unit="ratio",
        source="Route file entry edges joined with SUMO tripinfo.",
        aggregation=(
            "Exported per entry edge as `entry_departure_ratio__<entry_edge>`: departed / "
            "offered at that entry; shows whether the intended demand pattern reaches the "
            "network or is hidden by insertion starvation."
        ),
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="Reported as 0.0 when the entry offered no vehicles.",
        population="Measurement cohort grouped by entry edge.",
    ),
    "min_entry_departure_ratio": MetricDefinition(
        name="min_entry_departure_ratio",
        unit="ratio",
        source="Route file entry edges joined with SUMO tripinfo.",
        aggregation="Minimum over entry edges of departed / offered (cohort).",
        measurement_window=_COHORT_WINDOW,
        edge_case_policy="0.0 for an entry with no departures.",
        population="Measurement cohort grouped by entry edge.",
    ),
    # --- comunicação ---------------------------------------------------------------
    "messages_sent": MetricDefinition(
        name="messages_sent",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages published by cooperative controllers.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy=(
            "For non-communicating controllers, report 0 or omit from communication tables."
        ),
    ),
    "messages_delivered": MetricDefinition(
        name="messages_delivered",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages delivered to destination inboxes.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy=(
            "For non-communicating controllers, report 0 or omit from communication tables."
        ),
    ),
    "messages_dropped": MetricDefinition(
        name="messages_dropped",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages dropped by the configured loss process.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no drops are observed.",
    ),
    "messages_stale": MetricDefinition(
        name="messages_stale",
        unit="messages",
        source="Cooperative controller message freshness accounting.",
        aggregation="Total received messages rejected as stale.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no stale messages are observed.",
    ),
    "bytes_sent": MetricDefinition(
        name="bytes_sent",
        unit="bytes",
        source="MessageBus serialized message accounting.",
        aggregation="Total serialized bytes published.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no messages are sent.",
    ),
    "bytes_delivered": MetricDefinition(
        name="bytes_delivered",
        unit="bytes",
        source="MessageBus serialized message accounting.",
        aggregation="Total serialized bytes delivered.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no messages are delivered.",
    ),
    "mean_message_age_steps": MetricDefinition(
        name="mean_message_age_steps",
        unit="simulation steps/message",
        source="Cooperative controller message freshness accounting.",
        aggregation="Arithmetic mean age of observed messages.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no messages are observed.",
    ),
    "max_message_age_steps": MetricDefinition(
        name="max_message_age_steps",
        unit="simulation steps",
        source="Cooperative controller message freshness accounting.",
        aggregation="Maximum observed message age.",
        measurement_window=_COMM_WINDOW,
        edge_case_policy="Report 0 when no messages are observed.",
    ),
    "sumo_teleports_total": MetricDefinition(
        name="sumo_teleports_total",
        unit="vehicles",
        source="SUMO statistics.xml (<teleports total>), persisted in run_metrics counts.",
        aggregation="Total number of vehicles teleported by SUMO during the run.",
        measurement_window="Whole run (not a cohort metric).",
        edge_case_policy=(
            "Reported as 0 when SUMO reports no teleports. S4 follows ALLOW_AND_MEASURE: a "
            "teleport never invalidates a run by itself and is always reported beside S4 results."
        ),
    ),
    "throughput_change_vs_zero_loss": MetricDefinition(
        name="throughput_change_vs_zero_loss",
        unit="vehicles",
        source="Derived from throughput rows grouped by scenario, controller, and seed.",
        aggregation="throughput(drop_probability=x) - throughput(drop_probability=0).",
        measurement_window="Same measurement window as throughput.",
        edge_case_policy=(
            "Only exported when a same-scenario/controller/seed zero-loss baseline exists."
        ),
    ),
}

# Métricas de pareamento que devem acompanhar métricas de viagens concluídas (condicionais) em
# qualquer análise.
COMPANION_METRICS: tuple[str, ...] = (
    "throughput",
    "completion_ratio_offered",
    "departure_ratio",
    "mean_network_queue_vehicles",
)

_POPULATION_METRICS: tuple[str, ...] = (
    "offered_vehicle_count",
    "departed_vehicle_count",
    "arrived_vehicle_count",
    "never_inserted_vehicle_count",
    "unfinished_in_network_count",
    "departure_ratio",
    "completion_ratio_offered",
    "completion_ratio_departed",
    "mean_depart_delay_seconds",
)

_QUEUE_METRICS: tuple[str, ...] = (
    "mean_network_queue_vehicles",
    "max_network_queue_vehicles",
    "mean_intersection_queue_vehicles",
    "max_intersection_queue_vehicles",
    "max_lane_queue_vehicles",
)

SCENARIO_METRICS: Mapping[str, tuple[str, ...]] = {
    "S1_BALANCED": (
        "throughput",
        "mean_travel_time",
        "mean_waiting_time",
        "mean_time_loss",
        "mean_stops",
        *_QUEUE_METRICS,
        *_POPULATION_METRICS,
    ),
    "S2_DIRECTIONAL_PEAK": (
        "throughput",
        "mean_stops",
        "mean_time_loss",
        "corridor_throughput",
        "corridor_mean_travel_time",
        "corridor_mean_stops",
        "min_entry_departure_ratio",
        *_QUEUE_METRICS,
        *_POPULATION_METRICS,
    ),
    "S3_DEMAND_SHIFT": (
        "post_shock_mean_network_queue_vehicles",
        "post_shock_max_network_queue_vehicles",
        "post_shock_time_loss",
        "post_shock_queue_auc_vehicle_seconds",
        "throughput",
        *_POPULATION_METRICS,
    ),
    "S4_LOCAL_SATURATION": (
        "throughput",
        "mean_time_loss",
        "mean_travel_time",
        "internal_lane_persistence_events",
        *_QUEUE_METRICS,
        *_POPULATION_METRICS,
    ),
    "S5_COMMUNICATION_DEGRADATION": (
        "throughput",
        "mean_waiting_time",
        "mean_time_loss",
        "mean_network_queue_vehicles",
        "messages_sent",
        "messages_delivered",
        "messages_dropped",
        "messages_stale",
        "bytes_sent",
        "bytes_delivered",
        "mean_message_age_steps",
        "max_message_age_steps",
        "throughput_change_vs_zero_loss",
        "completion_ratio_offered",
    ),
}

METRIC_DEFINITION_ALIASES: Mapping[str, str] = {
    "network_throughput": "throughput",
    "vehicles_arrived": "throughput",
    "arrived": "throughput",
    "waiting_time": "mean_waiting_time",
    "avg_waiting_time": "mean_waiting_time",
    "average_waiting_time": "mean_waiting_time",
    "time_loss": "mean_time_loss",
    "avg_time_loss": "mean_time_loss",
    "average_time_loss": "mean_time_loss",
    "travel_time": "mean_travel_time",
    "mean_travel_time_seconds": "mean_travel_time",
    "stops": "mean_stops",
    "corridor_travel_time": "corridor_mean_travel_time",
    "corridor_stops": "corridor_mean_stops",
    "messages": "messages_sent",
    "bytes": "bytes_sent",
    "serialized_bytes": "bytes_sent",
    "message_bytes": "bytes_sent",
    "average_message_age": "mean_message_age_steps",
    "max_observed_message_age": "max_message_age_steps",
}
# Nomes legados ambíguos (``mean_queue``, ``max_queue``, ``queue``, ``post_shock_*_queue``,
# ``post_shock_queue_auc``) intencionalmente NÃO têm alias: uma métrica de fila deve sempre nomear
# seu escopo (lane / interseção / rede).


def metric_definition_payload(metric_names: Sequence[str]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for metric in sorted(set(metric_names)):
        definition = METRIC_DEFINITIONS.get(metric)
        if definition is not None:
            payload.append(definition.as_dict())
            continue
        canonical = METRIC_DEFINITION_ALIASES.get(metric)
        if canonical is None:
            continue
        alias_payload = METRIC_DEFINITIONS[canonical].as_dict()
        alias_payload["name"] = metric
        alias_payload["aggregation"] = f"Alias of `{canonical}`. {alias_payload['aggregation']}"
        payload.append(alias_payload)
    return payload
