"""TCC package assembly (Prompt 64): tables, presentation/document subsets, manifest and validation.

Run AFTER scripts/build_tcc_figures.py:

    python scripts/build_tcc_figures.py
    python scripts/build_tcc_package.py

Every number comes from artifacts/final-analysis/ (validated FINAL N=10 analysis).
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_figures_common as C  # noqa: E402
from tcc_figures_common import (  # noqa: E402
    B0, B1, B2, C1, C2, CT_COLOR, CT_SHORT, CTRLS, INK, MUTED, ROOT, SC_NAME, SCENARIOS, comma, pct, thousands,
)

C.style()
D = C.Data()
C.ensure_dirs()
TABLES: list[dict] = []
FIGS = json.loads((ROOT / "_figs_manifest_part.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "_figs_state.json").read_text(encoding="utf-8"))
SRC_PW = ["artifacts/final-analysis/final_pairwise_summary.csv"]


# ----------------------------------------------------------------------------------------------
# table export
# ----------------------------------------------------------------------------------------------
def md_escape(x: str) -> str:
    return str(x).replace("|", "/").replace("\n", " ")


def tex_escape(x: str) -> str:
    out = str(x).replace("\n", " ")
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("→", r"$\rightarrow$"),
                 ("−", "-"), ("≈", r"$\approx$"), ("×", r"$\times$"), ("Δ", r"$\Delta$")):
        out = out.replace(a, b)
    return out


def table(tid: str, title: str, caption: str, header: list[str], rows: list[list[str]], source_rows: list[dict], sources: list[str],
          *, col_w: list[float] | None = None, fs: float = 8.6, figsize: tuple[float, float] | None = None, scenarios=None, controllers=None,
          metrics=None, n="10 seeds por controlador/cenário"):
    out = ROOT / "tables"
    # csv (display) + md + tex
    with (out / f"{tid}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    md = f"**{title}**\n\n| " + " | ".join(header) + " |\n|" + "|".join("---" for _ in header) + "|\n" + "\n".join(
        "| " + " | ".join(md_escape(c) for c in r) + " |" for r in rows) + f"\n\n*{caption}*\n"
    (out / f"{tid}.md").write_text(md, encoding="utf-8")
    cols = "l" * len(header)
    tex = ("% requires booktabs\n\\begin{table}[htbp]\n\\centering\\small\n\\caption{" + tex_escape(caption) + "}\n\\begin{tabular}{" + cols + "}\n\\toprule\n"
           + " & ".join(tex_escape(h) for h in header) + " \\\\\n\\midrule\n" + "\n".join(" & ".join(tex_escape(c) for c in r) + " \\\\" for r in rows)
           + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    (out / f"{tid}.tex").write_text(tex, encoding="utf-8")
    C.write_csv(out / f"{tid}_source.csv", source_rows)
    # rendered figure (png/svg/pdf) with automatic text wrapping
    import textwrap
    widths = col_w or [1.0] * len(header)
    tot = sum(widths)
    fw = figsize[0] if figsize else 10.5
    char_in = 0.6 * fs / 72
    def wrap_cell(text, w):
        maxc = max(int(w / tot * fw * 0.94 / char_in) - 1, 6)
        return textwrap.wrap(str(text), maxc) or [""]
    wrapped = [[wrap_cell(c, widths[j]) for j, c in enumerate(r)] for r in rows]
    head_w = [wrap_cell(h, widths[j]) for j, h in enumerate(header)]
    line_in = fs * 1.5 / 72
    row_in = [max(len(x) for x in head_w) * line_in + 0.16] + [max(len(x) for x in r) * line_in + 0.12 for r in wrapped]
    fh_ = sum(row_in) + 0.75
    fig = plt.figure(figsize=(fw, fh_))
    ax = fig.add_axes([0.01, 0.01, 0.98, 1 - 0.7 / fh_])
    ax.axis("off")
    ax.grid(False)
    tb = ax.table(cellText=[["\n".join(c) for c in r] for r in wrapped], colLabels=["\n".join(h) for h in head_w], colWidths=[w / tot for w in widths],
                  loc="upper left", cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(fs)
    axes_h = fh_ * (1 - 0.7 / fh_)
    for (r, c), cell in tb.get_celld().items():
        cell.set_height(row_in[r] / axes_h)
        cell.set_edgecolor("#d5dadd")
        cell.set_linewidth(0.6)
        cell.PAD = 0.02
        if r == 0:
            cell.set_facecolor("#37474f")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#f6f8f9")
    ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold")
    files = {}
    for ext in ("png", "svg", "pdf"):
        p = out / f"{tid}.{ext}"
        fig.savefig(p, dpi=200 if ext == "png" else None, bbox_inches="tight", pad_inches=0.15)
        files[ext] = p.relative_to(ROOT).as_posix()
    plt.close(fig)
    files.update({"csv": f"tables/{tid}.csv", "markdown": f"tables/{tid}.md", "latex": f"tables/{tid}.tex", "source_csv": f"tables/{tid}_source.csv"})
    meta = {"figure_id": tid, "kind": "table", "title": title, "caption": caption, "source_artifacts": sources, "scenario": scenarios or [],
            "controllers": controllers or [], "metrics": metrics or [], "N": n, "statistical_method": C.METHOD,
            "scientific_source_git_sha": C.SRC_SHA, "freeze_manifest_sha256": C.FREEZE_SHA, "scientific_tree_sha256": C.TREE_SHA,
            "generation": C.GEN_VERSION + " + scripts/build_tcc_package.py", "files": files, "source_rows": len(source_rows), "final_only": True}
    (out / f"{tid}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta["files"]["metadata_json"] = f"tables/{tid}.json"
    TABLES.append(meta)


# ----------------------------------------------------------------------------------------------
# TABLE 1 / 2 (definitions)
# ----------------------------------------------------------------------------------------------
def table1():
    c1_b = float(C.rd("s5_communication_summary.csv")[0]["mean_bytes_per_message_sent"])
    comm = {r["controller"]: float(r["mean_bytes_per_message_sent"]) for r in D.comm if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 0.0}
    rows = [
        ["B0 — Tempo fixo calibrado", "Tempo fixo (plano fx_c84_demand_proportional_alternate: ciclo 84 s, divisão proporcional à demanda, offsets alternados)",
         "Nenhuma (plano estático)", "Não", "Baseline tradicional calibrado de tempo fixo"],
        ["B1 — Adaptativo local", "Adaptativo local simples: compara a pressão de fila da fase verde atual com as concorrentes (verde mín. 10 s, máx. 60 s)",
         "Observação local da interseção", "Não", "Baseline adaptativo secundário"],
        ["B2 — Pressão local", "Pressão de movimento local: fila a montante − ocupação a jusante (mesmo caminho de segurança dos demais)",
         "Observação local da interseção", "Não", "Baseline adaptativo não cooperativo primário"],
        ["C1 — Cooperativo compacto", "Núcleo de pressão local do B2 + ajuste cooperativo",
         "Observação local + mensagem compacta dos vizinhos", f"Sim — mensagem compacta (≈ {comma(comm[C1], 0)} B)", "Método cooperativo principal (efeito incremental sobre B2)"],
        ["C2 — Cooperativo expandido", "Mesmo núcleo e arquitetura do C1/B2; ajuste cooperativo com sinais adicionais",
         "Observação local + mensagem expandida dos vizinhos", f"Sim — mensagem expandida (≈ {comma(comm[C2], 0)} B)", "Comparação de riqueza de comunicação (C1 vs C2)"],
    ]
    src = [{"controller": r[0], "control_type": r[1], "local_information": r[2], "neighbor_communication": r[3], "purpose": r[4]} for r in rows]
    src += [{"controller": C1, "mean_bytes_per_message_sent": comm[C1]}, {"controller": C2, "mean_bytes_per_message_sent": comm[C2]}]
    table("TABLE01_CONTROLLERS", "Tabela 1 — Controladores do experimento final",
          "Definições dos controladores (todos reativos; nenhum prevê demanda nem usa aprendizado de máquina). Tamanho da mensagem: média de bytes por mensagem enviada (S5, perda 0%).",
          ["Controlador", "Tipo de controle", "Informação local", "Comunicação com vizinhos", "Papel no experimento"], rows, src,
          ["docs/methodology/controllers.md", "artifacts/final-analysis/s5_communication_summary.csv"], col_w=[1.4, 3.2, 1.9, 1.7, 2.0], fs=7.8, figsize=(12.5, 3.6),
          controllers=CTRLS)


def table2():
    s5_c1 = len({k for k in D.runs if k[0] == "FINAL_S5" and k[2] == C1})
    rows = [
        ["S1", "Demanda balanceada em todas as bordas (conversões 0,70 / 0,15 / 0,15)", "Referência sem estresse direcional", "—"],
        ["S2", "Forte viés de demanda oeste→leste (≈ 80% da demanda no corredor dominante)", "Pico direcional", "Tráfego-base do S5"],
        ["S3", "Primeira metade balanceada; choque direcional de demanda em t = 2100 s", "Resposta a mudança de demanda", "Choque congelado; métrica pós-choque (área da fila)"],
        ["S4", "Saturação localizada na interseção A5", "Congestionamento localizado", "Teleports SUMO medidos e mantidos (ALLOW_AND_MEASURE)"],
        ["S5", "Tráfego do S2 (não é um novo padrão de demanda)", "Comunicação: perda 0 / 20 / 50 / 100% (atraso 0) em C1 e C2; B2 como referência",
         f"C1 {s5_c1} + C2 {s5_c1} execuções + B2 {s5_c1 // 4} (1 por seed)"],
    ]
    src = [{"scenario": r[0], "traffic_condition": r[1], "purpose": r[2], "special_feature": r[3]} for r in rows]
    table("TABLE02_SCENARIOS", "Tabela 2 — Cenários do experimento final",
          "Aquecimento de 300 s e medição de 3600 s em todos os cenários; 10 seeds por condição. O S5 usa o tráfego do S2 e varia apenas a perda de comunicação.",
          ["Cenário", "Condição de tráfego", "Propósito", "Característica especial"], rows, src, ["docs/methodology/experimental-protocol.md", "artifacts/final-analysis/final_metrics.parquet"],
          col_w=[0.7, 4.0, 3.0, 3.2], fs=8.2, figsize=(12.5, 3.2), scenarios=SCENARIOS + ["S5"])


# ----------------------------------------------------------------------------------------------
# TABLE 3..6 (data)
# ----------------------------------------------------------------------------------------------
def table3():
    mets = ["throughput", "completion_ratio_offered", "mean_waiting_time", "mean_network_queue_vehicles", "max_network_queue_vehicles"]
    eff = {"TREATMENT_BETTER": "C1 favorecido", "BASELINE_BETTER": "B2 favorecido", "NO_CLEAR_DIFFERENCE": "Sem diferença clara"}
    rows, src = [], []
    for s in SCENARIOS:
        for m in mets:
            r = D.pair(s, B2, C1, m)
            d = 3 if "ratio" in m else 1
            rows.append([C.SC_NAME[s].split(" — ")[0], C.METRIC_PT[m], comma(float(r["baseline_mean"]), d), comma(float(r["treatment_mean"]), d),
                         comma(float(r["mean_difference"]), d, True), pct(float(r["relative_difference_of_means"])),
                         f"[{comma(float(r['ci95_low']), d, True)}; {comma(float(r['ci95_high']), d, True)}]", eff[r["effect"]]])
            src.append({"scenario": s, "metric": m, "B2_mean": float(r["baseline_mean"]), "C1_mean": float(r["treatment_mean"]), "mean_difference": float(r["mean_difference"]),
                        "relative_difference": float(r["relative_difference_of_means"]), "ci95_low": float(r["ci95_low"]), "ci95_high": float(r["ci95_high"]),
                        "n_pairs": int(r["n_pairs"]), "effect": r["effect"], "scenario_classification": D.klass(s, B2, C1)})
    table("TABLE03_PRIMARY_B2_VS_C1", "Tabela 3 — Resultado primário: B2 (pressão local) → C1 (cooperativo compacto)",
          "Diferença = C1 − B2, pareada por seed (N = 10); IC95% por bootstrap pareado. Relativo = diferença média / média do B2. Espera é condicional às viagens concluídas.",
          ["Cenário", "Métrica", "B2 média", "C1 média", "Dif. absoluta", "Dif. relativa", "IC95% (abs.)", "Interpretação"], rows, src, SRC_PW,
          col_w=[0.7, 2.6, 1.0, 1.0, 1.1, 1.0, 1.9, 1.6], fs=7.8, figsize=(12.5, 6.6), scenarios=SCENARIOS, controllers=[B2, C1], metrics=mets, n="10 pares por cenário")


def table4():
    TT, CMP = "reference_route_mean_travel_time_seconds", "reference_route_completion_ratio_offered"
    rows, src = [], []
    for s in SCENARIOS:
        t02, t21 = D.rr_pair(s, B0, B2, TT), D.rr_pair(s, B2, C1, TT)
        row = [SC_NAME[s].split(" — ")[0]]
        for c in (B0, B2, C1):
            row += [comma(D.rr_mean(s, c, TT), 1), comma(D.rr_mean(s, c, CMP), 3)]
        row += [f"{comma(float(t02['paired_mean_diff']), 1, True)} [{comma(float(t02['ci95_low']), 1, True)}; {comma(float(t02['ci95_high']), 1, True)}]",
                f"{comma(float(t21['paired_mean_diff']), 1, True)} [{comma(float(t21['ci95_low']), 1, True)}; {comma(float(t21['ci95_high']), 1, True)}]"]
        rows.append(row)
        src.append({"scenario": s, **{f"{CT_SHORT[c]}_travel_s": D.rr_mean(s, c, TT) for c in (B0, B2, C1)}, **{f"{CT_SHORT[c]}_completion": D.rr_mean(s, c, CMP) for c in (B0, B2, C1)},
                    "B0_to_B2_diff_s": float(t02["paired_mean_diff"]), "B0_to_B2_ci_low": float(t02["ci95_low"]), "B0_to_B2_ci_high": float(t02["ci95_high"]),
                    "B2_to_C1_diff_s": float(t21["paired_mean_diff"]), "B2_to_C1_ci_low": float(t21["ci95_low"]), "B2_to_C1_ci_high": float(t21["ci95_high"]),
                    "n_seeds": int(t02["n_seeds"])})
    table("TABLE04_REFERENCE_ROUTE", "Tabela 4 — Rota de referência (left1A1 → A1B1 → B1C1 → C1right1)",
          "Tempo de viagem médio (s) e conclusão (fração dos oferecidos) da coorte da rota; diferenças pareadas (tratamento − baseline), IC95% bootstrap (N = 10). "
          "Tempos valem só para viagens concluídas — leia-os junto da conclusão.",
          ["Cenário", "B0 viagem (s)", "B0 concl.", "B2 viagem (s)", "B2 concl.", "C1 viagem (s)", "C1 concl.", "B0→B2: Δ (s) [IC95%]", "B2→C1: Δ (s) [IC95%]"], rows, src,
          ["artifacts/final-analysis/reference_route_pairwise.csv", "artifacts/final-analysis/reference_route_summary.csv"], col_w=[0.7, 0.9, 0.8, 0.9, 0.8, 0.9, 0.8, 2.0, 2.0],
          fs=7.8, figsize=(12.5, 2.6), scenarios=SCENARIOS, controllers=[B0, B2, C1], metrics=[TT, CMP])


def table5():
    mets = [("throughput", 1), ("completion_ratio_offered", 3), ("mean_waiting_time", 1), ("mean_network_queue_vehicles", 1)]
    rows, src = [], []
    b2 = [CT_SHORT[B2] + " (referência)", "—"] + [comma(D.s5d(B2, None, m), d) for m, d in mets] + ["—", "—"]
    rows.append(b2)
    src.append({"controller": B2, "packet_loss": "reference", **{m: D.s5d(B2, None, m) for m, _ in mets}})
    for c in (C1, C2):
        for p in (0.0, 0.2, 0.5, 1.0):
            cm = next(r for r in D.comm if r["experiment"] == "FINAL_S5" and r["controller"] == c and float(r["packet_loss"]) == p)
            rows.append([CT_SHORT[c], f"{int(p * 100)}%"] + [comma(D.s5d(c, p, m), d) for m, d in mets] + [thousands(float(cm["mean_messages_delivered"])), comma(float(cm["mean_bytes_delivered"]) / 1e6, 1) + " MB"])
            src.append({"controller": c, "packet_loss": p, **{m: D.s5d(c, p, m) for m, _ in mets}, "mean_messages_delivered": float(cm["mean_messages_delivered"]),
                        "mean_bytes_delivered": float(cm["mean_bytes_delivered"]), "N": int(cm["N"])})
    table("TABLE05_S5", "Tabela 5 — S5: perda de comunicação (tráfego S2, 10 seeds)",
          "Médias por run (N = 10 seeds por linha). B2 é a referência sem comunicação (10 seeds, não duplicada). Espera é condicional às viagens concluídas. "
          "Com 100% de perda, C1 e C2 têm as mesmas métricas de tráfego do B2 e nenhuma mensagem é entregue.",
          ["Controlador", "Perda", "Vazão", "Conclusão", "Espera (s)", "Fila média (veíc.)", "Msgs entregues/run", "Bytes entregues/run"], rows, src,
          ["artifacts/final-analysis/s5_controller_summary.csv", "artifacts/final-analysis/s5_communication_summary.csv"], col_w=[1.4, 0.7, 1.0, 1.0, 1.0, 1.3, 1.5, 1.5],
          fs=8.2, figsize=(11, 4.4), scenarios=["S2_DIRECTIONAL_PEAK (base do S5)"], controllers=[B2, C1, C2],
          metrics=[m for m, _ in mets] + ["messages_delivered", "bytes_delivered"], n="10 seeds por nível (C1, C2); 10 seeds (B2)")


def table6():
    ov = next(r for r in D.ovh if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 0.0)
    comm = {c: next(r for r in D.comm if r["experiment"] == "FINAL_S5" and r["controller"] == c and float(r["packet_loss"]) == 0.0) for c in (C1, C2)}
    cls = {s: D.klass(s, C1, C2) for s in SCENARIOS}
    parts = []
    for s in SCENARIOS:
        k = cls[s]
        parts.append(f"{s.split('_')[0]}: " + ("C1 favorecido" if k.startswith(C1) else "trade-off" if k == "TRADE_OFF" else "C2 favorecido" if k.startswith(C2) else "sem diferença clara"))
    benefit = "Sem benefício geral (" + "; ".join(parts) + ")"
    rows = [["C1 — Cooperativo compacto", thousands(float(comm[C1]["mean_messages_sent"])), comma(float(comm[C1]["mean_bytes_sent"]) / 1e6, 1) + " MB", "1,0× (referência)", "—"],
            ["C2 — Cooperativo expandido", thousands(float(comm[C2]["mean_messages_sent"])), comma(float(comm[C2]["mean_bytes_sent"]) / 1e6, 1) + " MB",
             comma(float(ov["C2_over_C1_bytes_sent"]), 2) + "×", benefit]]
    src = [{"controller": c, "mean_messages_sent": float(comm[c]["mean_messages_sent"]), "mean_bytes_sent": float(comm[c]["mean_bytes_sent"]),
            "relative_bytes_vs_C1": float(comm[c]["mean_bytes_sent"]) / float(comm[C1]["mean_bytes_sent"]), "classification_C1_vs_C2": json.dumps(cls)} for c in (C1, C2)]
    table("TABLE06_COMMUNICATION_COST", "Tabela 6 — Custo de comunicação: C1 vs C2",
          "Médias por run (S2, perda 0%, N = 10). Benefício geral de tráfego conforme a classificação final C1 vs C2 por cenário (análise final N = 10).",
          ["Controlador", "Mensagens/run", "Bytes enviados/run", "Bytes relativos ao C1", "Benefício geral de tráfego"], rows, src,
          ["artifacts/final-analysis/s5_communication_summary.csv", "artifacts/final-analysis/communication_overhead_ratio.csv", "artifacts/final-analysis/final_scenario_pair_classification.csv"],
          col_w=[1.7, 1.2, 1.4, 1.5, 4.8], fs=8.2, figsize=(12.5, 1.9), scenarios=SCENARIOS, controllers=[C1, C2], metrics=["messages_sent", "bytes_sent"])


# ----------------------------------------------------------------------------------------------
# subsets
# ----------------------------------------------------------------------------------------------
PRESENTATION = ["01_overview/FIG01_FINAL_OVERVIEW", "02_adaptation/FIG03_B0_VS_B2", "03_cooperation/FIG04_B2_VS_C1", "03_cooperation/FIG06_S2_TRADEOFF",
                "05_s3_shock/FIG07_S3_SHOCK", "06_s4_saturation/FIG09_S4_B2_VS_C1", "04_reference_route/FIG11_REFERENCE_ROUTE",
                "07_s5_communication/FIG14_S5_PACKET_LOSS", "08_communication_cost/FIG16_COMMUNICATION_COST", "10_summary/FIG19_FINAL_RESULT_MATRIX"]
DOCUMENT = ["03_cooperation/FIG04_B2_VS_C1", "02_adaptation/FIG03_B0_VS_B2", "03_cooperation/FIG05_COOPERATION_RESULT_MATRIX", "03_cooperation/FIG06_S2_TRADEOFF",
            "05_s3_shock/FIG07_S3_SHOCK", "05_s3_shock/FIG08_S3_POST_SHOCK_AUC", "06_s4_saturation/FIG09_S4_B2_VS_C1", "06_s4_saturation/FIG10_S4_TELEPORTS",
            "04_reference_route/FIG11_REFERENCE_ROUTE", "04_reference_route/FIG12_REFERENCE_ROUTE_EFFECTS", "04_reference_route/FIG13_S3_NETWORK_VS_ROUTE",
            "07_s5_communication/FIG14_S5_PACKET_LOSS", "07_s5_communication/FIG15_S5_QUEUE_DELAY", "08_communication_cost/FIG16_COMMUNICATION_COST",
            "08_communication_cost/FIG17_PERFORMANCE_VS_COMMUNICATION_COST", "09_pilot_vs_final/FIG18_PILOT_VS_FINAL", "01_overview/FIG01_FINAL_OVERVIEW",
            "01_overview/FIG02_MAIN_CONTROLLER_OVERVIEW"]


def pad_16x9(src: Path, dst: Path, w: int = 1920, h: int = 1080) -> tuple[int, int]:
    im = Image.open(src).convert("RGB")
    scale = min((w - 80) / im.width, (h - 60) / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    canvas.save(dst)
    return canvas.size


def subsets():
    pres = ROOT / "presentation"
    doc = ROOT / "document"
    pres_files, doc_files = [], []
    for n, rel in enumerate(PRESENTATION, 1):
        base = Path(rel).name
        sz = pad_16x9(ROOT / f"{rel}.png", pres / f"{n:02d}_{base}_16x9.png")
        for ext in ("svg", "pdf"):
            shutil.copy2(ROOT / f"{rel}.{ext}", pres / f"{n:02d}_{base}.{ext}")
        pres_files.append({"order": n, "figure": base, "png_16x9": f"presentation/{n:02d}_{base}_16x9.png", "size": list(sz)})
    for rel in DOCUMENT:
        for ext in ("pdf", "svg"):
            shutil.copy2(ROOT / f"{rel}.{ext}", doc / f"{Path(rel).name}.{ext}")
        im = Image.open(ROOT / f"{rel}.png")
        scale = 1950 / im.width  # 6.5 in at 300 dpi (A4 text width)
        im.convert("RGB").resize((1950, round(im.height * scale)), Image.LANCZOS).save(doc / f"{Path(rel).name}_A4w_300dpi.png", dpi=(300, 300))
        doc_files.append(Path(rel).name)
    for t in TABLES:
        tid = t["figure_id"]
        for ext in ("pdf", "svg", "csv", "md", "tex"):
            key = {"md": "markdown", "tex": "latex"}.get(ext, ext)
            shutil.copy2(ROOT / t["files"][key], doc / f"{tid}.{ext}")
        doc_files.append(tid)
    (doc / "README.txt").write_text(
        "Pacote de documento (TCC)\n=========================\n"
        "- Figuras: PDF/SVG vetoriais (preferir) e PNG a 300 dpi com largura de 6,5 in (largura útil de texto A4).\n"
        "- Inserção sugerida (LaTeX): \\includegraphics[width=\\textwidth]{FIGxx.pdf}\n"
        "- Tabelas: .tex (booktabs), .md, .csv, e PDF/SVG renderizados.\n"
        "- Todas as figuras de resultados finais usam N = 10 seeds (FIG18 é a única que mostra o piloto, rotulada).\n"
        "- Rastreabilidade: figure-manifest.json na pasta pai.\n", encoding="utf-8")
    (pres / "README.txt").write_text(
        "Pacote de apresentação (16:9)\n=============================\nPNG 1920×1080 (figura centralizada em fundo branco) + SVG/PDF originais.\n"
        "Ordem sugerida: " + "; ".join(f"{p['order']}. {p['figure']}" for p in pres_files) + "\n", encoding="utf-8")
    return pres_files, doc_files


# ----------------------------------------------------------------------------------------------
# manifest + validation
# ----------------------------------------------------------------------------------------------
def build_manifest():
    entries = []
    for m in FIGS + TABLES:
        entries.append({"figure_id": m["figure_id"], "kind": m["kind"], "title": m["title"], "files": m["files"], "data_source": m["source_artifacts"],
                        "metrics": m["metrics"], "controllers": m["controllers"], "scenarios": m["scenario"], "N": m["N"], "analysis_artifact": "artifacts/final-analysis/",
                        "scientific_source_git_sha": C.SRC_SHA, "freeze_manifest_sha256": C.FREEZE_SHA, "generation_script": m["generation"],
                        "final_only": m.get("final_only", True), "statistical_method": m["statistical_method"], "caption": m["caption"]})
    doc = {"package": "TCC final figure package (Prompt 64)", "scientific_source_git_sha": C.SRC_SHA, "freeze_manifest_sha256": C.FREEZE_SHA,
           "scientific_tree_sha256": C.TREE_SHA, "analysis_dir": "artifacts/final-analysis/", "analysis_validation": json.loads((C.A / "analysis-validation.json").read_text(encoding="utf-8"))["FINAL_ANALYSIS_VALID"],
           "entries": entries, "figure_count": len(FIGS), "table_count": len(TABLES)}
    (ROOT / "figure-manifest.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def validate(manifest: dict, pres_files, doc_files):
    problems: list[str] = []
    want_fig = ["FIG01_FINAL_OVERVIEW", "FIG02_MAIN_CONTROLLER_OVERVIEW", "FIG03_B0_VS_B2", "FIG04_B2_VS_C1", "FIG05_COOPERATION_RESULT_MATRIX", "FIG06_S2_TRADEOFF",
                "FIG07_S3_SHOCK", "FIG08_S3_POST_SHOCK_AUC", "FIG09_S4_B2_VS_C1", "FIG10_S4_TELEPORTS", "FIG11_REFERENCE_ROUTE", "FIG12_REFERENCE_ROUTE_EFFECTS",
                "FIG13_S3_NETWORK_VS_ROUTE", "FIG14_S5_PACKET_LOSS", "FIG14B_S5_COMPLETION", "FIG15_S5_QUEUE_DELAY", "FIG16_COMMUNICATION_COST",
                "FIG17_PERFORMANCE_VS_COMMUNICATION_COST", "FIG18_PILOT_VS_FINAL", "FIG18B_N10_VALUE", "FIG19_FINAL_RESULT_MATRIX", "FIG20_RESEARCH_QUESTION"]
    want_tab = ["TABLE01_CONTROLLERS", "TABLE02_SCENARIOS", "TABLE03_PRIMARY_B2_VS_C1", "TABLE04_REFERENCE_ROUTE", "TABLE05_S5", "TABLE06_COMMUNICATION_COST"]
    have = {e["figure_id"]: e for e in manifest["entries"]}
    missing = [w for w in want_fig + want_tab if w not in have]
    if missing:
        problems.append(f"missing items {missing}")
    missing_files = []
    for e in manifest["entries"]:
        for k, rel in e["files"].items():
            if not (ROOT / rel).exists():
                missing_files.append(rel)
    if missing_files:
        problems.append(f"missing files {missing_files[:6]} (+{len(missing_files)})")
    # N / pilot / historical B0
    n_problems = []
    pilot_ok = True
    hist_b0 = False
    for e in manifest["entries"]:
        src_csv = ROOT / e["files"]["source_csv"]
        txt = src_csv.read_text(encoding="utf-8")
        if re.search(r"B0_FIXED(?!_CALIBRATED)|B0_FIXED_STATIC", txt) or "B0_FIXED_STATIC" in json.dumps(e):
            hist_b0 = True
        if e["final_only"]:
            if "pilot" in txt.lower() and e["figure_id"] not in ("FIG18_PILOT_VS_FINAL", "FIG18B_N10_VALUE"):
                pilot_ok = False
    # N checks on per-seed sources (every dot-plot source row must have N == 10; S5 rows N == 10)
    for fid in ("FIG02_MAIN_CONTROLLER_OVERVIEW", "FIG06_S2_TRADEOFF", "FIG08_S3_POST_SHOCK_AUC", "FIG11_REFERENCE_ROUTE", "FIG14_S5_PACKET_LOSS", "FIG14B_S5_COMPLETION", "FIG15_S5_QUEUE_DELAY"):
        rows = list(csv.DictReader((ROOT / have[fid]["files"]["source_csv"]).open(encoding="utf-8")))
        bad = [r for r in rows if r.get("N") not in ("", None) and int(float(r["N"])) != 10]
        if bad:
            n_problems.append((fid, len(bad)))
    if n_problems:
        problems.append(f"N != 10: {n_problems}")
    # S5 B2 not duplicated: exactly one B2 condition per S5 source, with N == 10
    s5_b2_ok = True
    for fid in ("FIG14_S5_PACKET_LOSS", "FIG14B_S5_COMPLETION", "FIG15_S5_QUEUE_DELAY"):
        rows = [r for r in csv.DictReader((ROOT / have[fid]["files"]["source_csv"]).open(encoding="utf-8")) if r["controller"] == B2]
        per_metric = {}
        for r in rows:
            per_metric.setdefault(r["metric"], []).append(r)
        if any(len(v) != 1 or int(float(v[0]["N"])) != 10 for v in per_metric.values()):
            s5_b2_ok = False
    run_index = {(k[0], k[2], k[3]) for k in D.runs if k[0] == "FINAL_S5" and k[2] == B2}
    s5_b2_ok = s5_b2_ok and len({k for k in D.runs if k[0] == "FINAL_S5" and k[2] == B2}) == 10
    # S3 time series: 10 seeds x 3 controllers, mean validated vs frozen metric at build time
    ts = list(csv.DictReader((ROOT / have["FIG07_S3_SHOCK"]["files"]["source_csv"]).open(encoding="utf-8")))
    ts_ok = all(int(r["n_seeds"]) == 10 for r in ts)
    # encoding sanity (mojibake) in titles/captions
    moj = [e["figure_id"] for e in manifest["entries"] if re.search("Ã|Â|�", e["title"] + e["caption"])]
    # figure sizes (not tiny/empty)
    small = [e["figure_id"] for e in manifest["entries"] if Image.open(ROOT / e["files"]["png"]).size[0] < 1200]
    # scientific consistency vs final_analysis.md / classification
    md = D.analysis_md.replace("−", "-").replace(",", ".")
    checks = {}
    s2 = lambda m: float(D.pair("S2_DIRECTIONAL_PEAK", B2, C1, m)["relative_difference_of_means"])  # noqa: E731
    s4 = lambda m: float(D.pair("S4_LOCAL_SATURATION", B2, C1, m)["relative_difference_of_means"])  # noqa: E731
    comp_pp = float(D.pair("S2_DIRECTIONAL_PEAK", B2, C1, "completion_ratio_offered")["mean_difference"]) * 100
    checks["S2_waiting_-15.2"] = abs(s2("mean_waiting_time") + 0.152) < 0.0006 and "-15.2%" in md
    checks["S2_queue_-18.3"] = abs(s2("mean_network_queue_vehicles") + 0.183) < 0.0006 and "-18.3%" in md
    checks["S2_throughput_-5.7"] = abs(s2("throughput") + 0.057) < 0.0006 and "-5.7%" in md
    checks["S2_completion_-4.9pp"] = abs(comp_pp + 4.9) < 0.06
    checks["S4_throughput_+8.8"] = abs(s4("throughput") - 0.088) < 0.0006 and "+8.8%" in md
    checks["S4_waiting_-19.5"] = abs(s4("mean_waiting_time") + 0.195) < 0.0006 and "-19.5%" in md
    checks["S4_queue_-17.3"] = abs(s4("mean_network_queue_vehicles") + 0.173) < 0.0006 and "-17.3%" in md
    tele = {r["controller"]: r["total_teleports"] for r in csv.DictReader((ROOT / have["FIG10_S4_TELEPORTS"]["files"]["source_csv"]).open(encoding="utf-8"))}
    checks["teleports_31_28_3_0"] = (sum(float(v) for v in tele.values()), float(tele[B0]), float(tele[B2]), float(tele[B1]) + float(tele[C1]) + float(tele[C2])) == (31, 28, 3, 0)
    n10 = STATE["n10"]
    checks["n10_direction_50_of_51"] = (n10[0], n10[1]) == (50, 51)
    checks["s4_pilot_12.0_to_8.8"] = abs(n10[2] - 0.12) < 0.0006 and abs(n10[3] - 0.088) < 0.0006
    ratio = float(next(r for r in D.ovh if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 0.0)["C2_over_C1_bytes_sent"])
    checks["C2_2.3x_bytes"] = 2.2 < ratio < 2.4
    checks["classification_S1"] = D.klass("S1_BALANCED", B2, C1) == f"{B2}_BETTER" and D.klass("S1_BALANCED", B0, B2) == f"{B2}_BETTER"
    checks["classification_S2_S3_S4"] = (D.klass("S2_DIRECTIONAL_PEAK", B2, C1) == "TRADE_OFF" and D.klass("S3_DEMAND_SHIFT", B2, C1) == f"{B2}_BETTER"
                                           and D.klass("S4_LOCAL_SATURATION", B2, C1) == f"{C1}_BETTER")
    checks["B0_better_S2_S3_S4"] = all(D.klass(s, B0, B2) == f"{B0}_BETTER" for s in ("S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"))
    s5 = lambda c, p: D.s5d(c, p, "throughput")  # noqa: E731
    checks["s5_nonmonotonic_both"] = all(s5(c, 0.2) > s5(c, 0.0) and s5(c, 0.5) > s5(c, 0.0) for c in (C1, C2))
    checks["s5_100_equals_B2"] = all(abs(s5(c, 1.0) - D.s5d(B2, None, "throughput")) < 1e-9 for c in (C1, C2))
    sent100 = sum(float(r["total_messages_sent"]) for r in D.comm if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    dlv100 = sum(float(r["total_messages_delivered"]) for r in D.comm if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    checks["s5_100_zero_delivered_1.872M"] = dlv100 == 0 and sent100 == 1_872_000
    if not all(checks.values()):
        problems.append(f"consistency failures {[k for k, v in checks.items() if not v]}")
    pres_ok = len(pres_files) == 10 and all((ROOT / p["png_16x9"]).exists() for p in pres_files)
    doc_ok = all((ROOT / "document" / f"{d}.pdf").exists() or (ROOT / "document" / f"{d}.pdf").exists() for d in doc_files)
    out = {
        "FIGURE_PACKAGE_VALID": not problems and pilot_ok and not hist_b0 and s5_b2_ok and ts_ok and not moj and not small and pres_ok and doc_ok,
        "figures": len(FIGS), "tables": len(TABLES), "all_requested_present": not missing, "all_files_exist": not missing_files,
        "FINAL_ONLY_FIGURES_USE_N10": not n_problems and ts_ok, "pilot_only_in_labeled_pilot_vs_final_figures": pilot_ok,
        "HISTORICAL_B0_IN_FINAL_FIGURES": "YES" if hist_b0 else "NO", "S5_B2_NOT_DUPLICATED": s5_b2_ok, "S3_TIMESERIES_10_SEEDS": ts_ok,
        "OUTLIERS_REMOVED": "NO", "mojibake_in_titles_or_captions": moj, "small_pngs": small, "presentation_ok": pres_ok, "document_ok": doc_ok,
        "SCIENTIFIC_CONSISTENCY_PASS": all(checks.values()), "consistency_checks": checks, "problems": problems,
        "outlier_policy": "All 10 seeds plotted in every distribution figure; no flagged observation removed (see final_outliers_flagged_not_removed.csv).",
    }
    (ROOT / "package-validation.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    table1(); table2(); table3(); table4(); table5(); table6()
    pres, docf = subsets()
    man = build_manifest()
    v = validate(man, pres, docf)
    print(json.dumps({k: v[k] for k in v if k not in ("consistency_checks",)}, indent=1, ensure_ascii=False))
    print("consistency:", {k: x for k, x in v["consistency_checks"].items() if not x} or "all pass")
