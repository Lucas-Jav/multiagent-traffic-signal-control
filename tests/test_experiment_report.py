from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from traffic_agents.experiments.report import ReportGenerationError, generate_experiment_report


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
    }
    assert report.figures_dir == experiment_folder / "figures"
    assert {path.name for path in report.generated_files} == expected_files
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


def _write_analysis(path: Path) -> None:
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "scenario": "s1",
                    "metric": "waiting_time",
                    "controller_a": "B2_LOCAL_PRESSURE",
                    "controller_b": "C1_COOPERATIVE_COMPACT",
                    "n_pairs": 3,
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
                    "n_pairs": 3,
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
