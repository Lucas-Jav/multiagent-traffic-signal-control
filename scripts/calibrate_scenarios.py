"""Calibração objetiva de cenários pré-Pilot-V2 (Prompt 46.7). Controlador: apenas B0_FIXED.

    uv run python scripts/calibrate_scenarios.py run

As grades de candidatos, as seeds de calibração e todo critério de aceitação são declarados em
``artifacts/calibration/pilot_v2-scenario-calibration/calibration-plan.md`` e espelhados pelas
constantes abaixo. Os critérios nunca olham o desempenho do controlador: o B0 é apenas o plano
semafórico de referência estável usado para observar a demanda. Todos os artefatos carregam
``campaign_role: CALIBRATION``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import generate_scenarios as gen
import numpy as np
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.config import load_scenario_config
from traffic_agents.metrics.run_metrics import load_offered_vehicles, parse_tripinfo_records
from traffic_agents.simulation import TraCISimulationRunner

CAMPAIGN_ROLE = "CALIBRATION"
CONTROLLER = "B0_FIXED"
CALIBRATION_SEEDS = (101, 1009, 2029)
OUT_ROOT = Path("artifacts/calibration/pilot_v2-scenario-calibration")
SOURCE_DIR = Path("scenarios/grid_3x3")

S1_GRID = (150.0, 200.0, 250.0, 300.0, 350.0, 400.0)
S2_GRID = (240.0, 280.0, 320.0, 360.0, 400.0)
S3_GRID = (50.0, 100.0, 150.0, 200.0, 300.0)
S4_GRID = (0.75, 1.0, 1.25, 1.5, 2.0)

WARMUP = 300
MEASUREMENT = 3600
END = WARMUP + MEASUREMENT
SHOCK = gen.SHOCK_START_SECONDS
BIN = 300
VEHICLE_SLOT_M = 7.5
MIN_QUEUE_FLOOR = 5.0
SLOPE_FRACTION = 0.10
HOTSPOT = "A5"
NEIGHBOURS = ("A2", "A4", "A6", "A8")
CORNERS = ("A1", "A3", "A7", "A9")
LEFT_RIGHT = ("l", "L", "r", "R")
GROUPS = ("dominant", "residual", "shock", "hotspot", "base")


def _candidate_params(scenario: str, value: float, s1_rate: float) -> gen.DemandParameters:
    base = gen.DemandParameters(
        s1_rate=s1_rate, s2_dominant_rate=240.0, s3_shock_rate=100.0, s4_scale=1.0
    )
    if scenario == "s1":
        return replace(base, s1_rate=value)
    if scenario == "s2":
        return replace(base, s2_dominant_rate=value)
    if scenario == "s3":
        return replace(base, s3_shock_rate=value)
    return replace(base, s4_scale=value)


def _lane_capacities(network_path: Path) -> dict[str, int]:
    root = ET.parse(network_path).getroot()
    return {
        lane.get("id", ""): int(float(lane.get("length", "0")) // VEHICLE_SLOT_M)
        for lane in root.iter("lane")
        if not lane.get("id", "").startswith(":")
    }


def _movement_dirs(network_path: Path) -> dict[tuple[str, str], str]:
    root = ET.parse(network_path).getroot()
    return {
        (c.get("from", ""), c.get("to", "")): c.get("dir", "")
        for c in root.findall("connection")
        if not c.get("from", "").startswith(":")
    }


def _slope_change(series: np.ndarray) -> tuple[float, float, bool]:
    """Variação linear projetada no intervalo, sua média e o veredito de estabilidade normalizado."""

    steps = np.arange(series.size, dtype=float)
    slope = float(np.polyfit(steps, series.astype(float), 1)[0])
    projected = slope * series.size
    mean = float(series.mean())
    return projected, mean, projected <= SLOPE_FRACTION * max(mean, MIN_QUEUE_FLOOR)


def _side(entry_edge: str) -> str:
    return {"l": "W", "r": "E", "t": "N", "b": "S"}[entry_edge[0]]


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _group_of(vehicle: Any) -> str:
    return str(vehicle.demand_id.split("_", maxsplit=1)[0])


def analyze_run(run_dir: Path, scenario_dir: Path, route_file: str) -> dict[str, Any]:
    """Métricas brutas, independentes do controlador, de uma execução de calibração."""

    route_path = scenario_dir / route_file
    metadata = json.loads(route_path.with_suffix("").with_suffix(".metadata.json").read_text())
    offered = load_offered_vehicles(route_path)
    trips = parse_tripinfo_records(run_dir / "sumo" / "tripinfo.xml")
    capacities = _lane_capacities(scenario_dir / "network.net.xml")
    dirs = _movement_dirs(scenario_dir / "network.net.xml")

    lanes = pq.read_table(run_dir / "lane_telemetry.parquet").to_pydict()
    lane_ids = [str(x) for x in lanes["lane_id"]]
    n_lane = len(set(lane_ids))
    steps = len(lane_ids) // n_lane
    queue = np.asarray(lanes["queue"], dtype=float).reshape(steps, n_lane)
    occupancy = np.asarray(lanes["occupancy"], dtype=float).reshape(steps, n_lane)
    junction_cols = np.asarray([str(x) for x in lanes["intersection_id"]][:n_lane])
    capacity = np.asarray([capacities[lane] for lane in lane_ids[:n_lane]], dtype=float)
    q_net = queue.sum(axis=1)

    cohort = [v for v in offered if WARMUP <= v.scheduled_depart < END]
    departed = [v for v in cohort if v.vehicle_id in trips]
    arrived_times = np.asarray([t.arrival for t in trips.values() if t.arrived], dtype=float)

    def arrivals_between(start: float, end: float) -> float:
        return float(((arrived_times >= start) & (arrived_times < end)).sum())

    bins = [int(arrivals_between(s, s + BIN)) for s in range(WARMUP, END, BIN)]
    row: dict[str, Any] = {
        "offered": len(cohort),
        "departed": len(departed),
        "arrived": sum(1 for v in cohort if v.vehicle_id in trips and trips[v.vehicle_id].arrived),
        "departure_ratio": _ratio(len(departed), len(cohort)),
        "steps": steps,
        "mean_network_queue": float(q_net[WARMUP:END].mean()),
        "max_network_queue": float(q_net[WARMUP:END].max()),
        "arrival_bins_300s": bins,
        "min_arrival_bin": min(bins),
        "mean_arrival_bin": float(np.mean(bins)),
        "arrivals_last_1200s": arrivals_between(END - 1200, END),
        "arrivals_last_1800s": arrivals_between(END - 1800, END),
        "offered_last_1200s": sum(1 for v in cohort if v.scheduled_depart >= END - 1200),
        "offered_last_1800s": sum(1 for v in cohort if v.scheduled_depart >= END - 1800),
    }
    row["completion_ratio_departed"] = _ratio(row["arrived"], row["departed"])
    row["never_inserted_fraction"] = 1.0 - row["departure_ratio"]

    side_counts = Counter(_side(v.entry_edge_id) for v in cohort)
    for side in "WENS":
        row[f"offered_share_{side}"] = _ratio(side_counts[side], len(cohort))
    row["min_junction_pass_share"] = float(
        min(metadata["coverage"]["junction_pass_share_by_node"].values())
    )

    final = q_net[END - MEASUREMENT // 5 : END]
    row["s1_projected_change"], row["s1_final_mean_queue"], row["s1_queue_stable"] = _slope_change(
        final
    )
    row["saturated_lane_step_fraction"] = float((queue[WARMUP:END] >= 0.8 * capacity).mean())

    for group in GROUPS:
        members = [v for v in cohort if _group_of(v) == group]
        got = [v for v in members if v.vehicle_id in trips]
        row[f"{group}_offered"] = len(members)
        row[f"{group}_departure_ratio"] = _ratio(len(got), len(members))
        row[f"{group}_mean_insertion_delay"] = (
            float(np.mean([trips[v.vehicle_id].depart_delay for v in got])) if got else 0.0
        )
    late = [
        v
        for v in cohort
        if _group_of(v) == "dominant" and v.scheduled_depart >= END - MEASUREMENT // 5
    ]
    row["dominant_departure_ratio_final20"] = _ratio(
        sum(1 for v in late if v.vehicle_id in trips), len(late)
    )
    row["offered_dominant_share"] = _ratio(row["dominant_offered"], len(cohort))
    row["directional_bias_index"] = _ratio(
        sum(1 for v in departed if _group_of(v) == "dominant"), len(departed)
    )
    moves = Counter(
        dirs.get((a, b), "?")
        for v in cohort
        if _group_of(v) == "dominant"
        for a, b in zip(v.route[:-1], v.route[1:], strict=True)
    )
    row["dominant_left_right_share"] = _ratio(
        sum(moves[d] for d in LEFT_RIGHT), sum(moves.values())
    )

    pre = q_net[SHOCK - 600 : SHOCK]
    post = q_net[SHOCK : SHOCK + 600]
    row["pre_shock_mean_queue"] = float(pre.mean())
    row["post_shock_mean_queue_600s"] = float(post.mean())
    row["shock_queue_ratio"] = _ratio(float(post.mean()), float(pre.mean()))
    row["shock_queue_increase"] = float(post.mean() - pre.mean())
    pre_final = q_net[SHOCK - int(0.2 * (SHOCK - WARMUP)) : SHOCK]
    row["pre_shock_projected_change"], _, row["pre_shock_queue_stable"] = _slope_change(pre_final)
    a5 = queue[:, junction_cols == HOTSPOT].sum(axis=1)
    row["a5_pre_shock_mean_queue"] = float(a5[SHOCK - 600 : SHOCK].mean())
    row["a5_post_shock_mean_queue_600s"] = float(a5[SHOCK : SHOCK + 600].mean())
    row["a5_shock_queue_ratio"] = _ratio(
        row["a5_post_shock_mean_queue_600s"], row["a5_pre_shock_mean_queue"]
    )
    rolling = np.convolve(q_net, np.ones(60) / 60.0, mode="valid")  # índice j: média de j..j+59
    threshold = 1.25 * row["pre_shock_mean_queue"]
    latency = float("inf")
    for j in range(SHOCK, rolling.size):
        if rolling[j] >= threshold:
            latency = float(j + 59 - SHOCK)
            break
    row["shock_latency_seconds"] = latency
    pre_cohort = [v for v in cohort if v.scheduled_depart < SHOCK]
    pre_got = [v for v in pre_cohort if v.vehicle_id in trips]
    row["pre_shock_departure_ratio"] = _ratio(len(pre_got), len(pre_cohort))
    row["pre_shock_mean_insertion_delay"] = (
        float(np.mean([trips[v.vehicle_id].depart_delay for v in pre_got])) if pre_got else 0.0
    )

    per_junction = {
        j: float(queue[WARMUP:END, junction_cols == j].sum(axis=1).mean())
        for j in sorted(set(junction_cols.tolist()))
    }
    row["junction_mean_queue"] = json.dumps(per_junction)
    others = [v for j, v in per_junction.items() if j != HOTSPOT]
    row["a5_mean_queue"] = per_junction[HOTSPOT]
    row["a5_is_max"] = bool(per_junction[HOTSPOT] >= max(others))
    row["a5_over_others"] = _ratio(per_junction[HOTSPOT], float(np.mean(others)))
    a5_cols = junction_cols == HOTSPOT
    row["a5_half_storage_fraction"] = float(
        (queue[WARMUP:END][:, a5_cols] >= 0.5 * capacity[a5_cols]).mean()
    )
    neighbours = float(np.mean([per_junction[j] for j in NEIGHBOURS]))
    corners = float(np.mean([per_junction[j] for j in CORNERS]))
    row["neighbour_mean_queue"] = neighbours
    row["corner_mean_queue"] = corners
    row["neighbour_over_corner"] = _ratio(neighbours, corners)
    row["mean_occupancy"] = float(occupancy[WARMUP:END].mean())
    return row


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    scenario = str(job["scenario"])
    seed = int(job["seed"])
    label = f"{scenario}_{job['value']:g}"
    scenario_dir = OUT_ROOT / "scenarios" / label
    scenario_dir.mkdir(parents=True, exist_ok=True)
    for name in ("network.net.xml", "scenario.yaml", "metadata.json"):
        target = scenario_dir / name
        if not target.exists():
            shutil.copy2(SOURCE_DIR / name, target)
    params = gen.DemandParameters(**job["params"])
    definition = next(d for d in gen.SCENARIOS if d.short == scenario)
    gen.generate(
        scenario_dir,
        seeds=(seed,),
        params=params,
        definitions=(definition,),
        write_base_files=False,
    )
    config_path = scenario_dir / f"{definition.file_stem}_seed_{seed}.yaml"
    summary = TraCISimulationRunner(
        scenario_config=load_scenario_config(config_path),
        scenario_dir=scenario_dir,
        controller_id=CONTROLLER,
        artifacts_dir=OUT_ROOT / "runs" / label,
        run_id=f"{label}_seed_{seed}",
        label=f"calibration_{label}_seed_{seed}",
    ).run()
    run_dir = summary.manifest_path.parent
    (run_dir / "calibration_role.json").write_text(
        json.dumps({"campaign_role": CAMPAIGN_ROLE, "controller": CONTROLLER, "seed": seed}),
        encoding="utf-8",
    )
    raw = analyze_run(run_dir, scenario_dir, f"routes_{scenario}_seed_{seed}.rou.xml")
    return {
        "campaign_role": CAMPAIGN_ROLE,
        "controller": CONTROLLER,
        "scenario": scenario,
        "candidate_value": float(job["value"]),
        "seed": seed,
        "run_dir": run_dir.as_posix(),
        **raw,
    }


def evaluate(row: dict[str, Any], *, s1_rate: float | None) -> dict[str, bool]:
    """Critérios pré-declarados (ver calibration-plan.md)."""

    scenario = row["scenario"]
    c: dict[str, bool] = {}
    if scenario == "s1":
        c["balanced_sides"] = all(abs(row[f"offered_share_{s}"] - 0.25) <= 0.02 for s in "WENS")
        c["nine_junctions_meaningful"] = row["min_junction_pass_share"] >= 0.08
        c["departure_ratio"] = row["departure_ratio"] >= 0.98
        c["completion_ratio_departed"] = row["completion_ratio_departed"] >= 0.95
        c["never_inserted"] = row["never_inserted_fraction"] <= 0.02
        c["queue_stable_final20"] = bool(row["s1_queue_stable"])
        c["no_widespread_saturation"] = row["saturated_lane_step_fraction"] <= 0.02
        c["arrivals_continue"] = row["min_arrival_bin"] >= 0.5 * row["mean_arrival_bin"]
    elif scenario == "s2":
        c["offered_share_080"] = abs(row["offered_dominant_share"] - 0.80) <= 0.02
        c["more_demanding_than_s1"] = s1_rate is not None and row["candidate_value"] > s1_rate
        c["departure_ratio"] = row["departure_ratio"] >= 0.95
        c["dominant_departure"] = row["dominant_departure_ratio"] >= 0.90
        c["residual_departure"] = row["residual_departure_ratio"] >= 0.90
        c["no_permanent_starvation"] = row["dominant_departure_ratio_final20"] >= 0.90
        c["bias_index"] = (
            row["directional_bias_index"] >= 0.75
            and abs(row["directional_bias_index"] - row["offered_dominant_share"]) <= 0.05
        )
        c["turns_present"] = row["dominant_left_right_share"] >= 0.20
        c["dominant_insertion_delay"] = row["dominant_mean_insertion_delay"] <= 60.0
    elif scenario == "s3":
        c["pre_shock_stable"] = bool(row["pre_shock_queue_stable"])
        c["pre_shock_no_backlog"] = (
            row["pre_shock_departure_ratio"] >= 0.98
            and row["pre_shock_mean_insertion_delay"] <= 5.0
        )
        c["shock_visible_network"] = (
            row["shock_queue_ratio"] >= 1.25 and row["shock_queue_increase"] >= 3.0
        )
        c["shock_visible_a5"] = row["a5_shock_queue_ratio"] >= 1.25
        c["bounded_latency"] = row["shock_latency_seconds"] <= 600.0
        c["no_large_backlog"] = row["departure_ratio"] >= 0.95
        c["dynamically_active"] = (
            row["min_arrival_bin"] >= 0.5 * row["mean_arrival_bin"]
            and row["arrivals_last_1200s"] >= 0.5 * row["offered_last_1200s"]
        )
    else:
        c["a5_primary_hotspot"] = bool(row["a5_is_max"]) and row["a5_over_others"] >= 1.5
        c["a5_congested"] = row["a5_half_storage_fraction"] >= 0.05
        c["propagation"] = row["neighbour_over_corner"] >= 1.25
        c["arrivals_every_bin"] = row["min_arrival_bin"] > 0
        c["not_deadlocked"] = row["arrivals_last_1800s"] >= 0.25 * row["offered_last_1800s"]
    return c


def select(rows: list[dict[str, Any]], scenario: str) -> float | None:
    by_value: dict[float, list[bool]] = {}
    for row in rows:
        if row["scenario"] == scenario:
            by_value.setdefault(row["candidate_value"], []).append(bool(row["all_pass"]))
    admissible = [
        value for value, oks in by_value.items() if len(oks) == len(CALIBRATION_SEEDS) and all(oks)
    ]
    return max(admissible) if admissible else None


def _run_stage(pool: ProcessPoolExecutor, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for done in pool.map(run_job, jobs):
        print("done", done["scenario"], done["candidate_value"], done["seed"], flush=True)
        results.append(done)
    return results


def _jobs(scenario: str, grid: tuple[float, ...], s1_rate: float) -> list[dict[str, Any]]:
    return [
        {
            "scenario": scenario,
            "value": value,
            "seed": seed,
            "params": _candidate_params(scenario, value, s1_rate).__dict__,
        }
        for value in grid
        for seed in CALIBRATION_SEEDS
    ]


def _annotate(rows: list[dict[str, Any]], s1_rate: float | None) -> None:
    for row in rows:
        criteria = evaluate(row, s1_rate=s1_rate)
        for name, ok in criteria.items():
            row[f"crit_{name}"] = ok
        row["failed_criteria"] = ",".join(name for name, ok in criteria.items() if not ok)
        row["all_pass"] = all(criteria.values())


def _write_results(rows: list[dict[str, Any]], s1_selected: float | None) -> dict[str, Any]:
    _annotate(rows, s1_selected)
    selected: dict[str, float | None] = {sc: select(rows, sc) for sc in ("s1", "s2", "s3", "s4")}
    keys = sorted({key for row in rows for key in row})
    table = pa.Table.from_pylist([{key: row.get(key) for key in keys} for row in rows])
    pq.write_table(table, OUT_ROOT / "candidate-results.parquet", compression="zstd")
    payload = {"campaign_role": CAMPAIGN_ROLE, "controller": CONTROLLER, "selected": selected}
    (OUT_ROOT / "selected-levels.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def cmd_run(workers: int) -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = _run_stage(
            pool,
            _jobs("s1", S1_GRID, 150.0) + _jobs("s2", S2_GRID, 150.0) + _jobs("s4", S4_GRID, 150.0),
        )
        s1_rows = [r for r in rows if r["scenario"] == "s1"]
        _annotate(s1_rows, None)
        s1_selected = select(s1_rows, "s1")
        print("S1 selected", s1_selected, flush=True)
        if s1_selected is not None:
            rows += _run_stage(pool, _jobs("s3", S3_GRID, s1_selected))
    print(json.dumps(_write_results(rows, s1_selected)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    return cmd_run(args.workers)


if __name__ == "__main__":
    sys.exit(main())
