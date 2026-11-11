from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.metrics import (
    JUNCTION_TELEMETRY_FILE,
    LANE_TELEMETRY_FILE,
    MetricsFinalizationError,
    finalize_run_metrics,
    load_offered_vehicles,
)

WARMUP = 10
MEASUREMENT = 20
SHOCK = WARMUP + MEASUREMENT // 2
LANES = ("top1A1_0", "right1A1_0", "bottom1A1_0", "left1A1_0")


def s3_config(*, warmup: int = WARMUP, measurement: int = MEASUREMENT) -> ScenarioConfig:
    return ScenarioConfig.model_validate(
        {
            "scenario_id": "grid_3x3",
            "network_file": "network.net.xml",
            "route_file": "routes.rou.xml",
            "simulation": {
                "warmup_seconds": warmup,
                "measurement_duration_seconds": measurement,
                "step_length": 1.0,
                "seed": 42,
            },
            "controller_id": "B0_FIXED",
            "traffic": {
                "demand_profile": "S3_DEMAND_SHIFT",
                "demand_level": "MEDIUM",
                "shock_start_seconds": warmup + measurement / 2,
                "entries": [
                    {
                        "demand_id": "base_left1A1",
                        "entry_edge_id": "left1A1",
                        "begin_seconds": 0,
                        "end_seconds": warmup + measurement,
                        "vehicles_per_hour": {"LOW": 1, "MEDIUM": 2, "HIGH": 3},
                    }
                ],
            },
            "intersections": [
                {
                    "intersection_id": "A1",
                    "incoming_lanes": list(LANES),
                    "outgoing_lanes": ["A1top1_0", "A1right1_0", "A1bottom1_0", "A1left1_0"],
                    "phases": ["north_south", "east_west"],
                }
            ],
        }
    )


def write_route_file(path: Path, scheduled: dict[str, float]) -> None:
    vehicles = "\n".join(
        f'  <vehicle id="base_left1A1.{index}" depart="{depart}" route="r0"/>'
        for index, depart in enumerate(scheduled.values())
    )
    path.write_text(
        f'<routes>\n  <route id="r0" edges="left1A1 A1B1 B1C1 C1right1"/>\n{vehicles}\n</routes>',
        encoding="utf-8",
    )


def write_tripinfo(path: Path, trips: list[dict[str, Any]]) -> None:
    lines = ['<tripinfos xmlns:xsi="x">']
    for trip in trips:
        lines.append(
            '  <tripinfo id="{id}" depart="{depart}" departDelay="{delay}" '
            'arrival="{arrival}" duration="{duration}" waitingTime="{wait}" '
            'timeLoss="{loss}" waitingCount="{stops}"/>'.format(**trip)
        )
    lines.append("</tripinfos>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_statistics(path: Path) -> None:
    path.write_text(
        '<statistics><vehicles loaded="6" inserted="4" running="1" waiting="2"/>'
        '<teleports total="0" jam="0" yield="0" wrongLane="0"/></statistics>',
        encoding="utf-8",
    )


def write_telemetry(run_dir: Path, *, steps: int = 30) -> None:
    lane_count = len(LANES)
    step_index = np.repeat(np.arange(steps, dtype=np.int32), lane_count)
    queue = np.zeros((steps, lane_count), dtype=np.int16)
    queue[:, 0] = np.arange(steps)  # uma única lane carrega toda a fila da rede
    pq.write_table(
        pa.table(
            {
                "step_index": pa.array(step_index),
                "queue": pa.array(queue.reshape(-1)),
            }
        ),
        run_dir / LANE_TELEMETRY_FILE,
    )
    junction_steps = np.arange(steps, dtype=np.int32)
    pq.write_table(
        pa.table(
            {
                "step_index": pa.array(junction_steps),
                "intersection_total_queue": pa.array(np.arange(steps, dtype=np.int16)),
                "internal_lane_persistence_events": pa.array(
                    (junction_steps >= WARMUP).astype(np.int16)
                ),
            }
        ),
        run_dir / JUNCTION_TELEMETRY_FILE,
    )


def build_run(tmp_path: Path, *, with_tripinfo: bool = True) -> tuple[Path, Path]:
    run_dir = tmp_path / "run"
    (run_dir / "sumo").mkdir(parents=True)
    route_path = tmp_path / "routes.rou.xml"
    # partida programada de v0..v5: warmup, depois cinco veículos da coorte.
    write_route_file(
        route_path,
        {"v0": 2.0, "v1": 12.0, "v2": 21.0, "v3": 22.0, "v4": 25.0, "v5": 29.0},
    )
    if with_tripinfo:
        write_tripinfo(
            run_dir / "sumo" / "tripinfo.xml",
            [
                # programado durante o warmup, chega dentro da janela (conta apenas como throughput)
                dict(
                    id="base_left1A1.0",
                    depart=2,
                    delay=0,
                    arrival=12,
                    duration=10,
                    wait=2,
                    loss=4,
                    stops=1,
                ),
                dict(
                    id="base_left1A1.1",
                    depart=12,
                    delay=0,
                    arrival=20,
                    duration=8,
                    wait=2,
                    loss=3,
                    stops=1,
                ),
                dict(
                    id="base_left1A1.2",
                    depart=23,
                    delay=2,
                    arrival=28,
                    duration=5,
                    wait=4,
                    loss=6,
                    stops=2,
                ),
                # inserido mas não chegou ao fim da execução
                dict(
                    id="base_left1A1.3",
                    depart=24,
                    delay=2,
                    arrival=-1,
                    duration=-1,
                    wait=0,
                    loss=0,
                    stops=0,
                ),
            ],
        )
        write_statistics(run_dir / "sumo" / "statistics.xml")
    write_telemetry(run_dir)
    return run_dir, route_path


def manifest() -> dict[str, Any]:
    return {
        "run_id": "run-1",
        "scenario_id": "grid_3x3",
        "demand_profile": "S3_DEMAND_SHIFT",
        "seed": 42,
        "controller": {"controller_id": "C1_COOPERATIVE_COMPACT"},
        "simulation": {"wall_time_seconds": 3.0},
        "communication_metrics": {"messages_sent": 30, "messages_dropped": 0, "bytes_sent": 900},
        "network_sha256": "n",
        "route_sha256": "r",
        "phase_plan_sha256": "p",
        "movement_model_sha256": "m",
        "turning_config_sha256": "t",
        "communication_topology_sha256": "c",
    }


def finalize(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    run_dir, route_path = build_run(tmp_path)
    arguments: dict[str, Any] = {
        "run_dir": run_dir,
        "manifest": manifest(),
        "scenario_config": s3_config(),
        "route_path": route_path,
        "route_metadata_path": None,
        "steps_executed": WARMUP + MEASUREMENT,
    }
    arguments.update(overrides)
    return finalize_run_metrics(**arguments)


def test_offered_inserted_arrived_populations_are_separated(tmp_path: Path) -> None:
    metrics = finalize(tmp_path)["metrics"]

    # Execução inteira: 6 ofertados, 4 inseridos, 3 chegaram, 2 nunca inseridos, 1 ainda na rede.
    assert metrics["full_run_offered_vehicle_count"] == 6
    assert metrics["full_run_departed_vehicle_count"] == 4
    assert metrics["full_run_arrived_vehicle_count"] == 3
    assert metrics["full_run_never_inserted_vehicle_count"] == 2
    assert metrics["full_run_unfinished_in_network_count"] == 1
    # Coorte de medição (programados dentro de [10, 30)): apenas v1..v5; o veículo de warmup v0 é
    # excluído.
    assert metrics["offered_vehicle_count"] == 5
    assert metrics["departed_vehicle_count"] == 3
    assert metrics["arrived_vehicle_count"] == 2
    assert metrics["never_inserted_vehicle_count"] == 2
    assert metrics["unfinished_in_network_count"] == 1
    assert metrics["measurement_offered_vehicle_count"] == 5
    assert metrics["measurement_departed_vehicle_count"] == 3
    assert metrics["measurement_arrived_vehicle_count"] == 2
    assert metrics["departure_ratio"] == pytest.approx(3 / 5)
    assert metrics["completion_ratio_offered"] == pytest.approx(2 / 5)
    assert metrics["completion_ratio_departed"] == pytest.approx(2 / 3)
    assert metrics["full_run_completion_ratio_offered"] == pytest.approx(3 / 6)


def test_throughput_counts_window_arrivals_and_warmup_demand_does_not_enter_cohort(
    tmp_path: Path,
) -> None:
    metrics = finalize(tmp_path)["metrics"]

    # v0 (programado no warmup) chega em t=12 dentro da janela: apenas contagem de fluxo.
    assert metrics["throughput"] == 3
    assert metrics["measurement_arrivals_from_warmup_offered_count"] == 1
    # As métricas de viagens concluídas usam a coorte (v1, v2) e excluem o veículo de warmup v0.
    assert metrics["completed_trip_count"] == 2
    assert metrics["mean_travel_time"] == pytest.approx((8 + 5) / 2)
    assert metrics["mean_waiting_time"] == pytest.approx((2 + 4) / 2)
    assert metrics["mean_time_loss"] == pytest.approx((3 + 6) / 2)
    assert metrics["mean_stops"] == pytest.approx((1 + 2) / 2)
    assert metrics["mean_time_in_system_seconds"] == pytest.approx((8 + 0 + 5 + 2) / 2)


def test_insertion_delay_and_never_inserted_backlog_are_reported_separately(
    tmp_path: Path,
) -> None:
    metrics = finalize(tmp_path)["metrics"]

    # Atrasos dos três veículos da coorte inseridos (v1=0, v2=2, v3=2).
    assert metrics["total_depart_delay_seconds"] == 4
    assert metrics["mean_depart_delay_seconds"] == pytest.approx(4 / 3)
    # Limite inferior para v4 (25) e v5 (29), nunca inseridos, com a execução terminando em t=30.
    assert metrics["never_inserted_backlog_delay_lower_bound_seconds"] == (30 - 25) + (30 - 29)
    # Veículos nunca inseridos não são incorporados ao tempo de viagem de viagens concluídas.
    assert metrics["mean_travel_time"] == pytest.approx(6.5)


def test_queue_metrics_use_unique_lanes_only(tmp_path: Path) -> None:
    metrics = finalize(tmp_path)["metrics"]

    steps = np.arange(WARMUP, WARMUP + MEASUREMENT)
    assert metrics["mean_network_queue_vehicles"] == pytest.approx(steps.mean())
    assert metrics["max_network_queue_vehicles"] == steps.max()
    assert metrics["mean_intersection_queue_vehicles"] == pytest.approx(steps.mean())
    assert metrics["max_intersection_queue_vehicles"] == steps.max()
    assert metrics["max_lane_queue_vehicles"] == steps.max()
    assert metrics["mean_lane_queue_vehicles"] == pytest.approx(steps.mean() / len(LANES))
    assert metrics["internal_lane_persistence_events"] == MEASUREMENT
    assert "max_queue" not in metrics
    assert "mean_queue" not in metrics


def test_post_shock_queue_auc_is_trapezoidal_over_network_total_queue(tmp_path: Path) -> None:
    payload = finalize(tmp_path)
    metrics = payload["metrics"]

    shock_step = int(SHOCK)
    post = np.arange(shock_step, WARMUP + MEASUREMENT, dtype=float)
    times = post + 1.0
    expected_auc = float(np.trapezoid(post, times))
    assert payload["windows"]["shock_start_seconds"] == SHOCK
    assert expected_auc == pytest.approx(220.5)
    assert metrics["post_shock_queue_auc_vehicle_seconds"] == pytest.approx(expected_auc)
    assert metrics["post_shock_mean_network_queue_vehicles"] == pytest.approx(post.mean())
    assert metrics["post_shock_max_network_queue_vehicles"] == post.max()
    assert metrics["pre_shock_mean_network_queue_vehicles"] == pytest.approx(
        np.arange(WARMUP, shock_step).mean()
    )
    # População por tempo PROGRAMADO: apenas v2 (21) e v3 (22, não finalizado) são pós-choque; v2
    # concluído.
    assert metrics["post_shock_completed_trip_count"] == 1
    assert metrics["post_shock_time_loss"] == pytest.approx(6.0)
    assert metrics["pre_shock_time_loss"] == pytest.approx(3.0)


def test_communication_and_performance_metrics_are_carried_into_run_metrics(
    tmp_path: Path,
) -> None:
    payload = finalize(tmp_path, performance={"controller_decision_mean_ms": 0.5})
    metrics = payload["metrics"]

    assert metrics["messages_sent"] == 30
    assert metrics["messages_dropped"] == 0
    assert metrics["bytes_sent"] == 900
    assert metrics["wall_time_seconds"] == 3.0
    assert metrics["steps_per_second"] == pytest.approx(10.0)
    assert metrics["controller_decision_mean_ms"] == 0.5
    assert metrics["sumo_vehicles_inserted"] == 4
    assert payload["controller_id"] == "C1_COOPERATIVE_COMPACT"
    assert payload["status"] == "COMPLETED"
    assert payload["invariants"]["route_sha256"] == "r"


def test_corridor_metrics_use_route_membership(tmp_path: Path) -> None:
    metrics = finalize(tmp_path)["metrics"]

    # todo veículo sintético atravessa A1B1 -> B1C1 (definição de corredor v2).
    assert metrics["corridor_throughput"] == 3
    assert metrics["corridor_mean_travel_time"] == pytest.approx(6.5)


def test_entry_and_group_accounting_from_route_metadata(tmp_path: Path) -> None:
    metadata_path = tmp_path / "routes.metadata.json"
    metadata_path.write_text(
        json.dumps({"entries": [{"demand_id": "base_left1A1", "group": "dominant"}]}),
        encoding="utf-8",
    )
    payload = finalize(tmp_path, route_metadata_path=metadata_path)

    assert payload["by_entry"]["left1A1"] == {
        "offered": 5,
        "departed": 3,
        "arrived": 2,
        "entry_departure_ratio": pytest.approx(0.6),
    }
    assert payload["metrics"]["offered_by_entry__left1A1"] == 5
    assert payload["metrics"]["departed_by_entry__left1A1"] == 3
    assert payload["metrics"]["arrived_by_entry__left1A1"] == 2
    assert payload["metrics"]["entry_departure_ratio__left1A1"] == pytest.approx(0.6)
    assert payload["by_group"]["dominant"]["offered"] == 5
    assert payload["metrics"]["group_dominant_departure_ratio"] == pytest.approx(0.6)
    assert payload["metrics"]["min_entry_departure_ratio"] == pytest.approx(0.6)


def test_zero_denominator_ratios_are_safe(tmp_path: Path) -> None:
    run_dir, route_path = build_run(tmp_path)
    write_tripinfo(run_dir / "sumo" / "tripinfo.xml", [])

    payload = finalize_run_metrics(
        run_dir=run_dir,
        manifest=manifest(),
        scenario_config=s3_config(),
        route_path=route_path,
        route_metadata_path=None,
        steps_executed=WARMUP + MEASUREMENT,
    )

    metrics = payload["metrics"]
    assert metrics["departure_ratio"] == 0.0
    assert metrics["completion_ratio_departed"] == 0.0
    assert metrics["throughput"] == 0
    assert "mean_travel_time" not in metrics


def test_finalization_fails_when_required_artifacts_are_missing(tmp_path: Path) -> None:
    run_dir, route_path = build_run(tmp_path, with_tripinfo=False)

    with pytest.raises(MetricsFinalizationError, match="tripinfo"):
        finalize_run_metrics(
            run_dir=run_dir,
            manifest=manifest(),
            scenario_config=s3_config(),
            route_path=route_path,
            route_metadata_path=None,
            steps_executed=WARMUP + MEASUREMENT,
        )


def test_finalization_fails_without_canonical_telemetry(tmp_path: Path) -> None:
    run_dir, route_path = build_run(tmp_path)
    (run_dir / LANE_TELEMETRY_FILE).unlink()

    with pytest.raises(MetricsFinalizationError, match="telemetry files are missing"):
        finalize_run_metrics(
            run_dir=run_dir,
            manifest=manifest(),
            scenario_config=s3_config(),
            route_path=route_path,
            route_metadata_path=None,
            steps_executed=WARMUP + MEASUREMENT,
        )


def test_finalization_fails_when_run_ends_before_measurement(tmp_path: Path) -> None:
    run_dir, route_path = build_run(tmp_path)

    with pytest.raises(MetricsFinalizationError, match="before the measurement window"):
        finalize_run_metrics(
            run_dir=run_dir,
            manifest=manifest(),
            scenario_config=s3_config(),
            route_path=route_path,
            route_metadata_path=None,
            steps_executed=WARMUP,
        )


def test_truncated_run_uses_effective_window_and_flags_incomplete_horizon(
    tmp_path: Path,
) -> None:
    payload = finalize(tmp_path, steps_executed=WARMUP + 8)

    assert payload["windows"]["horizon_complete"] is False
    assert payload["windows"]["effective_measurement_end_seconds"] == WARMUP + 8
    # coorte = veículos programados em [10, 18): apenas v1 (12).
    assert payload["metrics"]["offered_vehicle_count"] == 1


def test_legacy_flow_route_files_are_expanded_with_scheduled_departures(
    tmp_path: Path,
) -> None:
    route_path = tmp_path / "flows.rou.xml"
    route_path.write_text(
        '<routes><flow id="f" begin="0" end="100" vehsPerHour="360">'
        '<route edges="a b"/></flow></routes>',
        encoding="utf-8",
    )

    vehicles = load_offered_vehicles(route_path)

    assert len(vehicles) == 10
    assert vehicles[0].vehicle_id == "f.0"
    assert vehicles[3].scheduled_depart == pytest.approx(30.0)
    assert {vehicle.entry_edge_id for vehicle in vehicles} == {"a"}
