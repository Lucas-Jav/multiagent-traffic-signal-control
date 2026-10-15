"""Definitive TCC figure/table package (Prompt 64). Reads only artifacts/final-analysis/ (FINAL N=10).

    python scripts/build_tcc_figures.py

Writes artifacts/tcc-visuals/final/. Runs no simulation; every plotted number is loaded programmatically.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_figures_common as C  # noqa: E402
from tcc_figures_common import (  # noqa: E402
    B0, B1, B2, C1, C2, CT_COLOR, CT_HATCH, CT_LABEL, CT_MARKER, CT_SHORT, CTRLS, INK, METRIC_PT, MUTED,
    SC_NAME, SC_SHORT, SCENARIOS, comma, comma_axis, finish, footnote, legend_controllers, mean_sd, pct, thousands,
)

C.style()
D = C.Data()
C.ensure_dirs()
ROOT = C.ROOT
SRC_MAIN = ["artifacts/final-analysis/final_metrics.parquet", "artifacts/final-analysis/final_controller_summary.csv"]
SRC_PW = ["artifacts/final-analysis/final_pairwise_summary.csv", "artifacts/final-analysis/final_pairwise_analysis.parquet"]
SRC_RR = ["artifacts/final-analysis/reference_route_results.parquet", "artifacts/final-analysis/reference_route_pairwise.csv",
          "artifacts/final-analysis/reference_route_summary.csv"]
SRC_S5 = ["artifacts/final-analysis/s5_results.parquet", "artifacts/final-analysis/s5_pairwise.csv",
          "artifacts/final-analysis/s5_communication_summary.csv", "artifacts/final-analysis/s5_controller_summary.csv"]
FOUR = ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles"]
KEEP: dict[str, str] = {}  # figure id -> png path (relative to ROOT), for subsets
SHORT_TITLE = {"throughput": "Vazão", "completion_ratio_offered": "Conclusão (oferecidos)", "mean_waiting_time": "Espera média",
               "mean_network_queue_vehicles": "Fila média da rede", "max_network_queue_vehicles": "Fila máxima da rede"}
COND_NOTE = ("Espera, perda de tempo e tempo de viagem são condicionais às viagens concluídas; "
             "leia-os junto da conclusão e da razão de partida.")


def spath(rel: str) -> str:
    return rel


# =============================================================================================
# helpers
# =============================================================================================
def seed_dots(ax, x: float, vals: list[float], color: str, marker: str, rows: list[dict], meta: dict, *, size: float = 18) -> None:
    n = len(vals)
    for i, v in enumerate(sorted(vals)):
        ax.scatter(x + C.jitter(i, n, 0.16), v, s=size, color=color, alpha=0.35, marker=marker, linewidths=0, zorder=2)
    m, sd = mean_sd(vals)
    ax.errorbar(x, m, yerr=sd, color=INK, capsize=3, lw=1.1, zorder=3)
    ax.scatter(x, m, s=70, color=color, marker=marker, edgecolor=INK, linewidth=0.9, zorder=4)
    rows.append({**meta, "N": n, "mean": m, "sd": sd, "min": min(vals), "max": max(vals)})


def forest(fid, folder, title, subtitle, pairs, metrics, base, treat, *, treat_label, base_label, caption, sources,
           figsize=(10.5, 4.6), scenarios=SCENARIOS, extra_note=""):
    n = len(metrics)
    fig, axes = plt.subplots(1, n, figsize=figsize, sharey=True)
    axes = np.atleast_1d(axes)
    rows = []
    color = CT_COLOR[treat]
    for ax, m in zip(axes, metrics, strict=True):
        pts = []
        for i, s in enumerate(scenarios):
            r = D.pair(s, base, treat, m)
            rel, lo, hi = float(r["relative_difference_of_means"]) * 100, float(r["ci95_relative_low"]) * 100, float(r["ci95_relative_high"]) * 100
            sig = lo > 0 or hi < 0
            y = len(scenarios) - 1 - i
            ax.plot([lo, hi], [y, y], color=INK, lw=1.6, zorder=3)
            ax.scatter(rel, y, s=75, marker=CT_MARKER[treat], facecolor=color if sig else "white", edgecolor=color if sig else INK,
                       linewidth=1.6, zorder=4)
            pts.append((max(hi, rel), y, comma(rel, 1, True) + "%"))
            rows.append({"scenario": s, "metric": m, "baseline": base, "treatment": treat, "n_pairs": int(r["n_pairs"]),
                         "relative_difference_pct": rel, "ci95_relative_low_pct": lo, "ci95_relative_high_pct": hi,
                         "mean_difference": float(r["mean_difference"]), "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"]),
                         "baseline_mean": float(r["baseline_mean"]), "treatment_mean": float(r["treatment_mean"]),
                         "ci_excludes_zero": sig, "seeds_treatment_favourable": r["seeds_treatment_favourable"], "effect": r["effect"],
                         "classification_scenario_pair": D.klass(s, base, treat)})
        ax.axvline(0, color=MUTED, lw=1, ls="-")
        ax.set_title(SHORT_TITLE.get(m, METRIC_PT[m]), fontsize=10.2)
        ax.set_yticks(range(len(scenarios)))
        ax.set_yticklabels([SC_NAME[s] for s in scenarios][::-1])
        ax.set_xlabel(f"Δ relativo: {CT_SHORT[treat]} vs {CT_SHORT[base]} (%)")
        lo_x, hi_x = ax.get_xlim()
        ax.set_xlim(lo_x, hi_x + (hi_x - lo_x) * 0.30)
        span = ax.get_xlim()[1] - ax.get_xlim()[0]
        for px, py, ptxt in pts:
            ax.text(px + span * 0.045, py, ptxt, va="center", fontsize=9, color=INK)
        comma_axis(ax, "x", 0)
        ax.grid(axis="y", visible=False)
    fig.suptitle(title, fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.02)
    fig.text(0.01, 0.955, subtitle, fontsize=9.6, color=MUTED, ha="left")
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker=CT_MARKER[treat], color="w", markerfacecolor=color, markeredgecolor=color, markersize=9,
                      label="IC95% exclui 0 (marcador cheio)"),
               Line2D([0], [0], marker=CT_MARKER[treat], color="w", markerfacecolor="white", markeredgecolor=INK, markersize=9,
                      label="IC95% inclui 0 (marcador vazio)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.07))
    footnote(fig, f"Diferença = {treat_label} − {base_label}, pareada por seed (N = 10). Barra = IC95% bootstrap pareado. "
                  f"Sentido favorável depende da métrica (vazão/conclusão: maior é melhor; espera/fila: menor é melhor). {extra_note}", y=-0.13)
    return finish(fig, fid, folder, title, caption, sources, list(scenarios), [base, treat], metrics, "10 seeds por controlador/cenário (10 pares)", rows,
                  tight=True)


# =============================================================================================
# FIG01 overview
# =============================================================================================
def fig01():
    nmain = len({k[4] if False else v["run_id"] for k, v in D.runs.items() if k[0] == "FINAL_MAIN"})
    ns5 = len({v["run_id"] for k, v in D.runs.items() if k[0] == "FINAL_S5"})
    nseeds = len({k[4] for k in D.runs})
    c1_s5 = len({k for k in D.runs if k[0] == "FINAL_S5" and k[2] == C1})
    c2_s5 = len({k for k in D.runs if k[0] == "FINAL_S5" and k[2] == C2})
    b2_s5 = len({k for k in D.runs if k[0] == "FINAL_S5" and k[2] == B2})
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 66)
    ax.axis("off")
    ax.grid(False)

    def box(x, y, w, h, text, fc="#f4f6f7", ec=MUTED, fs=9.6, bold=False, color=INK, hatch=None):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", fc=fc, ec=ec, lw=1.1, hatch=hatch)
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", color=color)

    ax.text(1, 64.5, "Estrutura do experimento final", fontsize=14, fontweight="bold", va="top")
    ax.text(1, 61.3, f"Simulação SUMO · rede 3×3 · {nseeds} seeds por condição · {nmain + ns5} execuções científicas finais", fontsize=10, color=MUTED, va="top")
    # network 3x3
    for r in range(3):
        for c in range(3):
            x0, y0 = 4 + c * 9, 38 - r * 9 + 4
            ax.add_patch(Rectangle((x0, y0), 5, 5, fc="#dfe6eb", ec=MUTED, lw=1))
            ax.text(x0 + 2.5, y0 + 2.5, f"A{r * 3 + c + 1}", ha="center", va="center", fontsize=8.5)
    for r in range(3):
        ax.plot([2, 32], [38 - r * 9 + 6.5] * 2, color=MUTED, lw=0.8, zorder=0)
        ax.plot([6.5 + r * 9] * 2, [22.5, 53], color=MUTED, lw=0.8, zorder=0)
    ax.text(17, 20.6, "Rede 3×3 (9 interseções, um agente cada)", ha="center", fontsize=9.3)
    # controllers
    ax.text(40, 57, "5 controladores", fontsize=10.5, fontweight="bold")
    for i, c in enumerate(CTRLS):
        y = 52 - i * 4.6
        ax.add_patch(FancyBboxPatch((40, y), 22, 3.6, boxstyle="round,pad=0.2,rounding_size=0.6", fc="white", ec=CT_COLOR[c], lw=2.2))
        ax.scatter([42], [y + 1.8], marker=CT_MARKER[c], s=55, color=CT_COLOR[c], edgecolor=INK, linewidth=0.6, zorder=5)
        ax.text(43.6, y + 1.8, CT_LABEL[c], va="center", fontsize=8.8)
    # scenarios
    ax.text(68, 57, "Cenários de tráfego (S1–S4)", fontsize=10.5, fontweight="bold")
    descr = {"S1_BALANCED": "demanda balanceada", "S2_DIRECTIONAL_PEAK": "pico oeste→leste", "S3_DEMAND_SHIFT": "choque de demanda em 2100 s",
             "S4_LOCAL_SATURATION": "saturação localizada em A5"}
    for i, s in enumerate(SCENARIOS):
        box(68, 52 - i * 4.6, 30, 3.6, f"{SC_SHORT[s]} · {descr[s]}", fs=8.8)
    # main matrix
    box(40, 22.5, 58, 9, f"Experimento principal\n4 cenários × 5 controladores × {nseeds} seeds = {nmain} execuções\n"
                          "(pareamento por cenário + seed)", fc="#eef3fa", ec=CT_COLOR[B0], fs=9.2, bold=False)
    # S5
    ax.plot([2, 98], [19.2, 19.2], color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(2, 17.4, "Experimento de comunicação (S5) — NÃO é um novo padrão de demanda: usa o tráfego do S2", fontsize=10.5, fontweight="bold", va="center")
    box(2, 5, 30, 9, f"C1 · perda 0/20/50/100%\n4 níveis × {nseeds} seeds = {c1_s5 // 1} execuções", fc="#f2effb", ec=CT_COLOR[C1], fs=9.2)
    box(35, 5, 30, 9, f"C2 · perda 0/20/50/100%\n4 níveis × {nseeds} seeds = {c2_s5 // 1} execuções", fc="#fdeff5", ec=CT_COLOR[C2], fs=9.2)
    box(68, 5, 30, 9, f"B2 · referência sem comunicação\n1 por seed = {b2_s5} execuções", fc="#eaf7f1", ec=CT_COLOR[B2], fs=9.2)
    ax.text(50, 1.2, f"Total: {nmain} (principal) + {ns5} (S5) = {nmain + ns5} execuções finais", ha="center", fontsize=11, fontweight="bold")
    rows = [{"item": "main_runs", "value": nmain}, {"item": "s5_runs", "value": ns5}, {"item": "total_runs", "value": nmain + ns5},
            {"item": "seeds", "value": nseeds}, {"item": "controllers", "value": len(CTRLS)}, {"item": "main_scenarios", "value": len(SCENARIOS)},
            {"item": "s5_c1_runs", "value": c1_s5}, {"item": "s5_c2_runs", "value": c2_s5}, {"item": "s5_b2_runs", "value": b2_s5}]
    m = finish(fig, "FIG01_FINAL_OVERVIEW", "01_overview", "Estrutura do experimento final",
               "Diagrama explicativo (não é gráfico de desempenho): rede 3×3, 5 controladores, 4 cenários, 10 seeds e o experimento S5 sobre o tráfego do S2.",
               ["artifacts/final-analysis/final_metrics.parquet"], SCENARIOS + ["S5 (tráfego S2)"], CTRLS, [], "290 execuções finais", rows,
               tight=False)
    KEEP["FIG01"] = m["files"]["png"]


# =============================================================================================
# FIG02 main overview
# =============================================================================================
def fig02():
    fig, axes = plt.subplots(4, 4, figsize=(10.5, 10.2))
    rows = []
    for ri, m in enumerate(FOUR):
        for ci, s in enumerate(SCENARIOS):
            ax = axes[ri, ci]
            for xi, c in enumerate(CTRLS):
                vals = list(D.seeds_vals(s, c, m).values())
                seed_dots(ax, xi, vals, CT_COLOR[c], CT_MARKER[c], rows, {"scenario": s, "controller": c, "metric": m})
            ax.set_xticks(range(5))
            ax.set_xticklabels([CT_SHORT[c] for c in CTRLS], fontsize=8.8)
            ax.set_xlim(-0.6, 4.6)
            comma_axis(ax, "y", 3 if "ratio" in m else None)
            if ri == 0:
                ax.set_title(SC_NAME[s], fontsize=10.2)
            if ci == 0:
                ax.set_ylabel(METRIC_PT[m], fontsize=9.3)
            ax.grid(axis="x", visible=False)
    legend_controllers(fig, CTRLS, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.04), fontsize=8.8)
    fig.suptitle("Visão geral dos controladores por cenário (médias finais, N = 10 seeds)", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.0)
    footnote(fig, "Marcador grande = média; barra = ± 1 desvio-padrão entre seeds (descritivo); pontos claros = as 10 seeds (nenhuma removida). "
                  "Cada painel tem escala própria. " + COND_NOTE, y=-0.09)
    m = finish(fig, "FIG02_MAIN_CONTROLLER_OVERVIEW", "01_overview", "Visão geral dos controladores por cenário",
               "Médias finais por controlador e cenário para vazão, conclusão, espera e fila média da rede; N = 10 seeds.",
               SRC_MAIN, SCENARIOS, CTRLS, FOUR, "10 seeds por controlador/cenário", rows, method="Média ± desvio-padrão descritivos entre as 10 seeds",
               pad=0.8)
    KEEP["FIG02"] = m["files"]["png"]


# =============================================================================================
# FIG03/FIG04 forest figures, FIG05 matrix
# =============================================================================================
def fig03():
    m = forest("FIG03_B0_VS_B2", "02_adaptation", "Efeito da adaptação local em relação ao tempo fixo calibrado",
               "B0 (tempo fixo calibrado) → B2 (pressão local), por cenário · diferença relativa pareada com IC95%", None, FOUR, B0, B2,
               treat_label="B2", base_label="B0",
               caption="Diferenças relativas pareadas (B2 − B0)/B0 por cenário. Em S1 o B2 reduz espera e fila; em S2, S3 e S4 o tempo fixo calibrado (B0) é melhor "
                       "na maior parte das métricas-chave.", sources=SRC_PW)
    KEEP["FIG03"] = m["files"]["png"]


def fig04():
    m = forest("FIG04_B2_VS_C1", "03_cooperation", "Efeito da cooperação em relação ao adaptativo de pressão local",
               "B2 (pressão local) → C1 (cooperativo compacto), por cenário · diferença relativa pareada com IC95%", None, FOUR, B2, C1,
               treat_label="C1", base_label="B2",
               caption="Comparação primária B2 vs C1. S1 e S3: B2 favorecido; S2: trade-off (menos espera/fila, menor vazão/conclusão); S4: C1 favorecido nas "
                       "métricas principais de congestionamento.", sources=SRC_PW, extra_note=COND_NOTE)
    KEEP["FIG04"] = m["files"]["png"]


def label_for(cls_label: str, base: str, treat: str) -> str:
    if cls_label == "TRADE_OFF":
        return "Trade-off"
    if cls_label == "NO_CLEAR_DIFFERENCE":
        return "Sem diferença clara"
    if cls_label.startswith(treat):
        return f"{CT_SHORT[treat]} favorecido"
    if cls_label.startswith(base):
        return f"{CT_SHORT[base]} favorecido"
    return cls_label


def effect_text(r: dict, base: str, treat: str) -> str:
    e = r["effect"]
    if e == "TREATMENT_BETTER":
        return f"{CT_SHORT[treat]} favorecido"
    if e == "BASELINE_BETTER":
        return f"{CT_SHORT[base]} favorecido"
    return "Sem diferença clara"


def fig05():
    cols = ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles"]
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.grid(False)
    heads = ["Cenário", "Vazão", "Conclusão", "Espera", "Fila média", "Interpretação geral"]
    xs = [0, 1.55, 3.0, 4.45, 5.9, 7.3]
    ws = [1.5, 1.4, 1.4, 1.4, 1.35, 2.65]
    for x, w, h in zip(xs, ws, heads, strict=True):
        ax.add_patch(Rectangle((x, 4.65), w, 0.7, fc="#37474f", ec="white"))
        ax.text(x + w / 2, 5.0, h, ha="center", va="center", color="white", fontsize=9.6, fontweight="bold")
    tint = {f"{CT_SHORT[B2]} favorecido": "#d6f0e6", f"{CT_SHORT[C1]} favorecido": "#e1ddf6", "Sem diferença clara": "#f1f3f4"}
    rows = []
    for i, s in enumerate(SCENARIOS):
        y = 3.75 - i * 1.05
        ax.add_patch(Rectangle((xs[0], y), ws[0], 0.95, fc="#eceff1", ec="white"))
        ax.text(xs[0] + 0.08, y + 0.47, SC_NAME[s].replace(" — ", "\n").replace("Mudança de demanda", "Mudança de\ndemanda").replace("Saturação localizada", "Saturação\nlocalizada"), va="center", fontsize=9, fontweight="bold")
        for j, m in enumerate(cols):
            r = D.pair(s, B2, C1, m)
            t = effect_text(r, B2, C1)
            ax.add_patch(Rectangle((xs[j + 1], y), ws[j + 1], 0.95, fc=tint[t], ec="white"))
            ax.text(xs[j + 1] + ws[j + 1] / 2, y + 0.62, t, ha="center", va="center", fontsize=9, fontweight="bold")
            ax.text(xs[j + 1] + ws[j + 1] / 2, y + 0.27, f"Δ {pct(float(r['relative_difference_of_means']))}", ha="center", va="center", fontsize=8.8, color=MUTED)
            rows.append({"scenario": s, "metric": m, "reading": t, "relative_difference": float(r["relative_difference_of_means"]),
                         "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"]), "effect": r["effect"]})
        cl = D.klass(s, B2, C1)
        lab = label_for(cl, B2, C1)
        ax.add_patch(Rectangle((xs[5], y), ws[5], 0.95, fc="#fff8e1" if lab == "Trade-off" else tint.get(lab, "#f1f3f4"), ec="white"))
        ax.text(xs[5] + ws[5] / 2, y + 0.47, lab, ha="center", va="center", fontsize=10.5, fontweight="bold")
        rows.append({"scenario": s, "metric": "OVERALL", "reading": lab, "classification": cl})
    ax.set_title("Matriz de resultados da cooperação (B2 vs C1)", loc="left", fontsize=13, fontweight="bold", pad=10)
    footnote(fig, "Leitura por métrica: IC95% pareado exclui 0 ⇒ lado favorecido; caso contrário, sem diferença clara. Interpretação geral: regra fixada antes dos "
                  "resultados (métricas de serviço × atraso/fila); tempo de viagem não entra por ser condicional. Δ = (C1 − B2)/B2.", y=-0.01)
    m = finish(fig, "FIG05_COOPERATION_RESULT_MATRIX", "03_cooperation", "Matriz de resultados da cooperação (B2 vs C1)",
               "Matriz cenário × métrica com o lado favorecido e a interpretação geral validada na análise final.", SRC_PW + ["artifacts/final-analysis/final_scenario_pair_classification.csv"],
               SCENARIOS, [B2, C1], cols, "10 pares por cenário", rows, tight=False)
    KEEP["FIG05"] = m["files"]["png"]


# =============================================================================================
# FIG06 S2 trade-off
# =============================================================================================
def paired_dots(fid, folder, title, subtitle, scenario, ctrls, metrics, caption, note, sources, *, pair_for=None, figsize=(10.5, 4.4), extra_rows=None):
    fig, axes = plt.subplots(1, len(metrics), figsize=figsize)
    axes = np.atleast_1d(axes)
    rows = []
    for ax, m in zip(axes, metrics, strict=True):
        for xi, c in enumerate(ctrls):
            seed_dots(ax, xi, list(D.seeds_vals(scenario, c, m).values()), CT_COLOR[c], CT_MARKER[c], rows, {"scenario": scenario, "controller": c, "metric": m})
        ax.set_xticks(range(len(ctrls)))
        ax.set_xticklabels([CT_SHORT[c] for c in ctrls])
        ax.set_xlim(-0.6, len(ctrls) - 0.4)
        ax.set_title(METRIC_PT[m], fontsize=10.2)
        comma_axis(ax, "y", 3 if "ratio" in m else None)
        ax.grid(axis="x", visible=False)
        if pair_for:
            r = D.pair(scenario, pair_for[0], pair_for[1], m)
            lo, hi = float(r["ci95_relative_low"]), float(r["ci95_relative_high"])
            ax.text(0.5, 0.97, f"Δ {pct(float(r['relative_difference_of_means']))}\nIC95% [{pct(lo, 1, True)}; {pct(hi, 1, True)}]", transform=ax.transAxes,
                    ha="center", va="top", fontsize=9, color=INK, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C.GRID))
            rows.append({"scenario": scenario, "metric": m, "comparison": f"{pair_for[0]}->{pair_for[1]}", "relative_difference": float(r["relative_difference_of_means"]),
                         "ci95_relative_low": lo, "ci95_relative_high": hi, "mean_difference": float(r["mean_difference"]), "ci95_low": float(r["ci95_low"]),
                         "ci95_high": float(r["ci95_high"]), "effect": r["effect"]})
    fig.suptitle(title, fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.03)
    fig.text(0.01, 0.925, subtitle, fontsize=9.6, color=MUTED, ha="left")
    footnote(fig, note, y=-0.14)
    return finish(fig, fid, folder, title, caption, sources, [scenario], list(ctrls), metrics, "10 seeds por controlador", rows, pad=0.9)


def fig06():
    s = "S2_DIRECTIONAL_PEAK"
    r_w, r_q = D.pair(s, B2, C1, "mean_waiting_time"), D.pair(s, B2, C1, "mean_network_queue_vehicles")
    r_t, r_c = D.pair(s, B2, C1, "throughput"), D.pair(s, B2, C1, "completion_ratio_offered")
    sub = (f"C1 vs B2: espera {pct(float(r_w['relative_difference_of_means']))}, fila {pct(float(r_q['relative_difference_of_means']))}; "
           f"vazão {pct(float(r_t['relative_difference_of_means']))}, conclusão {comma(float(r_c['mean_difference']) * 100, 1, True)} p.p.")
    m = paired_dots("FIG06_S2_TRADEOFF", "03_cooperation", "S2 — Trade-off entre métricas: menos fila, menor capacidade concluída", sub, s, [B2, C1], FOUR,
                    "No S2, o C1 reduz espera e fila em 10/10 seeds, mas reduz vazão e conclusão. Tempos menores não podem ser lidos sem a conclusão.",
                    "Marcador grande = média; barra = ± 1 DP entre seeds; pontos claros = 10 seeds. Δ = (C1 − B2)/B2 com IC95% bootstrap pareado. "
                    "Atrasos condicionais menores não indicam melhora isolada: menos veículos são inseridos e concluídos com o C1.", SRC_PW + SRC_MAIN, pair_for=(B2, C1))
    KEEP["FIG06"] = m["files"]["png"]


# =============================================================================================
# FIG07 / FIG08 S3
# =============================================================================================
def s3_timeseries():
    out = ROOT / "05_s3_shock"
    cache = out / "FIG07_S3_SHOCK_timeseries_source.parquet"
    rows = []
    for c in (B0, B2, C1):
        for seed in sorted(D.seeds_vals("S3_DEMAND_SHIFT", c, "throughput")):
            run = D.runs[("FINAL_MAIN", "S3_DEMAND_SHIFT", c, 0.0, seed)]
            p = C.REPO / run["run_path"] / "lane_telemetry.parquet"
            t = pq.read_table(C.Path(chr(92) * 2 + "?" + chr(92) + str(p.resolve())), columns=["step_index", "queue"])
            steps = t.column("step_index").to_numpy()
            q = t.column("queue").to_numpy().astype(np.int64)
            lanes = int(np.sum(steps == steps[0]))
            net = q.reshape(-1, lanes).sum(axis=1)
            st = steps[::lanes]
            win = (st >= 300) & (st < 3900)
            stored = D.seeds_vals("S3_DEMAND_SHIFT", c, "mean_network_queue_vehicles")[seed]
            assert abs(float(net[win].mean()) - stored) < 1e-6, (c, seed, net[win].mean(), stored)
            for s_, v in zip(st[win], net[win], strict=True):
                rows.append({"controller": c, "seed": seed, "step": int(s_), "time_s": int(s_) + 1, "network_total_queue": int(v), "run_id": run["run_id"]})
    pq.write_table(pa.Table.from_pylist(rows), cache)
    return rows


def fig07():
    rows = s3_timeseries()
    by: dict[tuple, list] = {}
    for r in rows:
        by.setdefault((r["controller"], r["step"]), []).append(r["network_total_queue"])
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    bin_w = 30
    ts_rows = []
    for c in (B0, B2, C1):
        steps = sorted({k[1] for k in by if k[0] == c})
        xs, ms, sds = [], [], []
        for b0_ in range(steps[0], steps[-1] + 1, bin_w):
            vals = []
            seed_means = []
            for st in range(b0_, min(b0_ + bin_w, steps[-1] + 1)):
                vals.append(by[(c, st)])
            per_seed = np.mean(np.array(vals), axis=0)
            xs.append(b0_ + bin_w / 2)
            ms.append(float(per_seed.mean()))
            sds.append(float(per_seed.std(ddof=1)))
            ts_rows.append({"controller": c, "time_s": b0_ + bin_w / 2, "mean_across_10_seeds": ms[-1], "sd_across_seeds": sds[-1], "n_seeds": int(per_seed.size)})
        xs, ms, sds = np.array(xs), np.array(ms), np.array(sds)
        ax.fill_between(xs, ms - sds, ms + sds, color=CT_COLOR[c], alpha=0.16, lw=0)
        ax.plot(xs, ms, color=CT_COLOR[c], lw=2.0, label=CT_LABEL[c], marker=CT_MARKER[c], markevery=8, markersize=6, markeredgecolor=INK, markeredgewidth=0.5)
    ax.axvline(2100, color=INK, ls="--", lw=1.3)
    top = ax.get_ylim()[1]
    ax.text(2110, top * 0.97, "Choque de demanda\n(t = 2100 s)", va="top", fontsize=9.6, fontweight="bold")
    ax.axvspan(300, 2100, color="#f3f5f6", zorder=0)
    bot = ax.get_ylim()[0]
    ax.text(1200, bot + (top - bot) * 0.03, "pré-choque", ha="center", fontsize=9, color=MUTED)
    ax.text(3000, bot + (top - bot) * 0.03, "pós-choque", ha="center", fontsize=9, color=MUTED)
    ax.set_xlim(300, 3900)
    ax.set_xlabel("Tempo de simulação (s) — janela de medição")
    ax.set_ylabel("Fila total da rede (veículos parados)")
    comma_axis(ax, "both")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93))
    ax.set_title("S3 — Fila da rede ao longo do tempo (pré-choque, choque e pós-choque)", loc="left", fontsize=13, fontweight="bold")
    footnote(fig, "Linha = média entre as 10 seeds em janelas de 30 s; faixa = ± 1 desvio-padrão entre seeds (descritivo). Fila = soma das filas das lanes de entrada "
                  "(definição congelada de network_total_queue, telemetria de lane). Nenhuma métrica nova de recuperação foi criada.", y=-0.07)
    m = finish(fig, "FIG07_S3_SHOCK", "05_s3_shock", "S3 — Fila da rede ao longo do tempo",
               "Série temporal da fila total da rede em S3 para B0, B2 e C1 (média e ± 1 DP entre 10 seeds); choque em 2100 s.",
               ["artifacts/experiments/final_main (lane_telemetry.parquet, leitura somente)", "artifacts/final-analysis/final_metrics.parquet"],
               ["S3_DEMAND_SHIFT"], [B0, B2, C1], ["network_total_queue"], "10 seeds por controlador", ts_rows,
               method="Agregação descritiva por janelas de 30 s; média e DP entre seeds; conferida contra mean_network_queue_vehicles congelada (diferença < 1e-6)")
    KEEP["FIG07"] = m["files"]["png"]


def fig08():
    s, met = "S3_DEMAND_SHIFT", "post_shock_queue_auc_vehicle_seconds"
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    rows = []
    for xi, c in enumerate((B0, B2, C1)):
        seed_dots(ax, xi, list(D.seeds_vals(s, c, met).values()), CT_COLOR[c], CT_MARKER[c], rows, {"scenario": s, "controller": c, "metric": met})
    ax.set_xticks(range(3))
    ax.set_xticklabels([CT_LABEL[c].replace(" — ", "\n") for c in (B0, B2, C1)])
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylabel(METRIC_PT[met])
    comma_axis(ax, "y")
    ax.grid(axis="x", visible=False)
    y_top = ax.get_ylim()[1]
    for (a, b, x0, x1) in ((B0, B2, 0, 1), (B2, C1, 1, 2)):
        r = D.pair(s, a, b, met)
        lo, hi = float(r["ci95_relative_low"]), float(r["ci95_relative_high"])
        ax.annotate("", xy=(x1, y_top * 0.97), xytext=(x0, y_top * 0.97), arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
        ax.text((x0 + x1) / 2, y_top * 0.975, f"{CT_SHORT[a]}→{CT_SHORT[b]}: {pct(float(r['relative_difference_of_means']))}\nIC95% [{pct(lo)}; {pct(hi)}]",
                ha="center", va="bottom", fontsize=9, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C.GRID))
        rows.append({"scenario": s, "metric": met, "comparison": f"{a}->{b}", "relative_difference": float(r["relative_difference_of_means"]),
                     "ci95_relative_low": lo, "ci95_relative_high": hi, "mean_difference": float(r["mean_difference"]),
                     "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"])})
    ax.set_ylim(top=y_top * 1.12)
    ax.set_title("S3 — Área da fila pós-choque (métrica congelada)", loc="left", fontsize=13, fontweight="bold")
    footnote(fig, "Marcador grande = média; barra = ± 1 DP entre seeds; pontos claros = 10 seeds. Δ e IC95% = diferença pareada por seed (bootstrap congelado). "
                  "Não é uma métrica nova: post_shock_queue_auc_vehicle_seconds da metodologia S3 congelada.", y=-0.06)
    m = finish(fig, "FIG08_S3_POST_SHOCK_AUC", "05_s3_shock", "S3 — Área da fila pós-choque",
               "post_shock_queue_auc_vehicle_seconds para B0, B2 e C1 (N = 10) com diferenças pareadas e IC95%.", SRC_PW + SRC_MAIN, [s], [B0, B2, C1], [met],
               "10 seeds por controlador", rows)
    KEEP["FIG08"] = m["files"]["png"]


# =============================================================================================
# FIG09 / FIG10 S4
# =============================================================================================
def fig09():
    s = "S4_LOCAL_SATURATION"
    mets = ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_time_loss", "mean_network_queue_vehicles",
            "max_network_queue_vehicles", "mean_depart_delay_seconds"]
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    rows = []
    for i, m in enumerate(mets):
        r = D.pair(s, B2, C1, m)
        rel, lo, hi = float(r["relative_difference_of_means"]) * 100, float(r["ci95_relative_low"]) * 100, float(r["ci95_relative_high"]) * 100
        y = len(mets) - 1 - i
        ax.plot([lo, hi], [y, y], color=INK, lw=1.8, zorder=3)
        ax.scatter(rel, y, s=90, marker=CT_MARKER[C1], color=CT_COLOR[C1], edgecolor=INK, linewidth=0.8, zorder=4)
        ax.text(max(hi, rel) + 1.0, y, f"{comma(rel, 1, True)}%   (favoráveis: {r['seeds_treatment_favourable']}/10 seeds)", va="center", fontsize=9.2)
        rows.append({"scenario": s, "metric": m, "relative_difference_pct": rel, "ci95_relative_low_pct": lo, "ci95_relative_high_pct": hi,
                     "baseline_mean": float(r["baseline_mean"]), "treatment_mean": float(r["treatment_mean"]), "mean_difference": float(r["mean_difference"]),
                     "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"]), "seeds_treatment_favourable": r["seeds_treatment_favourable"],
                     "effect": r["effect"]})
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(range(len(mets)))
    ax.set_yticklabels([METRIC_PT[m] for m in mets][::-1])
    ax.set_xlabel("Δ relativo: C1 vs B2 (%)")
    ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + 28)
    comma_axis(ax, "x", 0)
    ax.grid(axis="y", visible=False)
    ax.set_title("S4 — Efeito da cooperação sob saturação localizada (B2 → C1)", loc="left", fontsize=13, fontweight="bold")
    footnote(fig, "Δ = (C1 − B2)/B2, pareado por seed (N = 10); barra = IC95% bootstrap pareado. Vazão, conclusão, espera, perda de tempo e filas favorecem o C1; "
                  "o atraso de partida piorou com o C1 (trade-off). Saturação severa: só uma minoria das viagens oferecidas conclui — métricas de tempo são condicionais.", y=-0.04)
    m = finish(fig, "FIG09_S4_B2_VS_C1", "06_s4_saturation", "S4 — Efeito da cooperação sob saturação localizada",
               "Efeitos pareados B2 → C1 em S4 com IC95%: o benefício aparece nas métricas de congestionamento; o atraso de partida piora.",
               SRC_PW, [s], [B2, C1], mets, "10 pares", rows)
    KEEP["FIG09"] = m["files"]["png"]


def fig10():
    t = {c: [r for r in D.tele_run if r["controller"] == c] for c in CTRLS}
    rows = []
    for c in CTRLS:
        vals = [float(r["sumo_teleports_total"]) for r in t[c]]
        rows.append({"controller": c, "runs": len(vals), "runs_with_teleports": sum(1 for v in vals if v > 0), "total_teleports": sum(vals),
                     "max_in_a_run": max(vals), "seeds_with_teleports": ";".join(r["seed"] for r in t[c] if float(r["sumo_teleports_total"]) > 0)})
    tot = sum(r["total_teleports"] for r in rows)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.9), gridspec_kw={"width_ratios": [1.1, 1]})
    ys = range(len(CTRLS))[::-1]
    for y, r in zip(ys, rows, strict=True):
        c = r["controller"]
        ax.barh(y, r["total_teleports"], color=CT_COLOR[c], edgecolor=INK, linewidth=0.7, hatch=CT_HATCH[c] or None, height=0.62)
        ax.text(r["total_teleports"] + 0.5, y, f"{int(r['total_teleports'])}", va="center", fontsize=10, fontweight="bold")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([CT_LABEL[c] for c in CTRLS])
    ax.set_xlabel("Total de teleports em 10 runs de S4")
    ax.set_xlim(0, max(r["total_teleports"] for r in rows) * 1.18 + 1)
    comma_axis(ax, "x", 0)
    ax.grid(axis="y", visible=False)
    ax2.axis("off")
    ax2.grid(False)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.text(0, 0.97, "Controlador", fontsize=9.5, fontweight="bold", va="top")
    ax2.text(0.62, 0.97, "Runs afetadas", fontsize=9.5, fontweight="bold", va="top", ha="center")
    ax2.text(0.88, 0.97, "Total", fontsize=9.5, fontweight="bold", va="top", ha="center")
    for i, r in enumerate(rows):
        y = 0.82 - i * 0.14
        ax2.text(0, y, CT_SHORT[r["controller"]], fontsize=9.8, va="center")
        ax2.text(0.62, y, f"{r['runs_with_teleports']} de {r['runs']}", fontsize=9.8, va="center", ha="center")
        ax2.text(0.88, y, f"{int(r['total_teleports'])}", fontsize=9.8, va="center", ha="center")
    ax2.text(0, 0.1, f"Total em S4: {int(tot)} teleports · nenhum teleport em S1–S3", fontsize=9.6, fontweight="bold")
    fig.suptitle("Teleports do SUMO no cenário S4", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.03)
    footnote(fig, "Política congelada: ALLOW_AND_MEASURE — teleports foram medidos e mantidos nos resultados; nenhuma run foi removida. "
                  "Contexto de congestionamento, não critério de exclusão.", y=-0.1)
    m = finish(fig, "FIG10_S4_TELEPORTS", "06_s4_saturation", "Teleports do SUMO no cenário S4",
               "Contagem de teleports por controlador no S4 (política ALLOW_AND_MEASURE).", ["artifacts/final-analysis/s4_teleports_by_run.csv"],
               ["S4_LOCAL_SATURATION"], CTRLS, ["sumo_teleports_total"], "10 runs por controlador", rows, method="Contagem direta (sem inferência)")
    KEEP["FIG10"] = m["files"]["png"]
    return rows


# =============================================================================================
# FIG11–FIG13 reference route
# =============================================================================================
RR3 = [B0, B2, C1]
TT, CMP = "reference_route_mean_travel_time_seconds", "reference_route_completion_ratio_offered"


def fig11():
    fig, axes = plt.subplots(2, 4, figsize=(10.5, 6.4))
    rows = []
    for ci, s in enumerate(SCENARIOS):
        for ri, met in enumerate((TT, CMP)):
            ax = axes[ri, ci]
            for xi, c in enumerate(RR3):
                vals = list(D.rr_vals[(s, c, met)].values())
                seed_dots(ax, xi, vals, CT_COLOR[c], CT_MARKER[c], rows, {"scenario": s, "controller": c, "metric": met})
            ax.set_xticks(range(3))
            ax.set_xticklabels([CT_SHORT[c] for c in RR3])
            ax.set_xlim(-0.6, 2.6)
            comma_axis(ax, "y", 2 if ri == 1 else None)
            ax.grid(axis="x", visible=False)
            if ri == 0:
                ax.set_title(SC_NAME[s], fontsize=10.2)
            if ci == 0:
                ax.set_ylabel("Tempo de viagem médio\n(s) — só viagens concluídas" if ri == 0 else "Conclusão da coorte\n(fração dos oferecidos)", fontsize=9.3)
    legend_controllers(fig, RR3, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.055))
    fig.suptitle("Rota de referência (left1A1 → A1B1 → B1C1 → C1right1): tempo de viagem e conclusão", fontsize=12.6, fontweight="bold", x=0.01, ha="left", y=1.0)
    footnote(fig, "Coorte = veículos oferecidos cuja sequência de arestas planejada é exatamente a rota. Marcador grande = média; barra = ± 1 DP entre seeds; "
                  "pontos claros = 10 seeds. O tempo de viagem (linha de cima) só existe para viagens concluídas: leia-o junto da conclusão (linha de baixo).", y=-0.11)
    m = finish(fig, "FIG11_REFERENCE_ROUTE", "04_reference_route", "Rota de referência: tempo de viagem e conclusão",
               "Tempo de viagem médio e conclusão da coorte da rota exata para B0, B2 e C1 em S1–S4 (N = 10), sempre juntos.", SRC_RR, SCENARIOS, RR3,
               [TT, CMP], "10 seeds por controlador/cenário", rows, method="Média ± DP descritivos; coorte por sequência exata de arestas planejada", pad=0.8)
    KEEP["FIG11"] = m["files"]["png"]


def fig12():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.7))
    rows = []
    for ax, (a, b, ttl) in zip(axes, ((B0, B2, "Efeito da adaptação (B0 → B2)"), (B2, C1, "Efeito da cooperação (B2 → C1)")), strict=True):
        xmax = 0.0
        for i, s in enumerate(SCENARIOS):
            r, rc = D.rr_pair(s, a, b, TT), D.rr_pair(s, a, b, CMP)
            d, lo, hi = float(r["paired_mean_diff"]), float(r["ci95_low"]), float(r["ci95_high"])
            y = len(SCENARIOS) - 1 - i
            ax.plot([lo, hi], [y, y], color=INK, lw=1.7, zorder=3)
            ax.scatter(d, y, s=85, marker=CT_MARKER[b], color=CT_COLOR[b], edgecolor=INK, linewidth=0.8, zorder=4)
            xmax = max(xmax, abs(lo), abs(hi))
            ax.text(1.02, y, f"{comma(d, 1, True)} s\nconcl. {comma(float(rc['paired_mean_diff']) * 100, 1, True)} p.p.", transform=ax.get_yaxis_transform(),
                    va="center", fontsize=8.8)
            rows.append({"scenario": s, "comparison": f"{a}->{b}", "route_travel_time_diff_s": d, "ci95_low": lo, "ci95_high": hi, "n_seeds": int(r["n_seeds"]),
                         "completion_diff_pp": float(rc["paired_mean_diff"]) * 100, "completion_ci95_low": float(rc["ci95_low"]), "completion_ci95_high": float(rc["ci95_high"])})
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_yticks(range(len(SCENARIOS)))
        ax.set_yticklabels([SC_NAME[s] for s in SCENARIOS][::-1])
        ax.set_xlim(-xmax * 1.15, xmax * 1.15)
        ax.set_xlabel("Δ tempo de viagem da rota (s)")
        ax.set_title(ttl, fontsize=11)
        comma_axis(ax, "x", 0)
        ax.grid(axis="y", visible=False)
    axes[1].set_yticklabels([])
    fig.subplots_adjust(left=0.2, right=0.9, wspace=0.62, bottom=0.2, top=0.82)
    fig.suptitle("Rota de referência — efeitos pareados no tempo de viagem", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.02)
    footnote(fig, "Diferença pareada por seed (tratamento − baseline), N = 10; barra = IC95% bootstrap pareado (semente por rótulo). Painéis com escalas distintas e efeitos "
                  "NÃO combinados. À direita: variação da conclusão (p.p.) — tempos valem só para viagens concluídas.", y=-0.07)
    m = finish(fig, "FIG12_REFERENCE_ROUTE_EFFECTS", "04_reference_route", "Rota de referência — efeitos pareados",
               "Efeito da adaptação (B0→B2) e da cooperação (B2→C1) no tempo de viagem da rota, com IC95% e variação da conclusão.", SRC_RR,
               SCENARIOS, RR3, [TT, CMP], "10 pares por comparação", rows, tight=False)
    KEEP["FIG12"] = m["files"]["png"]


def fig13():
    s = "S3_DEMAND_SHIFT"
    n = next(r for r in D.nvr if r["scenario"] == s and r["comparison"] == f"{B2}->{C1}")
    net = D.pair(s, B2, C1, "mean_travel_time")
    rr_ = D.rr_pair(s, B2, C1, TT)
    rc = D.rr_pair(s, B2, C1, CMP)
    nc = D.pair(s, B2, C1, "completion_ratio_offered")
    n_net = D.d(s, B2, "offered_vehicle_count")
    n_route = float(next(r for r in D.rr_coh if r["scenario"] == s and r["controller"] == B2)["mean_reference_route_offered"])
    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    items = [("Rede inteira\n(todas as viagens)", float(net["mean_difference"]), float(net["ci95_low"]), float(net["ci95_high"]), float(nc["mean_difference"]) * 100,
              n_net, "B2 favorecido"),
             ("Rota de referência\n(coorte left1A1→…→C1right1)", float(rr_["paired_mean_diff"]), float(rr_["ci95_low"]), float(rr_["ci95_high"]),
              float(rc["paired_mean_diff"]) * 100, n_route, "C1 reduz o tempo de viagem")]
    rows = []
    for i, (lab, d, lo, hi, dc, nveh, txt) in enumerate(items):
        y = 1 - i
        ax.plot([lo, hi], [y, y], color=INK, lw=2, zorder=3)
        ax.scatter(d, y, s=110, marker=CT_MARKER[C1], color=CT_COLOR[C1], edgecolor=INK, linewidth=0.9, zorder=4)
        ax.text(d, y + 0.22, f"{comma(d, 1, True)} s  [{comma(lo, 1, True)}; {comma(hi, 1, True)}]", ha="center", fontsize=9.6)
        ax.text(1.01, y, f"{txt}\nconclusão {comma(dc, 1, True)} p.p.\n≈ {thousands(nveh)} veíc. oferecidos/run", transform=ax.get_yaxis_transform(), va="center", fontsize=8.8)
        rows.append({"population": lab.split("\n")[0], "metric": "travel_time_diff_C1_minus_B2_s", "mean_difference": d, "ci95_low": lo, "ci95_high": hi,
                     "completion_diff_pp": dc, "offered_vehicles_per_run_mean": nveh, "comparison": f"{B2}->{C1}", "scenario": s})
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks([1, 0])
    ax.set_yticklabels([i[0] for i in items])
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel("Δ tempo de viagem médio: C1 − B2 (s)")
    lim = max(abs(r["ci95_low"]) for r in rows + [{"ci95_low": 0}]) * 1.15
    lim = max(lim, max(abs(r["ci95_high"]) for r in rows) * 1.15) * 1.3
    ax.set_xlim(-lim, lim)
    comma_axis(ax, "x", 0)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(right=0.74)
    fig.suptitle("Escalas diferentes de análise no S3", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.04)
    footnote(fig, "Rede inteira e coorte da rota são populações diferentes; os resultados não são contraditórios automaticamente. Diferença pareada por seed (N = 10), "
                  "IC95% bootstrap pareado. Tempos de viagem são condicionais às viagens concluídas.", y=-0.1)
    m = finish(fig, "FIG13_S3_NETWORK_VS_ROUTE", "04_reference_route", "Escalas diferentes de análise no S3",
               "No S3, o B2 é favorecido na rede inteira e o C1 reduz o tempo de viagem da rota de referência: são populações diferentes.",
               SRC_PW + SRC_RR + ["artifacts/final-analysis/network_vs_reference_route_direction.csv"], [s], [B2, C1], ["mean_travel_time", TT],
               "10 pares", rows, tight=False)
    KEEP["FIG13"] = m["files"]["png"]
    return m


# =============================================================================================
# S5 figures
# =============================================================================================
LOSSES = [0.0, 0.2, 0.5, 1.0]


def s5_lines(ax, metric, rows, *, ratio=False):
    xs = [0, 20, 50, 100]
    b2m, b2s = D.s5d(B2, None, metric), D.s5d(B2, None, metric, "std")
    ax.axhline(b2m, color=CT_COLOR[B2], ls="--", lw=1.8)
    ax.axhspan(b2m - b2s, b2m + b2s, color=CT_COLOR[B2], alpha=0.12, lw=0)
    ax.text(-7, b2m, "B2 (referência)", va="bottom", ha="left", fontsize=8.8, color=INK)
    for c in (C1, C2):
        ms = [D.s5d(c, p, metric) for p in LOSSES]
        sds = [D.s5d(c, p, metric, "std") for p in LOSSES]
        off = -1.2 if c == C1 else 1.2
        for p, x in zip(LOSSES, xs, strict=True):
            vals = list(D.s5_vals(c, p, metric).values())
            ax.scatter([x + off] * len(vals), vals, s=14, color=CT_COLOR[c], alpha=0.28, marker=CT_MARKER[c], linewidths=0, zorder=2)
        ax.errorbar([x + off for x in xs], ms, yerr=sds, color=CT_COLOR[c], lw=2.0, capsize=3, marker=CT_MARKER[c], markersize=8, markeredgecolor=INK,
                    markeredgewidth=0.7, zorder=4)
        for p, x, mm, sd in zip(LOSSES, xs, ms, sds, strict=True):
            rows.append({"controller": c, "packet_loss": p, "metric": metric, "mean": mm, "sd": sd, "N": len(D.s5_vals(c, p, metric))})
    rows.append({"controller": B2, "packet_loss": "reference", "metric": metric, "mean": b2m, "sd": b2s, "N": len(D.s5_vals(B2, 0.0, metric))})
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{x}%" for x in xs])
    ax.text(104, ms[-1], "C1 = C2 = B2\n(0 mensagens\nentregues)", fontsize=8.6, va="center", ha="left", color=INK)
    ax.set_xlim(-8, 128)
    ax.set_xlabel("Perda de pacotes configurada")
    comma_axis(ax, "y", 3 if ratio else None)


def s5_fig(fid, title, caption, panels, size, sub=None, y_note=-0.06, note=""):
    fig, axes = plt.subplots(1, len(panels), figsize=size)
    axes = np.atleast_1d(axes)
    rows = []
    for ax, (metric, ratio) in zip(axes, panels, strict=True):
        s5_lines(ax, metric, rows, ratio=ratio)
        ax.set_title(METRIC_PT[metric], fontsize=10.8)
    legend_controllers(fig, [C1, C2], loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.1 if len(panels) == 1 else -0.06))
    fig.suptitle(title, fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.03)
    if sub:
        fig.text(0.01, 0.965, sub, fontsize=9.6, color=MUTED, ha="left")
    footnote(fig, "Tráfego-base S2; atraso de comunicação 0. Linha = média; barra = ± 1 DP entre as 10 seeds; pontos claros = seeds; B2 tracejado = referência sem "
                  "comunicação (10 seeds, não duplicada) com faixa ± 1 DP. " + note, y=(-0.18 if len(panels) == 1 else y_note - 0.06))
    return finish(fig, fid, "07_s5_communication", title, caption, SRC_S5, ["S2_DIRECTIONAL_PEAK (base do S5)"], [B2, C1, C2],
                  [p[0] for p in panels], "10 seeds por nível de perda (C1, C2) e 10 seeds de referência (B2)", rows,
                  method="Média ± DP descritivos entre seeds", pad=0.9)


def fig14():
    cl = D.s5d
    c1_20, c1_0 = cl(C1, 0.2, "throughput"), cl(C1, 0.0, "throughput")
    sub = (f"C1: 20% e 50% de perda aumentam a vazão em relação a 0%; C2: idem; com 100% de perda C1 e C2 igualam B2 "
           f"(C1 {thousands(c1_0)} → {thousands(c1_20)} com 20%)")
    m = s5_fig("FIG14_S5_PACKET_LOSS", "S5 — Vazão em função da perda de pacotes", "Vazão média de C1 e C2 por nível de perda, com B2 como referência; padrão não monotônico.",
               [("throughput", False)], (7.4, 4.9), sub=sub)
    KEEP["FIG14"] = m["files"]["png"]
    s5_fig("FIG14B_S5_COMPLETION", "S5 — Conclusão em função da perda de pacotes", "Fração dos veículos oferecidos concluída por C1 e C2 por nível de perda, com B2 como referência.",
           [("completion_ratio_offered", True)], (7.4, 4.9), sub="Mesmo padrão não monotônico observado na vazão")


def fig15():
    s5_fig("FIG15_S5_QUEUE_DELAY", "S5 — Fila da rede e espera em função da perda de pacotes",
           "Fila média da rede e espera média de C1 e C2 por nível de perda (painéis com escalas próprias), B2 como referência.",
           [("mean_network_queue_vehicles", False), ("mean_waiting_time", False)], (10.2, 4.9),
           sub="Escalas distintas por painel; espera é condicional às viagens concluídas", note=COND_NOTE)


# =============================================================================================
# FIG16/17 communication cost
# =============================================================================================
def comm_row(exp, scn, ctrl, loss):
    return next(r for r in D.comm if r["experiment"] == exp and r["scenario"] == scn and r["controller"] == ctrl and float(r["packet_loss"]) == loss)


def fig16():
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.3))
    rows = []
    for ax, (key, ttl, scale, d) in zip(axes, (("mean_messages_sent", "Mensagens enviadas por run", 1, 0), ("mean_bytes_sent", "Bytes enviados por run (MB)", 1e6, 1),
                                               ("mean_bytes_delivered", "Bytes entregues por run (MB)", 1e6, 1)), strict=True):
        w = 0.36
        for j, p in enumerate(LOSSES):
            for k, c in enumerate((C1, C2)):
                r = comm_row("FINAL_S5", "S2_DIRECTIONAL_PEAK", c, p)
                v = float(r[key]) / scale
                x = j + (k - 0.5) * w
                ax.bar(x, v, w * 0.92, color=CT_COLOR[c], edgecolor=INK, linewidth=0.6, hatch=CT_HATCH[c] or None, zorder=3)
                if p in (0.0,) or key == "mean_bytes_delivered":
                    ax.text(x, v, (thousands(v, 0) if d == 0 else comma(v, 1)), ha="center", va="bottom", fontsize=7.6, rotation=90 if key == "mean_messages_sent" else 0)
                rows.append({"controller": c, "packet_loss": p, "metric": key, "value_per_run": float(r[key]), "N": int(r["N"])})
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"{int(p * 100)}%" for p in LOSSES])
        ax.set_xlabel("Perda de pacotes")
        ax.set_title(ttl, fontsize=10.2)
        comma_axis(ax, "y", None)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(top=ax.get_ylim()[1] * 1.12)
    legend_controllers(fig, [C1, C2], loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.075))
    ratio = float(next(r for r in D.ovh if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 0.0)["C2_over_C1_bytes_sent"])
    fig.suptitle(f"Custo de comunicação: C1 vs C2 (mesmas mensagens; C2 ≈ {comma(ratio, 1)}× os bytes)", fontsize=12.8, fontweight="bold", x=0.01, ha="left", y=1.03)
    footnote(fig, "Médias por run (N = 10 seeds por nível; S2). Mesmo número de mensagens enviadas; a mensagem expandida do C2 é maior. "
                  "Com 100% de perda, nenhum byte é entregue.", y=-0.15)
    m = finish(fig, "FIG16_COMMUNICATION_COST", "08_communication_cost", "Custo de comunicação: C1 vs C2",
               "Mensagens enviadas, bytes enviados e bytes entregues por run para C1 e C2 em cada nível de perda (S2).", SRC_S5 + ["artifacts/final-analysis/communication_overhead_ratio.csv"],
               ["S2_DIRECTIONAL_PEAK"], [C1, C2], ["messages_sent", "bytes_sent", "bytes_delivered"], "10 seeds por nível", rows, method="Médias por run (contagem)")
    KEEP["FIG16"] = m["files"]["png"]


def fig17():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
    rows = []
    for ax, (m, ttl) in zip(axes, (("throughput", "Vazão"), ("mean_waiting_time", "Espera média"))):
        pts17 = []
        for i, s in enumerate(SCENARIOS):
            r = D.pair(s, C1, C2, m)
            rel, lo, hi = float(r["relative_difference_of_means"]) * 100, float(r["ci95_relative_low"]) * 100, float(r["ci95_relative_high"]) * 100
            y = len(SCENARIOS) - 1 - i
            ax.plot([lo, hi], [y, y], color=INK, lw=1.7, zorder=3)
            ax.scatter(rel, y, s=85, marker=CT_MARKER[C2], color=CT_COLOR[C2], edgecolor=INK, linewidth=0.8, zorder=4)
            pts17.append((max(hi, rel), y, comma(rel, 1, True) + "%"))
            ov = next(x for x in D.ovh if x["experiment"] == "FINAL_MAIN" and x["scenario"] == s)
            rows.append({"scenario": s, "metric": m, "relative_difference_pct": rel, "ci95_relative_low_pct": lo, "ci95_relative_high_pct": hi, "mean_difference": float(r["mean_difference"]),
                         "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"]), "C2_over_C1_bytes_sent": float(ov["C2_over_C1_bytes_sent"]),
                         "C2_extra_MB_per_run": (float(ov["C2_mean_bytes_sent"]) - float(ov["C1_mean_bytes_sent"])) / 1e6})
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_yticks(range(len(SCENARIOS)))
        ax.set_yticklabels([SC_NAME[s] for s in SCENARIOS][::-1])
        ax.set_xlabel(f"Δ relativo de {ttl.lower()}: C2 vs C1 (%)")
        ax.set_title(ttl + (" (maior é melhor)" if m == "throughput" else " (menor é melhor)"), fontsize=10.8)
        ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.25)
        span17 = ax.get_xlim()[1] - ax.get_xlim()[0]
        for px, py, ptxt in pts17:
            ax.text(px + span17 * 0.05, py, ptxt, va="center", fontsize=9)
        comma_axis(ax, "x", 0)
        ax.grid(axis="y", visible=False)
    extra = [r["C2_extra_MB_per_run"] for r in rows if r["metric"] == "throughput"]
    ratio = statistics.fmean(r["C2_over_C1_bytes_sent"] for r in rows if r["metric"] == "throughput")
    fig.suptitle(f"Desempenho vs custo de comunicação (C2 vs C1): C2 envia ≈ {comma(ratio, 1)}× os bytes (+{comma(statistics.fmean(extra), 0)} MB/run)", fontsize=12.6,
                 fontweight="bold", x=0.01, ha="left", y=1.03)
    footnote(fig, "Diferença pareada por seed (C2 − C1)/C1, N = 10, IC95% bootstrap pareado; o custo de comunicação é o mesmo em todos os pontos (≈ 2,3× bytes). "
                  "Não é uma otimização econômica. Leitura: a comunicação adicional do C2 não trouxe benefício geral de tráfego. " + COND_NOTE, y=-0.1)
    m = finish(fig, "FIG17_PERFORMANCE_VS_COMMUNICATION_COST", "08_communication_cost", "Desempenho vs custo de comunicação (C2 vs C1)",
               "Efeito de C2 vs C1 em vazão e espera por cenário, junto do custo adicional de comunicação (≈ 2,3× bytes).", SRC_PW + ["artifacts/final-analysis/communication_overhead_ratio.csv"],
               SCENARIOS, [C1, C2], ["throughput", "mean_waiting_time", "bytes_sent"], "10 pares por cenário", rows, tight=True)
    KEEP["FIG17"] = m["files"]["png"]


# =============================================================================================
# FIG18 pilot vs final
# =============================================================================================
def fig18():
    mets = ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles"]
    fig, axes = plt.subplots(1, 4, figsize=(10.8, 5.1), sharey=True)
    rows = []
    for ax, m in zip(axes, mets, strict=True):
        for i, s in enumerate(SCENARIOS):
            r = next(x for x in D.pvf if x["scenario"] == s and x["metric"] == m)
            for k, (pre, lab, col, marker, fillc) in enumerate((("pilot", "Piloto V2 (N=5)", MUTED, "o", "white"), ("final", "Final (N=10)", CT_COLOR[C1], CT_MARKER[C1], CT_COLOR[C1]))):
                diff, lo, hi = float(r[f"{pre}_mean_diff_C1_minus_B2" if pre == "pilot" else "final_mean_diff_C1_minus_B2"]), float(r[f"{pre}_ci95_low"]), float(r[f"{pre}_ci95_high"])
                rel = float(r[f"{pre}_rel_diff"]) if r[f"{pre}_rel_diff"] not in ("", "None") else None
                base = diff / rel if rel not in (None, 0.0) else None
                if base is None:
                    continue
                y = (len(SCENARIOS) - 1 - i) + (0.17 if k == 0 else -0.17)
                ax.plot([lo / base * 100, hi / base * 100], [y, y], color=INK if k else MUTED, lw=1.6, zorder=3)
                ax.scatter(rel * 100, y, s=62, marker=marker, facecolor=fillc, edgecolor=col if k else MUTED, linewidth=1.5, zorder=4)
                rows.append({"scenario": s, "metric": m, "sample": lab, "n_seeds": 5 if pre == "pilot" else 10, "relative_difference_pct": rel * 100,
                             "ci95_relative_low_pct": lo / base * 100, "ci95_relative_high_pct": hi / base * 100, "mean_difference": diff, "ci95_low": lo, "ci95_high": hi,
                             "pilot_overlaps_first_5_final_seeds": True})
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(METRIC_PT[m].split(" (")[0], fontsize=10.2)
        ax.set_yticks([len(SCENARIOS) - 1 - i for i in range(4)])
        ax.set_yticklabels([SC_NAME[s] for s in SCENARIOS])
        ax.set_xlabel("Δ relativo C1 vs B2 (%)")
        comma_axis(ax, "x", 0)
        ax.grid(axis="y", visible=False)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor=MUTED, markersize=9, label="Piloto V2 — N = 5 (somente comparação metodológica)"),
                        Line2D([0], [0], marker=CT_MARKER[C1], color="w", markerfacecolor=CT_COLOR[C1], markeredgecolor=CT_COLOR[C1], markersize=9, label="Final — N = 10")],
               loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Piloto V2 (N = 5) vs Final (N = 10): efeito primário B2 → C1", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.03)
    footnote(fig, "As 5 seeds do piloto são as 5 primeiras seeds do final: as amostras NÃO são independentes e não foram combinadas (nada de N = 15). "
                  "Δ = (C1 − B2)/B2, IC95% bootstrap pareado. Figura exclusiva de comparação metodológica.", y=-0.1)
    m = finish(fig, "FIG18_PILOT_VS_FINAL", "09_pilot_vs_final", "Piloto V2 (N=5) vs Final (N=10): efeito primário B2 → C1",
               "Estimativas do efeito B2→C1 no piloto (N=5) e no final (N=10) para S1–S4, rotuladas e sem combinar amostras.", ["artifacts/final-analysis/pilot_vs_final.csv"],
               SCENARIOS, [B2, C1], mets, "Piloto 5 seeds; Final 10 seeds (5 comuns)", rows, final_only=False, tight=True)
    KEEP["FIG18"] = m["files"]["png"]


def fig18b():
    pvf = D.pvf
    nonzero = [r for r in pvf if r["pilot_mean_diff_C1_minus_B2"] not in ("0", "0.0")]
    persisted = sum(r["direction_persisted"] == "True" for r in nonzero)
    changed = [r for r in pvf if r["verdict_changed"] == "True"]
    s4_p = float(next(r for r in pvf if r["scenario"] == "S4_LOCAL_SATURATION" and r["metric"] == "throughput")["pilot_rel_diff"])
    s4_f = float(next(r for r in pvf if r["scenario"] == "S4_LOCAL_SATURATION" and r["metric"] == "throughput")["final_rel_diff"])
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), gridspec_kw={"width_ratios": [1, 1.05]})
    rows = []
    ax = axes[0]
    xs = np.arange(4)
    for k, m in enumerate(("throughput", "mean_waiting_time")):
        vals = [float(next(r for r in pvf if r["scenario"] == s and r["metric"] == m)["ci_width_ratio_final_over_pilot"]) for s in SCENARIOS]
        ax.bar(xs + (k - 0.5) * 0.36, vals, 0.34, color=CT_COLOR[C1] if k == 0 else "white", edgecolor=INK, hatch="" if k == 0 else "//", linewidth=0.8, label=METRIC_PT[m].split(" (")[0], zorder=3)
        for x, v, s in zip(xs + (k - 0.5) * 0.36, vals, SCENARIOS, strict=True):
            ax.text(x, v, comma(v, 2), ha="center", va="bottom", fontsize=8.6)
            rows.append({"scenario": s, "metric": m, "ci_width_ratio_final_over_pilot": v})
    ax.axhline(1, color=MUTED, lw=1, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([SC_SHORT[s] for s in SCENARIOS])
    ax.set_ylabel("Largura do IC95%: final (N=10) / piloto (N=5)")
    ax.set_title("Precisão: IC mais estreito quando < 1", fontsize=10.6)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    comma_axis(ax, "y", 1)
    ax.grid(axis="x", visible=False)
    ax2 = axes[1]
    ax2.axis("off")
    ax2.grid(False)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    lines = [("O que N = 10 acrescentou", True),
             (f"• Direção do efeito C1−B2 persistiu em {persisted}/{len(nonzero)} comparações com efeito não nulo no piloto.", False),
             (f"• Nenhuma conclusão principal foi revertida; {len(changed)} vereditos de IC mudaram.", False),
             (f"• S4, vazão (C1 vs B2): {pct(s4_p)} no piloto → {pct(s4_f)} no final: a estimativa do piloto era maior.", False),
             ("• ICs de vazão estreitaram em S2, S3 e S4 (gráfico ao lado).", False),
             ("• Retrospectiva metodológica — não é uma nova regra de parada.", False)]
    y = 0.95
    for t, b in lines:
        ax2.text(0, y, t, fontsize=10.2 if not b else 11.2, fontweight="bold" if b else "normal", va="top", wrap=True)
        y -= 0.1 if b else 0.17
    rows += [{"item": "direction_persisted", "value": persisted, "of": len(nonzero)}, {"item": "verdict_changed", "value": len(changed)},
             {"item": "s4_throughput_rel_pilot", "value": s4_p}, {"item": "s4_throughput_rel_final", "value": s4_f}]
    fig.suptitle("Valor de N = 10 em relação ao piloto", fontsize=13, fontweight="bold", x=0.01, ha="left", y=1.02)
    footnote(fig, "Razões calculadas de pilot_vs_final.csv. Piloto e final compartilham as 5 primeiras seeds e não foram combinados.", y=-0.1)
    finish(fig, "FIG18B_N10_VALUE", "09_pilot_vs_final", "Valor de N = 10 em relação ao piloto", "Direção persistiu em 50/51 comparações; ICs de vazão estreitaram; efeito de vazão em S4 menor com N=10.",
           ["artifacts/final-analysis/pilot_vs_final.csv"], SCENARIOS, [B2, C1], ["throughput", "mean_waiting_time"], "Piloto 5 / Final 10", rows, final_only=False)
    return persisted, len(nonzero), s4_p, s4_f


# =============================================================================================
# FIG19 / FIG20 summary matrices
# =============================================================================================
def key_rel(s, a, b, m):
    return pct(float(D.pair(s, a, b, m)["relative_difference_of_means"]))


def fig19():
    # qualitative text below is validated against the classification table (assertions)
    assert D.klass("S1_BALANCED", B0, B2) == f"{B2}_BETTER" and D.klass("S1_BALANCED", B2, C1) == f"{B2}_BETTER"
    assert D.klass("S2_DIRECTIONAL_PEAK", B0, B2) == f"{B0}_BETTER" and D.klass("S2_DIRECTIONAL_PEAK", B2, C1) == "TRADE_OFF"
    assert D.klass("S3_DEMAND_SHIFT", B0, B2) == f"{B0}_BETTER" and D.klass("S3_DEMAND_SHIFT", B2, C1) == f"{B2}_BETTER"
    assert D.klass("S4_LOCAL_SATURATION", B0, B2) == f"{B0}_BETTER" and D.klass("S4_LOCAL_SATURATION", B2, C1) == f"{C1}_BETTER"
    k = key_rel
    body = {
        "S1_BALANCED": (f"B2 favorecido\nespera {k('S1_BALANCED', B0, B2, 'mean_waiting_time')},\nfila {k('S1_BALANCED', B0, B2, 'mean_network_queue_vehicles')}",
                        f"B2 favorecido\nC1: espera {k('S1_BALANCED', B2, C1, 'mean_waiting_time')},\nfila {k('S1_BALANCED', B2, C1, 'mean_network_queue_vehicles')}",
                        "A adaptação ajuda;\na cooperação não ajuda"),
        "S2_DIRECTIONAL_PEAK": (f"B0 favorecido\nB2: vazão {k('S2_DIRECTIONAL_PEAK', B0, B2, 'throughput')},\nconclusão {k('S2_DIRECTIONAL_PEAK', B0, B2, 'completion_ratio_offered')}",
                                f"Trade-off\nC1: espera {k('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_waiting_time')},\nvazão {k('S2_DIRECTIONAL_PEAK', B2, C1, 'throughput')}",
                                "Tempo fixo mais forte;\ncooperação = trade-off"),
        "S3_DEMAND_SHIFT": ("B0 favorecido\nconclusão, partida,\natraso e fila",
                            f"B2 favorecido\nC1: espera {k('S3_DEMAND_SHIFT', B2, C1, 'mean_waiting_time')},\nfila {k('S3_DEMAND_SHIFT', B2, C1, 'mean_network_queue_vehicles')}",
                            "Tempo fixo mais forte;\nB2 supera o C1 na rede"),
        "S4_LOCAL_SATURATION": (f"B0 favorecido\nB2: vazão {k('S4_LOCAL_SATURATION', B0, B2, 'throughput')},\nconclusão e atraso",
                                f"C1 favorecido\nvazão {k('S4_LOCAL_SATURATION', B2, C1, 'throughput')},\nespera {k('S4_LOCAL_SATURATION', B2, C1, 'mean_waiting_time')}",
                                "B0 forte em capacidade;\ncooperação ajuda sob\nsaturação localizada"),
    }
    fig, ax = plt.subplots(figsize=(10.5, 5.3))
    ax.axis("off")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.grid(False)
    heads = ["Cenário", "Adaptação: B0 vs B2", "Cooperação: B2 vs C1", "Interpretação principal"]
    xs, ws = [0, 2.1, 5.35, 8.6], [2.05, 3.2, 3.2, 3.4]
    for x, w, h in zip(xs, ws, heads, strict=True):
        ax.add_patch(Rectangle((x, 5.2), w, 0.65, fc="#37474f", ec="white"))
        ax.text(x + w / 2, 5.52, h, ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    tint = {"B2": "#d6f0e6", "B0": "#dce9f9", "C1": "#e1ddf6", "Trade": "#fff3d6"}
    rows = []
    for i, s in enumerate(SCENARIOS):
        y = 4.15 - i * 1.3
        ax.add_patch(Rectangle((xs[0], y), ws[0], 1.2, fc="#eceff1", ec="white"))
        ax.text(xs[0] + 0.1, y + 0.6, SC_NAME[s].replace(" — ", "\n").replace("Mudança de demanda", "Mudança de\ndemanda").replace("Saturação localizada", "Saturação\nlocalizada"), va="center", fontsize=9.2, fontweight="bold")
        for j, t in enumerate(body[s][:2]):
            key = "B2" if t.startswith("B2") else "B0" if t.startswith("B0") else "C1" if t.startswith("C1") else "Trade"
            ax.add_patch(Rectangle((xs[j + 1], y), ws[j + 1], 1.2, fc=tint[key], ec="white"))
            ax.text(xs[j + 1] + ws[j + 1] / 2, y + 0.6, t, ha="center", va="center", fontsize=9.2)
        ax.add_patch(Rectangle((xs[3], y), ws[3], 1.2, fc="#f7f8f9", ec="white"))
        ax.text(xs[3] + ws[3] / 2, y + 0.6, body[s][2], ha="center", va="center", fontsize=9.6, fontweight="bold")
        rows.append({"scenario": s, "B0_vs_B2_classification": D.klass(s, B0, B2), "B2_vs_C1_classification": D.klass(s, B2, C1),
                     "B0_vs_B2_text": body[s][0].replace("\n", " "), "B2_vs_C1_text": body[s][1].replace("\n", " "), "interpretation": body[s][2].replace("\n", " ")})
    ax.set_title("Matriz final de resultados (N = 10 seeds)", loc="left", fontsize=13, fontweight="bold", pad=8)
    footnote(fig, "Classificação por cenário e comparação conforme a análise final validada (IC95% pareado exclui 0 nas métricas de serviço e de atraso/fila). "
                  "Valores = diferença relativa média pareada do segundo controlador em relação ao primeiro.", y=-0.01)
    m = finish(fig, "FIG19_FINAL_RESULT_MATRIX", "10_summary", "Matriz final de resultados", "Resumo por cenário das comparações B0 vs B2 e B2 vs C1 e da interpretação principal.",
               SRC_PW + ["artifacts/final-analysis/final_scenario_pair_classification.csv", "artifacts/final-analysis/final_analysis.md"], SCENARIOS, [B0, B2, C1],
               ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles"], "10 pares por cenário", rows, tight=False)
    KEEP["FIG19"] = m["files"]["png"]


def fig20():
    s4t = pct(float(D.pair("S4_LOCAL_SATURATION", B2, C1, "throughput")["relative_difference_of_means"]))
    fig, ax = plt.subplots(figsize=(10.5, 5.9))
    ax.axis("off")
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 6)
    ax.grid(False)
    ax.text(0.1, 5.75, "Resposta à pergunta de pesquisa", fontsize=15, fontweight="bold", va="top")
    ax.text(0.1, 5.1, "A cooperação apresentou efeito dependente do cenário.", fontsize=14.5, va="top", color=CT_COLOR[C1], fontweight="bold")
    items = [("S1", "não trouxe ganho", f"C1 vs B2: espera {key_rel('S1_BALANCED', B2, C1, 'mean_waiting_time')}, fila {key_rel('S1_BALANCED', B2, C1, 'mean_network_queue_vehicles')}"),
             ("S2", "trade-off", f"menos fila ({key_rel('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_network_queue_vehicles')}), menor vazão ({key_rel('S2_DIRECTIONAL_PEAK', B2, C1, 'throughput')})"),
             ("S3", "desempenho inferior ao B2 na rede", f"espera {key_rel('S3_DEMAND_SHIFT', B2, C1, 'mean_waiting_time')}, fila {key_rel('S3_DEMAND_SHIFT', B2, C1, 'mean_network_queue_vehicles')}"),
             ("S4", "benefício claro sob saturação localizada", f"vazão {s4t}, espera {key_rel('S4_LOCAL_SATURATION', B2, C1, 'mean_waiting_time')}, fila {key_rel('S4_LOCAL_SATURATION', B2, C1, 'mean_network_queue_vehicles')}")]
    rows = []
    for i, (sc, txt, num) in enumerate(items):
        y = 4.2 - i * 0.82
        ax.add_patch(FancyBboxPatch((0.1, y - 0.28), 0.8, 0.56, boxstyle="round,pad=0.04,rounding_size=0.1", fc="#37474f", ec="none"))
        ax.text(0.5, y, sc, color="white", ha="center", va="center", fontsize=13, fontweight="bold")
        ax.text(1.15, y + 0.1, txt, fontsize=12.4, fontweight="bold", va="center")
        ax.text(1.15, y - 0.24, num, fontsize=9.6, color=MUTED, va="center")
        rows.append({"scenario": sc, "statement": txt, "numbers": num})
    ax.add_patch(FancyBboxPatch((0.1, 0.1), 10.2, 0.85, boxstyle="round,pad=0.05,rounding_size=0.12", fc="#f4f6f7", ec=MUTED))
    ax.text(5.2, 0.52, "Não foi observada superioridade geral sobre o controle adaptativo local\nou sobre o tempo fixo calibrado.", ha="center", va="center",
            fontsize=11.2, fontweight="bold")
    footnote(fig, "Simulação SUMO, rede 3×3, 10 seeds por condição, sob os parâmetros congelados dos controladores. Valores: diferença relativa média pareada (C1 vs B2).", y=-0.02)
    m = finish(fig, "FIG20_RESEARCH_QUESTION", "10_summary", "Resposta à pergunta de pesquisa", "Síntese slide-ready: efeito da cooperação dependente do cenário; sem superioridade geral.",
               SRC_PW + ["artifacts/final-analysis/final_analysis.md"], SCENARIOS, [B2, C1], ["mean_waiting_time", "mean_network_queue_vehicles", "throughput"], "10 pares por cenário", rows, tight=False)
    KEEP["FIG20"] = m["files"]["png"]


# =============================================================================================
# main
# =============================================================================================
if __name__ == "__main__":
    fig01(); fig02(); fig03(); fig04(); fig05(); fig06(); fig07(); fig08(); fig09(); tele_rows = fig10()
    fig11(); fig12(); fig13(); fig14(); fig15(); fig16(); fig17(); fig18(); n10 = fig18b(); fig19(); fig20()
    json.dump({"keep": KEEP, "n10": list(n10), "teleports": tele_rows}, open(C.ROOT / "_figs_state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
    json.dump(C.MANIFEST, open(C.ROOT / "_figs_manifest_part.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("figures:", len(C.MANIFEST))
