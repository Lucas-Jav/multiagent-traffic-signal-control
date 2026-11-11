from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from traffic_agents.config import CommunicationConfig
from traffic_agents.experiments.runner import (
    ExperimentConfig,
    ExperimentRunConfig,
    ExperimentRunner,
)

SCENARIO = Path("scenarios/grid_3x3/scenario_s1_balanced_seed_42.yaml")


@pytest.mark.sumo
def test_unified_pipeline_finalizes_every_controller_and_aggregates_combined_metrics() -> None:
    # Raiz de artefatos curta: os diretórios de execução embutem ids longos e excederiam o limite
    # MAX_PATH do Windows sob o tmp_path profundamente aninhado do pytest.
    Path("artifacts").mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(dir="artifacts", prefix="ps_"))
    try:
        _assert_pipeline(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _assert_pipeline(root: Path) -> None:
    controllers = ("B0_FIXED", "B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT")
    config = ExperimentConfig(
        experiment_id="ps",
        max_steps=330,
        runs=tuple(
            ExperimentRunConfig(
                run_id=f"smoke_{controller.lower()}",
                scenario_base="S1_BALANCED",
                scenario=SCENARIO,
                controller_id=controller,
                seed=42,
                communication_seed_policy="derived_from_simulation_seed_delay_drop",
                communication=CommunicationConfig(),
            )
            for controller in controllers
        ),
    )

    summary = ExperimentRunner(config=config, artifacts_dir=root).run()

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["completed_count"] == 3
    assert manifest["failed_count"] == 0
    experiment_dir = summary.manifest_path.parent
    assert manifest["combined_metrics_file"] == "combined_metrics.parquet"
    rows = pq.read_table(experiment_dir / "combined_metrics.parquet").to_pylist()
    by_controller: dict[str, set[str]] = {}
    for row in rows:
        by_controller.setdefault(row["controller"], set()).add(row["metric"])
    assert set(by_controller) == set(controllers)
    for controller, metric_names in by_controller.items():
        # métricas de fila existem para TODO controlador, inclusive o baseline de tempo fixo (B0)
        assert {
            "mean_network_queue_vehicles",
            "max_network_queue_vehicles",
            "max_lane_queue_vehicles",
            "internal_lane_persistence_events",
            "throughput",
            "offered_vehicle_count",
            "completion_ratio_offered",
        } <= metric_names, controller
    assert {"messages_sent", "bytes_sent"} <= by_controller["C1_COOPERATIVE_COMPACT"]
    for run_manifest in experiment_dir.glob("runs/*/*/manifest.json"):
        run_dir = run_manifest.parent
        run = json.loads(run_manifest.read_text(encoding="utf-8"))
        assert run["metrics_finalized"] is True
        assert (run_dir / "run_metrics.json").exists()
        assert (run_dir / "lane_telemetry.parquet").exists()
        assert not (run_dir / "intersection_trace.csv").exists()
    # telemetria de lanes únicas: 36 lanes de entrada por passo na grade 3x3
    any_lane_table = next(experiment_dir.glob("runs/*/*/lane_telemetry.parquet"))
    lanes = pq.read_table(any_lane_table, columns=["step_index", "lane_id"]).to_pydict()
    assert len(lanes["step_index"]) == 330 * 36
    assert len(set(lanes["lane_id"])) == 36
