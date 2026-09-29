from pathlib import Path

from traffic_agents.experiments.metric_definitions import (
    CORRIDOR_DEFINITION,
    CORRIDOR_DEFINITION_VERSION,
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


def test_recovery_time_is_not_declared_as_implemented_metric() -> None:
    assert "recovery_time_seconds" not in METRIC_DEFINITIONS
    assert all("recovery_time_seconds" not in metrics for metrics in SCENARIO_METRICS.values())


def test_corridor_definition_is_explicit_and_versioned() -> None:
    assert CORRIDOR_DEFINITION_VERSION == "west-east-middle-corridor-v1"
    assert CORRIDOR_DEFINITION == {
        "label": "West -> A4 -> A5 -> A6 -> East",
        "sumo_tls_path": ("A1", "B1", "C1"),
        "entry_edge": "left1A1",
        "through_edges": ("A1B1", "B1C1"),
        "exit_edge": "C1right1",
    }


def test_metric_definition_payload_exports_known_metrics_only() -> None:
    payload = metric_definition_payload(
        ["throughput", "unknown_metric", "messages_dropped", "throughput"]
    )

    assert [definition["name"] for definition in payload] == [
        "messages_dropped",
        "throughput",
    ]


def test_metrics_document_contains_final_metric_names() -> None:
    content = Path("docs/methodology/metrics.md").read_text(encoding="utf-8")

    for metric in (
        "throughput",
        "mean_travel_time",
        "corridor_throughput",
        "post_shock_queue_auc",
        "internal_lane_persistence_events",
        "throughput_change_vs_zero_loss",
    ):
        assert metric in content
