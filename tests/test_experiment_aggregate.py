from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest

from analysis.statistics import _normalize_records
from traffic_agents.experiments.aggregate import (
    COMBINED_METRICS_FILE,
    ExperimentAggregationError,
    build_combined_metrics,
)


def write_run(
    root: Path,
    name: str,
    *,
    controller: str,
    finalized: bool = True,
    metrics: dict[str, float] | None = None,
) -> Path:
    run_dir = root / "runs" / "batch" / name
    run_dir.mkdir(parents=True)
    manifest: dict[str, Any] = {
        "run_id": name,
        "scenario_id": "grid_3x3",
        "demand_profile": "S1_BALANCED",
        "seed": 42,
        "controller": {"controller_id": controller},
        "communication": {"delay_steps": 0, "drop_probability": 0.0},
        "network_sha256": "net",
        "route_sha256": "route",
        "phase_plan_sha256": "phase",
        "phase_plan_version": "v1",
        "movement_model_version": "m1",
        "movement_model_sha256": "mm",
        "turning_ratios": {"straight": 0.7, "left": 0.15, "right": 0.15},
        "turning_config_sha256": "turn",
        "communication_topology_sha256": "topo",
        "metrics_finalized": finalized,
        "run_metrics_file": "run_metrics.json",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "run_metrics.json").write_text(
        json.dumps(
            {"metrics": metrics or {"throughput": 10.0, "mean_network_queue_vehicles": 2.5}}
        ),
        encoding="utf-8",
    )
    return run_dir


def write_status(experiment_dir: Path, records: list[dict[str, Any]]) -> None:
    with (experiment_dir / "run_status.jsonl").open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


def record(name: str, controller: str, status: str, run_dir: Path | None) -> dict[str, Any]:
    return {
        "run_key": f"key:{name}",
        "controller_id": controller,
        "scenario_base": "S1_BALANCED",
        "seed": 42,
        "status": status,
        "artifact_path": run_dir.as_posix() if run_dir is not None else None,
    }


def test_combined_metrics_are_built_from_finalized_runs_only(tmp_path: Path) -> None:
    experiment_dir = tmp_path / "experiments" / "exp"
    experiment_dir.mkdir(parents=True)
    b2 = write_run(experiment_dir, "run_b2", controller="B2_LOCAL_PRESSURE")
    c1 = write_run(
        experiment_dir,
        "run_c1",
        controller="C1_COOPERATIVE_COMPACT",
        metrics={"throughput": 12.0, "messages_sent": 100.0},
    )
    write_status(
        experiment_dir,
        [
            record("b2", "B2_LOCAL_PRESSURE", "RUNNING", b2),
            record("b2", "B2_LOCAL_PRESSURE", "COMPLETED", b2),
            record("c1", "C1_COOPERATIVE_COMPACT", "COMPLETED", c1),
            record("failed", "B1_LOCAL_ADAPTIVE", "FAILED", None),
        ],
    )

    path = build_combined_metrics(experiment_dir)

    assert path.name == COMBINED_METRICS_FILE
    rows = pq.read_table(path).to_pylist()
    assert {row["controller"] for row in rows} == {
        "B2_LOCAL_PRESSURE",
        "C1_COOPERATIVE_COMPACT",
    }
    assert {row["metric"] for row in rows} == {
        "throughput",
        "mean_network_queue_vehicles",
        "messages_sent",
    }
    assert all(row["status"] == "COMPLETED" and row["success"] is True for row in rows)
    assert all(row["scenario"] == "S1_BALANCED" and row["seed"] == 42 for row in rows)
    # The paired analysis consumes the file without further preparation.
    normalized = _normalize_records(rows)
    assert len(normalized) == len(rows)
    assert {row["route_hash"] for row in normalized} == {"route"}


def test_unfinalized_run_aborts_aggregation(tmp_path: Path) -> None:
    experiment_dir = tmp_path / "experiments" / "exp"
    experiment_dir.mkdir(parents=True)
    run_dir = write_run(experiment_dir, "run_b2", controller="B2_LOCAL_PRESSURE", finalized=False)
    write_status(experiment_dir, [record("b2", "B2_LOCAL_PRESSURE", "COMPLETED", run_dir)])

    with pytest.raises(ExperimentAggregationError, match="not finalized"):
        build_combined_metrics(experiment_dir)


def test_aggregation_requires_completed_runs(tmp_path: Path) -> None:
    experiment_dir = tmp_path / "experiments" / "exp"
    experiment_dir.mkdir(parents=True)
    write_status(experiment_dir, [record("x", "B2_LOCAL_PRESSURE", "FAILED", None)])

    with pytest.raises(ExperimentAggregationError, match="no COMPLETED runs"):
        build_combined_metrics(experiment_dir)
