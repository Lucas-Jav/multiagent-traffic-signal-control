from __future__ import annotations

# ruff: noqa: I001

import math
import json
import statistics
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.experiments.metric_definitions import metric_definition_payload

BANNED_SUMMARY_TERMS = (
    "better",
    "superior",
    "winning",
    "provou ser superior",
    "resolveu congestionamento",
    "metodo e eficiente",
    "método é eficiente",
)

TRAFFIC_METRIC_FIGURES: Mapping[str, tuple[str, ...]] = {
    "waiting_time_by_controller.png": (
        "waiting_time",
        "mean_waiting_time",
        "avg_waiting_time",
        "average_waiting_time",
    ),
    "time_loss_by_controller.png": (
        "time_loss",
        "mean_time_loss",
        "avg_time_loss",
        "average_time_loss",
    ),
    "queue_by_controller.png": (
        "mean_network_queue_vehicles",
        "queue",
        "mean_queue",
        "avg_queue",
        "average_queue",
        "movement_queue_mean",
    ),
    "max_queue_by_controller.png": (
        "max_network_queue_vehicles",
        "max_queue",
        "maximum_queue",
        "movement_queue_max",
    ),
    "throughput_by_controller.png": (
        "throughput",
        "vehicles_arrived",
        "arrived",
    ),
    "travel_time_by_controller.png": (
        "mean_travel_time",
        "travel_time",
        "mean_travel_time_seconds",
    ),
    "stops_by_controller.png": (
        "mean_stops",
        "stops",
    ),
    "network_throughput_by_controller.png": ("network_throughput",),
    "corridor_throughput_by_controller.png": ("corridor_throughput",),
    "corridor_travel_time_by_controller.png": (
        "corridor_mean_travel_time",
        "corridor_travel_time",
    ),
    "corridor_stops_by_controller.png": ("corridor_mean_stops", "corridor_stops"),
    "post_shock_queue_by_controller.png": (
        "post_shock_mean_network_queue_vehicles",
        "post_shock_mean_queue",
    ),
    "post_shock_max_queue_by_controller.png": (
        "post_shock_max_network_queue_vehicles",
        "post_shock_max_queue",
    ),
    "post_shock_time_loss_by_controller.png": ("post_shock_time_loss",),
    "post_shock_queue_auc_by_controller.png": (
        "post_shock_queue_auc_vehicle_seconds",
        "post_shock_queue_auc",
    ),
    "max_lane_queue_by_controller.png": ("max_lane_queue_vehicles",),
    "intersection_queue_by_controller.png": ("mean_intersection_queue_vehicles",),
    "completion_ratio_by_controller.png": ("completion_ratio_offered",),
    "depart_delay_by_controller.png": ("mean_depart_delay_seconds",),
    "internal_lane_persistence_by_controller.png": ("internal_lane_persistence_events",),
    "throughput_change_vs_zero_loss_by_controller.png": ("throughput_change_vs_zero_loss",),
}

COMMUNICATION_MESSAGE_METRICS = (
    "messages",
    "messages_sent",
    "messages_delivered",
)
COMMUNICATION_BYTE_METRICS = (
    "bytes",
    "bytes_sent",
    "bytes_delivered",
    "serialized_bytes",
    "message_bytes",
)
COMMUNICATION_METRICS = (
    *COMMUNICATION_MESSAGE_METRICS,
    *COMMUNICATION_BYTE_METRICS,
    "messages_dropped",
    "observed_drop_rate",
    "message_delay_steps",
    "average_message_delay",
    "max_message_delay",
    "messages_fresh",
    "messages_stale",
    "average_message_age",
    "max_observed_message_age",
    "mean_message_age_steps",
    "max_message_age_steps",
)
SENSITIVITY_TRAFFIC_METRICS = (
    "waiting_time",
    "mean_waiting_time",
    "time_loss",
    "mean_time_loss",
    "queue",
    "mean_queue",
    "mean_network_queue_vehicles",
    "throughput",
    "throughput_change_vs_zero_loss",
)
CONTROLLER_ALIASES: Mapping[str, str] = {
    "B0": "B0_FIXED",
    "B1": "B1_LOCAL_ADAPTIVE",
    "B2": "B2_LOCAL_PRESSURE",
    "C1": "C1_COOPERATIVE_COMPACT",
    "C2": "C2_COOPERATIVE_EXPANDED",
}


class ReportGenerationError(ValueError):
    """Raised when scientific figures cannot be generated from result files."""


@dataclass(frozen=True)
class FigureReport:
    experiment_folder: Path
    figures_dir: Path
    generated_files: tuple[Path, ...]
    metric_definitions_path: Path


@dataclass(frozen=True)
class SummaryReport:
    experiment_folder: Path
    summary_path: Path


def generate_experiment_report(experiment_folder: Path) -> FigureReport:
    combined_path = experiment_folder / "combined_metrics.parquet"
    analysis_path = experiment_folder / "analysis.parquet"
    _require_file(combined_path)
    _require_file(analysis_path)

    combined = _with_derived_metrics(_normalize_combined_metrics(_read_parquet(combined_path)))
    analysis = _normalize_analysis(_read_parquet(analysis_path))
    _validate_combined_metrics(combined)

    figures_dir = experiment_folder / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    metric_definitions_path = experiment_folder / "metric_definitions.json"
    metric_definitions_path.write_text(
        json.dumps(
            metric_definition_payload([str(row["metric"]) for row in combined]),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    generated: list[Path] = []
    for filename, candidates in TRAFFIC_METRIC_FIGURES.items():
        metric = _first_available_metric(combined, candidates)
        if metric is None:
            continue
        output_path = figures_dir / filename
        _plot_metric_by_controller(combined, analysis, metric, output_path)
        generated.append(output_path)

    communication_path = figures_dir / "communication_cost.png"
    if _has_any_metric(
        combined,
        (*COMMUNICATION_MESSAGE_METRICS, *COMMUNICATION_BYTE_METRICS),
    ) and _plot_communication_cost(combined, communication_path):
        generated.append(communication_path)

    sensitivity_metric = _first_available_metric(combined, SENSITIVITY_TRAFFIC_METRICS)
    if sensitivity_metric is not None and _has_non_null_column(combined, "delay_steps"):
        delay_path = figures_dir / "delay_sensitivity.png"
        if _plot_sensitivity(
            combined,
            x_field="delay_steps",
            metric=sensitivity_metric,
            xlabel="Delay steps",
            output_path=delay_path,
        ):
            generated.append(delay_path)
    if sensitivity_metric is not None and _has_non_null_column(combined, "drop_probability"):
        drop_path = figures_dir / "drop_sensitivity.png"
        if _plot_sensitivity(
            combined,
            x_field="drop_probability",
            metric=sensitivity_metric,
            xlabel="Drop probability",
            output_path=drop_path,
        ):
            generated.append(drop_path)

    turning_metric = _first_available_metric(
        combined,
        ("turning_movement_queue", "movement_queue_by_turn", "turn_movement_queue"),
    )
    if turning_metric is not None and _has_non_null_column(combined, "turn_type"):
        turning_path = figures_dir / "turning_movement_queue.png"
        if _plot_turning_movement_queue(combined, turning_metric, turning_path):
            generated.append(turning_path)

    if not generated:
        msg = "no supported metrics found for scientific figure generation"
        raise ReportGenerationError(msg)

    return FigureReport(
        experiment_folder=experiment_folder,
        figures_dir=figures_dir,
        generated_files=tuple(generated),
        metric_definitions_path=metric_definitions_path,
    )


def generate_experiment_summary(experiment_folder: Path) -> SummaryReport:
    manifest_path = experiment_folder / "manifest.json"
    combined_path = experiment_folder / "combined_metrics.parquet"
    analysis_path = experiment_folder / "analysis.parquet"
    analysis_json_path = experiment_folder / "analysis.json"
    for path in (manifest_path, combined_path, analysis_path, analysis_json_path):
        _require_file(path)

    manifest = _read_json_object(manifest_path)
    combined = _normalize_summary_metrics(_read_parquet(combined_path))
    analysis_rows = _normalize_analysis(_read_parquet(analysis_path))
    analysis_json = _read_json_object(analysis_json_path)

    summary_path = experiment_folder / "summary.md"
    content = _summary_markdown(
        experiment_folder=experiment_folder,
        manifest=manifest,
        combined=combined,
        analysis_rows=analysis_rows,
        analysis_json=analysis_json,
    )
    _assert_summary_language(content)
    summary_path.write_text(content, encoding="utf-8")
    return SummaryReport(experiment_folder=experiment_folder, summary_path=summary_path)


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    return [dict(row) for row in pq.read_table(path).to_pylist()]


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"JSON result must be an object: {path}"
        raise ReportGenerationError(msg)
    return payload


def _normalize_combined_metrics(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        metric = _first_present(record, ("metric", "metric_name"), required=True)
        value = _first_present(record, ("value", "metric_value"), required=True)
        row = {
            "_row_index": index,
            "scenario": _first_present(record, ("scenario", "scenario_id"), required=False),
            "controller": _canonical_controller(
                _first_present(record, ("controller", "controller_id"), required=True),
            ),
            "metric": str(metric),
            "value": _finite_float(value, row_index=index),
            "run_id": _first_present(record, ("run_id",), required=False),
            "seed": _first_present(record, ("seed", "simulation_seed"), required=False),
            "status": _first_present(record, ("status", "run_status"), required=False),
            "success": _first_present(record, ("success", "succeeded"), required=False),
            "delay_steps": _optional_float(
                _first_present(record, ("delay_steps",), required=False)
            ),
            "drop_probability": _optional_float(
                _first_present(record, ("drop_probability",), required=False)
            ),
            "turn_type": _first_present(record, ("turn_type", "turning_movement"), required=False),
        }
        normalized.append(row)
    return normalized


def _with_derived_metrics(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    enriched = [dict(record) for record in records]
    enriched.extend(_throughput_change_vs_zero_loss(records))
    return enriched


def _throughput_change_vs_zero_loss(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    zero_loss_by_key: dict[tuple[object, ...], float] = {}
    throughput_rows: list[Mapping[str, Any]] = []
    for row in records:
        if row.get("metric") != "throughput":
            continue
        if row.get("drop_probability") is None or row.get("seed") is None:
            continue
        throughput_rows.append(row)
        key = _loss_pair_key(row)
        if float(row["drop_probability"]) == 0.0:
            zero_loss_by_key[key] = float(row["value"])

    derived: list[dict[str, Any]] = []
    for row in throughput_rows:
        baseline = zero_loss_by_key.get(_loss_pair_key(row))
        if baseline is None:
            continue
        derived_row = dict(row)
        derived_row["metric"] = "throughput_change_vs_zero_loss"
        derived_row["value"] = float(row["value"]) - baseline
        derived.append(derived_row)
    return derived


def _loss_pair_key(row: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        row.get("scenario"),
        row.get("controller"),
        row.get("seed"),
    )


def _normalize_summary_metrics(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        metric = _first_present(record, ("metric", "metric_name"), required=True)
        value = _first_present(record, ("value", "metric_value"), required=False)
        failed = _is_failed_status(
            _first_present(record, ("status", "run_status"), required=False)
        ) or _is_failed_success(_first_present(record, ("success", "succeeded"), required=False))
        numeric_value = None if failed or value is None else _finite_float(value, row_index=index)
        normalized.append(
            {
                "_row_index": index,
                "run_id": _first_present(record, ("run_id",), required=False),
                "scenario": _first_present(record, ("scenario", "scenario_id"), required=False),
                "controller": _canonical_controller(
                    _first_present(record, ("controller", "controller_id"), required=True),
                ),
                "metric": str(metric),
                "value": numeric_value,
                "seed": _first_present(record, ("seed", "simulation_seed"), required=False),
                "status": _first_present(record, ("status", "run_status"), required=False),
                "success": _first_present(record, ("success", "succeeded"), required=False),
                "failed": failed,
                "git_sha": _first_present(record, ("git_sha",), required=False),
                "sumo_version": _first_present(record, ("sumo_version",), required=False),
                "network_hash": _first_present(
                    record,
                    ("network_hash", "network_sha256"),
                    required=False,
                ),
                "route_hash": _first_present(
                    record,
                    ("route_hash", "route_sha256"),
                    required=False,
                ),
                "scenario_hash": _first_present(
                    record,
                    ("scenario_hash", "scenario_sha256"),
                    required=False,
                ),
                "experiment_config_hash": _first_present(
                    record,
                    ("experiment_config_hash", "experiment_config_sha256", "config_hash"),
                    required=False,
                ),
                "phase_plan_version": _first_present(
                    record,
                    ("phase_plan_version",),
                    required=False,
                ),
                "movement_model_version": _first_present(
                    record,
                    ("movement_model_version",),
                    required=False,
                ),
            }
        )
    return normalized


def _normalize_analysis(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in records:
        metric = _first_present(record, ("metric", "metric_name"), required=False)
        if metric is None:
            continue
        row = dict(record)
        row["metric"] = str(metric)
        normalized.append(row)
    return normalized


def _validate_combined_metrics(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        msg = "combined_metrics.parquet has no rows"
        raise ReportGenerationError(msg)
    failed_rows = [
        row
        for row in records
        if _is_failed_status(row.get("status")) or _is_failed_success(row.get("success"))
    ]
    if failed_rows:
        row_indexes = [int(row["_row_index"]) for row in failed_rows]
        msg = (
            "failed runs are present in combined_metrics.parquet and cannot be plotted as zero: "
            f"rows={row_indexes}"
        )
        raise ReportGenerationError(msg)


def _summary_markdown(
    *,
    experiment_folder: Path,
    manifest: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
    analysis_rows: Sequence[Mapping[str, Any]],
    analysis_json: Mapping[str, Any],
) -> str:
    experiment_id = _first_non_empty(
        (manifest.get("experiment_id"), experiment_folder.name),
        default="not recorded",
    )
    completed_runs, failed_runs = _run_counts(manifest, combined)
    controllers = _controllers(manifest, combined)
    seeds = _seeds(manifest, combined)
    experiment_config_hash = _metadata_value(manifest, combined, "experiment_config_hash")
    network_hash = _metadata_value(manifest, combined, "network_hash")
    scenario_hash = _metadata_value(manifest, combined, "scenario_hash")
    route_hashes = ", ".join(_route_hashes(manifest, combined)) or "not recorded"
    phase_plan_version = _metadata_value(manifest, combined, "phase_plan_version")
    movement_model_version = _metadata_value(manifest, combined, "movement_model_version")
    scenario_info = str(manifest.get("scenario") or _metadata_value(manifest, combined, "scenario"))
    bootstrap_seed = str(_nested_value(analysis_json, ("bootstrap", "seed")) or "not recorded")
    bootstrap_resamples = str(
        _nested_value(analysis_json, ("bootstrap", "resamples")) or "not recorded"
    )

    lines = [
        f"# Experiment Summary: {experiment_id}",
        "",
        "## Experiment Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Experiment ID | {_escape_md(experiment_id)} |",
        f"| Git SHA | {_escape_md(_metadata_value(manifest, combined, 'git_sha'))} |",
        f"| SUMO version | {_escape_md(_metadata_value(manifest, combined, 'sumo_version'))} |",
        f"| Experiment config hash | {_escape_md(experiment_config_hash)} |",
        f"| Network hash | {_escape_md(network_hash)} |",
        f"| Scenario hash | {_escape_md(scenario_hash)} |",
        f"| Route hashes | {_escape_md(route_hashes)} |",
        f"| Phase plan version | {_escape_md(phase_plan_version)} |",
        f"| Movement model version | {_escape_md(movement_model_version)} |",
        f"| Controllers | {_escape_md(', '.join(controllers) or 'not recorded')} |",
        f"| Seeds | {_escape_md(', '.join(seeds) or 'not recorded')} |",
        f"| Completed runs | {completed_runs} |",
        f"| Failed runs | {failed_runs} |",
        "",
        "## Route And Scenario Info",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Scenario | {_escape_md(scenario_info)} |",
        f"| Batch ID | {_escape_md(str(manifest.get('batch_id') or 'not recorded'))} |",
        f"| Manifest runs | {len(_manifest_runs(manifest))} |",
        "",
        "## Traffic Metrics",
        "",
        *_metric_table_lines(combined, include_communication=False),
        "",
        "## Communication Metrics",
        "",
        *_metric_table_lines(combined, include_communication=True),
        "",
        "## Pairwise Comparisons And Confidence Intervals",
        "",
        *_pairwise_table_lines(analysis_rows),
        "",
        *_pairwise_observation_lines(analysis_rows),
        "",
        "## Figures",
        "",
        *_figure_link_lines(experiment_folder),
        "",
        "## Analysis Provenance",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Bootstrap seed | {_escape_md(bootstrap_seed)} |",
        f"| Bootstrap resamples | {_escape_md(bootstrap_resamples)} |",
        f"| Analysis input | {_escape_md(str(analysis_json.get('input') or 'not recorded'))} |",
        "",
    ]
    return "\n".join(lines)


def _run_counts(
    manifest: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
) -> tuple[int, int]:
    status_by_run: dict[tuple[Any, ...], bool] = {}
    for row in combined:
        key = _summary_run_key(row)
        status_by_run[key] = status_by_run.get(key, False) or bool(row.get("failed"))
    for index, run in enumerate(_manifest_runs(manifest)):
        key = _manifest_run_key(run, index)
        status_by_run[key] = status_by_run.get(key, False) or _manifest_run_failed(run)
    if status_by_run:
        failed = sum(1 for is_failed in status_by_run.values() if is_failed)
        completed = len(status_by_run) - failed
        return completed, failed

    runs = _manifest_runs(manifest)
    return len(runs), 0


def _summary_run_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    run_id = row.get("run_id")
    if run_id is not None:
        return ("run_id", run_id)
    return (
        row.get("scenario"),
        row.get("controller"),
        row.get("seed"),
    )


def _manifest_run_key(run: Mapping[str, Any], index: int) -> tuple[Any, ...]:
    run_id = run.get("run_id")
    if run_id is not None:
        return ("run_id", run_id)
    return ("manifest", index)


def _metric_table_lines(
    rows: Sequence[Mapping[str, Any]],
    *,
    include_communication: bool,
) -> list[str]:
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        metric = str(row["metric"])
        is_communication = metric in COMMUNICATION_METRICS
        if include_communication != is_communication:
            continue
        value = row.get("value")
        if value is None:
            continue
        values[(metric, str(row["controller"]))].append(float(value))

    if not values:
        return ["No observed completed-run metrics available."]

    lines = [
        "| Metric | Controller | N | Mean | Median | Min | Max |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (metric, controller), samples in sorted(values.items()):
        lines.append(
            "| "
            f"{_escape_md(_metric_label(metric))} | "
            f"{_escape_md(controller)} | "
            f"{len(samples)} | "
            f"{_format_number(statistics.fmean(samples))} | "
            f"{_format_number(statistics.median(samples))} | "
            f"{_format_number(min(samples))} | "
            f"{_format_number(max(samples))} |"
        )
    return lines


def _pairwise_table_lines(analysis_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    usable_rows = [
        row
        for row in analysis_rows
        if _has_numeric_fields(row, ("n_pairs", "mean_difference", "ci95_low", "ci95_high"))
    ]
    if not usable_rows:
        return ["No pairwise comparisons available."]

    lines = [
        "| Metric | Controller A | Controller B | N pairs | Mean difference | "
        "Median difference | CI95 low | CI95 high | Relative difference |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in usable_rows:
        relative = row.get("relative_difference")
        lines.append(
            "| "
            f"{_escape_md(_metric_label(str(row['metric'])))} | "
            f"{_escape_md(str(row.get('controller_a') or 'not recorded'))} | "
            f"{_escape_md(str(row.get('controller_b') or 'not recorded'))} | "
            f"{int(float(row['n_pairs']))} | "
            f"{_format_number(float(row['mean_difference']))} | "
            f"{_format_optional_number(row.get('median_difference'))} | "
            f"{_format_number(float(row['ci95_low']))} | "
            f"{_format_number(float(row['ci95_high']))} | "
            f"{_format_optional_number(relative)} |"
        )
    return lines


def _pairwise_observation_lines(analysis_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    usable_rows = [
        row
        for row in analysis_rows
        if _has_numeric_fields(row, ("n_pairs", "mean_difference", "ci95_low", "ci95_high"))
    ]
    if not usable_rows:
        return []
    lines = ["Observed pairwise differences:"]
    for row in usable_rows:
        lines.append(
            "- "
            f"{_escape_md(str(row.get('controller_b') or 'Controller B'))} apresentou "
            f"diferenca media de {_format_number(float(row['mean_difference']))} em relacao a "
            f"{_escape_md(str(row.get('controller_a') or 'Controller A'))} para "
            f"{_escape_md(_metric_label(str(row['metric'])))}; "
            f"IC95 [{_format_number(float(row['ci95_low']))}, "
            f"{_format_number(float(row['ci95_high']))}], "
            f"N={int(float(row['n_pairs']))}."
        )
    return lines


def _figure_link_lines(experiment_folder: Path) -> list[str]:
    figures_dir = experiment_folder / "figures"
    if not figures_dir.exists():
        return ["No figures directory found."]
    figures = sorted(path for path in figures_dir.glob("*.png") if path.is_file())
    if not figures:
        return ["No figure files found."]
    return [f"- [{path.name}](figures/{path.name})" for path in figures]


def _metadata_value(
    manifest: Mapping[str, Any],
    combined: Sequence[Mapping[str, Any]],
    field: str,
) -> str:
    manifest_value = manifest.get(field)
    if manifest_value is not None:
        return str(manifest_value)
    values = sorted({str(row[field]) for row in combined if row.get(field) is not None})
    if not values:
        return "not recorded"
    return ", ".join(values)


def _route_hashes(manifest: Mapping[str, Any], combined: Sequence[Mapping[str, Any]]) -> list[str]:
    values = {str(row["route_hash"]) for row in combined if row.get("route_hash") is not None}
    for run in _manifest_runs(manifest):
        route_hash = run.get("route_hash") or run.get("route_sha256")
        if route_hash is not None:
            values.add(str(route_hash))
    return sorted(values)


def _controllers(manifest: Mapping[str, Any], combined: Sequence[Mapping[str, Any]]) -> list[str]:
    values = {str(row["controller"]) for row in combined if row.get("controller") is not None}
    manifest_controllers = manifest.get("controllers")
    if isinstance(manifest_controllers, list):
        values.update(str(controller) for controller in manifest_controllers)
    for run in _manifest_runs(manifest):
        controller = run.get("controller_id") or run.get("configured_controller_id")
        if controller is not None:
            values.add(str(controller))
    return sorted(values)


def _seeds(manifest: Mapping[str, Any], combined: Sequence[Mapping[str, Any]]) -> list[str]:
    values = {str(row["seed"]) for row in combined if row.get("seed") is not None}
    manifest_seeds = manifest.get("seeds")
    if isinstance(manifest_seeds, list):
        values.update(str(seed) for seed in manifest_seeds)
    for run in _manifest_runs(manifest):
        seed = run.get("seed")
        if seed is not None:
            values.add(str(seed))
    return sorted(values, key=_numeric_sort_key)


def _manifest_runs(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    runs = manifest.get("runs")
    if not isinstance(runs, list):
        return []
    return [run for run in runs if isinstance(run, Mapping)]


def _manifest_run_failed(run: Mapping[str, Any]) -> bool:
    status = run["status"] if "status" in run else run.get("run_status")
    success = run["success"] if "success" in run else run.get("succeeded")
    return _is_failed_status(status) or _is_failed_success(success)


def _first_non_empty(values: Iterable[Any], *, default: str) -> str:
    for value in values:
        if value is not None and str(value):
            return str(value)
    return default


def _nested_value(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = payload
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _format_optional_number(value: Any) -> str:
    if value is None:
        return "not computed"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return _escape_md(str(value))
    if not math.isfinite(numeric):
        return "not computed"
    return _format_number(numeric)


def _format_number(value: float) -> str:
    return f"{value:.6g}"


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|")


def _numeric_sort_key(value: str) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except ValueError:
        return (1, value)


def _assert_summary_language(content: str) -> None:
    lowered = content.lower()
    for term in BANNED_SUMMARY_TERMS:
        if term in lowered:
            msg = f"summary contains disallowed interpretive language: {term}"
            raise ReportGenerationError(msg)


def _plot_metric_by_controller(
    rows: Sequence[Mapping[str, Any]],
    analysis_rows: Sequence[Mapping[str, Any]],
    metric: str,
    output_path: Path,
) -> None:
    values = _values_by_controller(rows, metric)
    if not values:
        return

    fig, (box_ax, diff_ax) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(7.2, 7.6),
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )
    controllers = sorted(values)
    box_ax.boxplot(
        [values[controller] for controller in controllers],
        tick_labels=controllers,
    )
    _scatter_observations(box_ax, values, controllers)
    scenario_label = _scenario_label(rows)
    box_ax.set_title(f"{_metric_label(metric)} by controller - {scenario_label}")
    box_ax.set_xlabel("Controller")
    box_ax.set_ylabel(_metric_label(metric))
    box_ax.tick_params(axis="x", rotation=20)
    box_ax.grid(axis="y", alpha=0.25)

    ci_rows = [
        row
        for row in analysis_rows
        if row.get("metric") == metric
        and _has_numeric_fields(row, ("mean_difference", "ci95_low", "ci95_high"))
    ]
    if ci_rows:
        labels = [f"{row.get('controller_a')} -> {row.get('controller_b')}" for row in ci_rows]
        means = [float(row["mean_difference"]) for row in ci_rows]
        lows = [float(row["ci95_low"]) for row in ci_rows]
        highs = [float(row["ci95_high"]) for row in ci_rows]
        positions = list(range(1, len(ci_rows) + 1))
        lower_errors = [mean - low for mean, low in zip(means, lows, strict=True)]
        upper_errors = [high - mean for mean, high in zip(means, highs, strict=True)]
        diff_ax.errorbar(
            positions,
            means,
            yerr=[lower_errors, upper_errors],
            fmt="o",
            capsize=4,
            color="#2f5597",
        )
        diff_ax.axhline(0.0, color="#555555", linewidth=1.0)
        diff_ax.set_xticks(positions, labels, rotation=20)
        diff_ax.set_ylabel("Paired difference")
        diff_ax.set_xlabel("Controller comparison")
        diff_ax.grid(axis="y", alpha=0.25)
    else:
        diff_ax.axis("off")

    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_communication_cost(
    rows: Sequence[Mapping[str, Any]],
    output_path: Path,
) -> bool:
    message_metric = _first_available_metric(rows, COMMUNICATION_MESSAGE_METRICS)
    byte_metric = _first_available_metric(rows, COMMUNICATION_BYTE_METRICS)
    if message_metric is None and byte_metric is None:
        return False

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(9.4, 4.6))
    plotted = False
    for ax, metric, title in (
        (axes[0], message_metric, "Messages"),
        (axes[1], byte_metric, "Bytes"),
    ):
        if metric is None:
            ax.axis("off")
            continue
        values = {
            controller: samples
            for controller, samples in _values_by_controller(rows, metric).items()
            if controller in {"C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED"}
        }
        if not values:
            ax.axis("off")
            continue
        plotted = True
        controllers = sorted(values)
        ax.boxplot(
            [values[controller] for controller in controllers],
            tick_labels=controllers,
        )
        _scatter_observations(ax, values, controllers)
        ax.set_title(f"{title} - {_scenario_label(rows)}")
        ax.set_xlabel("Controller")
        ax.set_ylabel(_metric_label(metric))
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="y", alpha=0.25)

    if not plotted:
        plt.close(fig)
        return False
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return True


def _plot_sensitivity(
    rows: Sequence[Mapping[str, Any]],
    *,
    x_field: str,
    metric: str,
    xlabel: str,
    output_path: Path,
) -> bool:
    grouped: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["metric"] != metric or row.get(x_field) is None:
            continue
        grouped[str(row["controller"])][float(row[x_field])].append(float(row["value"]))
    grouped = {controller: by_x for controller, by_x in grouped.items() if by_x}
    if not grouped:
        return False

    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for controller in sorted(grouped):
        by_x = grouped[controller]
        xs = sorted(by_x)
        means = [_mean(by_x[x]) for x in xs]
        ax.plot(xs, means, marker="o", linewidth=1.6, label=controller)
        for x in xs:
            samples = by_x[x]
            ax.scatter(
                [x] * len(samples),
                samples,
                alpha=0.35,
                s=18,
            )

    ax.set_title(f"{_metric_label(metric)} sensitivity - {_scenario_label(rows)}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(_metric_label(metric))
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return True


def _plot_turning_movement_queue(
    rows: Sequence[Mapping[str, Any]],
    metric: str,
    output_path: Path,
) -> bool:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["metric"] == metric and row.get("turn_type") is not None:
            grouped[str(row["turn_type"])].append(float(row["value"]))
    if len(grouped) < 2:
        return False

    turn_types = sorted(grouped)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.boxplot(
        [grouped[turn_type] for turn_type in turn_types],
        tick_labels=turn_types,
    )
    for index, turn_type in enumerate(turn_types, start=1):
        values = grouped[turn_type]
        ax.scatter([index] * len(values), values, alpha=0.35, s=18)
    ax.set_title(f"Turning movement queue - {_scenario_label(rows)}")
    ax.set_xlabel("Turning movement")
    ax.set_ylabel(_metric_label(metric))
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return True


def _values_by_controller(
    rows: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, list[float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["metric"] == metric:
            values[str(row["controller"])].append(float(row["value"]))
    return dict(values)


def _scatter_observations(
    ax: Any,
    values: Mapping[str, Sequence[float]],
    controllers: Sequence[str],
) -> None:
    for index, controller in enumerate(controllers, start=1):
        samples = values[controller]
        ax.scatter([index] * len(samples), samples, alpha=0.35, s=18, color="#555555")


def _first_available_metric(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
) -> str | None:
    available = {str(row["metric"]) for row in rows}
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def _has_any_metric(rows: Sequence[Mapping[str, Any]], candidates: Sequence[str]) -> bool:
    return _first_available_metric(rows, candidates) is not None


def _has_non_null_column(rows: Sequence[Mapping[str, Any]], column: str) -> bool:
    return any(row.get(column) is not None for row in rows)


def _has_numeric_fields(row: Mapping[str, Any], fields: Sequence[str]) -> bool:
    for field in fields:
        value = row.get(field)
        if value is None:
            return False
        try:
            if not math.isfinite(float(value)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def _scenario_label(rows: Sequence[Mapping[str, Any]]) -> str:
    scenarios = sorted({str(row["scenario"]) for row in rows if row.get("scenario") is not None})
    if not scenarios:
        return "scenario: unspecified"
    if len(scenarios) == 1:
        return f"scenario: {scenarios[0]}"
    return f"scenarios: {', '.join(scenarios)}"


def _metric_label(metric: str) -> str:
    labels: Mapping[str, str] = {
        "waiting_time": "Waiting time (s)",
        "mean_waiting_time": "Waiting time (s)",
        "avg_waiting_time": "Waiting time (s)",
        "average_waiting_time": "Waiting time (s)",
        "mean_travel_time": "Travel time (s)",
        "travel_time": "Travel time (s)",
        "mean_travel_time_seconds": "Travel time (s)",
        "time_loss": "Time loss (s)",
        "mean_time_loss": "Time loss (s)",
        "avg_time_loss": "Time loss (s)",
        "average_time_loss": "Time loss (s)",
        "post_shock_time_loss": "Post-shock time loss (s)",
        "queue": "Queue length (vehicles)",
        "mean_queue": "Queue length (vehicles)",
        "avg_queue": "Queue length (vehicles)",
        "average_queue": "Queue length (vehicles)",
        "movement_queue_mean": "Queue length (vehicles)",
        "post_shock_mean_queue": "Post-shock mean queue (vehicles)",
        "mean_network_queue_vehicles": "Mean network queue (vehicles)",
        "max_network_queue_vehicles": "Max network queue (vehicles)",
        "mean_intersection_queue_vehicles": "Mean intersection queue (vehicles)",
        "max_intersection_queue_vehicles": "Max intersection queue (vehicles)",
        "max_lane_queue_vehicles": "Max lane queue (vehicles)",
        "post_shock_mean_network_queue_vehicles": "Post-shock mean network queue (vehicles)",
        "post_shock_max_network_queue_vehicles": "Post-shock max network queue (vehicles)",
        "post_shock_queue_auc_vehicle_seconds": "Post-shock queue AUC (vehicle-s)",
        "corridor_mean_travel_time": "Corridor travel time (s, completed trips)",
        "corridor_mean_stops": "Corridor stops (stops/vehicle, completed trips)",
        "completion_ratio_offered": "Completion ratio (arrived / offered)",
        "departure_ratio": "Departure ratio (departed / offered)",
        "mean_depart_delay_seconds": "Insertion delay (s)",
        "max_queue": "Max queue length (vehicles)",
        "maximum_queue": "Max queue length (vehicles)",
        "movement_queue_max": "Max queue length (vehicles)",
        "post_shock_max_queue": "Post-shock max queue (vehicles)",
        "post_shock_queue_auc": "Post-shock queue AUC (vehicle-s)",
        "throughput": "Throughput (vehicles)",
        "network_throughput": "Network throughput (vehicles)",
        "corridor_throughput": "Corridor throughput (vehicles)",
        "corridor_travel_time": "Corridor travel time (s)",
        "corridor_stops": "Corridor stops (stops/vehicle)",
        "throughput_change_vs_zero_loss": "Throughput change vs zero loss (vehicles)",
        "vehicles_arrived": "Throughput (vehicles)",
        "arrived": "Throughput (vehicles)",
        "mean_stops": "Stops (stops/vehicle)",
        "stops": "Stops (stops/vehicle)",
        "internal_lane_persistence_events": "Internal lane persistence events",
        "messages": "Messages (count)",
        "messages_sent": "Messages (count)",
        "messages_delivered": "Messages (count)",
        "messages_dropped": "Messages dropped (count)",
        "messages_stale": "Stale messages (count)",
        "bytes": "Bytes",
        "bytes_sent": "Bytes sent",
        "bytes_delivered": "Bytes delivered",
        "serialized_bytes": "Bytes",
        "message_bytes": "Bytes",
        "mean_message_age_steps": "Mean message age (steps)",
        "max_message_age_steps": "Max message age (steps)",
    }
    return labels.get(metric, metric.replace("_", " ").title())


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _require_file(path: Path) -> None:
    if not path.exists():
        msg = f"required result file not found: {path}"
        raise FileNotFoundError(msg)
    if not path.is_file():
        msg = f"required result path is not a file: {path}"
        raise ReportGenerationError(msg)


def _first_present(
    record: Mapping[str, Any],
    aliases: Sequence[str],
    *,
    required: bool,
) -> Any:
    for alias in aliases:
        if alias in record:
            return record[alias]
    if required:
        msg = f"result parquet missing required column; expected one of {tuple(aliases)}"
        raise ReportGenerationError(msg)
    return None


def _canonical_controller(value: Any) -> str:
    controller = str(value)
    return CONTROLLER_ALIASES.get(controller, controller)


def _finite_float(value: Any, *, row_index: int) -> float:
    if value is None:
        msg = f"metric value is missing at row {row_index}"
        raise ReportGenerationError(msg)
    numeric = float(value)
    if not math.isfinite(numeric):
        msg = f"metric value must be finite at row {row_index}; got {value!r}"
        raise ReportGenerationError(msg)
    return numeric


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        msg = f"optional numeric field must be finite; got {value!r}"
        raise ReportGenerationError(msg)
    return numeric


def _is_failed_status(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"failed", "failure", "error", "crashed"}


def _is_failed_success(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return not value
    return str(value).strip().lower() in {"false", "0", "no"}
