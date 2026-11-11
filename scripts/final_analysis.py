"""Análise final definitiva de FINAL_MAIN (200 execuções) + FINAL_S5 (90 execuções). Nenhuma simulação é executada.

Somente leitura sobre todo artefato bruto. Reutiliza a estatística congelada (analysis/statistics.py:
bootstrap por percentil de diferenças pareadas, 10 000 reamostragens, seed de RNG 20260910; rota de
referência: traffic_agents.experiments.reference_route). Grava apenas em artifacts/final-analysis/ e
docs/evidencias/final-analysis/.

    python scripts/final_analysis.py

Segurança de caminhos longos: alguns diretórios de execução S5 C2 atingem o limite de 260 caracteres
do Windows. Todo arquivo bruto é aberto pelo prefixo de caminho estendido (``\\\\?\\``); nada é
renomeado, movido ou reescrito.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from analysis import statistics as fstats  # noqa: E402
from traffic_agents.experiments import reference_route as rr  # noqa: E402
from traffic_agents.metrics.run_metrics import (  # noqa: E402
    load_offered_vehicles,
    parse_tripinfo_records,
)

SRC_SHA = "176178e36eeafb329a5a1350161be61cf97902b0"
TREE = "b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff"
MANIFEST_SHA = "de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec"

MAIN_DIR = REPO / "artifacts/experiments/final_main"
S5_DIR = REPO / "artifacts/experiments/final_s5_packet_loss"
PILOT_PARQUET = REPO / "artifacts/experiments/pilot_v2/combined_metrics.parquet"
OUT = REPO / "artifacts/final-analysis"
EVID = REPO / "docs/evidencias/final-analysis"

SCENARIOS = ["S1_BALANCED", "S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"]
CONTROLLERS = [
    "B0_FIXED_CALIBRATED", "B1_LOCAL_ADAPTIVE", "B2_LOCAL_PRESSURE",
    "C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED",
]
B0, B1, B2, C1, C2 = CONTROLLERS
SEEDS = [42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001]
PILOT_SEEDS = SEEDS[:5]
LOSSES = [0.0, 0.2, 0.5, 1.0]
S5_SCENARIO = "S2_DIRECTIONAL_PEAK"
BOOT_SEED = fstats.DEFAULT_BOOTSTRAP_SEED
BOOT_N = fstats.DEFAULT_BOOTSTRAP_RESAMPLES

HIGHER_BETTER = {
    "throughput", "departure_ratio", "completion_ratio_offered", "completion_ratio_departed",
    "arrived_vehicle_count", "departed_vehicle_count", "completed_trip_count",
}
NEUTRAL = {"offered_vehicle_count", "messages_sent", "bytes_sent", "bytes_delivered",
           "messages_delivered", "messages_dropped", "messages_stale"}
CORE = [
    "throughput", "departure_ratio", "completion_ratio_offered", "completion_ratio_departed",
    "mean_depart_delay_seconds", "mean_waiting_time", "mean_time_loss", "mean_travel_time",
    "mean_stops", "mean_network_queue_vehicles", "max_network_queue_vehicles",
    "sumo_teleports_total",
]
CONTEXT = [
    "offered_vehicle_count", "departed_vehicle_count", "arrived_vehicle_count",
    "never_inserted_vehicle_count", "unfinished_in_network_count", "max_lane_queue_vehicles",
    "mean_lane_queue_vehicles", "controller_decision_mean_ms", "controller_decision_p95_ms",
]
S3_EXTRA = [
    "post_shock_queue_auc_vehicle_seconds", "post_shock_mean_network_queue_vehicles",
    "post_shock_max_network_queue_vehicles", "post_shock_time_loss", "post_shock_completed_trip_count",
    "pre_shock_mean_network_queue_vehicles", "pre_shock_max_network_queue_vehicles",
    "pre_shock_time_loss",
]
COMM = [
    "messages_sent", "messages_delivered", "messages_dropped", "messages_stale",
    "bytes_sent", "bytes_delivered", "mean_message_age_steps", "max_message_age_steps",
]
MAIN_METRICS = CORE + CONTEXT + S3_EXTRA
S5_METRICS = CORE + CONTEXT + COMM
CONDITIONAL = ("mean_waiting_time", "mean_time_loss", "mean_travel_time")
# Classificação de cenário/par (declarada no prompt da análise antes de qualquer resultado ser inspecionado):
# grupo de serviço e grupo de atraso; mean_travel_time fica fora da votação por ser condicional.
SERVICE_KEYS = ("throughput", "completion_ratio_offered", "departure_ratio")
DELAY_KEYS = ("mean_waiting_time", "mean_time_loss", "mean_network_queue_vehicles")
KEY_METRICS = SERVICE_KEYS + DELAY_KEYS


def direction(metric: str) -> str:
    if metric in NEUTRAL:
        return "neutral"
    return "higher_better" if metric in HIGHER_BETTER else "lower_better"


def xp(path: Path | str) -> Path:
    """Caminho estendido (acesso somente leitura a caminhos do Windows com mais de 260 caracteres)."""

    return Path(chr(92) * 2 + "?" + chr(92) + str(Path(path).resolve()))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------------------------------------
# 1. Carregar execuções (apenas a última tentativa CONCLUÍDA por run_key)
# ---------------------------------------------------------------------------------------------
def load_runs(exp_dir: Path, experiment: str) -> list[dict[str, Any]]:
    log = [json.loads(x) for x in (exp_dir / "run_status.jsonl").read_text().splitlines()]
    by_key: dict[str, list[dict]] = defaultdict(list)
    for rec in log:
        by_key[rec["run_key"]].append(rec)
    runs = []
    for key, recs in by_key.items():
        last = recs[-1]
        if last["status"] != "COMPLETED":
            raise RuntimeError(f"{experiment}: {key} not COMPLETED ({last['status']})")
        d = REPO / last["artifact_path"]
        manifest = json.loads(xp(d / "manifest.json").read_text(encoding="utf-8"))
        rmj = json.loads(xp(d / "run_metrics.json").read_text(encoding="utf-8"))
        runs.append({
            "experiment": experiment,
            "run_key": key,
            "config_run_id": last.get("config_run_id"),
            "run_id": manifest["run_id"],
            "dir": d,
            "run_path": last["artifact_path"],
            "attempts": sum(1 for r in recs if r["status"] in ("COMPLETED", "FAILED")),
            "failed_attempt_paths": [r["artifact_path"] for r in recs if r["status"] == "FAILED"],
            "manifest": manifest,
            "metrics": rmj["metrics"],
            "windows": rmj["windows"],
            "controller": manifest["controller"]["controller_id"],
            "scenario": manifest["demand_profile"],
            "seed": int(manifest["seed"]),
            "loss": float(manifest["communication"]["drop_probability"]),
            "delay": int(manifest["communication"]["delay_steps"]),
            "comm": manifest.get("communication_metrics") or {},
            "metrics_finalized": manifest.get("metrics_finalized") is True,
            "rm_status": rmj.get("status"),
        })
    return runs


def readable(run: dict[str, Any]) -> dict[str, Any]:
    d = run["dir"]
    out: dict[str, Any] = {"run_id": run["run_id"]}
    longest = len(str(d.resolve())) + 1 + len("junction_telemetry.parquet")
    out["abs_path_len"] = longest
    out["needs_extended_path"] = longest >= 260
    ok = True
    for f in ("manifest.json", "run_metrics.json", "sumo/tripinfo.xml", "sumo/statistics.xml",
              "performance.json", "sumo_traffic_metrics.json"):
        try:
            ok &= xp(d / f).read_bytes()[:1] != b"" or (d / f).stat().st_size == 0
        except OSError:
            ok = False
    for f in ("lane_telemetry.parquet", "junction_telemetry.parquet"):
        try:
            ok &= pq.ParquetFile(str(xp(d / f))).metadata.num_rows > 0
        except Exception:  # noqa: BLE001
            ok = False
    out["readable"] = bool(ok)
    return out


# ---------------------------------------------------------------------------------------------
# 2. Construção de registros
# ---------------------------------------------------------------------------------------------
def make_rows(runs: list[dict], metrics: list[str], label_fn, scenario_fn) -> list[dict[str, Any]]:
    rows = []
    for r in runs:
        m = r["manifest"]
        for metric in metrics:
            v = r["metrics"].get(metric)
            if v is None:
                v = r["comm"].get(metric) if metric in COMM else None
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                continue
            rows.append({
                "_row_index": len(rows), "controller": label_fn(r), "scenario": scenario_fn(r), "metric": metric,
                "value": float(v), "seed": r["seed"], "demand": m["demand_profile"],
                "route_hash": m["route_sha256"], "network_hash": m["network_sha256"],
                "phase_plan": m["phase_plan_sha256"],
                "phase_plan_version": m["phase_plan_version"],
                "movement_model_version": m["movement_model_version"],
                "turning_ratios": fstats._canonical_turning_ratios(m["turning_ratios"]),
                "communication_topology_hash": m["communication_topology_sha256"],
                "run_id": r["run_id"], "status": "COMPLETED", "success": True,
            })
    return rows


def effect_label(row: dict[str, Any], metric: str) -> str:
    lo, hi = row["ci95_low"], row["ci95_high"]
    excl = lo > 0 or hi < 0
    d = direction(metric)
    if not excl:
        return "NO_CLEAR_DIFFERENCE"
    if d == "neutral":
        return "DIFFERENT"
    inc = lo > 0
    better = inc if d == "higher_better" else not inc
    return "TREATMENT_BETTER" if better else "BASELINE_BETTER"


def flat(cmp: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    pd = cmp["paired_differences"]
    a = [p["controller_a_value"] for p in pd]
    b = [p["controller_b_value"] for p in pd]
    diffs = [p["difference"] for p in pd]
    am = statistics.fmean(a)
    d = direction(cmp["metric"])
    fav = sum(1 for x in diffs if (x > 0 if d == "higher_better" else x < 0)) if d != "neutral" else None
    unf = sum(1 for x in diffs if (x < 0 if d == "higher_better" else x > 0)) if d != "neutral" else None
    row = {
        "scenario": cmp["scenario"], "baseline": cmp["controller_a"], "treatment": cmp["controller_b"],
        "metric": cmp["metric"], "direction": d, "n_pairs": cmp["n_pairs"],
        "baseline_mean": am, "treatment_mean": statistics.fmean(b),
        "baseline_median": statistics.median(a), "treatment_median": statistics.median(b),
        "mean_difference": cmp["mean_difference"], "median_difference": cmp["median_difference"],
        "relative_difference_of_means": (cmp["mean_difference"] / am) if am else None,
        "relative_difference_mean_of_pairs": cmp["relative_difference"],
        "ci95_low": cmp["ci95_low"], "ci95_high": cmp["ci95_high"],
        "ci95_relative_low": (cmp["ci95_low"] / am) if am else None,
        "ci95_relative_high": (cmp["ci95_high"] / am) if am else None,
        "seeds_treatment_favourable": fav, "seeds_treatment_unfavourable": unf,
        "bootstrap_seed": cmp["bootstrap_seed"], "bootstrap_resamples": cmp["bootstrap_resamples"],
        "paired_seeds": json.dumps([p["seed"] for p in pd]),
        "paired_differences": json.dumps([p["difference"] for p in pd]),
    }
    row["effect"] = effect_label(row, cmp["metric"])
    if extra:
        row.update(extra)
    return row


def scenario_classification(rows: list[dict[str, Any]], base: str, treat: str) -> dict[str, Any]:
    by = {r["metric"]: r for r in rows}
    fav = [m for m in KEY_METRICS if m in by and by[m]["effect"] == "TREATMENT_BETTER"]
    unf = [m for m in KEY_METRICS if m in by and by[m]["effect"] == "BASELINE_BETTER"]
    if fav and unf:
        label = "TRADE_OFF"
    elif fav:
        label = f"{treat}_BETTER"
    elif unf:
        label = f"{base}_BETTER"
    else:
        label = "NO_CLEAR_DIFFERENCE"
    return {"classification": label, "treatment_favourable_key_metrics": fav,
            "baseline_favourable_key_metrics": unf}


def add_conditional_context(rows: list[dict[str, Any]]) -> None:
    idx = {(r["scenario"], r["baseline"], r["treatment"], r["metric"]): r for r in rows}
    for r in rows:
        if r["metric"] in CONDITIONAL:
            k = (r["scenario"], r["baseline"], r["treatment"])
            comp = idx.get((*k, "completion_ratio_offered"))
            unf = idx.get((*k, "unfinished_in_network_count"))
            ni = idx.get((*k, "never_inserted_vehicle_count"))
            r["conditional_metric"] = True
            r["ctx_completion_offered_mean_diff"] = comp["mean_difference"] if comp else None
            r["ctx_completion_offered_effect"] = comp["effect"] if comp else None
            r["ctx_unfinished_mean_diff"] = unf["mean_difference"] if unf else None
            r["ctx_never_inserted_mean_diff"] = ni["mean_difference"] if ni else None
            r["conditional_warning"] = bool(comp and comp["effect"] == "BASELINE_BETTER")
        else:
            r["conditional_metric"] = False


def write_csv(path: Path, rows: list[dict[str, Any]], drop: tuple[str, ...] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols and k not in drop:
                cols.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def pair_cmp(rows: list[dict], scenario: str, metric: str, a: str, b: str) -> dict[str, Any]:
    sel = [r for r in rows if r["scenario"] == scenario and r["metric"] == metric]
    return fstats._compare_controller_pair(
        sel, scenario=scenario, metric=metric, controller_a=a, controller_b=b,
        bootstrap_seed=BOOT_SEED, bootstrap_resamples=BOOT_N,
    )


# ---------------------------------------------------------------------------------------------
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []

    # ---- verificações prévias ----
    status = git("status", "--short")
    ver = subprocess.run([str(REPO / ".venv/Scripts/python.exe"), "scripts/build_final_freeze.py", "--verify",
                          "--scientific-source-sha", SRC_SHA], cwd=REPO, capture_output=True, text=True)
    chk = subprocess.run([str(REPO / ".venv/Scripts/python.exe"), "scripts/build_final_freeze.py", "--check",
                          "--scientific-source-sha", SRC_SHA], cwd=REPO, capture_output=True, text=True)
    tree_now = [x.split("=")[1] for x in chk.stdout.splitlines() if x.startswith("scientific_tree_sha256=")]
    msha = sha256_file(REPO / "docs/evidencias/final-freeze/final-freeze-manifest.json")
    fm = json.loads((REPO / "artifacts/final-main/final-main-validation.json").read_text())
    s5v = json.loads((REPO / "artifacts/final-s5/s5-validation.json").read_text())
    preflight = {
        "git_status_short_before_outputs": status, "freeze_verify_rc": ver.returncode,
        "scientific_tree_now": tree_now, "freeze_manifest_sha256_now": msha,
        "FINAL_MAIN_VALID": fm["FINAL_MAIN_VALID"], "S5_VALID": s5v["S5_VALID"],
    }
    if (ver.returncode != 0 or tree_now != [TREE] or msha != MANIFEST_SHA
            or fm["FINAL_MAIN_VALID"] != "YES" or s5v["S5_VALID"] != "YES"):
        print(json.dumps(preflight, indent=2))
        raise SystemExit("PRE-FLIGHT FAILED")

    # ---- carga ----
    main_runs = load_runs(MAIN_DIR, "FINAL_MAIN")
    s5_runs = load_runs(S5_DIR, "FINAL_S5")
    all_runs = main_runs + s5_runs
    read = [readable(r) for r in all_runs]
    long_path_runs = [x for x in read if x["needs_extended_path"]]
    long_readable = all(x["readable"] for x in read)

    # ---- validação da população ----
    id_main = Counter((r["scenario"], r["controller"], r["seed"]) for r in main_runs)
    id_s5 = Counter((r["controller"], r["seed"], r["loss"]) for r in s5_runs)
    dup_main = [k for k, v in id_main.items() if v > 1]
    dup_s5 = [k for k, v in id_s5.items() if v > 1]
    exp_main = {(s, c, e) for s in SCENARIOS for c in CONTROLLERS for e in SEEDS}
    exp_s5 = {(c, e, p) for c in (C1, C2) for e in SEEDS for p in LOSSES} | {(B2, e, 0.0) for e in SEEDS}
    if set(id_main) != exp_main:
        problems.append("FINAL_MAIN identity set differs from plan")
    if set(id_s5) != exp_s5:
        problems.append("FINAL_S5 identity set differs from plan")
    for r in all_runs:
        if not r["metrics_finalized"] or r["rm_status"] != "COMPLETED":
            problems.append(f"run not finalized/completed: {r['run_id']}")
        if r["experiment"] == "FINAL_MAIN" and r["controller"] in ("B0_FIXED", "B0_FIXED_STATIC", "B0_FIXED_STATIC_V2"):
            problems.append("historical B0 present")
    final_ids = {r["run_id"] for r in all_runs}
    pilot_ids = set(pq.read_table(PILOT_PARQUET, columns=["run_id"]).column("run_id").to_pylist())
    pilot_overlap = sorted(final_ids & pilot_ids)
    if pilot_overlap:
        problems.append("pilot run ids inside final population")
    exps = Counter(r["manifest"].get("experiment_config_sha256") for r in all_runs)
    retried = [r for r in s5_runs if r["attempts"] > 1]
    retried_ok = [r for r in retried if r["controller"] == C2 and r["seed"] in (10007, 12011, 16001)
                  and all(fp != r["run_path"] for fp in r["failed_attempt_paths"])]
    retried_unique = len({(r["controller"], r["seed"], r["loss"]) for r in retried})
    main_retried = [r for r in main_runs if r["attempts"] > 1]

    # ---- final_metrics (formato longo, rastreável) ----
    prov = {"scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": MANIFEST_SHA}
    fm_rows = []
    for r in all_runs:
        m = r["manifest"]
        mets = MAIN_METRICS if r["experiment"] == "FINAL_MAIN" else S5_METRICS
        for metric in mets:
            v = r["metrics"].get(metric)
            if v is None and metric in COMM:
                v = r["comm"].get(metric)
            if v is None:
                continue
            fm_rows.append({
                "experiment": r["experiment"], "scenario": r["scenario"], "controller": r["controller"],
                "seed": r["seed"], "packet_loss": r["loss"], "delay_steps": r["delay"],
                "condition": ("B2_REFERENCE" if (r["experiment"] == "FINAL_S5" and r["controller"] == B2)
                              else (f"LOSS_{int(round(r['loss'] * 100))}" if r["experiment"] == "FINAL_S5" else "MAIN")),
                "metric": metric, "value": float(v), "direction": direction(metric),
                "run_id": r["run_id"], "run_path": r["run_path"], "config_run_id": r["config_run_id"],
                "attempts": r["attempts"], "scenario_sha256": m["scenario_sha256"],
                "route_sha256": m["route_sha256"], "network_sha256": m["network_sha256"], **prov,
            })
    write_parquet(OUT / "final_metrics.parquet", fm_rows)

    # checagem cruzada contra o agregado congelado (combined_metrics.parquet gravado pelo executor)
    cm = pq.read_table(MAIN_DIR / "combined_metrics.parquet").to_pylist()
    cm_idx = {(x["run_id"], x["metric"]): x["value"] for x in cm}
    cm_mismatch = 0
    cm_checked = 0
    for x in fm_rows:
        if x["experiment"] == "FINAL_MAIN" and (x["run_id"], x["metric"]) in cm_idx:
            cm_checked += 1
            if abs(cm_idx[(x["run_id"], x["metric"])] - x["value"]) > 1e-9:
                cm_mismatch += 1

    # ---------------------------------------------------------------------------------------
    # MAIN descritivo + pareado
    # ---------------------------------------------------------------------------------------
    main_rows = make_rows(main_runs, MAIN_METRICS, lambda r: r["controller"], lambda r: r["scenario"])
    desc = fstats._descriptive_statistics(main_rows)
    for d in desc:
        d["N"] = d.pop("count")
    write_csv(OUT / "final_controller_summary.csv", desc)

    outliers = fstats._outlier_records(main_rows)
    write_csv(OUT / "final_outliers_flagged_not_removed.csv",
              [{k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in o.items()} for o in outliers])

    comparisons = []
    for scenario in SCENARIOS:
        for metric in MAIN_METRICS:
            present = {r["controller"] for r in main_rows if r["scenario"] == scenario and r["metric"] == metric}
            for a, b in fstats.DEFAULT_CONTROLLER_PAIRS:
                if a in present and b in present:
                    comparisons.append(pair_cmp(main_rows, scenario, metric, a, b))
    supp = []
    for scenario in SCENARIOS:
        for metric in KEY_METRICS + ("mean_travel_time", "max_network_queue_vehicles", "mean_stops",
                                     "never_inserted_vehicle_count", "unfinished_in_network_count",
                                     "sumo_teleports_total"):
            for a, b in ((B0, C1), (B0, C2)):
                supp.append(flat(pair_cmp(main_rows, scenario, metric, a, b),
                                 {"status": "EXPLORATORY_NOT_IN_FROZEN_COMPARISON_LIST"}))
    write_csv(OUT / "supplementary_B0_vs_cooperative_exploratory.csv", supp, drop=("paired_differences",))
    fstats._write_pairwise_parquet(OUT / "final_pairwise_analysis.parquet", comparisons)
    pw = [flat(c) for c in comparisons]
    add_conditional_context(pw)
    classes = []
    for scenario in SCENARIOS:
        for a, b in fstats.DEFAULT_CONTROLLER_PAIRS:
            sub = [r for r in pw if r["scenario"] == scenario and r["baseline"] == a and r["treatment"] == b]
            cl = scenario_classification(sub, a, b)
            classes.append({"scenario": scenario, "baseline": a, "treatment": b, **cl})
            for r in sub:
                r["scenario_pair_classification"] = cl["classification"]
    write_csv(OUT / "final_pairwise_summary.csv", pw, drop=("paired_differences",))
    write_csv(OUT / "final_scenario_pair_classification.csv",
              [{**c, "treatment_favourable_key_metrics": ";".join(c["treatment_favourable_key_metrics"]),
                "baseline_favourable_key_metrics": ";".join(c["baseline_favourable_key_metrics"])} for c in classes])

    # teletransportes do S4
    tele_rows = []
    for r in main_runs:
        if r["scenario"] == "S4_LOCAL_SATURATION":
            tele_rows.append({"controller": r["controller"], "seed": r["seed"],
                              "sumo_teleports_total": r["metrics"].get("sumo_teleports_total"),
                              "run_id": r["run_id"]})
    write_csv(OUT / "s4_teleports_by_run.csv", tele_rows)
    tele_summary = {}
    for c in CONTROLLERS:
        vals = [t["sumo_teleports_total"] for t in tele_rows if t["controller"] == c]
        tele_summary[c] = {"runs": len(vals), "runs_with_teleports": sum(1 for v in vals if v and v > 0),
                           "total": sum(vals), "max": max(vals),
                           "seeds_with_teleports": [t["seed"] for t in tele_rows
                                                    if t["controller"] == c and t["sumo_teleports_total"] > 0]}
    tele_any_other = {s: sum(r["metrics"].get("sumo_teleports_total", 0) or 0 for r in main_runs if r["scenario"] == s)
                      for s in SCENARIOS}

    # ---------------------------------------------------------------------------------------
    # Rota de referência (seleção de coorte congelada + estatística pareada congelada), N=10
    # ---------------------------------------------------------------------------------------
    rr_rows = []
    rr_vals: dict[tuple[str, str], dict[str, dict[int, float | None]]] = defaultdict(lambda: defaultdict(dict))
    rr_counts: dict[tuple[str, str, int], dict[str, int]] = {}
    route_hash_ok = 0
    for r in main_runs:
        if r["controller"] not in rr.CONTROLLERS:
            continue
        m = r["manifest"]
        tag = r["scenario"].split("_")[0].lower()
        route = REPO / "scenarios/grid_3x3" / f"routes_{tag}_seed_{r['seed']}.rou.xml"
        if sha256_file(route) == m["route_sha256"]:
            route_hash_ok += 1
        else:
            from traffic_agents.experiments.text_hashing import canonical_sha256
            if canonical_sha256(route.read_bytes()) == m["route_sha256"]:
                route_hash_ok += 1
        cohort = rr.select_reference_cohort(
            load_offered_vehicles(route), warmup_seconds=float(m["warmup_seconds"]),
            measurement_duration_seconds=float(m["measurement"]["measurement_duration_seconds"]))
        rows = rr.build_vehicle_rows(cohort, parse_tripinfo_records(xp(r["dir"] / "sumo/tripinfo.xml")))
        counts = rr.population_counts(rows)
        mets = rr.run_metrics(rows)
        rr_counts[(r["scenario"], r["controller"], r["seed"])] = counts
        for k, v in {**counts, **mets}.items():
            rr_rows.append({"scenario": r["scenario"], "controller": r["controller"], "seed": r["seed"],
                            "metric": k, "value": v, "run_id": r["run_id"], "run_path": r["run_path"],
                            "route_edges": "|".join(rr.REFERENCE_ROUTE_EDGES), **prov})
            if k in mets:
                rr_vals[(r["scenario"], k)][r["controller"]][r["seed"]] = v
    write_parquet(OUT / "reference_route_results.parquet", rr_rows)
    rr_pw = []
    for scenario in SCENARIOS:
        for metric in rr.METRICS:
            vbc = rr_vals[(scenario, metric)]
            for base, treat in rr.COMPARISONS:
                row = rr.pairwise_comparison(scenario=scenario, baseline=base, treatment=treat,
                                             metric=metric, values_by_controller=vbc, seeds=SEEDS)
                rr_pw.append(row)
    # flag de interpretação (`interpret` congelado)
    idx_rr = {(r["scenario"], r["baseline"], r["treatment"], r["metric"]): r for r in rr_pw}
    for r in rr_pw:
        r["interpretation"] = (rr.interpret(
            idx_rr[(r["scenario"], r["baseline"], r["treatment"], rr.PRIMARY_METRIC)],
            idx_rr[(r["scenario"], r["baseline"], r["treatment"], rr.COMPLETION_METRIC)])
            if r["metric"] == rr.PRIMARY_METRIC else "")
    write_csv(OUT / "reference_route_pairwise.csv", rr_pw,
              drop=("baseline_per_seed", "treatment_per_seed", "paired_diff_per_seed"))
    rr_cohort_summary = []
    for scenario in SCENARIOS:
        for c in rr.CONTROLLERS:
            cs = [rr_counts[(scenario, c, e)] for e in SEEDS]
            rr_cohort_summary.append({
                "scenario": scenario, "controller": c, "N": len(cs),
                **{f"mean_{k}": statistics.fmean(x[k] for x in cs) for k in rr.POPULATION_KEYS},
                **{f"{k}_per_seed": json.dumps([x[k] for x in cs]) for k in ("reference_route_offered",)},
            })
    write_csv(OUT / "reference_route_cohort_summary.csv", rr_cohort_summary)
    # descritivo da rota de referência por cenário/controlador/métrica
    rr_desc = []
    for scenario in SCENARIOS:
        for metric in rr.METRICS:
            for c in rr.CONTROLLERS:
                vals = [v for v in (rr_vals[(scenario, metric)][c].get(e) for e in SEEDS) if v is not None]
                if vals:
                    sv = sorted(vals)
                    q1, q3 = fstats._quantile(sv, 0.25), fstats._quantile(sv, 0.75)
                    rr_desc.append({"scenario": scenario, "controller": c, "metric": metric, "N": len(vals),
                                    "mean": statistics.fmean(vals), "median": statistics.median(vals),
                                    "std": statistics.stdev(vals) if len(vals) > 1 else None,
                                    "iqr": q3 - q1, "min": sv[0], "max": sv[-1]})
    write_csv(OUT / "reference_route_summary.csv", rr_desc)

    # tabela de direção rede-vs-rota (B0->B2 e B2->C1)
    net_vs_route = []
    for scenario in SCENARIOS:
        for base, treat in ((B0, B2), (B2, C1)):
            def g(metric):
                return next(r for r in pw if r["scenario"] == scenario and r["baseline"] == base
                            and r["treatment"] == treat and r["metric"] == metric)
            rrow = idx_rr[(scenario, base, treat, "reference_route_mean_travel_time_seconds")]
            n_tt = g("mean_travel_time")
            net_vs_route.append({
                "scenario": scenario, "comparison": f"{base}->{treat}",
                "network_mean_travel_time_diff": n_tt["mean_difference"],
                "network_mean_travel_time_ci": f"[{n_tt['ci95_low']:.2f},{n_tt['ci95_high']:.2f}]",
                "route_mean_travel_time_diff": rrow["paired_mean_diff"],
                "route_mean_travel_time_ci": f"[{rrow['ci95_low']:.2f},{rrow['ci95_high']:.2f}]",
                "network_queue_diff": g("mean_network_queue_vehicles")["mean_difference"],
                "network_completion_diff": g("completion_ratio_offered")["mean_difference"],
                "route_completion_diff": idx_rr[(scenario, base, treat, rr.COMPLETION_METRIC)]["paired_mean_diff"],
            })
    write_csv(OUT / "network_vs_reference_route_direction.csv", net_vs_route)

    # ---------------------------------------------------------------------------------------
    # S5
    # ---------------------------------------------------------------------------------------
    def s5_label(r):
        return f"{r['controller']}@REF" if r["controller"] == B2 else f"{r['controller']}@{r['loss']:.2f}"

    s5_rows = make_rows(s5_runs, S5_METRICS, s5_label, lambda r: "S5_" + S5_SCENARIO)
    write_parquet(OUT / "s5_results.parquet", [x for x in fm_rows if x["experiment"] == "FINAL_S5"])
    s5_desc = fstats._descriptive_statistics(s5_rows)
    for d in s5_desc:
        d["N"] = d.pop("count")
    write_csv(OUT / "s5_controller_summary.csv", s5_desc)
    scen5 = "S5_" + S5_SCENARIO

    def s5_pairs():
        for ctrl in (C1, C2):
            for p in LOSSES[1:]:
                yield "DEGRADATION_VS_0", f"{ctrl}@0.00", f"{ctrl}@{p:.2f}"
            for p in LOSSES:
                yield "VS_B2_REFERENCE", f"{B2}@REF", f"{ctrl}@{p:.2f}"
        for p in LOSSES:
            yield "C1_VS_C2", f"{C1}@{p:.2f}", f"{C2}@{p:.2f}"

    s5_cmp = []
    for family, a, b in s5_pairs():
        for metric in S5_METRICS:
            sub = [r for r in s5_rows if r["metric"] == metric]
            if {a, b} <= {r["controller"] for r in sub}:
                c = pair_cmp(s5_rows, scen5, metric, a, b)
                c["family"] = family
                s5_cmp.append(c)
    fstats._write_pairwise_parquet(OUT / "s5_pairwise.parquet", s5_cmp)
    s5_pw = [flat(c, {"family": c["family"]}) for c in s5_cmp]
    add_conditional_context(s5_pw)
    s5_classes = []
    for family, a, b in s5_pairs():
        sub = [r for r in s5_pw if r["baseline"] == a and r["treatment"] == b]
        cl = scenario_classification(sub, a, b)
        s5_classes.append({"family": family, "baseline": a, "treatment": b, **cl})
        for r in sub:
            r["pair_classification"] = cl["classification"]
    write_csv(OUT / "s5_pairwise.csv", s5_pw, drop=("paired_differences",))
    write_csv(OUT / "s5_pair_classification.csv",
              [{**c, "treatment_favourable_key_metrics": ";".join(c["treatment_favourable_key_metrics"]),
                "baseline_favourable_key_metrics": ";".join(c["baseline_favourable_key_metrics"])} for c in s5_classes])

    # resumo de comunicação (S5 + MAIN), razões de overhead
    comm_rows = []
    for r in all_runs:
        if r["controller"] in (C1, C2):
            cm_ = r["comm"]
            sent = cm_["messages_sent"]
            comm_rows.append({
                "experiment": r["experiment"], "scenario": r["scenario"], "controller": r["controller"],
                "packet_loss": r["loss"], "seed": r["seed"], **{k: cm_[k] for k in COMM},
                "observed_drop_ratio": cm_["messages_dropped"] / sent if sent else None,
                "delivered_ratio": cm_["messages_delivered"] / sent if sent else None,
                "run_id": r["run_id"],
            })
    grp: dict[tuple, list] = defaultdict(list)
    for x in comm_rows:
        grp[(x["experiment"], x["scenario"], x["controller"], x["packet_loss"])].append(x)
    comm_sum = []
    for (exp, scen, ctrl, p), xs in sorted(grp.items()):
        def mean(k):
            return statistics.fmean(x[k] for x in xs)
        comm_sum.append({
            "experiment": exp, "scenario": scen, "controller": ctrl, "packet_loss": p, "N": len(xs),
            **{f"mean_{k}": mean(k) for k in COMM},
            "total_messages_sent": sum(x["messages_sent"] for x in xs),
            "total_messages_delivered": sum(x["messages_delivered"] for x in xs),
            "total_messages_dropped": sum(x["messages_dropped"] for x in xs),
            "observed_drop_ratio_min": min(x["observed_drop_ratio"] for x in xs),
            "observed_drop_ratio_mean": statistics.fmean(x["observed_drop_ratio"] for x in xs),
            "observed_drop_ratio_max": max(x["observed_drop_ratio"] for x in xs),
            "mean_bytes_per_message_sent": mean("bytes_sent") / mean("messages_sent"),
        })
    # razão de overhead C2/C1 por cenário/perda
    key_c = {(s["experiment"], s["scenario"], s["controller"], s["packet_loss"]): s for s in comm_sum}
    overhead = []
    for (exp, scen, ctrl, p), s in sorted(key_c.items()):
        if ctrl == C2 and (exp, scen, C1, p) in key_c:
            c1s = key_c[(exp, scen, C1, p)]
            overhead.append({
                "experiment": exp, "scenario": scen, "packet_loss": p,
                "C2_over_C1_messages_sent": s["mean_messages_sent"] / c1s["mean_messages_sent"],
                "C2_over_C1_bytes_sent": s["mean_bytes_sent"] / c1s["mean_bytes_sent"],
                "C2_over_C1_bytes_delivered": (s["mean_bytes_delivered"] / c1s["mean_bytes_delivered"]
                                               if c1s["mean_bytes_delivered"] else None),
                "C1_mean_bytes_sent": c1s["mean_bytes_sent"], "C2_mean_bytes_sent": s["mean_bytes_sent"],
            })
    write_csv(OUT / "s5_communication_summary.csv", comm_sum)
    write_csv(OUT / "communication_overhead_ratio.csv", overhead)
    write_csv(OUT / "communication_by_run.csv", comm_rows)
    total_100 = {"sent": sum(x["messages_sent"] for x in comm_rows if x["experiment"] == "FINAL_S5" and x["packet_loss"] == 1.0),
                 "delivered": sum(x["messages_delivered"] for x in comm_rows if x["experiment"] == "FINAL_S5" and x["packet_loss"] == 1.0),
                 "dropped": sum(x["messages_dropped"] for x in comm_rows if x["experiment"] == "FINAL_S5" and x["packet_loss"] == 1.0),
                 "bytes_delivered": sum(x["bytes_delivered"] for x in comm_rows if x["experiment"] == "FINAL_S5" and x["packet_loss"] == 1.0)}

    # checagem cruzada de determinismo: S5 @0% / referência B2 vs FINAL_MAIN S2 (mesmas entradas, experimentos separados)
    main_idx = {(r["controller"], r["seed"]): r for r in main_runs if r["scenario"] == S5_SCENARIO}
    det = {"compared_runs": 0, "max_abs_diff": 0.0, "identical_runs": 0}
    for r in s5_runs:
        if r["loss"] == 0.0 and (r["controller"], r["seed"]) in main_idx:
            mr = main_idx[(r["controller"], r["seed"])]
            diffs = [abs(float(r["metrics"][k]) - float(mr["metrics"][k])) for k in CORE + CONTEXT
                     if k in r["metrics"] and k in mr["metrics"]
                     and k not in ("controller_decision_mean_ms", "controller_decision_p95_ms")
                     and r["metrics"][k] is not None and mr["metrics"][k] is not None]
            det["compared_runs"] += 1
            det["max_abs_diff"] = max(det["max_abs_diff"], max(diffs))
            det["identical_runs"] += int(max(diffs) == 0)

    # ---------------------------------------------------------------------------------------
    # Piloto vs final (nunca agrupados)
    # ---------------------------------------------------------------------------------------
    pilot = [x for x in pq.read_table(PILOT_PARQUET).to_pylist() if x["controller"] in (B2, C1)]
    pilot_rows = []
    for x in pilot:
        pilot_rows.append({
            "controller": x["controller"], "scenario": x["scenario"], "metric": x["metric"],
            "value": float(x["value"]), "seed": int(x["seed"]), "demand": x["demand_profile"],
            "route_hash": x["route_hash"], "network_hash": x["network_hash"], "phase_plan": x["phase_plan"],
            "phase_plan_version": x["phase_plan_version"], "movement_model_version": x["movement_model_version"],
            "turning_ratios": fstats._canonical_turning_ratios(x["turning_ratios"]),
            "communication_topology_hash": x["communication_topology_hash"], "run_id": x["run_id"],
            "status": x["status"], "success": x["success"]})
    first5 = [r for r in main_rows if r["seed"] in PILOT_SEEDS and r["controller"] in (B2, C1)]
    pvf = []
    pilot_final_value_diff = 0.0
    pidx = {(x["controller"], x["scenario"], x["metric"], x["seed"]): x["value"] for x in pilot_rows}
    for x in first5:
        k = (x["controller"], x["scenario"], x["metric"], x["seed"])
        if k in pidx and not x["metric"].startswith("controller_decision"):
            pilot_final_value_diff = max(pilot_final_value_diff, abs(pidx[k] - x["value"]))
    pilot_metrics = CORE + ["never_inserted_vehicle_count", "unfinished_in_network_count", "post_shock_queue_auc_vehicle_seconds"]
    for scenario in SCENARIOS:
        for metric in pilot_metrics:
            try:
                p5 = pair_cmp(pilot_rows, scenario, metric, B2, C1)
                f5 = pair_cmp(first5, scenario, metric, B2, C1)
                f10 = pair_cmp(main_rows, scenario, metric, B2, C1)
            except (fstats.AnalysisValidationError, StopIteration):
                continue
            w5, w10 = p5["ci95_high"] - p5["ci95_low"], f10["ci95_high"] - f10["ci95_low"]
            sd5 = statistics.stdev([d["difference"] for d in p5["paired_differences"]])
            sd10 = statistics.stdev([d["difference"] for d in f10["paired_differences"]])
            sgn = lambda x: (x > 0) - (x < 0)  # noqa: E731
            lab5 = effect_label({"ci95_low": p5["ci95_low"], "ci95_high": p5["ci95_high"]}, metric)
            lab10 = effect_label({"ci95_low": f10["ci95_low"], "ci95_high": f10["ci95_high"]}, metric)
            bm5 = statistics.fmean(d["controller_a_value"] for d in p5["paired_differences"])
            rel5 = p5["mean_difference"] / bm5 if bm5 else None
            bm10 = statistics.fmean(d["controller_a_value"] for d in f10["paired_differences"])
            rel10 = f10["mean_difference"] / bm10 if bm10 else None
            pvf.append({
                "scenario": scenario, "metric": metric, "direction": direction(metric),
                "pilot_N": p5["n_pairs"], "pilot_mean_diff_C1_minus_B2": p5["mean_difference"],
                "pilot_ci95_low": p5["ci95_low"], "pilot_ci95_high": p5["ci95_high"], "pilot_ci_width": w5,
                "pilot_rel_diff": rel5, "pilot_effect": lab5,
                "final_first5_mean_diff": f5["mean_difference"],
                "final_first5_identical_to_pilot": abs(f5["mean_difference"] - p5["mean_difference"]) < 1e-9
                and abs(f5["ci95_low"] - p5["ci95_low"]) < 1e-9,
                "final_N": f10["n_pairs"], "final_mean_diff_C1_minus_B2": f10["mean_difference"],
                "final_ci95_low": f10["ci95_low"], "final_ci95_high": f10["ci95_high"], "final_ci_width": w10,
                "final_rel_diff": rel10, "final_effect": lab10,
                "direction_persisted": sgn(p5["mean_difference"]) == sgn(f10["mean_difference"]),
                "ci_width_ratio_final_over_pilot": (w10 / w5) if w5 else None,
                "effect_magnitude_ratio_final_over_pilot": (abs(f10["mean_difference"]) / abs(p5["mean_difference"])) if p5["mean_difference"] else None,
                "sd_paired_diff_pilot": sd5, "sd_paired_diff_final": sd10,
                "verdict_pilot": lab5, "verdict_final": lab10,
                "verdict_changed": lab5 != lab10,
            })
    write_csv(OUT / "pilot_vs_final.csv", pvf)
    # valor N=10: larguras de IC + variabilidade entre seeds do S4
    n10 = []
    for scenario in SCENARIOS:
        for c in (B2, C1):
            for metric in ("throughput", "mean_waiting_time", "mean_network_queue_vehicles"):
                v5 = [x["value"] for x in first5 if x["scenario"] == scenario and x["controller"] == c and x["metric"] == metric]
                v10 = [x["value"] for x in main_rows if x["scenario"] == scenario and x["controller"] == c and x["metric"] == metric]
                n10.append({"scenario": scenario, "controller": c, "metric": metric,
                            "sd_first5": statistics.stdev(v5), "sd_all10": statistics.stdev(v10),
                            "cv_first5": statistics.stdev(v5) / statistics.fmean(v5),
                            "cv_all10": statistics.stdev(v10) / statistics.fmean(v10)})
    write_csv(OUT / "n10_variability.csv", n10)

    # ---------------------------------------------------------------------------------------
    # Validação
    # ---------------------------------------------------------------------------------------
    s5_in_final_metrics = {(x["controller"], x["seed"], x["packet_loss"]) for x in fm_rows if x["experiment"] == "FINAL_S5"}
    retried_ids = {(r["controller"], r["seed"], r["loss"]) for r in retried}
    long12_included = len(retried_ids & s5_in_final_metrics)
    runs_by_experiment = Counter(x["experiment"] for x in {(y["experiment"], y["run_id"]): y for y in fm_rows}.values())
    obs_unique = len({(x["experiment"], x["scenario"], x["controller"], x["seed"], x["packet_loss"], x["metric"]) for x in fm_rows})
    validation = {
        **preflight,
        "FINAL_MAIN_RUNS_ANALYZED": f"{runs_by_experiment['FINAL_MAIN']}/200",
        "FINAL_S5_RUNS_ANALYZED": f"{runs_by_experiment['FINAL_S5']}/90",
        "TOTAL_FINAL_SCIENTIFIC_RUNS_ANALYZED": f"{runs_by_experiment['FINAL_MAIN'] + runs_by_experiment['FINAL_S5']}/290",
        "duplicate_main_identities": dup_main, "duplicate_s5_identities": dup_s5,
        "duplicate_metric_observations": len(fm_rows) - obs_unique,
        "pilot_run_ids_in_final_population": pilot_overlap,
        "historical_b0_ids_in_final_population": [r["controller"] for r in main_runs if r["controller"].startswith("B0_FIXED") and r["controller"] != B0],
        "calibration_or_replay_runs_included": 0,
        "experiment_config_sha256_values": dict(exps),
        "LONG_PATH_RUNS_READABLE": "YES" if long_readable else "NO",
        "runs_readable": f"{sum(1 for x in read if x['readable'])}/{len(read)}",
        "runs_needing_extended_path": len(long_path_runs),
        "long_path_workaround": "files opened with the extended-length prefix (\\\\?\\); no raw artifact renamed, moved or rewritten",
        "S5_retried_identities": len(retried_ids),
        "S5_retried_identities_expected_set_ok": len(retried_ok) == 12,
        "retry_failed_attempt_dirs_contributing": 0,
        "LONG_PATH_S5_IDENTITIES_INCLUDED": f"{long12_included}/12",
        "main_retried_identities": len(main_retried),
        "combined_metrics_crosscheck": {"values_checked": cm_checked, "mismatches": cm_mismatch},
        "reference_route_route_hash_ok": f"{route_hash_ok}/120",
        "reference_route_runs": len({(r['scenario'], r['controller'], r['seed']) for r in rr_rows}),
        "pilot_first5_vs_final_first5_max_abs_value_diff_excluding_wall_clock_metrics": pilot_final_value_diff,
        "s5_0pct_vs_main_s2_determinism_check": det,
        "bootstrap": {"seed": BOOT_SEED, "resamples": BOOT_N, "route_seed_base": rr.BOOTSTRAP_BASE_SEED},
        "problems": problems,
    }
    valid = (not problems and not dup_main and not dup_s5 and not pilot_overlap
             and validation["LONG_PATH_RUNS_READABLE"] == "YES" and long12_included == 12
             and runs_by_experiment["FINAL_MAIN"] == 200 and runs_by_experiment["FINAL_S5"] == 90
             and cm_mismatch == 0 and validation["duplicate_metric_observations"] == 0
             and len(retried_ok) == 12 and not main_retried)
    validation["FINAL_ANALYSIS_VALID"] = "YES" if valid else "NO"
    (OUT / "analysis-validation.json").write_text(json.dumps(validation, indent=2, default=str) + "\n", encoding="utf-8")

    analysis = {
        "provenance": {**prov, "scientific_tree_sha256": TREE, "head_git_sha": git("rev-parse", "HEAD"),
                       "bootstrap": validation["bootstrap"]},
        "classification_rule": {
            "service_keys": SERVICE_KEYS, "delay_keys": DELAY_KEYS,
            "rule": "per key metric: TREATMENT_BETTER/BASELINE_BETTER only if the paired bootstrap 95% CI excludes 0 "
                    "in that direction; scenario/pair label: TRADE_OFF if both occur, otherwise the better side, "
                    "otherwise NO_CLEAR_DIFFERENCE. mean_travel_time is conditional and excluded from the vote.",
            "relative_difference": "mean paired difference / baseline mean (statistical-plan.json); the frozen "
                                   "mean-of-pair-ratios is also kept as relative_difference_mean_of_pairs"},
        "scenario_pair_classification": classes,
        "s5_pair_classification": s5_classes,
        "s4_teleports": {"per_controller": tele_summary, "teleports_in_other_scenarios_total": tele_any_other},
        "s5_total_at_100_percent_loss": total_100,
        "determinism_check": det,
        "outliers_flagged_not_removed": len(outliers),
        "validation_ref": "analysis-validation.json",
    }
    (OUT / "final_analysis.json").write_text(json.dumps(analysis, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: validation[k] for k in validation if k not in ("experiment_config_sha256_values",)}, indent=2, default=str))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
