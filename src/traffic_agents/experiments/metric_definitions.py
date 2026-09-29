from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

CORRIDOR_DEFINITION_VERSION = "west-east-middle-corridor-v1"
CORRIDOR_DEFINITION = {
    "label": "West -> A4 -> A5 -> A6 -> East",
    "sumo_tls_path": ("A1", "B1", "C1"),
    "entry_edge": "left1A1",
    "through_edges": ("A1B1", "B1C1"),
    "exit_edge": "C1right1",
}


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    unit: str
    source: str
    aggregation: str
    measurement_window: str
    edge_case_policy: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


METRIC_DEFINITIONS: Mapping[str, MetricDefinition] = {
    "throughput": MetricDefinition(
        name="throughput",
        unit="vehicles",
        source="SUMO arrived counts in the measurement window.",
        aggregation="Count of vehicles that arrive during the configured measurement window.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no vehicles arrive, report 0.",
    ),
    "network_throughput": MetricDefinition(
        name="network_throughput",
        unit="vehicles",
        source="SUMO arrived counts in the measurement window.",
        aggregation="Alias of throughput when the whole network is the counting scope.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no vehicles arrive, report 0.",
    ),
    "mean_travel_time": MetricDefinition(
        name="mean_travel_time",
        unit="seconds/vehicle",
        source="SUMO tripinfo duration for arrived vehicles.",
        aggregation="Arithmetic mean over vehicles that arrived in the measurement window.",
        measurement_window="Warmup excluded by final metric aggregation policy.",
        edge_case_policy="If no vehicles arrive, omit the metric for that run.",
    ),
    "mean_waiting_time": MetricDefinition(
        name="mean_waiting_time",
        unit="seconds/vehicle",
        source="SUMO tripinfo waitingTime for arrived vehicles.",
        aggregation="Arithmetic mean over vehicles that arrived in the measurement window.",
        measurement_window="Warmup excluded by final metric aggregation policy.",
        edge_case_policy="If no vehicles arrive, omit the metric for that run.",
    ),
    "mean_time_loss": MetricDefinition(
        name="mean_time_loss",
        unit="seconds/vehicle",
        source="SUMO tripinfo timeLoss for arrived vehicles.",
        aggregation="Arithmetic mean over vehicles that arrived in the measurement window.",
        measurement_window="Warmup excluded by final metric aggregation policy.",
        edge_case_policy="If no vehicles arrive, omit the metric for that run.",
    ),
    "mean_queue": MetricDefinition(
        name="mean_queue",
        unit="vehicles",
        source="intersection_trace.csv movement-level queue records.",
        aggregation="Arithmetic mean over post-warmup movement queue samples.",
        measurement_window="Warmup excluded; only measurement rows are included.",
        edge_case_policy="If no trace rows exist, omit the metric for that run.",
    ),
    "max_queue": MetricDefinition(
        name="max_queue",
        unit="vehicles",
        source="intersection_trace.csv movement-level queue records.",
        aggregation="Maximum post-warmup movement queue sample.",
        measurement_window="Warmup excluded; only measurement rows are included.",
        edge_case_policy="If no trace rows exist, omit the metric for that run.",
    ),
    "mean_stops": MetricDefinition(
        name="mean_stops",
        unit="stops/vehicle",
        source="SUMO tripinfo waitingCount for arrived vehicles.",
        aggregation="Arithmetic mean over vehicles that arrived in the measurement window.",
        measurement_window="Warmup excluded by final metric aggregation policy.",
        edge_case_policy="If no vehicles arrive, omit the metric for that run.",
    ),
    "corridor_throughput": MetricDefinition(
        name="corridor_throughput",
        unit="vehicles",
        source=f"SUMO tripinfo joined to route/flow IDs for {CORRIDOR_DEFINITION_VERSION}.",
        aggregation="Count of arrived vehicles assigned to the corridor.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no corridor vehicles arrive, report 0.",
    ),
    "corridor_travel_time": MetricDefinition(
        name="corridor_travel_time",
        unit="seconds/vehicle",
        source=f"SUMO tripinfo duration filtered to {CORRIDOR_DEFINITION_VERSION}.",
        aggregation="Arithmetic mean over arrived corridor vehicles.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no corridor vehicles arrive, omit the metric for that run.",
    ),
    "corridor_stops": MetricDefinition(
        name="corridor_stops",
        unit="stops/vehicle",
        source=f"SUMO tripinfo waitingCount filtered to {CORRIDOR_DEFINITION_VERSION}.",
        aggregation="Arithmetic mean over arrived corridor vehicles.",
        measurement_window="Warmup excluded; measurement interval from scenario config.",
        edge_case_policy="If no corridor vehicles arrive, omit the metric for that run.",
    ),
    "post_shock_mean_queue": MetricDefinition(
        name="post_shock_mean_queue",
        unit="vehicles",
        source="intersection_trace.csv movement-level queue records after the frozen shock time.",
        aggregation="Arithmetic mean of post-shock queue samples.",
        measurement_window="Post-shock subset of the measurement window.",
        edge_case_policy="If no post-shock trace rows exist, omit the metric for that run.",
    ),
    "post_shock_max_queue": MetricDefinition(
        name="post_shock_max_queue",
        unit="vehicles",
        source="intersection_trace.csv movement-level queue records after the frozen shock time.",
        aggregation="Maximum post-shock queue sample.",
        measurement_window="Post-shock subset of the measurement window.",
        edge_case_policy="If no post-shock trace rows exist, omit the metric for that run.",
    ),
    "post_shock_time_loss": MetricDefinition(
        name="post_shock_time_loss",
        unit="seconds/vehicle",
        source="SUMO tripinfo timeLoss for vehicles departing at or after the shock time.",
        aggregation="Arithmetic mean over post-shock arrived vehicles.",
        measurement_window="Post-shock subset of the measurement window.",
        edge_case_policy="If no post-shock vehicles arrive, omit the metric for that run.",
    ),
    "post_shock_queue_auc": MetricDefinition(
        name="post_shock_queue_auc",
        unit="vehicle-seconds",
        source="intersection_trace.csv movement-level queue records after the frozen shock time.",
        aggregation="Trapezoidal integration of the post-shock queue time series.",
        measurement_window="Post-shock subset of the measurement window.",
        edge_case_policy="If fewer than two post-shock queue samples exist, report 0.",
    ),
    "internal_lane_persistence_events": MetricDefinition(
        name="internal_lane_persistence_events",
        unit="events",
        source="intersection_trace.csv internal-lane vehicle persistence tracker.",
        aggregation="Sum of post-warmup persistence events.",
        measurement_window="Warmup excluded; only measurement rows are included.",
        edge_case_policy="Report 0 when no persistence events are observed.",
    ),
    "messages_sent": MetricDefinition(
        name="messages_sent",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages published by cooperative controllers.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy=(
            "For non-communicating controllers, report 0 or omit from communication tables."
        ),
    ),
    "messages_delivered": MetricDefinition(
        name="messages_delivered",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages delivered to destination inboxes.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy=(
            "For non-communicating controllers, report 0 or omit from communication tables."
        ),
    ),
    "messages_dropped": MetricDefinition(
        name="messages_dropped",
        unit="messages",
        source="MessageBus communication metrics.",
        aggregation="Total messages dropped by the configured loss process.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no drops are observed.",
    ),
    "messages_stale": MetricDefinition(
        name="messages_stale",
        unit="messages",
        source="Cooperative controller message freshness accounting.",
        aggregation="Total received messages rejected as stale.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no stale messages are observed.",
    ),
    "bytes_sent": MetricDefinition(
        name="bytes_sent",
        unit="bytes",
        source="MessageBus serialized message accounting.",
        aggregation="Total serialized bytes published.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no messages are sent.",
    ),
    "bytes_delivered": MetricDefinition(
        name="bytes_delivered",
        unit="bytes",
        source="MessageBus serialized message accounting.",
        aggregation="Total serialized bytes delivered.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no messages are delivered.",
    ),
    "mean_message_age_steps": MetricDefinition(
        name="mean_message_age_steps",
        unit="simulation steps/message",
        source="Cooperative controller message freshness accounting.",
        aggregation="Arithmetic mean age of observed messages.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no messages are observed.",
    ),
    "max_message_age_steps": MetricDefinition(
        name="max_message_age_steps",
        unit="simulation steps",
        source="Cooperative controller message freshness accounting.",
        aggregation="Maximum observed message age.",
        measurement_window="Full simulated run, including warmup, unless report labels otherwise.",
        edge_case_policy="Report 0 when no messages are observed.",
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

SCENARIO_METRICS: Mapping[str, tuple[str, ...]] = {
    "S1_BALANCED": (
        "throughput",
        "mean_travel_time",
        "mean_waiting_time",
        "mean_time_loss",
        "mean_queue",
        "max_queue",
        "mean_stops",
    ),
    "S2_DIRECTIONAL_PEAK": (
        "network_throughput",
        "mean_stops",
        "mean_time_loss",
        "mean_queue",
        "corridor_throughput",
        "corridor_travel_time",
        "corridor_stops",
    ),
    "S3_DEMAND_SHIFT": (
        "post_shock_mean_queue",
        "post_shock_max_queue",
        "post_shock_time_loss",
        "post_shock_queue_auc",
    ),
    "S4_LOCAL_SATURATION": (
        "mean_queue",
        "max_queue",
        "throughput",
        "mean_time_loss",
        "mean_travel_time",
        "internal_lane_persistence_events",
    ),
    "S5_COMMUNICATION_DEGRADATION": (
        "throughput",
        "mean_waiting_time",
        "mean_time_loss",
        "mean_queue",
        "messages_sent",
        "messages_delivered",
        "messages_dropped",
        "messages_stale",
        "bytes_sent",
        "bytes_delivered",
        "mean_message_age_steps",
        "max_message_age_steps",
        "throughput_change_vs_zero_loss",
    ),
}

METRIC_DEFINITION_ALIASES: Mapping[str, str] = {
    "waiting_time": "mean_waiting_time",
    "avg_waiting_time": "mean_waiting_time",
    "average_waiting_time": "mean_waiting_time",
    "time_loss": "mean_time_loss",
    "avg_time_loss": "mean_time_loss",
    "average_time_loss": "mean_time_loss",
    "queue": "mean_queue",
    "avg_queue": "mean_queue",
    "average_queue": "mean_queue",
    "movement_queue_mean": "mean_queue",
    "maximum_queue": "max_queue",
    "movement_queue_max": "max_queue",
    "travel_time": "mean_travel_time",
    "mean_travel_time_seconds": "mean_travel_time",
    "stops": "mean_stops",
    "vehicles_arrived": "throughput",
    "arrived": "throughput",
    "messages": "messages_sent",
    "bytes": "bytes_sent",
    "serialized_bytes": "bytes_sent",
    "message_bytes": "bytes_sent",
    "average_message_age": "mean_message_age_steps",
    "max_observed_message_age": "max_message_age_steps",
}


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
