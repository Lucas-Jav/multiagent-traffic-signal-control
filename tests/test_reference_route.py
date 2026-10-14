from __future__ import annotations

import math
import random

import pytest

from traffic_agents.experiments import reference_route as rr
from traffic_agents.metrics.run_metrics import OfferedVehicle, TripRecord

ROUTE = rr.REFERENCE_ROUTE_EDGES
WARMUP = 300.0
DURATION = 3600.0


def _vehicle(vehicle_id: str, depart: float, route: tuple[str, ...] = ROUTE) -> OfferedVehicle:
    return OfferedVehicle(
        vehicle_id=vehicle_id,
        demand_id=vehicle_id.split(".")[0],
        scheduled_depart=depart,
        entry_edge_id=route[0],
        route=route,
    )


def _trip(
    vehicle_id: str,
    depart: float,
    *,
    arrival: float = -1.0,
    duration: float = -1.0,
    waiting: float = 0.0,
    loss: float = 0.0,
    stops: float = 0.0,
) -> TripRecord:
    return TripRecord(
        vehicle_id=vehicle_id,
        depart=depart,
        depart_delay=0.0,
        arrival=arrival,
        duration=duration,
        waiting_time=waiting,
        time_loss=loss,
        waiting_count=stops,
    )


def test_exact_edge_sequence_matching() -> None:
    assert rr.matches_reference_route(ROUTE)
    assert rr.matches_reference_route(list(ROUTE))
    # prefixes, suffixes, longer routes and other O-D pairs through A5 do not match
    assert not rr.matches_reference_route(ROUTE[:3])
    assert not rr.matches_reference_route(ROUTE[1:])
    assert not rr.matches_reference_route((*ROUTE, "C1C0"))
    assert not rr.matches_reference_route(("left1A1", "A1B1", "B1C1", "C1C0", "C0bottom2"))
    assert not rr.matches_reference_route(("right1C1", "C1B1", "B1A1", "A1left1"))
    assert not rr.matches_reference_route(tuple(reversed(ROUTE)))


def test_logical_mapping_of_the_reference_route() -> None:
    assert rr.REFERENCE_ROUTE_LOGICAL_PATH == ("West entry", "A4", "A5", "A6", "East exit")
    assert ROUTE == ("left1A1", "A1B1", "B1C1", "C1right1")


def test_cohort_selection_is_route_id_independent_and_deterministic() -> None:
    # The same planned route under different SUMO route ids (r2 in S2, r12 in S1): the offered
    # vehicle only carries the resolved edge sequence, never the route id.
    vehicles = [
        _vehicle("b.1", 1000.0),
        _vehicle("a.0", 400.0),
        _vehicle("c.2", 400.0),
        _vehicle("warmup.0", 120.0),  # scheduled in warmup: excluded
        _vehicle("late.0", 3900.0),  # at the end of the window: excluded
        _vehicle("other.0", 500.0, ("left0A0", "A0B0", "B0bottom1")),
        _vehicle("sub.0", 600.0, ("left1A1", "A1B1", "B1C1", "C1C0", "C0bottom2")),
    ]
    shuffled = vehicles[:]
    random.Random(7).shuffle(shuffled)

    first = rr.select_reference_cohort(
        vehicles, warmup_seconds=WARMUP, measurement_duration_seconds=DURATION
    )
    second = rr.select_reference_cohort(
        shuffled, warmup_seconds=WARMUP, measurement_duration_seconds=DURATION
    )

    assert [v.vehicle_id for v in first] == ["a.0", "c.2", "b.1"]
    assert first == second  # order of the input never matters


def test_unfinished_and_never_inserted_trips_get_no_duration() -> None:
    cohort = [_vehicle("done.0", 400.0), _vehicle("stuck.0", 500.0), _vehicle("never.0", 600.0)]
    trips = {
        "done.0": _trip("done.0", 400.0, arrival=480.0, duration=80.0, waiting=10.0, loss=30.0,
                        stops=2.0),
        "stuck.0": _trip("stuck.0", 510.0, duration=3390.0, waiting=900.0, loss=900.0, stops=9.0),
    }  # fmt: skip

    rows = rr.build_vehicle_rows(cohort, trips)
    by_id = {row.vehicle_id: row for row in rows}

    assert by_id["done.0"].status == "COMPLETED"
    assert by_id["done.0"].travel_time == 80.0
    assert by_id["stuck.0"].status == "UNFINISHED"
    assert by_id["stuck.0"].travel_time is None  # never a zero or a partial duration
    assert by_id["stuck.0"].waiting_time is None
    assert by_id["never.0"].status == "NEVER_INSERTED"
    assert by_id["never.0"].actual_depart_time is None

    metrics = rr.run_metrics(rows)
    assert metrics["reference_route_mean_travel_time_seconds"] == 80.0
    assert metrics["reference_route_median_travel_time_seconds"] == 80.0
    assert metrics["reference_route_mean_waiting_time_seconds"] == 10.0
    assert metrics["reference_route_mean_stops"] == 2.0
    assert metrics["reference_route_completion_ratio_offered"] == pytest.approx(1 / 3)
    assert metrics["reference_route_completion_ratio_departed"] == pytest.approx(1 / 2)


def test_run_without_completed_trips_has_no_means_instead_of_zero() -> None:
    rows = rr.build_vehicle_rows([_vehicle("a.0", 400.0)], {})

    metrics = rr.run_metrics(rows)

    assert metrics["reference_route_mean_travel_time_seconds"] is None
    assert metrics["reference_route_completion_ratio_offered"] == 0.0
    assert metrics["reference_route_completion_ratio_departed"] is None


def test_population_accounting_is_consistent() -> None:
    cohort = [_vehicle(f"v.{i}", 400.0 + i) for i in range(10)]
    trips = {}
    for i in range(7):  # 7 inserted, 3 never inserted
        completed = i < 4  # 4 completed, 3 unfinished
        trips[f"v.{i}"] = (
            _trip(f"v.{i}", 400.0 + i, arrival=500.0 + i, duration=100.0)
            if completed
            else _trip(f"v.{i}", 400.0 + i, duration=3000.0)
        )

    counts = rr.population_counts(rr.build_vehicle_rows(cohort, trips))

    assert counts == {
        "reference_route_offered": 10,
        "reference_route_departed": 7,
        "reference_route_arrived": 4,
        "reference_route_never_inserted": 3,
        "reference_route_unfinished": 3,
    }
    assert counts["reference_route_departed"] == (
        counts["reference_route_arrived"] + counts["reference_route_unfinished"]
    )
    assert counts["reference_route_offered"] == (
        counts["reference_route_departed"] + counts["reference_route_never_inserted"]
    )


def _manifest(**overrides: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "network_sha256": "n",
        "route_sha256": "r",
        "turning_config_sha256": "t",
        "scenario_neutral_sha256": "s",
        "demand_profile": "S2_DIRECTIONAL_PEAK",
        "seed": 42,
        "warmup_seconds": 300.0,
        "measurement": {"measurement_duration_seconds": 3600.0},
    }
    manifest.update(overrides)
    return manifest


def test_pairing_accepts_identical_invariants() -> None:
    manifests = {controller: _manifest() for controller in rr.CONTROLLERS}

    assert rr.pairing_mismatches(manifests) == []


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"network_sha256": "x"}, "network_sha256"),
        ({"route_sha256": "x"}, "route_sha256"),
        ({"turning_config_sha256": "x"}, "turning_config_sha256"),
        ({"scenario_neutral_sha256": "x"}, "scenario_neutral_sha256"),
        ({"demand_profile": "S1_BALANCED"}, "demand_profile"),
        ({"seed": 2027}, "seed"),
        ({"warmup_seconds": 0.0}, "warmup_seconds"),
        ({"measurement": {"measurement_duration_seconds": 1800.0}}, "measurement_duration"),
    ],
)
def test_pairing_flags_any_mismatch(override: dict[str, object], field: str) -> None:
    manifests = {controller: _manifest() for controller in rr.CONTROLLERS}
    manifests[rr.C1] = _manifest(**override)

    mismatches = rr.pairing_mismatches(manifests)

    assert len(mismatches) == 1
    assert mismatches[0].startswith(field)


def test_pairing_flags_missing_fields() -> None:
    manifests = {controller: _manifest() for controller in rr.CONTROLLERS}
    del manifests[rr.B2]["route_sha256"]
    del manifests[rr.B0_CALIBRATED]["route_sha256"]

    assert any(m.startswith("route_sha256") for m in rr.pairing_mismatches(manifests))


def test_bootstrap_is_reproducible_and_seed_specific() -> None:
    diffs = [-12.0, -3.5, 4.0, -8.25, -1.0]
    seed = rr.stable_seed("S2_DIRECTIONAL_PEAK|B2|C1|metric")

    first = rr.paired_bootstrap_ci(diffs, seed=seed)
    second = rr.paired_bootstrap_ci(diffs, seed=seed)
    other = rr.paired_bootstrap_ci(diffs, seed=seed + 1)

    assert first == second
    assert first != other
    assert first[0] <= sum(diffs) / len(diffs) <= first[1]
    assert rr.stable_seed("a") == rr.stable_seed("a")
    assert rr.stable_seed("a") != rr.stable_seed("b")


def test_bootstrap_of_constant_differences_is_degenerate_and_empty_is_nan() -> None:
    assert rr.paired_bootstrap_ci([2.0, 2.0, 2.0], seed=1) == (2.0, 2.0)
    low, high = rr.paired_bootstrap_ci([], seed=1)
    assert math.isnan(low)
    assert math.isnan(high)


def test_pairwise_comparison_sign_and_relative_difference() -> None:
    values = {
        rr.B2: {1: 100.0, 2: 120.0, 3: 110.0},
        rr.C1: {1: 90.0, 2: 108.0, 3: 99.0},
    }

    row = rr.pairwise_comparison(
        scenario="S1_BALANCED",
        baseline=rr.B2,
        treatment=rr.C1,
        metric=rr.PRIMARY_METRIC,
        values_by_controller=values,
        seeds=(1, 2, 3),
    )

    assert row["n_seeds"] == 3
    assert row["paired_diff_per_seed"] == [-10.0, -12.0, -11.0]
    assert row["paired_mean_diff"] == pytest.approx(-11.0)
    assert row["paired_median_diff"] == pytest.approx(-11.0)
    assert row["baseline_mean"] == pytest.approx(110.0)
    assert row["relative_diff"] == pytest.approx(-0.1)
    assert row["ci95_high"] < 0  # type: ignore[operator]
    # deterministic: the CI does not change between calls
    again = rr.pairwise_comparison(
        scenario="S1_BALANCED",
        baseline=rr.B2,
        treatment=rr.C1,
        metric=rr.PRIMARY_METRIC,
        values_by_controller=values,
        seeds=(1, 2, 3),
    )
    assert (again["ci95_low"], again["ci95_high"]) == (row["ci95_low"], row["ci95_high"])


def test_pairwise_comparison_skips_seeds_without_data_and_never_forces_a_sign() -> None:
    values = {rr.B2: {1: 100.0, 2: None, 3: 100.0}, rr.C1: {1: 110.0, 2: 90.0, 3: 90.0}}

    row = rr.pairwise_comparison(
        scenario="S4_LOCAL_SATURATION",
        baseline=rr.B2,
        treatment=rr.C1,
        metric=rr.PRIMARY_METRIC,
        values_by_controller=values,
        seeds=(1, 2, 3),
    )

    assert row["n_seeds"] == 2
    assert row["seeds"] == [1, 3]
    assert row["paired_diff_per_seed"] == [10.0, -10.0]
    text = rr.interpret(row, None)
    assert "sem diferença distinguível" in text  # CI includes 0: no positive spin


def test_interpretation_reports_completion_changes() -> None:
    travel = {"ci95_low": -20.0, "ci95_high": -5.0, "paired_mean_diff": -12.0}
    completion = {"ci95_low": -0.3, "ci95_high": -0.1, "paired_mean_diff": -0.2}

    text = rr.interpret(travel, completion)

    assert "menor" in text
    assert "conclusão" in text
    assert "cautela" in text
    assert "maior" in rr.interpret(
        {"ci95_low": 1.0, "ci95_high": 9.0, "paired_mean_diff": 5.0}, None
    )
