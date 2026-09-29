from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from traffic_agents.experiments.report import (
    ReportGenerationError,
    generate_experiment_report,
    generate_experiment_summary,
)


def test_generate_experiment_report_writes_expected_figures(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "smoke"
    experiment_folder.mkdir(parents=True)
    _write_combined_metrics(experiment_folder / "combined_metrics.parquet")
    _write_analysis(experiment_folder / "analysis.parquet")

    report = generate_experiment_report(experiment_folder)

    expected_files = {
        "waiting_time_by_controller.png",
        "time_loss_by_controller.png",
        "queue_by_controller.png",
        "max_queue_by_controller.png",
        "throughput_by_controller.png",
        "communication_cost.png",
        "delay_sensitivity.png",
        "drop_sensitivity.png",
        "turning_movement_queue.png",
        "throughput_change_vs_zero_loss_by_controller.png",
    }
    assert report.figures_dir == experiment_folder / "figures"
    assert {path.name for path in report.generated_files} == expected_files
    assert report.metric_definitions_path == experiment_folder / "metric_definitions.json"
    metric_definitions = json.loads(report.metric_definitions_path.read_text(encoding="utf-8"))
    exported_metric_names = {definition["name"] for definition in metric_definitions}
    assert "waiting_time" in exported_metric_names
    assert "throughput" in exported_metric_names
    assert "throughput_change_vs_zero_loss" in exported_metric_names
    assert "messages_sent" in exported_metric_names
    assert "serialized_bytes" in exported_metric_names
    for figure_path in report.generated_files:
        assert figure_path.parent == experiment_folder / "figures"
        assert figure_path.exists()
        assert figure_path.stat().st_size > 0


def test_generate_experiment_report_fails_on_missing_inputs(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "missing"
    experiment_folder.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match=r"combined_metrics\.parquet"):
        generate_experiment_report(experiment_folder)

    pq.write_table(pa.Table.from_pylist([]), experiment_folder / "combined_metrics.parquet")
    with pytest.raises(FileNotFoundError, match=r"analysis\.parquet"):
        generate_experiment_report(experiment_folder)


def test_generate_experiment_report_fails_on_failed_runs(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "failed"
    experiment_folder.mkdir(parents=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                _metric_row("C1_COOPERATIVE_COMPACT", "waiting_time", 0.0, status="failed"),
            ]
        ),
        experiment_folder / "combined_metrics.parquet",
    )
    _write_analysis(experiment_folder / "analysis.parquet")

    with pytest.raises(ReportGenerationError, match="failed runs"):
        generate_experiment_report(experiment_folder)

    figures_dir = experiment_folder / "figures"
    assert not figures_dir.exists()


def test_generate_experiment_report_uses_deterministic_output_path(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "deterministic"
    experiment_folder.mkdir(parents=True)
    _write_combined_metrics(experiment_folder / "combined_metrics.parquet")
    _write_analysis(experiment_folder / "analysis.parquet")

    first = generate_experiment_report(experiment_folder)
    second = generate_experiment_report(experiment_folder)

    assert first.figures_dir == second.figures_dir == experiment_folder / "figures"
    assert tuple(path.name for path in first.generated_files) == tuple(
        path.name for path in second.generated_files
    )


def test_generate_experiment_summary_writes_required_observed_fields(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "summary"
    figures_dir = experiment_folder / "figures"
    figures_dir.mkdir(parents=True)
    (figures_dir / "waiting_time_by_controller.png").write_bytes(b"png")
    _write_manifest(experiment_folder / "manifest.json")
    _write_summary_combined_metrics(experiment_folder / "combined_metrics.parquet")
    _write_analysis(experiment_folder / "analysis.parquet")
    _write_analysis_json(experiment_folder / "analysis.json")

    report = generate_experiment_summary(experiment_folder)

    assert report.summary_path == experiment_folder / "summary.md"
    content = report.summary_path.read_text(encoding="utf-8")
    assert "# Experiment Summary: summary" in content
    assert "| Git SHA | abc123 |" in content
    assert "| SUMO version | 1.27.1 |" in content
    assert "| Experiment config hash | cfg-hash |" in content
    assert "| Network hash | net-hash |" in content
    assert "| Route hashes | route-a |" in content
    assert "| Phase plan version | phase-v1 |" in content
    assert "| Movement model version | movement-v1 |" in content
    assert "| Completed runs | 2 |" in content
    assert "| Failed runs | 1 |" in content
    assert "Waiting time (s)" in content
    assert "Messages (count)" in content
    assert "N=2" in content
    assert "IC95 [-1.5, -0.5]" in content
    assert "[waiting_time_by_controller.png](figures/waiting_time_by_controller.png)" in content
    forbidden = ("better", "superior", "winning", "resolveu congestionamento")
    assert not any(term in content.lower() for term in forbidden)


def test_generate_experiment_summary_fails_on_missing_inputs(tmp_path: Path) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "missing-summary"
    experiment_folder.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match=r"manifest\.json"):
        generate_experiment_summary(experiment_folder)


def _write_combined_metrics(path: Path) -> None:
    rows: list[dict[str, object]] = []
    controllers = (
        "B2_LOCAL_PRESSURE",
        "C1_COOPERATIVE_COMPACT",
        "C2_COOPERATIVE_EXPANDED",
    )
    traffic_metrics = {
        "waiting_time": (10.0, 9.0, 8.5),
        "time_loss": (20.0, 19.0, 18.0),
        "queue": (4.0, 3.5, 3.0),
        "max_queue": (9.0, 8.0, 7.0),
        "throughput": (100.0, 102.0, 103.0),
    }
    for seed in (1, 2, 3):
        for controller_index, controller in enumerate(controllers):
            for metric, base_values in traffic_metrics.items():
                rows.append(
                    _metric_row(
                        controller,
                        metric,
                        base_values[controller_index] + seed,
                        seed=seed,
                        delay_steps=float(seed - 1),
                        drop_probability=0.05 * (seed - 1),
                    )
                )
            rows.append(
                _metric_row(
                    controller,
                    "messages_sent",
                    20.0 + seed + controller_index,
                    seed=seed,
                    delay_steps=float(seed - 1),
                    drop_probability=0.05 * (seed - 1),
                )
            )
            rows.append(
                _metric_row(
                    controller,
                    "serialized_bytes",
                    1000.0 + seed + controller_index * 100,
                    seed=seed,
                    delay_steps=float(seed - 1),
                    drop_probability=0.05 * (seed - 1),
                )
            )
    for turn_type, value in (("left", 2.0), ("right", 2.5), ("straight", 5.0)):
        rows.append(
            _metric_row(
                "B2_LOCAL_PRESSURE",
                "turning_movement_queue",
                value,
                turn_type=turn_type,
            )
        )
    pq.write_table(pa.Table.from_pylist(rows), path)


def _write_summary_combined_metrics(path: Path) -> None:
    rows = [
        _summary_metric_row("run-b2-1", "B2_LOCAL_PRESSURE", "waiting_time", 10.0),
        _summary_metric_row("run-b2-1", "B2_LOCAL_PRESSURE", "messages_sent", 20.0),
        _summary_metric_row("run-c1-1", "C1_COOPERATIVE_COMPACT", "waiting_time", 9.0),
        _summary_metric_row("run-c1-1", "C1_COOPERATIVE_COMPACT", "messages_sent", 22.0),
        _summary_metric_row(
            "run-c1-2",
            "C1_COOPERATIVE_COMPACT",
            "waiting_time",
            0.0,
            status="failed",
        ),
    ]
    pq.write_table(pa.Table.from_pylist(rows), path)


def _write_analysis(path: Path) -> None:
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "scenario": "s1",
                    "metric": "waiting_time",
                    "controller_a": "B2_LOCAL_PRESSURE",
                    "controller_b": "C1_COOPERATIVE_COMPACT",
                    "n_pairs": 2,
                    "mean_difference": -1.0,
                    "median_difference": -1.0,
                    "ci95_low": -1.5,
                    "ci95_high": -0.5,
                    "relative_difference": -0.1,
                    "test_name": None,
                    "p_value": None,
                },
                {
                    "scenario": "s1",
                    "metric": "time_loss",
                    "controller_a": "B2_LOCAL_PRESSURE",
                    "controller_b": "C1_COOPERATIVE_COMPACT",
                    "n_pairs": 2,
                    "mean_difference": -1.0,
                    "median_difference": -1.0,
                    "ci95_low": -1.5,
                    "ci95_high": -0.5,
                    "relative_difference": -0.05,
                    "test_name": None,
                    "p_value": None,
                },
            ]
        ),
        path,
    )


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "experiment_id": "summary",
                "batch_id": "20260910T000000Z",
                "scenario": "scenarios/grid_3x3/scenario.yaml",
                "controllers": ["B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT"],
                "seeds": [1],
                "runs": [
                    {
                        "run_id": "run-b2-1",
                        "controller_id": "B2_LOCAL_PRESSURE",
                        "seed": 1,
                    },
                    {
                        "run_id": "run-c1-1",
                        "controller_id": "C1_COOPERATIVE_COMPACT",
                        "seed": 1,
                    },
                    {
                        "run_id": "run-c1-2",
                        "controller_id": "C1_COOPERATIVE_COMPACT",
                        "seed": 2,
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_analysis_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "input": "combined_metrics.parquet",
                "bootstrap": {"seed": 123, "resamples": 200},
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _metric_row(
    controller: str,
    metric: str,
    value: float,
    *,
    seed: int = 1,
    delay_steps: float = 0.0,
    drop_probability: float = 0.0,
    turn_type: str | None = None,
    status: str = "success",
) -> dict[str, object]:
    row: dict[str, object] = {
        "scenario": "s1",
        "controller": controller,
        "metric": metric,
        "value": value,
        "seed": seed,
        "delay_steps": delay_steps,
        "drop_probability": drop_probability,
        "status": status,
        "turn_type": turn_type,
    }
    return row


def _summary_metric_row(
    run_id: str,
    controller: str,
    metric: str,
    value: float,
    *,
    status: str = "success",
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "scenario": "s1",
        "controller": controller,
        "metric": metric,
        "value": value,
        "seed": 1,
        "status": status,
        "git_sha": "abc123",
        "sumo_version": "1.27.1",
        "experiment_config_hash": "cfg-hash",
        "network_hash": "net-hash",
        "route_hash": "route-a",
        "scenario_hash": "scenario-hash",
        "phase_plan_version": "phase-v1",
        "movement_model_version": "movement-v1",
    }
