from __future__ import annotations

# ruff: noqa: I001

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

import pyarrow.parquet as pq  # type: ignore[import-untyped]


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
        "queue",
        "mean_queue",
        "avg_queue",
        "average_queue",
        "movement_queue_mean",
    ),
    "max_queue_by_controller.png": (
        "max_queue",
        "maximum_queue",
        "movement_queue_max",
    ),
    "throughput_by_controller.png": (
        "throughput",
        "vehicles_arrived",
        "arrived",
    ),
}

COMMUNICATION_MESSAGE_METRICS = (
    "messages",
    "messages_sent",
    "messages_delivered",
)
COMMUNICATION_BYTE_METRICS = (
    "bytes",
    "serialized_bytes",
    "message_bytes",
)
SENSITIVITY_TRAFFIC_METRICS = (
    "waiting_time",
    "mean_waiting_time",
    "time_loss",
    "mean_time_loss",
    "queue",
    "mean_queue",
    "throughput",
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


def generate_experiment_report(experiment_folder: Path) -> FigureReport:
    combined_path = experiment_folder / "combined_metrics.parquet"
    analysis_path = experiment_folder / "analysis.parquet"
    _require_file(combined_path)
    _require_file(analysis_path)

    combined = _normalize_combined_metrics(_read_parquet(combined_path))
    analysis = _normalize_analysis(_read_parquet(analysis_path))
    _validate_combined_metrics(combined)

    figures_dir = experiment_folder / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

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
    )


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    return [dict(row) for row in pq.read_table(path).to_pylist()]


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
        "time_loss": "Time loss (s)",
        "mean_time_loss": "Time loss (s)",
        "avg_time_loss": "Time loss (s)",
        "average_time_loss": "Time loss (s)",
        "queue": "Queue length (vehicles)",
        "mean_queue": "Queue length (vehicles)",
        "avg_queue": "Queue length (vehicles)",
        "average_queue": "Queue length (vehicles)",
        "movement_queue_mean": "Queue length (vehicles)",
        "max_queue": "Max queue length (vehicles)",
        "maximum_queue": "Max queue length (vehicles)",
        "movement_queue_max": "Max queue length (vehicles)",
        "throughput": "Throughput (vehicles)",
        "vehicles_arrived": "Throughput (vehicles)",
        "arrived": "Throughput (vehicles)",
        "messages": "Messages (count)",
        "messages_sent": "Messages (count)",
        "messages_delivered": "Messages (count)",
        "bytes": "Bytes",
        "serialized_bytes": "Bytes",
        "message_bytes": "Bytes",
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
