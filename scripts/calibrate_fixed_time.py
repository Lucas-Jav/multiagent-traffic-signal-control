"""Final fixed-time baseline calibration (Prompt 55.5). Controller: B0 only.

    uv run python scripts/calibrate_fixed_time.py plan       # predeclare + candidates (no sim)
    uv run python scripts/calibrate_fixed_time.py run        # calibration runs (B0 only)
    uv run python scripts/calibrate_fixed_time.py select     # apply the predeclared objective
    uv run python scripts/calibrate_fixed_time.py validate   # untouched validation seeds
    uv run python scripts/calibrate_fixed_time.py finalize   # write the final plan file

Everything that defines the calibration (search space, objective, guards, seeds, tie-break rule) is
declared by the constants below and frozen into ``calibration-plan.json`` by the ``plan`` command,
BEFORE any candidate is simulated. The objective uses only B0 traffic outcomes measured on the
calibration scenarios; no B1/B2/C1/C2 result is read anywhere in this script.
All artifacts carry ``campaign_role: BASELINE_CALIBRATION``; they are not scientific results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import generate_scenarios as gen
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.config import load_scenario_config
from traffic_agents.controllers import (
    FixedTimePlan,
    FixedTimePlanController,
    TrafficLightTiming,
)
from traffic_agents.metrics.sumo_trip_metrics import SumoTripMetricsError
from traffic_agents.simulation import TraCISimulationRunner

CAMPAIGN_ROLE = "BASELINE_CALIBRATION"
OUT_ROOT = Path("artifacts/calibration/fixed_time_b0")
SOURCE_DIR = Path("scenarios/grid_3x3")
FINAL_PLAN_PATH = Path("experiments/fixed_time/b0_fixed_calibrated.json")

# --- Seeds (never Pilot V2 seeds, never the reserved final-analysis pool) -------------------------
CALIBRATION_SEEDS = (101, 1009, 2029)
VALIDATION_SEEDS = (3011, 4021, 5003)
SCENARIOS = ("s1", "s2", "s3", "s4")  # demand levels = the already calibrated gen.CALIBRATED

# --- Search space ---------------------------------------------------------------------------------
YELLOW_SECONDS = 3
ALL_RED_SECONDS = 2
LOST_SECONDS = 4 * (YELLOW_SECONDS + ALL_RED_SECONDS)  # 20 s per cycle
CYCLES = (68, 84, 100, 116, 132)  # (cycle - 20) divisible by 4: equal greens 12/16/20/24/28 s
SPLITS = ("EQUAL", "DEMAND_PROPORTIONAL")
OFFSETS = ("ZERO", "STAGGER", "ALTERNATE")
MIN_GREEN = 10
MAX_GREEN = 60
STAGGER_STEP_SECONDS = 10  # same rule as the historical plan: ((logical index - 1) * 10) mod cycle
REFERENCE_ID = "static98"  # historical B0_FIXED_STATIC, evaluated natively (no override)

# --- Objective (lower is better; the reference plan scores exactly 1.0) ---------------------------
W_COMPLETION = 0.40
W_QUEUE = 0.35
W_TIME_LOSS = 0.25
GUARD_MIN_COMPLETION_REL = 0.95  # per scenario: mean completion_ratio_offered >= 0.95 x reference
GUARD_MIN_DEPARTURE_REL = 0.95  # per scenario: mean departure_ratio >= 0.95 x reference
GUARD_MAX_QUEUE_REL = 1.25  # per scenario: mean network queue <= 1.25 x reference
GUARD_MAX_TIME_LOSS_REL = 1.25  # per scenario: mean time loss <= 1.25 x reference
TIE_TOLERANCE = 0.005  # J within tolerance of the best: higher mean completion, then shorter cycle
VALIDATION_MAX_J_REGRESSION = 1.0  # selected plan must score J <= 1.0 on validation seeds too


def objective_spec() -> dict[str, Any]:
    return {
        "per_run": (
            "J_run = 1 - 0.40*dC + 0.35*dQ + 0.25*dL ; dC=(c-c_ref)/c_ref, dQ=(q-q_ref)/q_ref, "
            "dL=(l-l_ref)/l_ref ; c=completion_ratio_offered, q=mean_network_queue_vehicles, "
            "l=mean_time_loss ; *_ref = same scenario and seed under the historical static plan"
        ),
        "aggregate": "J_plan = mean over the 4 scenarios of the mean over seeds of J_run",
        "weights": {"completion": W_COMPLETION, "queue": W_QUEUE, "time_loss": W_TIME_LOSS},
        "guards_per_scenario_mean": {
            "completion_ratio_offered_min_rel": GUARD_MIN_COMPLETION_REL,
            "departure_ratio_min_rel": GUARD_MIN_DEPARTURE_REL,
            "mean_network_queue_vehicles_max_rel": GUARD_MAX_QUEUE_REL,
            "mean_time_loss_max_rel": GUARD_MAX_TIME_LOSS_REL,
        },
        "selection": "minimum J_plan among candidates that pass every guard in every scenario",
        "tie_break": (
            f"candidates with J within {TIE_TOLERANCE} of the minimum: higher mean "
            "completion_ratio_offered, then shorter cycle, then plan_id"
        ),
        "validation": (
            "selected plan vs reference on untouched validation seeds: J <= "
            f"{VALIDATION_MAX_J_REGRESSION} and all guards pass"
        ),
    }


def predeclaration() -> dict[str, Any]:
    return {
        "campaign_role": CAMPAIGN_ROLE,
        "controller": "B0 only (fixed-time plans, no traffic-responsive behavior)",
        "method": "EMPIRICAL_FIXED_TIME (predeclared grid search; Webster is NOT claimed)",
        "calibration_seeds": list(CALIBRATION_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
        "scenarios": list(SCENARIOS),
        "demand_levels": "gen.CALIBRATED (already fixed by the Pilot V2 scenario calibration)",
        "yellow_seconds": YELLOW_SECONDS,
        "all_red_seconds": ALL_RED_SECONDS,
        "cycles": list(CYCLES),
        "splits": list(SPLITS),
        "offsets": list(OFFSETS),
        "reference": REFERENCE_ID,
        "green_bounds": [MIN_GREEN, MAX_GREEN],
        "objective": objective_spec(),
    }


# --- Plan construction ----------------------------------------------------------------------------
def _network(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def tls_approach_edges(network_path: Path) -> dict[str, list[str]]:
    """Incoming edge of each approach phase (network phase order) of every traffic light."""

    root = _network(network_path)
    edges_by_tls_link: dict[str, dict[int, str]] = defaultdict(dict)
    for connection in root.findall("connection"):
        tls = connection.get("tl")
        if tls is None:
            continue
        edges_by_tls_link[tls][int(connection.get("linkIndex", "-1"))] = connection.get("from", "")
    result: dict[str, list[str]] = {}
    for program in root.findall("tlLogic"):
        tls = program.get("id", "")
        approaches: list[str] = []
        for phase in program.findall("phase"):
            state = phase.get("state", "")
            if "G" not in state:
                continue
            greens = [index for index, signal in enumerate(state) if signal == "G"]
            edges = {edges_by_tls_link[tls][index] for index in greens}
            if len(edges) != 1:
                msg = f"{tls}: a green phase serves {len(edges)} incoming edges"
                raise ValueError(msg)
            approaches.append(next(iter(edges)))
        result[tls] = approaches
    return result


def demand_shares(
    scenarios_root: Path, approach_edges: dict[str, list[str]]
) -> dict[str, list[float]]:
    """Mean approach share per traffic light over S1-S4 and calibration seeds (equal weights)."""

    shares: dict[str, list[list[float]]] = {tls: [] for tls in approach_edges}
    for scenario in SCENARIOS:
        for seed in CALIBRATION_SEEDS:
            root = _network(scenarios_root / scenario / f"routes_{scenario}_seed_{seed}.rou.xml")
            routes = {r.get("id"): (r.get("edges") or "").split() for r in root.findall("route")}
            counts: dict[str, int] = defaultdict(int)
            for vehicle in root.findall("vehicle"):
                depart = float(vehicle.get("depart", "0"))
                if not gen.WARMUP_SECONDS <= depart < gen.TOTAL_SECONDS:
                    continue
                for edge in routes[vehicle.get("route")][:-1]:  # last edge exits the network
                    counts[edge] += 1
            for tls, edges in approach_edges.items():
                flows = [counts[edge] for edge in edges]
                total = sum(flows)
                shares[tls].append([f / total if total else 0.25 for f in flows])
    return {
        tls: [sum(column) / len(rows) for column in zip(*rows, strict=True)]
        for tls, rows in shares.items()
    }


def allocate_greens(shares: list[float], green_total: int) -> list[int]:
    """Webster split rule under equal saturation flows: green proportional to flow share.

    Each approach first gets MIN_GREEN; the rest is shared by largest remainder; the greens are then
    capped at MAX_GREEN. Deterministic.
    """

    n = len(shares)
    free = green_total - n * MIN_GREEN
    total_share = sum(shares) or 1.0
    raw = [free * share / total_share for share in shares]
    base = [int(value) for value in raw]
    order = sorted(range(n), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[: free - sum(base)]:
        base[i] += 1
    greens = [MIN_GREEN + extra for extra in base]
    if any(green > MAX_GREEN for green in greens) or sum(greens) != green_total:
        msg = f"cannot allocate {green_total}s from shares {shares}"
        raise ValueError(msg)
    return greens


def tls_grid_position(tls_id: str) -> tuple[int, int]:
    return "ABC".index(tls_id[0]), int(tls_id[1])  # (column, row) in SUMO naming


def offsets_for(strategy: str, cycle: int, logical_index: dict[str, int]) -> dict[str, int]:
    offsets: dict[str, int] = {}
    for tls, index in logical_index.items():
        if strategy == "ZERO":
            offsets[tls] = 0
        elif strategy == "STAGGER":
            offsets[tls] = ((index - 1) * STAGGER_STEP_SECONDS) % cycle
        else:  # ALTERNATE: checkerboard half-cycle offset
            column, row = tls_grid_position(tls)
            offsets[tls] = ((column + row) % 2) * (cycle // 2)
    return offsets


def build_plan(
    cycle: int,
    split: str,
    offset: str,
    shares: dict[str, list[float]],
    logical_index: dict[str, int],
) -> FixedTimePlan:
    green_total = cycle - LOST_SECONDS
    offsets = offsets_for(offset, cycle, logical_index)
    timings = {}
    for tls in sorted(shares):
        if split == "EQUAL":
            greens = [green_total // 4] * 4
        else:
            greens = allocate_greens(shares[tls], green_total)
        timings[tls] = TrafficLightTiming(tuple(greens), offsets[tls])
    return FixedTimePlan(
        plan_id=f"fx_c{cycle}_{split.lower()}_{offset.lower()}",
        cycle_seconds=cycle,
        traffic_lights=timings,
        provenance={"campaign_role": CAMPAIGN_ROLE, "split": split, "offset": offset},
    )


def candidate_plans(network_path: Path, scenarios_root: Path) -> list[FixedTimePlan]:
    metadata = json.loads((SOURCE_DIR / "metadata.json").read_text(encoding="utf-8"))
    logical_index = {sumo: int(label[1:]) for label, sumo in metadata["traffic_light_ids"].items()}
    shares = demand_shares(scenarios_root, tls_approach_edges(network_path))
    return [
        build_plan(cycle, split, offset, shares, logical_index)
        for cycle in CYCLES
        for split in SPLITS
        for offset in OFFSETS
    ]


# --- Simulation -----------------------------------------------------------------------------------
def _scenario_dir(scenario: str) -> Path:
    return OUT_ROOT / "scenarios" / scenario


def prepare_scenarios(seeds: tuple[int, ...]) -> None:
    for scenario in SCENARIOS:
        scenario_dir = _scenario_dir(scenario)
        scenario_dir.mkdir(parents=True, exist_ok=True)
        for name in ("network.net.xml", "scenario.yaml", "metadata.json"):
            target = scenario_dir / name
            if not target.exists():
                shutil.copy2(SOURCE_DIR / name, target)
        definition = next(d for d in gen.SCENARIOS if d.short == scenario)
        gen.generate(
            scenario_dir,
            seeds=seeds,
            params=gen.CALIBRATED,
            definitions=(definition,),
            write_base_files=False,
        )


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    """Run one job, retrying on SUMO output flush races.

    Under heavy parallel load the runner may parse ``tripinfo.xml`` before SUMO finished writing it
    (``traci.close(wait=False)``). The simulation is deterministic, so a retry reproduces the same
    run; the retry never changes any metric or decision.
    """

    last_error: Exception | None = None
    for _attempt in range(4):
        try:
            return _run_job_once(job)
        except SumoTripMetricsError as error:
            last_error = error
            shutil.rmtree(
                OUT_ROOT
                / "runs"
                / str(job["stage"])
                / str(job["plan_id"])
                / f"{job['plan_id']}_{job['scenario']}_seed_{job['seed']}",
                ignore_errors=True,
            )
    assert last_error is not None
    raise last_error


def _run_job_once(job: dict[str, Any]) -> dict[str, Any]:
    scenario, seed, plan_id = str(job["scenario"]), int(job["seed"]), str(job["plan_id"])
    stage = str(job["stage"])
    scenario_dir = _scenario_dir(scenario)
    definition = next(d for d in gen.SCENARIOS if d.short == scenario)
    config_path = scenario_dir / f"{definition.file_stem}_seed_{seed}.yaml"
    override = None
    controller_id = "B0_FIXED"
    if job["plan"] is not None:
        from traffic_agents.controllers import plan_from_payload  # local import for workers

        override = FixedTimePlanController(plan_from_payload(job["plan"]))
        controller_id = override.controller_id
    summary = TraCISimulationRunner(
        scenario_config=load_scenario_config(config_path),
        scenario_dir=scenario_dir,
        controller_id=controller_id,
        controller_override=override,
        artifacts_dir=OUT_ROOT / "runs" / stage / plan_id,
        run_id=f"{plan_id}_{scenario}_seed_{seed}",
        label=f"fxcal_{stage}_{plan_id}_{scenario}_{seed}",
    ).run()
    assert summary.manifest_path is not None
    run_dir = summary.manifest_path.parent
    (run_dir / "calibration_role.json").write_text(
        json.dumps({"campaign_role": CAMPAIGN_ROLE, "stage": stage, "plan_id": plan_id}),
        encoding="utf-8",
    )
    return _row_from_run_dir(run_dir, stage, plan_id, scenario, seed)


ROW_KEYS = (
    "completion_ratio_offered",
    "departure_ratio",
    "mean_network_queue_vehicles",
    "mean_time_loss",
    "mean_waiting_time",
    "mean_travel_time",
    "throughput",
    "max_network_queue_vehicles",
    "never_inserted_vehicle_count",
    "unfinished_in_network_count",
    "sumo_teleports_total",
)


def _row_from_run_dir(
    run_dir: Path, stage: str, plan_id: str, scenario: str, seed: int
) -> dict[str, Any]:
    metrics = json.loads((run_dir / "run_metrics.json").read_text(encoding="utf-8"))["metrics"]
    return {
        "campaign_role": CAMPAIGN_ROLE,
        "stage": stage,
        "plan_id": plan_id,
        "scenario": scenario,
        "seed": seed,
        "run_dir": run_dir.as_posix(),
        **{key: metrics.get(key) for key in ROW_KEYS},
    }


def scan_finalized_runs(stage: str) -> list[dict[str, Any]]:
    """Rows of runs already finalized on disk (resume after an interrupted session).

    A finished run is deterministic, so it is reused instead of re-simulated; incomplete run
    directories (no finalized metrics) are deleted so that they are simulated again.
    """

    rows: list[dict[str, Any]] = []
    stage_dir = OUT_ROOT / "runs" / stage
    if not stage_dir.exists():
        return rows
    for plan_dir in sorted(p for p in stage_dir.iterdir() if p.is_dir()):
        for run_dir in sorted(p for p in plan_dir.iterdir() if p.is_dir()):
            plan_id = plan_dir.name
            name = run_dir.name.removeprefix(f"{plan_id}_")
            scenario, _, seed_text = name.partition("_seed_")
            manifest_path = run_dir / "manifest.json"
            finalized = (
                manifest_path.exists()
                and (run_dir / "run_metrics.json").exists()
                and json.loads(manifest_path.read_text(encoding="utf-8")).get("metrics_finalized")
                is True
            )
            if not finalized:
                shutil.rmtree(run_dir, ignore_errors=True)
                continue
            rows.append(_row_from_run_dir(run_dir, stage, plan_id, scenario, int(seed_text)))
    return rows


def _jobs(
    stage: str, seeds: tuple[int, ...], plans: list[FixedTimePlan | None]
) -> list[dict[str, Any]]:
    jobs = []
    for plan in plans:
        plan_id = REFERENCE_ID if plan is None else plan.plan_id
        payload = None if plan is None else plan.to_payload()
        for scenario in SCENARIOS:
            for seed in seeds:
                jobs.append(
                    {
                        "stage": stage,
                        "plan_id": plan_id,
                        "plan": payload,
                        "scenario": scenario,
                        "seed": seed,
                    }
                )
    return jobs


def _run(
    stage: str, seeds: tuple[int, ...], plans: list[FixedTimePlan | None], workers: int
) -> None:
    jobs = _jobs(stage, seeds, plans)
    results_path = OUT_ROOT / f"{stage}-results.json"
    rows = scan_finalized_runs(stage)
    done = {(r["plan_id"], r["scenario"], r["seed"]) for r in rows}
    pending = [j for j in jobs if (j["plan_id"], j["scenario"], j["seed"]) not in done]
    print(f"{stage}: {len(jobs)} jobs, {len(pending)} pending", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_job, job) for job in pending]
        for index, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if index % 12 == 0 or index == len(pending):
                results_path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
                print(f"  {index}/{len(pending)} done", flush=True)
    results_path.write_text(json.dumps(rows, indent=1), encoding="utf-8")


# --- Evaluation -----------------------------------------------------------------------------------
def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def evaluate(rows: list[dict[str, Any]], plan_ids: list[str]) -> list[dict[str, Any]]:
    """Apply the predeclared objective. Reference rows are the baseline of every comparison."""

    index = {(r["plan_id"], r["scenario"], r["seed"]): r for r in rows}
    evaluations = []
    for plan_id in plan_ids:
        per_scenario: dict[str, dict[str, float]] = {}
        guards_ok = True
        for scenario in SCENARIOS:
            seeds = sorted({r["seed"] for r in rows if r["plan_id"] == plan_id})
            j_runs, comp, dep, queue, loss = [], [], [], [], []
            comp_ref, dep_ref, queue_ref, loss_ref = [], [], [], []
            for seed in seeds:
                run = index[(plan_id, scenario, seed)]
                ref = index[(REFERENCE_ID, scenario, seed)]
                d_c = (run["completion_ratio_offered"] - ref["completion_ratio_offered"]) / ref[
                    "completion_ratio_offered"
                ]
                d_q = (
                    run["mean_network_queue_vehicles"] - ref["mean_network_queue_vehicles"]
                ) / ref["mean_network_queue_vehicles"]
                d_l = (run["mean_time_loss"] - ref["mean_time_loss"]) / ref["mean_time_loss"]
                j_runs.append(1 - W_COMPLETION * d_c + W_QUEUE * d_q + W_TIME_LOSS * d_l)
                comp.append(run["completion_ratio_offered"])
                comp_ref.append(ref["completion_ratio_offered"])
                dep.append(run["departure_ratio"])
                dep_ref.append(ref["departure_ratio"])
                queue.append(run["mean_network_queue_vehicles"])
                queue_ref.append(ref["mean_network_queue_vehicles"])
                loss.append(run["mean_time_loss"])
                loss_ref.append(ref["mean_time_loss"])
            guard = (
                _mean(comp) >= GUARD_MIN_COMPLETION_REL * _mean(comp_ref)
                and _mean(dep) >= GUARD_MIN_DEPARTURE_REL * _mean(dep_ref)
                and _mean(queue) <= GUARD_MAX_QUEUE_REL * _mean(queue_ref)
                and _mean(loss) <= GUARD_MAX_TIME_LOSS_REL * _mean(loss_ref)
            )
            guards_ok = guards_ok and guard
            per_scenario[scenario] = {
                "J": _mean(j_runs),
                "completion_ratio_offered": _mean(comp),
                "departure_ratio": _mean(dep),
                "mean_network_queue_vehicles": _mean(queue),
                "mean_time_loss": _mean(loss),
                "guard_ok": guard,
            }
        evaluations.append(
            {
                "plan_id": plan_id,
                "J": _mean([per_scenario[s]["J"] for s in SCENARIOS]),
                "mean_completion": _mean(
                    [per_scenario[s]["completion_ratio_offered"] for s in SCENARIOS]
                ),
                "guards_ok": guards_ok,
                "per_scenario": per_scenario,
            }
        )
    return evaluations


def pick(evaluations: list[dict[str, Any]], cycles: dict[str, int]) -> dict[str, Any] | None:
    feasible = [e for e in evaluations if e["guards_ok"] and e["plan_id"] != REFERENCE_ID]
    if not feasible:
        return None
    best_j = min(e["J"] for e in feasible)
    near = [e for e in feasible if e["J"] <= best_j + TIE_TOLERANCE]
    return sorted(near, key=lambda e: (-e["mean_completion"], cycles[e["plan_id"]], e["plan_id"]))[
        0
    ]


# --- Commands -------------------------------------------------------------------------------------
def _load_plans() -> list[FixedTimePlan]:
    from traffic_agents.controllers import plan_from_payload

    payload = json.loads((OUT_ROOT / "candidates.json").read_text(encoding="utf-8"))
    return [plan_from_payload(p) for p in payload["plans"]]


def cmd_plan() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    frozen = OUT_ROOT / "calibration-plan.json"
    if frozen.exists():
        print("calibration-plan.json already frozen; refusing to overwrite")
        return 1
    spec = predeclaration()
    text = json.dumps(spec, indent=2, sort_keys=True)
    frozen.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (OUT_ROOT / "calibration-plan.sha256").write_text(digest + "\n", encoding="utf-8")
    prepare_scenarios(CALIBRATION_SEEDS + VALIDATION_SEEDS)
    plans = candidate_plans(SOURCE_DIR / "network.net.xml", _scenario_dir_root())
    (OUT_ROOT / "candidates.json").write_text(
        json.dumps({"plans": [p.to_payload() for p in plans]}, indent=1), encoding="utf-8"
    )
    print(f"predeclaration sha256={digest}; {len(plans)} candidate plans + reference")
    return 0


def _scenario_dir_root() -> Path:
    return OUT_ROOT / "scenarios"


def cmd_run(workers: int) -> int:
    _run("calibration", CALIBRATION_SEEDS, [None, *_load_plans()], workers)
    return 0


def cmd_select() -> int:
    rows = json.loads((OUT_ROOT / "calibration-results.json").read_text(encoding="utf-8"))
    plans = _load_plans()
    cycles = {p.plan_id: p.cycle_seconds for p in plans} | {REFERENCE_ID: 98}
    evaluations = evaluate(rows, [REFERENCE_ID] + [p.plan_id for p in plans])
    selected = pick(evaluations, cycles)
    table = pa.Table.from_pylist(
        [
            {
                "plan_id": e["plan_id"],
                "cycle_seconds": cycles[e["plan_id"]],
                "J": e["J"],
                "mean_completion": e["mean_completion"],
                "guards_ok": e["guards_ok"],
                **{f"{s}_J": e["per_scenario"][s]["J"] for s in SCENARIOS},
            }
            for e in evaluations
        ]
    )
    pq.write_table(table, OUT_ROOT / "calibration-candidates.parquet", compression="zstd")
    payload = {
        "campaign_role": CAMPAIGN_ROLE,
        "selected_plan_id": None if selected is None else selected["plan_id"],
        "evaluations": sorted(evaluations, key=lambda e: e["J"]),
    }
    (OUT_ROOT / "selection.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for e in payload["evaluations"][:10]:
        print(
            f"{e['plan_id']:36s} J={e['J']:.4f} guards={e['guards_ok']} "
            f"C={e['mean_completion']:.4f}"
        )
    print("selected:", payload["selected_plan_id"])
    return 0


def cmd_validate(workers: int) -> int:
    selection = json.loads((OUT_ROOT / "selection.json").read_text(encoding="utf-8"))
    selected_id = selection["selected_plan_id"]
    plans = {p.plan_id: p for p in _load_plans()}
    _run("validation", VALIDATION_SEEDS, [None, plans[selected_id]], workers)
    rows = json.loads((OUT_ROOT / "validation-results.json").read_text(encoding="utf-8"))
    evaluation = evaluate(rows, [REFERENCE_ID, selected_id])[1]
    passed = evaluation["guards_ok"] and evaluation["J"] <= VALIDATION_MAX_J_REGRESSION
    payload = {
        "campaign_role": CAMPAIGN_ROLE,
        "selected_plan_id": selected_id,
        "passed": passed,
        **evaluation,
    }
    (OUT_ROOT / "validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"validation {selected_id}: J={evaluation['J']:.4f} "
        f"guards={evaluation['guards_ok']} pass={passed}"
    )
    return 0 if passed else 2


def cmd_finalize() -> int:
    validation = json.loads((OUT_ROOT / "validation.json").read_text(encoding="utf-8"))
    if not validation["passed"]:
        print("validation did not pass; refusing to write the final plan")
        return 2
    plans = {p.plan_id: p for p in _load_plans()}
    plan = plans[validation["selected_plan_id"]]
    final = FixedTimePlan(
        plan_id=plan.plan_id,
        cycle_seconds=plan.cycle_seconds,
        traffic_lights=plan.traffic_lights,
        method="EMPIRICAL_FIXED_TIME",
        provenance={
            "campaign_role": CAMPAIGN_ROLE,
            "calibration_plan_sha256": (OUT_ROOT / "calibration-plan.sha256").read_text().strip(),
            "calibration_seeds": list(CALIBRATION_SEEDS),
            "validation_seeds": list(VALIDATION_SEEDS),
            "J_calibration": next(
                e["J"]
                for e in json.loads((OUT_ROOT / "selection.json").read_text())["evaluations"]
                if e["plan_id"] == plan.plan_id
            ),
            "J_validation": validation["J"],
        },
    )
    FINAL_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINAL_PLAN_PATH.write_text(json.dumps(final.to_payload(), indent=2) + "\n", encoding="utf-8")
    print("wrote", FINAL_PLAN_PATH, final.plan_id, final.sha256())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("select")
    sub.add_parser("finalize")
    for name in ("run", "validate"):
        sub.add_parser(name).add_argument("--workers", type=int, default=10)
    args = parser.parse_args(argv)
    if args.cmd == "plan":
        return cmd_plan()
    if args.cmd == "run":
        return cmd_run(args.workers)
    if args.cmd == "select":
        return cmd_select()
    if args.cmd == "validate":
        return cmd_validate(args.workers)
    return cmd_finalize()


if __name__ == "__main__":
    sys.exit(main())
