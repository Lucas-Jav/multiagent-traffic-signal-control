"""Agregação canônica: arquivos ``run_metrics.json`` -> ``combined_metrics.parquet``.

``combined_metrics.parquet`` é a entrada única da geração de relatórios e da análise estatística
pareada. Tem uma linha por (execução concluída, métrica) em formato longo e carrega os
invariantes científicos necessários para o pareamento. Execuções falhas ou cientificamente
incompletas nunca são exportadas como zeros: uma execução cujas métricas não foram finalizadas
aborta a agregação.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

COMBINED_METRICS_FILE = "combined_metrics.parquet"
RUN_STATUS_FILE = "run_status.jsonl"


class ExperimentAggregationError(RuntimeError):
    """Lançada quando as métricas das execuções não podem ser agregadas em métricas combinadas."""


def build_combined_metrics(experiment_dir: Path, *, output_path: Path | None = None) -> Path:
    """Agrega as métricas finalizadas de toda execução CONCLUÍDA de um experimento."""

    status_path = experiment_dir / RUN_STATUS_FILE
    if not status_path.exists():
        msg = f"run status file not found: {status_path}"
        raise ExperimentAggregationError(msg)
    latest = _latest_run_records(status_path)
    completed = [record for record in latest.values() if record.get("status") == "COMPLETED"]
    if not completed:
        msg = f"no COMPLETED runs to aggregate in {experiment_dir}"
        raise ExperimentAggregationError(msg)

    columns: dict[str, list[Any]] = {
        name: []
        for name in (
            "experiment_id",
            "run_id",
            "scenario",
            "demand_profile",
            "controller",
            "seed",
            "metric",
            "value",
            "status",
            "success",
            "route_hash",
            "network_hash",
            "phase_plan",
            "phase_plan_version",
            "movement_model_version",
            "turning_ratios",
            "turning_config_sha256",
            "communication_topology_hash",
            "delay_steps",
            "drop_probability",
        )
    }
    for record in sorted(completed, key=lambda item: str(item.get("run_key"))):
        run_dir = _resolve_run_dir(record, experiment_dir)
        manifest = _read_json(run_dir / "manifest.json")
        if manifest.get("metrics_finalized") is not True:
            msg = f"run metrics are not finalized: {run_dir}"
            raise ExperimentAggregationError(msg)
        run_metrics = _read_json(
            run_dir / str(manifest.get("run_metrics_file", "run_metrics.json"))
        )
        metrics = run_metrics.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            msg = f"run_metrics.json has no metrics: {run_dir}"
            raise ExperimentAggregationError(msg)
        communication = manifest.get("communication")
        communication = communication if isinstance(communication, dict) else {}
        controller = manifest.get("controller")
        controller_id = (
            controller.get("controller_id")
            if isinstance(controller, dict)
            else record.get("controller_id")
        )
        for name, value in sorted(metrics.items()):
            columns["experiment_id"].append(experiment_dir.name)
            columns["run_id"].append(str(manifest.get("run_id")))
            columns["scenario"].append(
                str(record.get("scenario_base") or manifest["demand_profile"])
            )
            columns["demand_profile"].append(str(manifest.get("demand_profile")))
            columns["controller"].append(str(controller_id))
            columns["seed"].append(int(manifest["seed"]))
            columns["metric"].append(str(name))
            columns["value"].append(float(value))
            columns["status"].append("COMPLETED")
            columns["success"].append(True)
            columns["route_hash"].append(str(manifest["route_sha256"]))
            columns["network_hash"].append(str(manifest["network_sha256"]))
            columns["phase_plan"].append(str(manifest["phase_plan_sha256"]))
            columns["phase_plan_version"].append(str(manifest["phase_plan_version"]))
            columns["movement_model_version"].append(str(manifest["movement_model_version"]))
            columns["turning_ratios"].append(json.dumps(manifest["turning_ratios"], sort_keys=True))
            columns["turning_config_sha256"].append(str(manifest["turning_config_sha256"]))
            columns["communication_topology_hash"].append(
                str(manifest["communication_topology_sha256"])
            )
            columns["delay_steps"].append(float(communication.get("delay_steps", 0)))
            columns["drop_probability"].append(float(communication.get("drop_probability", 0.0)))

    destination = output_path or experiment_dir / COMBINED_METRICS_FILE
    table = pa.table(columns)
    pq.write_table(table, destination, compression="zstd")
    return destination


def _latest_run_records(status_path: Path) -> dict[object, dict[str, Any]]:
    latest: dict[object, dict[str, Any]] = {}
    with status_path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                latest[payload.get("run_key")] = payload
    return latest


def _resolve_run_dir(record: Mapping[str, Any], experiment_dir: Path) -> Path:
    artifact_path = record.get("artifact_path")
    if not isinstance(artifact_path, str):
        msg = f"run record has no artifact_path: {record.get('run_key')}"
        raise ExperimentAggregationError(msg)
    candidate = Path(artifact_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for base in (Path.cwd(), experiment_dir.parent.parent, experiment_dir.parent):
        resolved = base / candidate
        if resolved.exists():
            return resolved
    msg = f"run artifact directory not found: {artifact_path}"
    raise ExperimentAggregationError(msg)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        msg = f"required run artifact not found: {path}"
        raise ExperimentAggregationError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"JSON artifact must be an object: {path}"
        raise ExperimentAggregationError(msg)
    return payload
