"""Carga de dados, estilo e exportação compartilhados do pacote de figuras do TCC (Prompt 64).

Todo valor científico plotado é carregado de artifacts/final-analysis/ (análise FINAL N=10 validada).
Nada aqui executa simulação nem toca uma saída bruta de experimento (a série temporal do S3 é uma
reagregação somente leitura da telemetria de lanes congelada, usando a definição congelada de
network_total_queue).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
A = REPO / "artifacts/final-analysis"
ROOT = REPO / "artifacts/tcc-visuals/final"
SRC_SHA = "176178e36eeafb329a5a1350161be61cf97902b0"
FREEZE_SHA = "de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec"
TREE_SHA = "b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff"
GEN_VERSION = "tcc-figures-v1 (scripts/build_tcc_figures.py + scripts/tcc_figures_common.py)"
METHOD = ("Média ± desvio-padrão descritivos (10 seeds); efeitos: diferença pareada por seed (cenário + seed), "
          "IC95% por bootstrap percentil pareado (10 000 reamostragens, semente 20260910)")

FOLDERS = ["01_overview", "02_adaptation", "03_cooperation", "04_reference_route", "05_s3_shock",
           "06_s4_saturation", "07_s5_communication", "08_communication_cost", "09_pilot_vs_final",
           "10_summary", "tables", "presentation", "document"]

SCENARIOS = ["S1_BALANCED", "S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"]
SC_SHORT = {"S1_BALANCED": "S1", "S2_DIRECTIONAL_PEAK": "S2", "S3_DEMAND_SHIFT": "S3", "S4_LOCAL_SATURATION": "S4"}
SC_NAME = {"S1_BALANCED": "S1 — Balanceado", "S2_DIRECTIONAL_PEAK": "S2 — Pico direcional",
           "S3_DEMAND_SHIFT": "S3 — Mudança de demanda", "S4_LOCAL_SATURATION": "S4 — Saturação localizada"}
B0, B1, B2, C1, C2 = ("B0_FIXED_CALIBRATED", "B1_LOCAL_ADAPTIVE", "B2_LOCAL_PRESSURE",
                      "C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED")
CTRLS = [B0, B1, B2, C1, C2]
CT_SHORT = {B0: "B0", B1: "B1", B2: "B2", C1: "C1", C2: "C2"}
CT_LABEL = {B0: "B0 — Tempo fixo calibrado", B1: "B1 — Adaptativo local", B2: "B2 — Pressão local",
            C1: "C1 — Cooperativo compacto", C2: "C2 — Cooperativo expandido"}
# slots categóricos 1-5 da paleta de referência validada, em ordem segura quanto à adjacência
# (validado: CVD ΔE >= 9,2, visão normal ΔE >= 27 em pares adjacentes); codificação secundária =
# forma do marcador + hachura + rótulos diretos
CT_COLOR = {B0: "#2a78d6", B1: "#eb6834", B2: "#1baf7a", C1: "#6250d6", C2: "#e87ba4"}
CT_MARKER = {B0: "s", B1: "^", B2: "o", C1: "D", C2: "P"}
CT_HATCH = {B0: "", B1: "//", B2: "..", C1: "xx", C2: "\\\\"}
INK, MUTED, GRID = "#1c242c", "#5d6a76", "#e3e7ea"

METRIC_PT = {
    "throughput": "Vazão (veículos concluídos)", "completion_ratio_offered": "Conclusão (fração dos oferecidos)",
    "completion_ratio_departed": "Conclusão (fração dos partidos)", "departure_ratio": "Razão de partida",
    "mean_waiting_time": "Espera média (s)", "mean_time_loss": "Perda de tempo média (s)",
    "mean_travel_time": "Tempo de viagem médio (s)", "mean_network_queue_vehicles": "Fila média da rede (veíc.)",
    "max_network_queue_vehicles": "Fila máxima da rede (veíc.)", "mean_stops": "Paradas médias",
    "mean_depart_delay_seconds": "Atraso de partida (s)", "never_inserted_vehicle_count": "Veículos nunca inseridos",
    "unfinished_in_network_count": "Veículos inacabados na rede", "sumo_teleports_total": "Teleports SUMO",
    "post_shock_queue_auc_vehicle_seconds": "Área da fila pós-choque (veíc.·s)",
}
HIGHER_BETTER = {"throughput", "completion_ratio_offered", "completion_ratio_departed", "departure_ratio"}


def comma(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def pct(x: float, d: int = 1, sign: bool = True) -> str:
    return comma(x * 100, d, sign) + "%"


def thousands(x: float, d: int = 0) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 10.5, "axes.titlesize": 11.5, "axes.titleweight": "bold",
        "axes.labelsize": 10.5, "axes.edgecolor": MUTED, "axes.linewidth": 0.8, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 9.5, "svg.fonttype": "path",
        "pdf.fonttype": 42, "axes.formatter.useoffset": False, "axes.formatter.limits": (-9, 9),
        "savefig.dpi": 200, "figure.dpi": 100,
    })


def comma_axis(ax, which: str = "both", d: int | None = None) -> None:
    def f(v, _p):
        if abs(v) >= 1000:
            return thousands(v)
        s = f"{v:.{d}f}" if d is not None else f"{v:g}"
        return s.replace(".", ",").replace("-", "−")
    fm = FuncFormatter(f)
    if which in ("x", "both"):
        ax.xaxis.set_major_formatter(fm)
    if which in ("y", "both"):
        ax.yaxis.set_major_formatter(fm)


# ----------------------------------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------------------------------
def rd(name: str) -> list[dict[str, str]]:
    with (A / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Data:
    def __init__(self) -> None:
        self.desc = rd("final_controller_summary.csv")
        self.pw = rd("final_pairwise_summary.csv")
        self.cls = rd("final_scenario_pair_classification.csv")
        self.rr_pw = rd("reference_route_pairwise.csv")
        self.rr_sum = rd("reference_route_summary.csv")
        self.rr_coh = rd("reference_route_cohort_summary.csv")
        self.nvr = rd("network_vs_reference_route_direction.csv")
        self.s5_desc = rd("s5_controller_summary.csv")
        self.s5_pw = rd("s5_pairwise.csv")
        self.s5_cls = rd("s5_pair_classification.csv")
        self.comm = rd("s5_communication_summary.csv")
        self.comm_run = rd("communication_by_run.csv")
        self.ovh = rd("communication_overhead_ratio.csv")
        self.pvf = rd("pilot_vs_final.csv")
        self.tele_run = rd("s4_teleports_by_run.csv")
        self.n10 = rd("n10_variability.csv")
        self.analysis = json.loads((A / "final_analysis.json").read_text(encoding="utf-8"))
        self.validation = json.loads((A / "analysis-validation.json").read_text(encoding="utf-8"))
        self.analysis_md = (A / "final_analysis.md").read_text(encoding="utf-8")
        fm = pq.read_table(A / "final_metrics.parquet").to_pylist()
        self.fm = fm
        # (experimento, cenário, controlador, perda, métrica) -> {seed: valor}
        self.vals: dict[tuple, dict[int, float]] = defaultdict(dict)
        self.runs: dict[tuple, dict] = {}
        for r in fm:
            self.vals[(r["experiment"], r["scenario"], r["controller"], float(r["packet_loss"]), r["metric"])][int(r["seed"])] = r["value"]
            self.runs[(r["experiment"], r["scenario"], r["controller"], float(r["packet_loss"]), int(r["seed"]))] = {
                "run_id": r["run_id"], "run_path": r["run_path"]}
        self.rr_runs = pq.read_table(A / "reference_route_results.parquet").to_pylist()
        self.rr_vals: dict[tuple, dict[int, float]] = defaultdict(dict)
        for r in self.rr_runs:
            if r["value"] is not None:
                self.rr_vals[(r["scenario"], r["controller"], r["metric"])][int(r["seed"])] = r["value"]

    # valores por seed do experimento principal
    def seeds_vals(self, scenario: str, controller: str, metric: str) -> dict[int, float]:
        return self.vals[("FINAL_MAIN", scenario, controller, 0.0, metric)]

    def s5_vals(self, controller: str, loss: float, metric: str) -> dict[int, float]:
        return self.vals[("FINAL_S5", "S2_DIRECTIONAL_PEAK", controller, loss if controller != B2 else 0.0, metric)]

    def d(self, scenario: str, controller: str, metric: str, key: str = "mean") -> float:
        return float(next(r for r in self.desc if r["scenario"] == scenario and r["controller"] == controller and r["metric"] == metric)[key])

    def pair(self, scenario: str, base: str, treat: str, metric: str) -> dict[str, str]:
        return next(r for r in self.pw if r["scenario"] == scenario and r["baseline"] == base and r["treatment"] == treat and r["metric"] == metric)

    def klass(self, scenario: str, base: str, treat: str) -> str:
        return next(r["classification"] for r in self.cls if r["scenario"] == scenario and r["baseline"] == base and r["treatment"] == treat)

    def rr_pair(self, scenario: str, base: str, treat: str, metric: str) -> dict[str, str]:
        return next(r for r in self.rr_pw if r["scenario"] == scenario and r["baseline"] == base and r["treatment"] == treat and r["metric"] == metric)

    def rr_mean(self, scenario: str, controller: str, metric: str, key: str = "mean") -> float:
        return float(next(r for r in self.rr_sum if r["scenario"] == scenario and r["controller"] == controller and r["metric"] == metric)[key])

    def s5d(self, controller: str, loss: float | None, metric: str, key: str = "mean") -> float:
        label = f"{B2}@REF" if controller == B2 else f"{controller}@{loss:.2f}"
        return float(next(r for r in self.s5_desc if r["controller"] == label and r["metric"] == metric)[key])


# ----------------------------------------------------------------------------------------------
# Registro de exportação
# ----------------------------------------------------------------------------------------------
MANIFEST: list[dict[str, Any]] = []


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def finish(fig, fid: str, folder: str, title: str, caption: str, sources: list[str], scenarios: list[str],
           controllers: list[str], metrics: list[str], n: str, rows: list[dict[str, Any]], *,
           method: str = METHOD, final_only: bool = True, tight: bool = True, pad: float = 1.0) -> dict[str, Any]:
    out = ROOT / folder
    out.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.tight_layout(pad=pad)
    files = {}
    for ext in ("png", "svg", "pdf"):
        p = out / f"{fid}.{ext}"
        fig.savefig(p, dpi=200 if ext == "png" else None, bbox_inches="tight", pad_inches=0.15)
        files[ext] = p.relative_to(ROOT).as_posix()
    src_csv = out / f"{fid}_source.csv"
    write_csv(src_csv, rows)
    files["source_csv"] = src_csv.relative_to(ROOT).as_posix()
    meta = {
        "figure_id": fid, "kind": "figure", "title": title, "caption": caption, "source_artifacts": sources,
        "scenario": scenarios, "controllers": controllers, "metrics": metrics, "N": n,
        "statistical_method": method, "final_only": final_only,
        "scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": FREEZE_SHA,
        "scientific_tree_sha256": TREE_SHA, "generation": GEN_VERSION, "files": files,
        "source_rows": len(rows),
    }
    meta_p = out / f"{fid}.json"
    meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta["files"]["metadata_json"] = meta_p.relative_to(ROOT).as_posix()
    MANIFEST.append(meta)
    plt.close(fig)
    return meta


def footnote(fig, text: str, y: float = 0.005) -> None:
    fig.text(0.01, y, text, fontsize=8.3, color=MUTED, ha="left", va="bottom", wrap=True)


def legend_controllers(ax_or_fig, controllers: list[str], **kw) -> None:
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker=CT_MARKER[c], color=CT_COLOR[c], lw=0, markersize=8, markeredgecolor=INK,
                      markeredgewidth=0.6, label=CT_LABEL[c]) for c in controllers]
    ax_or_fig.legend(handles=handles, **kw)


def jitter(i: int, n: int, w: float = 0.18) -> float:
    return (i - (n - 1) / 2) / max(n - 1, 1) * w * 2


def mean_sd(vals: list[float]) -> tuple[float, float]:
    return statistics.fmean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)


def ensure_dirs() -> None:
    for f in FOLDERS:
        (ROOT / f).mkdir(parents=True, exist_ok=True)


def copy_to(subset: str, files: list[str]) -> None:
    dst = ROOT / subset
    dst.mkdir(parents=True, exist_ok=True)
    for rel in files:
        shutil.copy2(ROOT / rel, dst / Path(rel).name)
