from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_BOOTSTRAP_SEED = 20260910
DEFAULT_BOOTSTRAP_RESAMPLES = 10_000

CONTROLLER_ALIASES: Mapping[str, str] = {
    "B0": "B0_FIXED",
    "B1": "B1_LOCAL_ADAPTIVE",
    "B2": "B2_LOCAL_PRESSURE",
    "C1": "C1_COOPERATIVE_COMPACT",
    "C2": "C2_COOPERATIVE_EXPANDED",
}

DEFAULT_CONTROLLER_PAIRS: tuple[tuple[str, str], ...] = (
    ("B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT"),
    ("B2_LOCAL_PRESSURE", "C2_COOPERATIVE_EXPANDED"),
    ("B0_FIXED", "B1_LOCAL_ADAPTIVE"),
)

REQUIRED_ALIAS_GROUPS: Mapping[str, tuple[str, ...]] = {
    "scenario": ("scenario", "scenario_id"),
    "controller": ("controller", "controller_id"),
    "metric": ("metric", "metric_name"),
    "value": ("value", "metric_value"),
    "seed": ("seed", "simulation_seed"),
    "route_hash": ("route_hash", "route_sha256"),
    "network_hash": ("network_hash", "network_sha256"),
    "phase_plan": ("phase_plan", "phase_plan_hash", "phase_plan_sha256"),
    "turning_ratios": ("turning_ratios",),
}

OPTIONAL_ALIAS_GROUPS: Mapping[str, tuple[str, ...]] = {
    "demand": ("demand", "demand_profile", "demand_hash"),
    "phase_plan_version": ("phase_plan_version",),
    "movement_model_version": ("movement_model_version",),
    "communication_topology_hash": (
        "communication_topology_hash",
        "communication_topology_sha256",
    ),
    "run_id": ("run_id",),
    "status": ("status", "run_status"),
    "success": ("success", "succeeded"),
}

PAIRING_COLUMNS: tuple[str, ...] = (
    "scenario",
    "seed",
    "demand",
    "route_hash",
    "network_hash",
    "phase_plan",
    "phase_plan_version",
    "movement_model_version",
    "turning_ratios",
    "communication_topology_hash",
)


class AnalysisValidationError(ValueError):
    """Raised when experiment metrics cannot be analyzed safely."""


@dataclass(frozen=True)
class AnalysisConfig:
    input_path: Path = Path("combined_metrics.parquet")
    output_parquet_path: Path = Path("analysis.parquet")
    output_json_path: Path = Path("analysis.json")
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES
    controller_pairs: tuple[tuple[str, str], ...] = DEFAULT_CONTROLLER_PAIRS


def run_analysis(config: AnalysisConfig | None = None) -> dict[str, object]:
    active_config = config or AnalysisConfig()
    records = _read_metrics(active_config.input_path)
    normalized = _normalize_records(records)
    _validate_records(normalized)

    descriptive = _descriptive_statistics(normalized)
    comparisons = _pairwise_comparisons(
        normalized,
        controller_pairs=active_config.controller_pairs,
        bootstrap_seed=active_config.bootstrap_seed,
        bootstrap_resamples=active_config.bootstrap_resamples,
    )
    outliers = _outlier_records(normalized)

    payload: dict[str, object] = {
        "input": active_config.input_path.as_posix(),
        "outputs": {
            "analysis_parquet": active_config.output_parquet_path.as_posix(),
            "analysis_json": active_config.output_json_path.as_posix(),
        },
        "bootstrap": {
            "seed": active_config.bootstrap_seed,
            "resamples": active_config.bootstrap_resamples,
            "confidence_level": 0.95,
            "method": "paired percentile bootstrap over controller differences",
        },
        "pairing_unit": [
            "scenario",
            "seed",
            "demand/route hash",
            "network hash",
            "phase plan",
            "turning ratios",
        ],
        "test_assumptions": [
            "Pairing is performed before inference and requires equal invariant inputs.",
            "No failed run or NaN metric value is converted to zero.",
            "Outliers are reported with the 1.5*IQR rule and retained in all statistics.",
            "p-values are not emitted by default; confidence intervals and effect sizes lead.",
        ],
        "descriptive_statistics": descriptive,
        "pairwise_comparisons": comparisons,
        "outliers": outliers,
    }

    _write_pairwise_parquet(active_config.output_parquet_path, comparisons)
    active_config.output_json_path.parent.mkdir(parents=True, exist_ok=True)
    active_config.output_json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze paired traffic experiment metrics.")
    parser.add_argument("input", nargs="?", default="combined_metrics.parquet")
    parser.add_argument("--output-parquet", default="analysis.parquet")
    parser.add_argument("--output-json", default="analysis.json")
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    args = parser.parse_args(argv)

    run_analysis(
        AnalysisConfig(
            input_path=Path(args.input),
            output_parquet_path=Path(args.output_parquet),
            output_json_path=Path(args.output_json),
            bootstrap_seed=args.bootstrap_seed,
            bootstrap_resamples=args.bootstrap_resamples,
        )
    )
    return 0


def _read_metrics(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        msg = f"combined metrics parquet not found: {path}"
        raise FileNotFoundError(msg)
    return [dict(row) for row in pq.read_table(path).to_pylist()]


def _normalize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        row: dict[str, Any] = {"_row_index": index}
        for canonical, aliases in REQUIRED_ALIAS_GROUPS.items():
            row[canonical] = _first_present(record, aliases, required=True)
        for canonical, aliases in OPTIONAL_ALIAS_GROUPS.items():
            row[canonical] = _first_present(record, aliases, required=False)
        row["controller"] = _canonical_controller(str(row["controller"]))
        row["turning_ratios"] = _canonical_turning_ratios(row["turning_ratios"])
        row["value"] = _finite_float(row["value"], field="value", row_index=index)
        row["seed"] = _canonical_seed(row["seed"], row_index=index)
        normalized.append(row)
    return normalized


def _validate_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        msg = "combined metrics parquet has no rows"
        raise AnalysisValidationError(msg)

    failed_rows = [
        row
        for row in records
        if _is_failed_status(row.get("status")) or _is_failed_success(row.get("success"))
    ]
    if failed_rows:
        row_indexes = [int(row["_row_index"]) for row in failed_rows]
        msg = (
            "failed runs are present in combined metrics and cannot be analyzed as zero: "
            f"rows={row_indexes}"
        )
        raise AnalysisValidationError(msg)

    duplicate_keys = _duplicate_keys(
        records,
        (*PAIRING_COLUMNS, "metric", "controller"),
    )
    if duplicate_keys:
        msg = f"duplicate metric rows for the same paired unit/controller: {duplicate_keys[0]}"
        raise AnalysisValidationError(msg)


def _descriptive_statistics(records: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    values_by_group: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for row in records:
        key = (row["scenario"], row["controller"], row["metric"])
        values_by_group[key].append(float(row["value"]))

    output: list[dict[str, object]] = []
    for (scenario, controller, metric), values in sorted(values_by_group.items()):
        sorted_values = sorted(values)
        q1 = _quantile(sorted_values, 0.25)
        q3 = _quantile(sorted_values, 0.75)
        output.append(
            {
                "scenario": scenario,
                "controller": controller,
                "metric": metric,
                "count": len(sorted_values),
                "mean": statistics.fmean(sorted_values),
                "median": statistics.median(sorted_values),
                "std": statistics.stdev(sorted_values) if len(sorted_values) > 1 else None,
                "min": min(sorted_values),
                "max": max(sorted_values),
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
            }
        )
    return output


def _pairwise_comparisons(
    records: Sequence[Mapping[str, Any]],
    *,
    controller_pairs: Sequence[tuple[str, str]],
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> list[dict[str, object]]:
    if bootstrap_resamples <= 0:
        msg = "bootstrap_resamples must be positive"
        raise AnalysisValidationError(msg)

    output: list[dict[str, object]] = []
    scenarios = sorted({str(row["scenario"]) for row in records})
    metrics = sorted({str(row["metric"]) for row in records})

    for scenario in scenarios:
        for metric in metrics:
            rows = [
                row for row in records if row["scenario"] == scenario and row["metric"] == metric
            ]
            present_controllers = {str(row["controller"]) for row in rows}
            for controller_a, controller_b in controller_pairs:
                if (
                    controller_a not in present_controllers
                    or controller_b not in present_controllers
                ):
                    continue
                output.append(
                    _compare_controller_pair(
                        rows,
                        scenario=scenario,
                        metric=metric,
                        controller_a=controller_a,
                        controller_b=controller_b,
                        bootstrap_seed=bootstrap_seed,
                        bootstrap_resamples=bootstrap_resamples,
                    )
                )
    return output


def _compare_controller_pair(
    rows: Sequence[Mapping[str, Any]],
    *,
    scenario: str,
    metric: str,
    controller_a: str,
    controller_b: str,
    bootstrap_seed: int,
    bootstrap_resamples: int,
) -> dict[str, object]:
    by_controller: dict[str, dict[tuple[Any, ...], Mapping[str, Any]]] = {
        controller_a: {},
        controller_b: {},
    }
    for row in rows:
        controller = str(row["controller"])
        if controller not in by_controller:
            continue
        by_controller[controller][_pairing_key(row)] = row

    keys_a = set(by_controller[controller_a])
    keys_b = set(by_controller[controller_b])
    if keys_a != keys_b:
        mismatch_message = _first_invariant_mismatch_message(
            by_controller[controller_a].values(),
            by_controller[controller_b].values(),
        )
        if mismatch_message is not None:
            raise AnalysisValidationError(mismatch_message)
        missing_b = sorted(keys_a - keys_b)
        missing_a = sorted(keys_b - keys_a)
        msg = (
            f"missing paired runs for {scenario}/{metric}/{controller_a} vs {controller_b}; "
            f"missing {controller_b} for {missing_b}; missing {controller_a} for {missing_a}"
        )
        raise AnalysisValidationError(msg)

    differences: list[float] = []
    relative_differences: list[float] = []
    paired_differences: list[dict[str, object]] = []
    relative_valid = True
    for key in sorted(keys_a):
        row_a = by_controller[controller_a][key]
        row_b = by_controller[controller_b][key]
        _validate_pair_equivalence(row_a, row_b)
        value_a = float(row_a["value"])
        value_b = float(row_b["value"])
        difference = value_b - value_a
        differences.append(difference)
        relative_difference = None
        if value_a == 0 or not math.isfinite(value_a):
            relative_valid = False
        else:
            relative_difference = difference / value_a
            relative_differences.append(relative_difference)
        paired_differences.append(
            {
                "seed": row_a["seed"],
                "demand": row_a["demand"],
                "route_hash": row_a["route_hash"],
                "network_hash": row_a["network_hash"],
                "phase_plan": row_a["phase_plan"],
                "turning_ratios": row_a["turning_ratios"],
                "controller_a_value": value_a,
                "controller_b_value": value_b,
                "difference": difference,
                "relative_difference": relative_difference,
            }
        )

    if not differences:
        msg = f"no paired rows for {scenario}/{metric}/{controller_a} vs {controller_b}"
        raise AnalysisValidationError(msg)

    ci_low, ci_high = _paired_bootstrap_ci(
        differences,
        seed=bootstrap_seed,
        resamples=bootstrap_resamples,
    )
    relative_difference = (
        statistics.fmean(relative_differences)
        if relative_valid and len(relative_differences) == len(differences)
        else None
    )
    return {
        "scenario": scenario,
        "metric": metric,
        "controller_a": controller_a,
        "controller_b": controller_b,
        "n_pairs": len(differences),
        "mean_difference": statistics.fmean(differences),
        "median_difference": statistics.median(differences),
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "relative_difference": relative_difference,
        "relative_difference_valid": relative_difference is not None,
        "relative_difference_reason": None
        if relative_difference is not None
        else "baseline contains zero or mathematically inadequate values",
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_resamples": bootstrap_resamples,
        "test_name": None,
        "p_value": None,
        "paired_differences": paired_differences,
    }


def _validate_pair_equivalence(
    row_a: Mapping[str, Any],
    row_b: Mapping[str, Any],
) -> None:
    mismatches = [
        field
        for field in PAIRING_COLUMNS
        if _canonical_comparable(row_a.get(field)) != _canonical_comparable(row_b.get(field))
    ]
    if mismatches:
        details = {
            field: {
                "controller_a": row_a.get(field),
                "controller_b": row_b.get(field),
            }
            for field in mismatches
        }
        msg = f"paired rows have different invariant inputs: {details}"
        raise AnalysisValidationError(msg)


def _first_invariant_mismatch_message(
    rows_a: Iterable[Mapping[str, Any]],
    rows_b: Iterable[Mapping[str, Any]],
) -> str | None:
    by_loose_key_a = {_loose_pairing_key(row): row for row in rows_a}
    by_loose_key_b = {_loose_pairing_key(row): row for row in rows_b}
    for key in sorted(set(by_loose_key_a) & set(by_loose_key_b)):
        row_a = by_loose_key_a[key]
        row_b = by_loose_key_b[key]
        mismatches = [
            field
            for field in PAIRING_COLUMNS
            if _canonical_comparable(row_a.get(field)) != _canonical_comparable(row_b.get(field))
        ]
        if mismatches:
            details = {
                field: {
                    "controller_a": row_a.get(field),
                    "controller_b": row_b.get(field),
                }
                for field in mismatches
            }
            return f"paired rows have different invariant inputs: {details}"
    return None


def _paired_bootstrap_ci(
    differences: Sequence[float],
    *,
    seed: int,
    resamples: int,
) -> tuple[float, float]:
    if len(differences) == 1:
        return differences[0], differences[0]

    rng = random.Random(seed)
    n = len(differences)
    bootstrap_means = [
        statistics.fmean(differences[rng.randrange(n)] for _ in range(n)) for _ in range(resamples)
    ]
    bootstrap_means.sort()
    return _quantile(bootstrap_means, 0.025), _quantile(bootstrap_means, 0.975)


def _outlier_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    values_by_group: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for row in records:
        key = (row["scenario"], row["controller"], row["metric"])
        values_by_group[key].append(float(row["value"]))

    bounds_by_group: dict[tuple[Any, ...], tuple[float, float]] = {}
    for key, values in values_by_group.items():
        sorted_values = sorted(values)
        q1 = _quantile(sorted_values, 0.25)
        q3 = _quantile(sorted_values, 0.75)
        iqr = q3 - q1
        bounds_by_group[key] = q1 - 1.5 * iqr, q3 + 1.5 * iqr

    outliers: list[dict[str, object]] = []
    for row in records:
        group_key = (row["scenario"], row["controller"], row["metric"])
        low, high = bounds_by_group[group_key]
        value = float(row["value"])
        if value < low or value > high:
            outliers.append(
                {
                    "scenario": row["scenario"],
                    "controller": row["controller"],
                    "metric": row["metric"],
                    "value": value,
                    "seed": row["seed"],
                    "route_hash": row["route_hash"],
                    "network_hash": row["network_hash"],
                    "phase_plan": row["phase_plan"],
                    "turning_ratios": row["turning_ratios"],
                    "row_index": row["_row_index"],
                    "lower_bound": low,
                    "upper_bound": high,
                }
            )
    return outliers


def _write_pairwise_parquet(path: Path, comparisons: Sequence[Mapping[str, object]]) -> None:
    fields = [
        "scenario",
        "metric",
        "controller_a",
        "controller_b",
        "n_pairs",
        "mean_difference",
        "median_difference",
        "ci95_low",
        "ci95_high",
        "relative_difference",
        "relative_difference_valid",
        "relative_difference_reason",
        "bootstrap_seed",
        "bootstrap_resamples",
        "test_name",
        "p_value",
    ]
    rows = [{field: comparison.get(field) for field in fields} for comparison in comparisons]
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=_analysis_schema())
    pq.write_table(table, path)


def _analysis_schema() -> pa.Schema:
    return pa.schema(
        [
            ("scenario", pa.string()),
            ("metric", pa.string()),
            ("controller_a", pa.string()),
            ("controller_b", pa.string()),
            ("n_pairs", pa.int64()),
            ("mean_difference", pa.float64()),
            ("median_difference", pa.float64()),
            ("ci95_low", pa.float64()),
            ("ci95_high", pa.float64()),
            ("relative_difference", pa.float64()),
            ("relative_difference_valid", pa.bool_()),
            ("relative_difference_reason", pa.string()),
            ("bootstrap_seed", pa.int64()),
            ("bootstrap_resamples", pa.int64()),
            ("test_name", pa.string()),
            ("p_value", pa.float64()),
        ]
    )


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
        msg = f"combined metrics missing required column; expected one of {tuple(aliases)}"
        raise AnalysisValidationError(msg)
    return None


def _canonical_controller(controller: str) -> str:
    return CONTROLLER_ALIASES.get(controller, controller)


def _canonical_turning_ratios(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
    else:
        parsed = value
    if not isinstance(parsed, Mapping):
        msg = "turning_ratios must be a JSON object, mapping, or canonical string"
        raise AnalysisValidationError(msg)
    canonical = {str(key): float(parsed[key]) for key in sorted(parsed)}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def _finite_float(value: Any, *, field: str, row_index: int) -> float:
    if value is None:
        msg = f"{field} is missing at row {row_index}"
        raise AnalysisValidationError(msg)
    numeric = float(value)
    if not math.isfinite(numeric):
        msg = f"{field} must be finite; got {value!r} at row {row_index}"
        raise AnalysisValidationError(msg)
    return numeric


def _canonical_seed(value: Any, *, row_index: int) -> int:
    if isinstance(value, bool):
        msg = f"seed must be an integer at row {row_index}"
        raise AnalysisValidationError(msg)
    seed = int(value)
    if seed != float(value):
        msg = f"seed must be an integer at row {row_index}"
        raise AnalysisValidationError(msg)
    return seed


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


def _duplicate_keys(
    records: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> list[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: list[tuple[Any, ...]] = []
    for row in records:
        key = tuple(_canonical_comparable(row.get(field)) for field in fields)
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    return duplicates


def _pairing_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(_canonical_comparable(row.get(field)) for field in PAIRING_COLUMNS)


def _loose_pairing_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _canonical_comparable(row.get("scenario")),
        _canonical_comparable(row.get("seed")),
        _canonical_comparable(row.get("demand")),
    )


def _canonical_comparable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        msg = "cannot compute quantile of an empty sequence"
        raise AnalysisValidationError(msg)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


if __name__ == "__main__":
    raise SystemExit(main())
