"""Helpers for the TCC content generator (Prompt 65).

Templates (scripts/tcc_content_templates/*.md) contain ``{{ expression }}`` markers. Each marker is
evaluated with the helpers below; every number therefore comes from artifacts/final-analysis/ (the
validated FINAL N=10 analysis) and every evaluation is recorded for the claims-traceability file.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
A = REPO / "artifacts/final-analysis"
SRC_SHA = "176178e36eeafb329a5a1350161be61cf97902b0"
TREE_SHA = "b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff"
FREEZE_SHA = "de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec"

B0, B1, B2, C1, C2 = ("B0_FIXED_CALIBRATED", "B1_LOCAL_ADAPTIVE", "B2_LOCAL_PRESSURE",
                      "C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED")
S1, S2, S3, S4 = "S1_BALANCED", "S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"
SCEN = [S1, S2, S3, S4]
CT = {B0: "B0", B1: "B1", B2: "B2", C1: "C1", C2: "C2"}
CT_PT = {B0: "B0 (tempo fixo calibrado)", B1: "B1 (adaptativo local)", B2: "B2 (pressão local)",
         C1: "C1 (cooperativo compacto)", C2: "C2 (cooperativo expandido)"}
SC_PT = {S1: "S1 — balanceado", S2: "S2 — pico direcional", S3: "S3 — mudança de demanda", S4: "S4 — saturação localizada"}
MET_PT = {
    "throughput": "vazão (veículos concluídos)", "completion_ratio_offered": "razão de conclusão (oferecidos)",
    "completion_ratio_departed": "razão de conclusão (partidos)", "departure_ratio": "razão de partida",
    "mean_waiting_time": "tempo de espera médio (s)", "mean_time_loss": "perda de tempo média (s)",
    "mean_travel_time": "tempo de viagem médio (s)", "mean_stops": "paradas médias",
    "mean_network_queue_vehicles": "fila média da rede (veículos)", "max_network_queue_vehicles": "fila máxima da rede (veículos)",
    "mean_depart_delay_seconds": "atraso de partida médio (s)", "never_inserted_vehicle_count": "veículos nunca inseridos",
    "unfinished_in_network_count": "veículos inacabados na rede", "sumo_teleports_total": "teleports SUMO",
    "post_shock_queue_auc_vehicle_seconds": "área da fila pós-choque (veículo·s)",
}
RATIO = {"completion_ratio_offered", "completion_ratio_departed", "departure_ratio"}


def rd(name: str) -> list[dict[str, str]]:
    with (A / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


PW = rd("final_pairwise_summary.csv")
DESC = rd("final_controller_summary.csv")
CLS = rd("final_scenario_pair_classification.csv")
RRP = rd("reference_route_pairwise.csv")
RRS = rd("reference_route_summary.csv")
RRC = rd("reference_route_cohort_summary.csv")
NVR = rd("network_vs_reference_route_direction.csv")
S5D = rd("s5_controller_summary.csv")
S5P = rd("s5_pairwise.csv")
S5C = rd("s5_pair_classification.csv")
COMM = rd("s5_communication_summary.csv")
COMMRUN = rd("communication_by_run.csv")
OVH = rd("communication_overhead_ratio.csv")
PVF = rd("pilot_vs_final.csv")
TELE = rd("s4_teleports_by_run.csv")
N10 = rd("n10_variability.csv")
ANALYSIS = json.loads((A / "final_analysis.json").read_text(encoding="utf-8"))
VALID = json.loads((A / "analysis-validation.json").read_text(encoding="utf-8"))
RR_RUNS = pq.read_table(A / "reference_route_results.parquet").to_pylist()
TESTS = json.loads((REPO / "artifacts/tcc-content-validation/test_counts.json").read_text(encoding="utf-8")) \
    if (REPO / "artifacts/tcc-content-validation/test_counts.json").exists() else {}

LOG: list[dict[str, Any]] = []
_CTX: dict[str, Any] = {}


def _rec(value: str, **meta: Any) -> str:
    _CTX.clear()
    _CTX.update(meta)
    _CTX["value"] = value
    return value


def pt(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def en(s: str) -> str:
    """English number format for an already formatted pt-BR value (decimal point, ASCII minus sign kept as U+2212)."""
    return str(s).replace(",", ".")


def thousands(x: float, d: int = 0) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def _pair(scn: str, a: str, b: str, m: str) -> dict[str, str]:
    return next(r for r in PW if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b and r["metric"] == m)


def _digits(m: str) -> int:
    return 3 if m in RATIO else 1


# ---- main experiment helpers ------------------------------------------------------------------
def rel(scn, a, b, m, d=1):
    r = _pair(scn, a, b, m)
    return _rec(pt(float(r["relative_difference_of_means"]) * 100, d, True) + "%", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="relative_difference_of_means")


def relci(scn, a, b, m, d=1):
    r = _pair(scn, a, b, m)
    lo, hi = float(r["ci95_relative_low"]) * 100, float(r["ci95_relative_high"]) * 100
    return _rec(f"IC95% [{pt(lo, d, True)}%; {pt(hi, d, True)}%]", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="ci95_relative")


def dabs(scn, a, b, m, d=None):
    r = _pair(scn, a, b, m)
    d = _digits(m) if d is None else d
    return _rec(pt(float(r["mean_difference"]), d, True), artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="mean_difference")


def ci(scn, a, b, m, d=None):
    r = _pair(scn, a, b, m)
    d = _digits(m) if d is None else d
    return _rec(f"[{pt(float(r['ci95_low']), d, True)}; {pt(float(r['ci95_high']), d, True)}]", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="ci95_abs")


def pp(scn, a, b, m="completion_ratio_offered", d=1):
    r = _pair(scn, a, b, m)
    return _rec(pt(float(r["mean_difference"]) * 100, d, True) + " p.p.", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="mean_difference_pp")


def medd(scn, a, b, m, d=None):
    r = _pair(scn, a, b, m)
    d = _digits(m) if d is None else d
    return _rec(pt(float(r["median_difference"]), d, True), artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="median_difference")


def nfav(scn, a, b, m):
    r = _pair(scn, a, b, m)
    return _rec(f"{r['seeds_treatment_favourable']}/{r['n_pairs']}", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_pairs"], kind="seeds_treatment_favourable")


def effect(scn, a, b, m):
    r = _pair(scn, a, b, m)
    return {"TREATMENT_BETTER": "favorável ao tratamento", "BASELINE_BETTER": "favorável ao baseline", "NO_CLEAR_DIFFERENCE": "sem diferença clara"}[r["effect"]]


def cls(scn, a, b):
    k = next(r["classification"] for r in CLS if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b)
    if k == "TRADE_OFF":
        out = "trade-off"
    elif k == "NO_CLEAR_DIFFERENCE":
        out = "sem diferença clara"
    else:
        out = CT[k.split("_")[0] + "_" + k.split("_")[1] + "_" + k.split("_")[2]] if False else k.replace("_BETTER", "")
        out = CT.get(out, out) + " favorecido"
    return _rec(out, artifact="final_scenario_pair_classification.csv", scenario=scn, comparison=f"{a}→{b}", metric="classificação (métricas de serviço × atraso/fila)", N="10 pares", kind="classification")


def mu(scn, c, m, d=None, key="mean"):
    d = _digits(m) if d is None else d
    v = float(next(r for r in DESC if r["scenario"] == scn and r["controller"] == c and r["metric"] == m)[key])
    return _rec(thousands(v, 0) if d == 0 and abs(v) >= 1000 else pt(v, d), artifact="final_controller_summary.csv", scenario=scn, comparison=c, metric=m, N=10, kind=key)


def sd(scn, c, m, d=None):
    return mu(scn, c, m, d, "std")


def med(scn, c, m, d=None):
    return mu(scn, c, m, d, "median")


def iqr(scn, c, m, d=None):
    return mu(scn, c, m, d, "iqr")


def num(scn, c, m, key="mean") -> float:
    return float(next(r for r in DESC if r["scenario"] == scn and r["controller"] == c and r["metric"] == m)[key])


def nmin(scn, c, m, d=None):
    return mu(scn, c, m, d, "min")


def nmax(scn, c, m, d=None):
    return mu(scn, c, m, d, "max")


def span(scn, m, key="mean", d=None):
    """min–max of the 5 controller means (used for ranges)."""
    d = _digits(m) if d is None else d
    vals = [num(scn, c, m, key) for c in (B0, B1, B2, C1, C2)]
    fm = (lambda v: thousands(v, 0)) if d == 0 else (lambda v: pt(v, d))
    return _rec(f"{fm(min(vals))}–{fm(max(vals))}", artifact="final_controller_summary.csv", scenario=scn, comparison="B0–C2", metric=m, N=10, kind="range of means")


def pct_not_completing(scn):
    vals = [1 - num(scn, c, "completion_ratio_offered") for c in (B0, B1, B2, C1, C2)]
    return _rec(f"{pt(min(vals) * 100, 0)}–{pt(max(vals) * 100, 0)}%", artifact="final_controller_summary.csv", scenario=scn, comparison="B0–C2", metric="1 − completion_ratio_offered", N=10, kind="range")


# ---- reference route -----------------------------------------------------------------------------
TT, CMP = "reference_route_mean_travel_time_seconds", "reference_route_completion_ratio_offered"


def rrm(scn, c, kind="tt", d=None):
    m = TT if kind == "tt" else CMP
    d = (1 if kind == "tt" else 3) if d is None else d
    v = float(next(r for r in RRS if r["scenario"] == scn and r["controller"] == c and r["metric"] == m)["mean"])
    return _rec(pt(v, d), artifact="reference_route_summary.csv", scenario=scn, comparison=c, metric=m, N=10, kind="mean")


def rrd(scn, a, b, kind="tt", d=None):
    m = TT if kind == "tt" else CMP
    r = next(x for x in RRP if x["scenario"] == scn and x["baseline"] == a and x["treatment"] == b and x["metric"] == m)
    d = (1 if kind == "tt" else 3) if d is None else d
    return _rec(pt(float(r["paired_mean_diff"]), d, True), artifact="reference_route_pairwise.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_seeds"], kind="paired_mean_diff")


def rrpp(scn, a, b, d=1):
    r = next(x for x in RRP if x["scenario"] == scn and x["baseline"] == a and x["treatment"] == b and x["metric"] == CMP)
    return _rec(pt(float(r["paired_mean_diff"]) * 100, d, True) + " p.p.", artifact="reference_route_pairwise.csv", scenario=scn, comparison=f"{a}→{b}", metric=CMP, N=r["n_seeds"], kind="paired_mean_diff_pp")


def rrci(scn, a, b, kind="tt", d=None):
    m = TT if kind == "tt" else CMP
    r = next(x for x in RRP if x["scenario"] == scn and x["baseline"] == a and x["treatment"] == b and x["metric"] == m)
    d = (1 if kind == "tt" else 3) if d is None else d
    return _rec(f"[{pt(float(r['ci95_low']), d, True)}; {pt(float(r['ci95_high']), d, True)}]", artifact="reference_route_pairwise.csv", scenario=scn, comparison=f"{a}→{b}", metric=m, N=r["n_seeds"], kind="ci95")


def rrcoh(scn, c, key="offered", d=1):
    r = next(x for x in RRC if x["scenario"] == scn and x["controller"] == c)
    v = float(r[f"mean_reference_route_{key}"])
    return _rec(pt(v, d), artifact="reference_route_cohort_summary.csv", scenario=scn, comparison=c, metric=f"reference_route_{key}", N=10, kind="mean")


def net_vs_route(key, scn=S3, comp=f"{B2}->{C1}", d=1):
    r = next(x for x in NVR if x["scenario"] == scn and x["comparison"] == comp)
    v = r[key]
    if key.endswith("_ci"):
        return _rec(v.replace(".", ",").replace("-", "−").replace(",", ";", 1).replace("[", "[").replace(";", "; "), artifact="network_vs_reference_route_direction.csv", scenario=scn, comparison=comp, metric=key, N=10, kind="ci")
    return _rec(pt(float(v), d, True), artifact="network_vs_reference_route_direction.csv", scenario=scn, comparison=comp, metric=key, N=10, kind="diff")


# ---- S5 ---------------------------------------------------------------------------------------------
def _s5(c, loss, m, key="mean"):
    label = f"{B2}@REF" if c == B2 else f"{c}@{loss:.2f}"
    return float(next(r for r in S5D if r["controller"] == label and r["metric"] == m)[key])


def s5m(c, loss, m, d=None, key="mean"):
    d = (3 if m in RATIO else 1) if d is None else d
    return _rec(pt(_s5(c, loss, m, key), d), artifact="s5_controller_summary.csv", scenario="S5 (tráfego S2)", comparison=f"{c}@{loss}", metric=m, N=10, kind=key)


def s5rel(c, loss, m, d=1):
    r = next(x for x in S5P if x["family"] == "DEGRADATION_VS_0" and x["baseline"] == f"{c}@0.00" and x["treatment"] == f"{c}@{loss:.2f}" and x["metric"] == m)
    return _rec(pt(float(r["relative_difference_of_means"]) * 100, d, True) + "%", artifact="s5_pairwise.csv", scenario="S5 (tráfego S2)", comparison=f"{c}@0.00→{c}@{loss:.2f}", metric=m, N=r["n_pairs"], kind="relative_difference_of_means")


def s5relci(c, loss, m, d=1):
    r = next(x for x in S5P if x["family"] == "DEGRADATION_VS_0" and x["baseline"] == f"{c}@0.00" and x["treatment"] == f"{c}@{loss:.2f}" and x["metric"] == m)
    return _rec(f"IC95% [{pt(float(r['ci95_relative_low']) * 100, d, True)}%; {pt(float(r['ci95_relative_high']) * 100, d, True)}%]", artifact="s5_pairwise.csv", scenario="S5 (tráfego S2)", comparison=f"{c}@0.00→{c}@{loss:.2f}", metric=m, N=r["n_pairs"], kind="ci95_relative")


def s5vsb2(c, loss, m, d=1):
    r = next(x for x in S5P if x["family"] == "VS_B2_REFERENCE" and x["treatment"] == f"{c}@{loss:.2f}" and x["metric"] == m)
    return _rec(pt(float(r["relative_difference_of_means"]) * 100, d, True) + "%", artifact="s5_pairwise.csv", scenario="S5 (tráfego S2)", comparison=f"B2@REF→{c}@{loss:.2f}", metric=m, N=r["n_pairs"], kind="relative_difference_of_means")


def s5c1c2(loss, m, d=1):
    r = next(x for x in S5P if x["family"] == "C1_VS_C2" and x["baseline"] == f"{C1}@{loss:.2f}" and x["metric"] == m)
    return _rec(pt(float(r["relative_difference_of_means"]) * 100, d, True) + "%", artifact="s5_pairwise.csv", scenario="S5 (tráfego S2)", comparison=f"C1@{loss:.2f}→C2@{loss:.2f}", metric=m, N=r["n_pairs"], kind="relative_difference_of_means")


def s5cls(family, a, b):
    r = next(x for x in S5C if x["family"] == family and x["baseline"] == a and x["treatment"] == b)
    return r["classification"]


def comm(c, loss, key, d=0, exp="FINAL_S5", scn="S2_DIRECTIONAL_PEAK"):
    r = next(x for x in COMM if x["experiment"] == exp and x["scenario"] == scn and x["controller"] == c and float(x["packet_loss"]) == loss)
    v = float(r[key])
    scale = 1e6 if "bytes" in key and "per_message" not in key else 1
    d = 1 if scale == 1e6 and d == 0 else d
    return _rec(thousands(v / scale, d), artifact="s5_communication_summary.csv", scenario=f"{exp} {scn}", comparison=f"{c}@{loss}", metric=key, N=10, kind="mean per run" + (" (MB)" if scale == 1e6 else ""))


def drop_ratio(loss, which="min"):
    vals = [float(r[f"observed_drop_ratio_{which}"]) for r in COMM if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == loss]
    v = min(vals) if which == "min" else max(vals)
    return _rec(pt(v * 100, 1) + "%", artifact="s5_communication_summary.csv", scenario="S5", comparison=f"loss {loss}", metric=f"observed_drop_ratio_{which}", N=20, kind=which)


def total100(key):
    v = sum(float(r[f"total_messages_{key}"]) for r in COMM if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    return _rec(thousands(v), artifact="s5_communication_summary.csv", scenario="S5 loss 100%", comparison="C1+C2", metric=f"total_messages_{key}", N=20, kind="sum")


def bytes100():
    v = sum(float(r["bytes_delivered"]) for r in COMMRUN if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    return _rec(thousands(v), artifact="communication_by_run.csv", scenario="S5 loss 100%", comparison="C1+C2", metric="bytes_delivered", N=20, kind="sum")


def eq_b2():
    n, bad = s5_equal_b2()
    return _rec(f"{n - bad}/{n}", artifact="s5_results.parquet", scenario="S5 loss 100%", comparison="C1,C2 vs B2 (mesma seed)", metric="métricas de tráfego idênticas", N=20, kind="count")


def n_runs_s4_below(thr=0.5):
    return None


def bytes_gap_pct(c, exp="FINAL_S5", scn="S2_DIRECTIONAL_PEAK", loss=0.0):
    r = next(x for x in COMM if x["experiment"] == exp and x["scenario"] == scn and x["controller"] == c and float(x["packet_loss"]) == loss)
    gap = (1 - float(r["mean_bytes_delivered"]) / float(r["mean_bytes_sent"])) * 100
    return _rec(pt(gap, 2), artifact="s5_communication_summary.csv", scenario=f"{exp} {scn}", comparison=f"{c}@{loss}", metric="bytes_sent vs bytes_delivered gap (%)", N=10, kind="derived")


def ratio_bytes(exp="FINAL_S5", scn="S2_DIRECTIONAL_PEAK", loss=0.0, d=2):
    r = next(x for x in OVH if x["experiment"] == exp and x["scenario"] == scn and float(x["packet_loss"]) == loss)
    return _rec(pt(float(r["C2_over_C1_bytes_sent"]), d), artifact="communication_overhead_ratio.csv", scenario=f"{exp} {scn}", comparison="C2/C1", metric="bytes_sent", N=10, kind="ratio")


def ratio_range():
    vals = [float(r["C2_over_C1_bytes_sent"]) for r in OVH]
    return _rec(f"{pt(min(vals), 2)}–{pt(max(vals), 2)}", artifact="communication_overhead_ratio.csv", scenario="todos", comparison="C2/C1", metric="bytes_sent", N=10, kind="range")


def bytes_msg(c, d=0):
    r = next(x for x in COMM if x["experiment"] == "FINAL_S5" and x["controller"] == c and float(x["packet_loss"]) == 0.0)
    return _rec(pt(float(r["mean_bytes_per_message_sent"]), d), artifact="s5_communication_summary.csv", scenario="S5 loss 0%", comparison=c, metric="mean_bytes_per_message_sent", N=10, kind="mean")


def s5_equal_b2():
    """Number of (controller, seed, metric) comparisons at 100% loss that are identical to B2 (traffic metrics)."""
    tr = {}
    for r in pq.read_table(A / "s5_results.parquet").to_pylist():
        tr[(r["controller"], int(r["seed"]), r["packet_loss"], r["metric"])] = r["value"]
    skip = ("controller_decision", "messages", "bytes", "mean_message", "max_message")
    metrics = {k[3] for k in tr if not k[3].startswith(skip)}
    n = bad = 0
    for c in (C1, C2):
        for seed in {k[1] for k in tr}:
            for m in metrics:
                a, b = tr.get((c, seed, 1.0, m)), tr.get((B2, seed, 0.0, m))
                if a is None or b is None:
                    continue
                n += 1
                bad += a != b
    return n, bad


# ---- teleports ----------------------------------------------------------------------------------------
def tele(c=None, what="total"):
    t = ANALYSIS["s4_teleports"]["per_controller"]
    if c is None:
        total = sum(v["total"] for v in t.values())
        runs = sum(v["runs_with_teleports"] for v in t.values())
        out = {"total": total, "runs": runs}[what]
    else:
        out = {"total": t[c]["total"], "runs": t[c]["runs_with_teleports"], "max": t[c]["max"]}[what]
    return _rec(f"{out:.0f}", artifact="final_analysis.json (s4_teleports)", scenario=S4, comparison=c or "todos", metric="sumo_teleports_total", N=10 if c else 50, kind=what)


# ---- pilot vs final -----------------------------------------------------------------------------------
def pvf(scn, m, field, d=1, pct_=False):
    r = next(x for x in PVF if x["scenario"] == scn and x["metric"] == m)
    v = float(r[field])
    out = (pt(v * 100, d, True) + "%") if pct_ else pt(v, d, True)
    return _rec(out, artifact="pilot_vs_final.csv", scenario=scn, comparison=f"{B2}→{C1} (piloto vs final)", metric=m, N="piloto 5 / final 10", kind=field)


def direction_persisted():
    nz = [r for r in PVF if r["pilot_mean_diff_C1_minus_B2"] not in ("0", "0.0")]
    k = sum(r["direction_persisted"] == "True" for r in nz)
    return _rec(f"{k}/{len(nz)}", artifact="pilot_vs_final.csv", scenario="todos", comparison="piloto vs final", metric="direction_persisted", N="piloto 5 / final 10", kind="count")


def verdict_changes():
    ch = [r for r in PVF if r["verdict_changed"] == "True"]
    return _rec("; ".join(f"{r['scenario'].split('_')[0]} {MET_PT.get(r['metric'], r['metric'])}" for r in ch), artifact="pilot_vs_final.csv", scenario="todos", comparison="piloto vs final", metric="verdict_changed", N="piloto 5 / final 10", kind="list")


def n_verdict_changes():
    return _rec(str(sum(r["verdict_changed"] == "True" for r in PVF)), artifact="pilot_vs_final.csv", scenario="todos", comparison="piloto vs final", metric="verdict_changed", N="piloto 5 / final 10", kind="count")


def first5_identical():
    k = sum(r["final_first5_identical_to_pilot"] == "True" for r in PVF)
    return _rec(f"{k}/{len(PVF)}", artifact="pilot_vs_final.csv", scenario="todos", comparison="piloto vs final (5 primeiras seeds)", metric="final_first5_identical_to_pilot", N=5, kind="count")


def width_ratio(scn, m="throughput", d=2):
    r = next(x for x in PVF if x["scenario"] == scn and x["metric"] == m)
    return _rec(pt(float(r["ci_width_ratio_final_over_pilot"]), d), artifact="pilot_vs_final.csv", scenario=scn, comparison="final/piloto", metric=m, N="5/10", kind="ci_width_ratio")


# ---- run counts / validation -----------------------------------------------------------------------------
def val(key):
    return _rec(str(VALID[key]), artifact="analysis-validation.json", scenario="—", comparison="—", metric=key, N=290, kind="validation")


def tests(key):
    return _rec(str(TESTS.get(key, "n/d")), artifact="artifacts/tcc-content-validation/test_counts.json", scenario="—", comparison="—", metric=key, N="—", kind="validation")


# ---- tables -------------------------------------------------------------------------------------------------
def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def T_desc(scn):
    mets = ["throughput", "completion_ratio_offered", "departure_ratio", "mean_waiting_time", "mean_time_loss", "mean_travel_time", "mean_network_queue_vehicles",
            "max_network_queue_vehicles", "sumo_teleports_total"]
    rows = []
    for c in (B0, B1, B2, C1, C2):
        rows.append([CT[c]] + [f"{pt(num(scn, c, m), _digits(m) if m != 'sumo_teleports_total' else 1)} ± {pt(num(scn, c, m, 'std'), _digits(m) if m != 'sumo_teleports_total' else 1)}" for m in mets])
    head = ["Ctrl", "Vazão", "Concl. (ofer.)", "Razão de partida", "Espera (s)", "Perda de tempo (s)", "Viagem (s)", "Fila média", "Fila máx.", "Teleports"]
    _rec("tabela", artifact="final_controller_summary.csv", scenario=scn, comparison="B0–C2", metric="resumo descritivo", N=10, kind="table (média ± DP)")
    return md_table(head, rows)


def T_pair(scn, a, b, mets=None):
    mets = mets or ["throughput", "completion_ratio_offered", "departure_ratio", "mean_waiting_time", "mean_time_loss", "mean_travel_time", "mean_network_queue_vehicles",
                    "max_network_queue_vehicles", "mean_depart_delay_seconds", "never_inserted_vehicle_count", "unfinished_in_network_count", "sumo_teleports_total"]
    rows = []
    lab = {"TREATMENT_BETTER": f"{CT[b]} favorecido", "BASELINE_BETTER": f"{CT[a]} favorecido", "NO_CLEAR_DIFFERENCE": "sem diferença clara"}
    for m in mets:
        r = _pair(scn, a, b, m)
        d = _digits(m) if m != "sumo_teleports_total" else 2
        base = float(r["baseline_mean"])
        rel_ = pt(float(r["relative_difference_of_means"]) * 100, 1, True) + "%" if r["relative_difference_of_means"] not in ("", "None") and base != 0 else "n/a"
        rows.append([MET_PT[m], pt(float(r["baseline_mean"]), d), pt(float(r["treatment_mean"]), d), pt(float(r["mean_difference"]), d, True), rel_,
                     f"[{pt(float(r['ci95_low']), d, True)}; {pt(float(r['ci95_high']), d, True)}]", f"{r['seeds_treatment_favourable']}/{r['n_pairs']}" if r["seeds_treatment_favourable"] not in ("", "None") else "—", lab[r["effect"]]])
    _rec("tabela", artifact="final_pairwise_summary.csv", scenario=scn, comparison=f"{a}→{b}", metric="comparação pareada", N=10, kind="table")
    return md_table(["Métrica", f"{CT[a]} (média)", f"{CT[b]} (média)", "Dif. média pareada", "Dif. relativa", "IC95% (dif.)", "Seeds favoráveis ao tratamento", "Leitura"], rows)


def T_class():
    rows = []
    for s in SCEN:
        rows.append([SC_PT[s]] + [cls(s, a, b) for a, b in ((B2, C1), (B0, B2), (B0, B1), (C1, C2))])
    _rec("tabela", artifact="final_scenario_pair_classification.csv", scenario="S1–S4", comparison="4 comparações congeladas", metric="classificação", N=10, kind="table")
    return md_table(["Cenário", "B2 → C1 (primária)", "B0 → B2", "B0 → B1", "C1 → C2"], rows)


def T_ref():
    rows = []
    for s in SCEN:
        rows.append([SC_PT[s].split(" — ")[0]] + [f"{rrm(s, c)} s / {rrm(s, c, 'cmp')}" for c in (B0, B2, C1)] +
                    [f"{rrd(s, B0, B2)} s {rrci(s, B0, B2)}; concl. {rrpp(s, B0, B2)}", f"{rrd(s, B2, C1)} s {rrci(s, B2, C1)}; concl. {rrpp(s, B2, C1)}"])
    _rec("tabela", artifact="reference_route_pairwise.csv + reference_route_summary.csv", scenario="S1–S4", comparison="B0, B2, C1", metric="tempo de viagem e conclusão da rota", N=10, kind="table")
    return md_table(["Cenário", "B0: viagem / conclusão", "B2: viagem / conclusão", "C1: viagem / conclusão", "B0 → B2 (Δ viagem [IC95%]; Δ conclusão)", "B2 → C1 (Δ viagem [IC95%]; Δ conclusão)"], rows)


def T_s5():
    mets = [("throughput", None), ("completion_ratio_offered", None), ("mean_waiting_time", None), ("mean_network_queue_vehicles", None)]
    rows = [[f"{CT[B2]} (referência)", "—"] + [s5m(B2, 0.0, m) for m, _ in mets] + ["—", "—"]]
    for c in (C1, C2):
        for loss in (0.0, 0.2, 0.5, 1.0):
            rows.append([CT[c], f"{int(loss * 100)}%"] + [f"{s5m(c, loss, m)} ± {s5m(c, loss, m, key='std')}" for m, _ in mets] +
                        [comm(c, loss, "mean_messages_delivered"), comm(c, loss, "mean_bytes_delivered") + " MB"])
    _rec("tabela", artifact="s5_controller_summary.csv + s5_communication_summary.csv", scenario="S5 (tráfego S2)", comparison="B2, C1, C2", metric="resumo S5", N=10, kind="table")
    return md_table(["Controlador", "Perda", "Vazão", "Concl. (ofer.)", "Espera (s)", "Fila média", "Msgs entregues/run", "Bytes entregues/run"], rows)


def T_s5deg():
    rows = []
    for c in (C1, C2):
        for loss in (0.2, 0.5, 1.0):
            rows.append([CT[c], f"0% → {int(loss * 100)}%"] + [f"{s5rel(c, loss, m)} {s5relci(c, loss, m)}" for m in ("throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles")])
    _rec("tabela", artifact="s5_pairwise.csv", scenario="S5 (tráfego S2)", comparison="degradação vs 0%", metric="variação relativa", N=10, kind="table")
    return md_table(["Controlador", "Mudança", "Vazão", "Conclusão (ofer.)", "Espera", "Fila média"], rows)


def T_cost():
    rows = []
    for c in (C1, C2):
        rows.append([CT[c], comm(c, 0.0, "mean_messages_sent"), comm(c, 0.0, "mean_bytes_sent") + " MB", bytes_msg(c)])
    _rec("tabela", artifact="s5_communication_summary.csv", scenario="S5 loss 0%", comparison="C1, C2", metric="custo de comunicação", N=10, kind="table")
    return md_table(["Controlador", "Mensagens enviadas/run", "Bytes enviados/run", "Bytes por mensagem"], rows)


def T_pilot():
    rows = []
    for s in SCEN:
        for m in ("throughput", "mean_waiting_time", "mean_network_queue_vehicles"):
            r = next(x for x in PVF if x["scenario"] == s and x["metric"] == m)
            rows.append([SC_PT[s].split(" — ")[0], MET_PT[m], pvf(s, m, "pilot_rel_diff", pct_=True), pvf(s, m, "final_rel_diff", pct_=True),
                         "sim" if r["direction_persisted"] == "True" else "não", width_ratio(s, m)])
    _rec("tabela", artifact="pilot_vs_final.csv", scenario="S1–S4", comparison=f"{B2}→{C1}", metric="piloto vs final", N="5/10", kind="table")
    return md_table(["Cenário", "Métrica", "Piloto (N=5): Δ relativo C1 vs B2", "Final (N=10): Δ relativo C1 vs B2", "Direção persistiu", "Largura IC final/piloto"], rows)


# ---- rendering ----------------------------------------------------------------------------------------------------
NS = {k: v for k, v in globals().items() if callable(v) or k in ("B0", "B1", "B2", "C1", "C2", "S1", "S2", "S3", "S4", "SCEN", "CT", "CT_PT", "SC_PT", "MET_PT", "TESTS", "VALID", "ANALYSIS")}
PATTERN = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)


def render(text: str, source: str) -> str:
    def repl(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        _CTX.clear()
        value = eval(expr, {"__builtins__": {"abs": abs, "min": min, "max": max, "str": str, "float": float, "int": int, "round": round, "sum": sum, "len": len}}, NS)  # noqa: S307
        value = str(value)
        LOG.append({"file": source, "expression": expr, "value": value if len(value) < 160 else value[:157] + "...", **{k: v for k, v in _CTX.items() if k != "value"}})
        return value

    return PATTERN.sub(repl, text)


# ---- figure / table placement -------------------------------------------------------------------------------
PLACEMENT = {
    "FIG01_FINAL_OVERVIEW": ("3.2 Rede e visão geral do experimento", "Metodologia", "Visão geral: rede 3×3, 5 controladores, 4 cenários, 10 seeds, S5 e 290 execuções."),
    "FIG02_MAIN_CONTROLLER_OVERVIEW": ("6.1 Visão geral", "Resultados", "Médias finais por controlador e cenário (vazão, conclusão, espera, fila)."),
    "FIG03_B0_VS_B2": ("6.2 e 6.6 (adaptação)", "Resultados", "Efeito da adaptação local em relação ao tempo fixo calibrado (B0 → B2)."),
    "FIG04_B2_VS_C1": ("6.2–6.6 (comparação primária)", "Resultados", "Comparação primária da cooperação (B2 → C1), com IC95%."),
    "FIG05_COOPERATION_RESULT_MATRIX": ("6.6 Síntese", "Resultados", "Matriz de resultados da cooperação por cenário e métrica."),
    "FIG06_S2_TRADEOFF": ("6.3 S2", "Resultados", "Trade-off do S2: menos fila e espera, menor vazão e conclusão."),
    "FIG07_S3_SHOCK": ("6.4 S3", "Resultados", "Fila da rede antes, durante e depois do choque de 2100 s."),
    "FIG08_S3_POST_SHOCK_AUC": ("6.4 S3", "Resultados", "Área da fila pós-choque (métrica congelada)."),
    "FIG09_S4_B2_VS_C1": ("6.5 S4", "Resultados", "Benefício da cooperação sob saturação localizada e piora do atraso de partida."),
    "FIG10_S4_TELEPORTS": ("6.5 S4", "Resultados", "Teleports do SUMO no S4 (ALLOW_AND_MEASURE)."),
    "FIG11_REFERENCE_ROUTE": ("6.7 Rota de referência", "Resultados", "Tempo de viagem e conclusão da rota (B0, B2, C1)."),
    "FIG12_REFERENCE_ROUTE_EFFECTS": ("6.7 Rota de referência", "Resultados", "Efeitos pareados: adaptação (B0 → B2) e cooperação (B2 → C1) na rota."),
    "FIG13_S3_NETWORK_VS_ROUTE": ("6.7 Rota de referência (rede × rota em S3)", "Resultados", "Escalas diferentes de análise no S3."),
    "FIG14_S5_PACKET_LOSS": ("6.8 S5", "Resultados", "Vazão em função da perda de pacotes (C1, C2, B2)."),
    "FIG14B_S5_COMPLETION": ("6.8 S5", "Resultados", "Conclusão em função da perda de pacotes."),
    "FIG15_S5_QUEUE_DELAY": ("6.8 S5", "Resultados", "Fila e espera em função da perda de pacotes."),
    "FIG16_COMMUNICATION_COST": ("6.9 Custo de comunicação", "Resultados", "Mensagens, bytes enviados e entregues (C1 vs C2)."),
    "FIG17_PERFORMANCE_VS_COMMUNICATION_COST": ("6.9 e 7 (discussão do custo)", "Resultados/Discussão", "Desempenho de C2 vs C1 junto do custo de comunicação."),
    "FIG18_PILOT_VS_FINAL": ("6.10 Piloto × Final", "Resultados (metodológico)", "Efeito B2 → C1: piloto (N=5) vs final (N=10), amostras não combinadas."),
    "FIG18B_N10_VALUE": ("6.10 Piloto × Final", "Resultados (metodológico)", "Valor de N=10: direção persistente, ICs mais estreitos."),
    "FIG19_FINAL_RESULT_MATRIX": ("7 Discussão e 10 Conclusão", "Discussão/Conclusão", "Matriz final de resultados por cenário."),
    "FIG20_RESEARCH_QUESTION": ("10.1 Conclusão (e defesa)", "Conclusão", "Resposta à pergunta de pesquisa."),
    "TABLE01_CONTROLLERS": ("3.4 Controladores", "Metodologia", "Definição dos cinco controladores."),
    "TABLE02_SCENARIOS": ("3.3 Cenários e 3.7 Delineamento", "Metodologia", "Definição dos cenários S1–S5."),
    "TABLE03_PRIMARY_B2_VS_C1": ("6.6 Resultados primários (e 6.2–6.5)", "Resultados", "Resultado primário B2 → C1 (5 métricas × 4 cenários). Corresponde ao 'TABLE03_PRIMARY_FINAL_RESULTS' citado no plano."),
    "TABLE04_REFERENCE_ROUTE": ("6.7 Rota de referência", "Resultados", "Tempo de viagem e conclusão por controlador; Δ B0→B2 e B2→C1."),
    "TABLE05_S5": ("6.8 S5", "Resultados", "S5: desempenho e comunicação por nível de perda."),
    "TABLE06_COMMUNICATION_COST": ("6.9 e 7 Discussão", "Resultados/Discussão", "Custo de comunicação C1 vs C2."),
}


def _fig_manifest():
    p = REPO / "artifacts/tcc-visuals/final/figure-manifest.json"
    return {e["figure_id"]: e for e in json.loads(p.read_text(encoding="utf-8"))["entries"]}


def T_placement():
    man = _fig_manifest()
    rows = []
    for fid, (sec, chap, role) in PLACEMENT.items():
        e = man.get(fid)
        assert e is not None, fid
        files = e["files"]
        rows.append([f"`{fid}`", sec, chap, role, "N = " + str(e["N"]).split(" ")[0] if str(e["N"]).split(" ")[0].isdigit() else str(e["N"]),
                     f"`artifacts/tcc-visuals/final/{files['pdf']}`"])
    _rec("tabela", artifact="artifacts/tcc-visuals/final/figure-manifest.json", scenario="—", comparison="—", metric="figuras e tabelas", N="—", kind="placement")
    return md_table(["Figura/Tabela", "Seção sugerida", "Capítulo", "Papel", "N", "Arquivo vetorial (PDF)"], rows)


def T_captions():
    man = _fig_manifest()
    out = []
    for fid in PLACEMENT:
        cap = man[fid]["caption"].replace("sempre juntos", "em conjunto").replace(" é melhor ", " é favorecido ")
        out.append(f"**{fid}** — {cap}")
    return "\n\n".join(out)


NS.update({k: v for k, v in globals().items() if callable(v)})
