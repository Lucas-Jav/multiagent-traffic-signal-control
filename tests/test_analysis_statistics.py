from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from analysis.statistics import AnalysisConfig, AnalysisValidationError, run_analysis


def test_run_analysis_writes_descriptive_and_pairwise_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 10.0),
            _row("C1_COOPERATIVE_COMPACT", 1, 8.0),
            _row("B2_LOCAL_PRESSURE", 2, 20.0),
            _row("C1_COOPERATIVE_COMPACT", 2, 18.0),
            _row("B2_LOCAL_PRESSURE", 3, 30.0),
            _row("C1_COOPERATIVE_COMPACT", 3, 27.0),
        ],
    )

    payload = run_analysis(
        AnalysisConfig(
            input_path=input_path,
            output_parquet_path=tmp_path / "analysis.parquet",
            output_json_path=tmp_path / "analysis.json",
            bootstrap_seed=123,
            bootstrap_resamples=200,
        )
    )

    comparison = payload["pairwise_comparisons"][0]
    assert comparison["controller_a"] == "B2_LOCAL_PRESSURE"
    assert comparison["controller_b"] == "C1_COOPERATIVE_COMPACT"
    assert comparison["n_pairs"] == 3
    assert comparison["mean_difference"] == pytest.approx(-7 / 3)
    assert comparison["median_difference"] == pytest.approx(-2.0)
    assert comparison["relative_difference"] == pytest.approx((-0.2 - 0.1 - 0.1) / 3)
    assert comparison["bootstrap_seed"] == 123
    assert comparison["bootstrap_resamples"] == 200

    descriptive = payload["descriptive_statistics"]
    b2_stats = next(item for item in descriptive if item["controller"] == "B2_LOCAL_PRESSURE")
    assert b2_stats["count"] == 3
    assert b2_stats["mean"] == pytest.approx(20.0)
    assert b2_stats["median"] == pytest.approx(20.0)
    assert b2_stats["std"] == pytest.approx(10.0)
    assert b2_stats["q1"] == pytest.approx(15.0)
    assert b2_stats["q3"] == pytest.approx(25.0)
    assert b2_stats["iqr"] == pytest.approx(10.0)

    parquet_rows = pq.read_table(tmp_path / "analysis.parquet").to_pylist()
    assert parquet_rows[0]["mean_difference"] == pytest.approx(-7 / 3)
    json_payload = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
    assert json_payload["bootstrap"]["seed"] == 123


def test_run_analysis_fails_on_missing_pair(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 10.0),
            _row("C1_COOPERATIVE_COMPACT", 1, 8.0),
            _row("B2_LOCAL_PRESSURE", 2, 20.0),
        ],
    )

    with pytest.raises(AnalysisValidationError, match="missing paired runs"):
        run_analysis(AnalysisConfig(input_path=input_path))


def test_run_analysis_fails_on_duplicate_seed_for_same_controller(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 10.0),
            _row("B2_LOCAL_PRESSURE", 1, 11.0),
            _row("C1_COOPERATIVE_COMPACT", 1, 8.0),
        ],
    )

    with pytest.raises(AnalysisValidationError, match="duplicate metric rows"):
        run_analysis(AnalysisConfig(input_path=input_path))


def test_run_analysis_fails_on_different_route_hash(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 10.0, route_hash="route-a"),
            _row("C1_COOPERATIVE_COMPACT", 1, 8.0, route_hash="route-b"),
        ],
    )

    with pytest.raises(AnalysisValidationError, match="route_hash"):
        run_analysis(AnalysisConfig(input_path=input_path))


def test_run_analysis_does_not_compute_relative_difference_for_zero_baseline(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 0.0),
            _row("C1_COOPERATIVE_COMPACT", 1, 5.0),
        ],
    )

    payload = run_analysis(
        AnalysisConfig(
            input_path=input_path,
            output_parquet_path=tmp_path / "analysis.parquet",
            output_json_path=tmp_path / "analysis.json",
            bootstrap_resamples=10,
        )
    )

    comparison = payload["pairwise_comparisons"][0]
    assert comparison["mean_difference"] == pytest.approx(5.0)
    assert comparison["relative_difference"] is None
    assert comparison["relative_difference_valid"] is False


def test_run_analysis_fails_on_nan_metric_value(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, float("nan")),
            _row("C1_COOPERATIVE_COMPACT", 1, 5.0),
        ],
    )

    with pytest.raises(AnalysisValidationError, match="value must be finite"):
        run_analysis(AnalysisConfig(input_path=input_path))


def test_run_analysis_fails_on_failed_runs(tmp_path: Path) -> None:
    input_path = tmp_path / "combined_metrics.parquet"
    _write_metrics(
        input_path,
        [
            _row("B2_LOCAL_PRESSURE", 1, 0.0, status="failed"),
            _row("C1_COOPERATIVE_COMPACT", 1, 5.0),
        ],
    )

    with pytest.raises(AnalysisValidationError, match="failed runs are present"):
        run_analysis(AnalysisConfig(input_path=input_path))


def _write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    pq.write_table(pa.Table.from_pylist(rows), path)


def _row(
    controller: str,
    seed: int,
    value: float,
    *,
    route_hash: str = "route-a",
    network_hash: str = "network-a",
    phase_plan: str = "phase-a",
    status: str = "success",
) -> dict[str, object]:
    return {
        "scenario": "s1",
        "controller": controller,
        "metric": "mean_delay",
        "value": value,
        "seed": seed,
        "route_hash": route_hash,
        "network_hash": network_hash,
        "phase_plan": phase_plan,
        "turning_ratios": {"straight": 0.6, "left": 0.2, "right": 0.2},
        "status": status,
    }
