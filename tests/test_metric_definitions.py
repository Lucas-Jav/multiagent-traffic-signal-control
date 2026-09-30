from pathlib import Path

from traffic_agents.experiments.metric_definitions import (
    COMPANION_METRICS,
    CORRIDOR_DEFINITION,
    CORRIDOR_DEFINITION_VERSION,
    METRIC_DEFINITION_ALIASES,
    METRIC_DEFINITIONS,
    SCENARIO_METRICS,
    metric_definition_payload,
)


def test_final_protocol_metrics_have_operational_definitions() -> None:
    for scenario, metrics in SCENARIO_METRICS.items():
        assert metrics, scenario
        for metric in metrics:
            definition = METRIC_DEFINITIONS[metric]
            assert definition.name == metric
            assert definition.unit
            assert definition.source
            assert definition.aggregation
            assert definition.measurement_window
            assert definition.edge_case_policy
            assert definition.population


def test_recovery_time_is_not_declared_as_implemented_metric() -> None:
    assert "recovery_time_seconds" not in METRIC_DEFINITIONS
    assert all("recovery_time_seconds" not in metrics for metrics in SCENARIO_METRICS.values())


def test_corridor_definition_is_explicit_and_versioned() -> None:
    assert CORRIDOR_DEFINITION_VERSION == "west-east-middle-corridor-v2"
    assert CORRIDOR_DEFINITION == {
        "label": "West -> A4 -> A5 -> A6 -> East",
        "sumo_tls_path": ("A1", "B1", "C1"),
        "entry_edge": "left1A1",
        "through_edges": ("A1B1", "B1C1"),
        "exit_edge": "C1right1",
        "membership_rule": "route traverses edge A1B1 immediately followed by edge B1C1",
    }


def test_metric_definition_payload_exports_known_metrics_only() -> None:
    payload = metric_definition_payload(
        ["throughput", "unknown_metric", "messages_dropped", "throughput"]
    )

    assert [definition["name"] for definition in payload] == [
        "messages_dropped",
        "throughput",
    ]


def test_queue_metrics_always_name_their_scope() -> None:
    for ambiguous in ("mean_queue", "max_queue", "queue", "post_shock_queue_auc"):
        assert ambiguous not in METRIC_DEFINITIONS
        assert ambiguous not in METRIC_DEFINITION_ALIASES
    for metrics in SCENARIO_METRICS.values():
        assert not {"mean_queue", "max_queue"} & set(metrics)
    scopes = ("network", "intersection", "lane")
    queue_metrics = [name for name in METRIC_DEFINITIONS if name.endswith("queue_vehicles")]
    assert queue_metrics
    assert all(any(scope in name for scope in scopes) for name in queue_metrics)


def test_max_lane_queue_documents_physical_saturation() -> None:
    definition = METRIC_DEFINITIONS["max_lane_queue_vehicles"]

    assert "storage capacity" in definition.aggregation
    assert "loses discriminatory power" in definition.aggregation


def test_completed_trip_metrics_are_labeled_conditional() -> None:
    conditional = {
        name for name, definition in METRIC_DEFINITIONS.items() if definition.completed_trips_only
    }

    assert {
        "mean_travel_time",
        "mean_waiting_time",
        "mean_time_loss",
        "mean_stops",
        "post_shock_time_loss",
    } <= conditional
    for name in conditional:
        assert "conditional" in METRIC_DEFINITIONS[name].population.lower()
        assert METRIC_DEFINITIONS[name].as_dict()["completed_trips_only"] == "true"
    assert not METRIC_DEFINITIONS["throughput"].completed_trips_only
    assert set(COMPANION_METRICS) <= set(METRIC_DEFINITIONS)


def test_post_shock_auc_definition_is_frozen() -> None:
    definition = METRIC_DEFINITIONS["post_shock_queue_auc_vehicle_seconds"]

    assert definition.unit == "vehicle-seconds"
    assert "Trapezoidal" in definition.aggregation
    assert "network_total_queue" in definition.aggregation
    assert "never movement rows" in definition.population


def test_metrics_document_contains_final_metric_names() -> None:
    content = Path("docs/methodology/metrics.md").read_text(encoding="utf-8")

    for metric in METRIC_DEFINITIONS:
        assert metric in content, metric
