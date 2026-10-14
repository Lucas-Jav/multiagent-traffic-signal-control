"""Reference-route experiment: travel time of one fixed origin-destination route (Prompt 56).

The reference cohort is selected only by the PLANNED EDGE SEQUENCE of a vehicle. SUMO route ids
(``r2``, ``r12``, ...) change between scenarios and seeds and are never used. Population accounting
and trip means follow the project rules: means use COMPLETED trips only, an unfinished trip never
gets a duration, and the completion ratio always accompanies every travel-time metric.
"""

from __future__ import annotations

import math
import statistics
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from traffic_agents.metrics.run_metrics import OfferedVehicle, TripRecord

REFERENCE_ROUTE_EDGES: tuple[str, ...] = ("left1A1", "A1B1", "B1C1", "C1right1")
REFERENCE_ROUTE_LOGICAL_PATH: tuple[str, ...] = ("West entry", "A4", "A5", "A6", "East exit")
REFERENCE_ROUTE_ID = "WE_A4_A5_A6"

B0_CALIBRATED = "B0_FIXED_CALIBRATED"
B2 = "B2_LOCAL_PRESSURE"
C1 = "C1_COOPERATIVE_COMPACT"
CONTROLLERS: tuple[str, ...] = (B0_CALIBRATED, B2, C1)
# (baseline, treatment): the difference is always treatment - baseline.
COMPARISONS: tuple[tuple[str, str], ...] = ((B0_CALIBRATED, B2), (B2, C1), (B0_CALIBRATED, C1))
SCENARIOS: tuple[str, ...] = (
    "S1_BALANCED",
    "S2_DIRECTIONAL_PEAK",
    "S3_DEMAND_SHIFT",
    "S4_LOCAL_SATURATION",
)
PILOT_SEEDS: tuple[int, ...] = (42, 2027, 3253, 4517, 5791)

METRICS: tuple[str, ...] = (
    "reference_route_mean_travel_time_seconds",
    "reference_route_median_travel_time_seconds",
    "reference_route_mean_waiting_time_seconds",
    "reference_route_mean_time_loss_seconds",
    "reference_route_mean_stops",
    "reference_route_completion_ratio_offered",
    "reference_route_completion_ratio_departed",
)
PRIMARY_METRIC = "reference_route_mean_travel_time_seconds"
COMPLETION_METRIC = "reference_route_completion_ratio_offered"

POPULATION_KEYS: tuple[str, ...] = (
    "reference_route_offered",
    "reference_route_departed",
    "reference_route_arrived",
    "reference_route_never_inserted",
    "reference_route_unfinished",
)

# Pairing invariants: any mismatch between controllers of the same scenario+seed is CRITICAL.
# ``scenario_neutral_sha256`` is the scenario config hash with the controller id neutralised: the
# manifest ``scenario_sha256`` includes ``controller_id`` and therefore differs between controllers
# by design (it differs between B2 and C1 inside Pilot V2 itself).
PAIRING_FIELDS: tuple[str, ...] = (
    "network_sha256",
    "route_sha256",
    "turning_config_sha256",
    "scenario_neutral_sha256",
    "demand_profile",
    "seed",
    "warmup_seconds",
    "measurement_duration_seconds",
)
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_BASE_SEED = 20260930
SANITY_RANGES: Mapping[str, tuple[int, int]] = {
    "S1_BALANCED": (45, 59),
    "S2_DIRECTIONAL_PEAK": (97, 127),
    "S3_DEMAND_SHIFT": (106, 116),
    "S4_LOCAL_SATURATION": (188, 205),
}


# --- Cohort ---------------------------------------------------------------------------------------
def matches_reference_route(route: Sequence[str]) -> bool:
    """True only for the exact planned edge sequence (no prefix, suffix or sub-path match)."""

    return tuple(route) == REFERENCE_ROUTE_EDGES


def select_reference_cohort(
    offered: Sequence[OfferedVehicle],
    *,
    warmup_seconds: float,
    measurement_duration_seconds: float,
) -> tuple[OfferedVehicle, ...]:
    """Offered vehicles on the reference route scheduled inside the measurement window.

    The result is ordered by ``(scheduled_depart, vehicle_id)`` so it is deterministic.
    """

    end = warmup_seconds + measurement_duration_seconds
    cohort = [
        vehicle
        for vehicle in offered
        if matches_reference_route(vehicle.route)
        and warmup_seconds <= vehicle.scheduled_depart < end
    ]
    return tuple(sorted(cohort, key=lambda v: (v.scheduled_depart, v.vehicle_id)))


# --- Per-vehicle rows (also the data for the future visual replay) --------------------------------
@dataclass(frozen=True)
class VehicleRow:
    vehicle_id: str
    planned_depart_time: float
    status: str  # COMPLETED | UNFINISHED | NEVER_INSERTED
    actual_depart_time: float | None
    depart_delay: float | None
    arrival_time: float | None
    travel_time: float | None  # None unless the trip completed: never zero for unfinished trips
    waiting_time: float | None
    time_loss: float | None
    stops: float | None


def build_vehicle_rows(
    cohort: Sequence[OfferedVehicle],
    trips: Mapping[str, TripRecord],
) -> tuple[VehicleRow, ...]:
    rows: list[VehicleRow] = []
    for vehicle in cohort:
        trip = trips.get(vehicle.vehicle_id)
        if trip is None:
            rows.append(
                VehicleRow(
                    vehicle_id=vehicle.vehicle_id,
                    planned_depart_time=vehicle.scheduled_depart,
                    status="NEVER_INSERTED",
                    actual_depart_time=None,
                    depart_delay=None,
                    arrival_time=None,
                    travel_time=None,
                    waiting_time=None,
                    time_loss=None,
                    stops=None,
                )
            )
        elif not trip.arrived:
            rows.append(
                VehicleRow(
                    vehicle_id=vehicle.vehicle_id,
                    planned_depart_time=vehicle.scheduled_depart,
                    status="UNFINISHED",
                    actual_depart_time=trip.depart,
                    depart_delay=trip.depart_delay,
                    arrival_time=None,
                    travel_time=None,
                    waiting_time=None,
                    time_loss=None,
                    stops=None,
                )
            )
        else:
            rows.append(
                VehicleRow(
                    vehicle_id=vehicle.vehicle_id,
                    planned_depart_time=vehicle.scheduled_depart,
                    status="COMPLETED",
                    actual_depart_time=trip.depart,
                    depart_delay=trip.depart_delay,
                    arrival_time=trip.arrival,
                    travel_time=trip.duration,
                    waiting_time=trip.waiting_time,
                    time_loss=trip.time_loss,
                    stops=trip.waiting_count,
                )
            )
    return tuple(rows)


def population_counts(rows: Sequence[VehicleRow]) -> dict[str, int]:
    offered = len(rows)
    never_inserted = sum(1 for row in rows if row.status == "NEVER_INSERTED")
    arrived = sum(1 for row in rows if row.status == "COMPLETED")
    unfinished = sum(1 for row in rows if row.status == "UNFINISHED")
    return {
        "reference_route_offered": offered,
        "reference_route_departed": offered - never_inserted,
        "reference_route_arrived": arrived,
        "reference_route_never_inserted": never_inserted,
        "reference_route_unfinished": unfinished,
    }


def run_metrics(rows: Sequence[VehicleRow]) -> dict[str, float | None]:
    """Reference-route metrics of one run; trip means use COMPLETED trips only."""

    counts = population_counts(rows)
    completed = [row for row in rows if row.status == "COMPLETED"]
    travel = [row.travel_time for row in completed if row.travel_time is not None]
    waiting = [row.waiting_time for row in completed if row.waiting_time is not None]
    loss = [row.time_loss for row in completed if row.time_loss is not None]
    stops = [row.stops for row in completed if row.stops is not None]
    offered = counts["reference_route_offered"]
    departed = counts["reference_route_departed"]
    arrived = counts["reference_route_arrived"]
    return {
        "reference_route_mean_travel_time_seconds": statistics.fmean(travel) if travel else None,
        "reference_route_median_travel_time_seconds": statistics.median(travel) if travel else None,
        "reference_route_mean_waiting_time_seconds": statistics.fmean(waiting) if waiting else None,
        "reference_route_mean_time_loss_seconds": statistics.fmean(loss) if loss else None,
        "reference_route_mean_stops": statistics.fmean(stops) if stops else None,
        "reference_route_completion_ratio_offered": arrived / offered if offered else None,
        "reference_route_completion_ratio_departed": arrived / departed if departed else None,
    }


# --- Pairing --------------------------------------------------------------------------------------
def pairing_fields(manifest: Mapping[str, object]) -> dict[str, object]:
    measurement = manifest.get("measurement")
    duration = (
        measurement.get("measurement_duration_seconds") if isinstance(measurement, dict) else None
    )
    return {
        "network_sha256": manifest.get("network_sha256"),
        "route_sha256": manifest.get("route_sha256"),
        "turning_config_sha256": manifest.get("turning_config_sha256"),
        "scenario_neutral_sha256": manifest.get("scenario_neutral_sha256"),
        "demand_profile": manifest.get("demand_profile"),
        "seed": manifest.get("seed"),
        "warmup_seconds": manifest.get("warmup_seconds"),
        "measurement_duration_seconds": duration,
    }


def pairing_mismatches(manifests_by_controller: Mapping[str, Mapping[str, object]]) -> list[str]:
    """Fields in which the controllers of one scenario+seed disagree (empty list = paired)."""

    fields = {controller: pairing_fields(m) for controller, m in manifests_by_controller.items()}
    mismatches = []
    for name in PAIRING_FIELDS:
        values = {controller: f[name] for controller, f in fields.items()}
        if len({repr(v) for v in values.values()}) != 1 or any(v is None for v in values.values()):
            mismatches.append(f"{name}: {values}")
    return mismatches


# --- Statistics -----------------------------------------------------------------------------------
def stable_seed(label: str, base_seed: int = BOOTSTRAP_BASE_SEED) -> int:
    """Deterministic, label-specific RNG seed (independent of iteration order)."""

    return (base_seed + zlib.crc32(label.encode("utf-8"))) % (2**32)


def paired_bootstrap_ci(
    differences: Sequence[float],
    *,
    seed: int,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean of paired differences (resampling the pairs)."""

    values = np.asarray(differences, dtype=float)
    if values.size == 0:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, values.size, size=(n_resamples, values.size))
    means = values[indices].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(means, [alpha, 1.0 - alpha])
    return (float(low), float(high))


def pairwise_comparison(
    *,
    scenario: str,
    baseline: str,
    treatment: str,
    metric: str,
    values_by_controller: Mapping[str, Mapping[int, float | None]],
    seeds: Sequence[int],
) -> dict[str, object]:
    """Paired comparison (treatment - baseline) of one metric over seeds, one scenario."""

    paired = [
        (seed, values_by_controller[baseline].get(seed), values_by_controller[treatment].get(seed))
        for seed in seeds
    ]
    usable = [(s, a, b) for s, a, b in paired if a is not None and b is not None]
    baseline_values = [a for _, a, _ in usable]
    treatment_values = [b for _, _, b in usable]
    diffs = [b - a for _, a, b in usable]
    row: dict[str, object] = {
        "scenario": scenario,
        "baseline": baseline,
        "treatment": treatment,
        "comparison": f"{baseline} -> {treatment}",
        "metric": metric,
        "n_seeds": len(usable),
        "seeds": [s for s, _, _ in usable],
        "baseline_per_seed": baseline_values,
        "treatment_per_seed": treatment_values,
        "paired_diff_per_seed": diffs,
    }
    if not usable:
        row.update(
            baseline_mean=None, treatment_mean=None, baseline_median=None, treatment_median=None,
            paired_mean_diff=None, paired_median_diff=None, relative_diff=None,
            ci95_low=None, ci95_high=None, ci95_relative_low=None, ci95_relative_high=None,
        )  # fmt: skip
        return row
    baseline_mean = statistics.fmean(baseline_values)
    low, high = paired_bootstrap_ci(
        diffs, seed=stable_seed(f"{scenario}|{baseline}|{treatment}|{metric}")
    )
    relative = (lambda x: x / baseline_mean) if baseline_mean else (lambda x: math.nan)
    row.update(
        baseline_mean=baseline_mean,
        treatment_mean=statistics.fmean(treatment_values),
        baseline_median=statistics.median(baseline_values),
        treatment_median=statistics.median(treatment_values),
        paired_mean_diff=statistics.fmean(diffs),
        paired_median_diff=statistics.median(diffs),
        relative_diff=relative(statistics.fmean(diffs)),
        ci95_low=low,
        ci95_high=high,
        ci95_relative_low=relative(low),
        ci95_relative_high=relative(high),
    )
    return row


def interpret(
    travel_time: Mapping[str, object],
    completion: Mapping[str, object] | None,
) -> str:
    """Neutral reading of a travel-time comparison; the sign is never forced."""

    low, high = travel_time.get("ci95_low"), travel_time.get("ci95_high")
    diff = travel_time.get("paired_mean_diff")
    if low is None or high is None or diff is None:
        return "sem dados suficientes"
    assert isinstance(low, float | int)
    assert isinstance(high, float | int)
    assert isinstance(diff, float | int)
    if high < 0:
        text = f"tempo de viagem menor ({diff:+.1f} s, IC exclui 0)"
    elif low > 0:
        text = f"tempo de viagem maior ({diff:+.1f} s, IC exclui 0)"
    else:
        text = f"sem diferença distinguível ({diff:+.1f} s, IC inclui 0)"
    if completion is not None:
        c_low, c_high = completion.get("ci95_low"), completion.get("ci95_high")
        c_diff = completion.get("paired_mean_diff")
        if (
            isinstance(c_low, float | int)
            and isinstance(c_high, float | int)
            and isinstance(c_diff, float | int)
            and (c_high < 0 or c_low > 0)
        ):
            text += f"; conclusão {c_diff * 100:+.1f} p.p. (IC exclui 0): ler com cautela"
    return text
