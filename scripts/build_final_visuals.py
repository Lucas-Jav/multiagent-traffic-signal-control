"""Official TCC visual evidence (Prompt 63): compose clips, cards and the summary video.

Reads raw SUMO screenshots captured by ``scripts/record_before_after.py --keep-frames`` (frozen replay
pipeline, official seed 42, predeclared windows in artifacts/demos/final/summary/predeclared_plan.json)
and re-composes them with NEUTRAL labels, the "10 seeds" disclaimer and result cards derived from the
FINAL N=10 analysis tables. No simulation is run here and nothing scientific is modified.

    python scripts/build_final_visuals.py compose <clip>      # e.g. s1_b0_vs_b2, reference_route/b2_vs_c1
    python scripts/build_final_visuals.py three-panel
    python scripts/build_final_visuals.py cards
    python scripts/build_final_visuals.py summary
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from traffic_agents.replay import overlay  # noqa: E402
from traffic_agents.replay.annotations import SHOCK_LABEL  # noqa: E402
from traffic_agents.replay.camera import ViewWindow  # noqa: E402
from traffic_agents.replay.fairness import build_replay_side, resolve_scenario_path  # noqa: E402
from traffic_agents.replay.metadata import frame_path  # noqa: E402
from traffic_agents.replay.network_geometry import intersection_junctions, load_network_geometry  # noqa: E402
from traffic_agents.replay.recorder import _reference_route_polyline  # noqa: E402
from traffic_agents.replay.video import encode_command, encode_frames, find_ffmpeg  # noqa: E402
from traffic_agents.replay.visual_metrics import read_visual_metrics  # noqa: E402

FINAL = REPO / "artifacts/demos/final"
ANALYSIS = REPO / "artifacts/final-analysis"
PLAN = json.loads((FINAL / "summary/predeclared_plan.json").read_text(encoding="utf-8"))
SRC_SHA = PLAN["scientific_source_git_sha"]
FREEZE_SHA = PLAN["freeze_manifest_sha256"]
FPS = 30
SEED = 42
DISCLAIMER = "Visualização ilustrativa — resultados científicos utilizam 10 seeds."
B0, B1, B2, C1, C2 = ("B0_FIXED_CALIBRATED", "B1_LOCAL_ADAPTIVE", "B2_LOCAL_PRESSURE",
                      "C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED")
NAMES = {B0: "Tempo fixo calibrado", B1: "Adaptativo local simples", B2: "Adaptativo local",
         C1: "Cooperativo compacto", C2: "Cooperativo expandido"}
SCENARIO_TITLE = {"S1_BALANCED": "S1 — Demanda balanceada", "S2_DIRECTIONAL_PEAK": "S2 — Pico direcional",
                  "S3_DEMAND_SHIFT": "S3 — Mudança de demanda", "S4_LOCAL_SATURATION": "S4 — Saturação localizada"}
END_CARD_SECONDS = 8
BG = (250, 250, 248)
INK = (28, 36, 44)
MUTED = (96, 108, 118)
BAND = (55, 71, 79)
ACCENT = (0, 105, 140)


# ----------------------------------------------------------------------------------------------
# Numbers from the FINAL N=10 analysis (never typed by hand)
# ----------------------------------------------------------------------------------------------
def _rd(name: str) -> list[dict[str, str]]:
    with (ANALYSIS / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


PW = _rd("final_pairwise_summary.csv")
RRP = _rd("reference_route_pairwise.csv")
RRS = _rd("reference_route_summary.csv")
NVR = _rd("network_vs_reference_route_direction.csv")
S5D = _rd("s5_controller_summary.csv")
COMM = _rd("s5_communication_summary.csv")
OVH = _rd("communication_overhead_ratio.csv")
CTRL = _rd("final_controller_summary.csv")
TELE = json.loads((ANALYSIS / "final_analysis.json").read_text())["s4_teleports"]["per_controller"]


def pt(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def g(scn: str, a: str, b: str, m: str) -> dict[str, str]:
    return next(r for r in PW if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b and r["metric"] == m)


def rel(scn: str, a: str, b: str, m: str) -> str:
    return pt(float(g(scn, a, b, m)["relative_difference_of_means"]) * 100, 1, True) + "%"


def dif(scn: str, a: str, b: str, m: str, d: int = 3) -> str:
    return pt(float(g(scn, a, b, m)["mean_difference"]), d, True)


def cmean(scn: str, c: str, m: str) -> float:
    return float(next(r for r in CTRL if r["scenario"] == scn and r["controller"] == c and r["metric"] == m)["mean"])


def rr(scn: str, a: str, b: str, m: str) -> dict[str, str]:
    return next(r for r in RRP if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b and r["metric"] == m)


def rrm(scn: str, c: str, m: str) -> float:
    return float(next(r for r in RRS if r["scenario"] == scn and r["controller"] == c and r["metric"] == m)["mean"])


TT, CMP = "reference_route_mean_travel_time_seconds", "reference_route_completion_ratio_offered"


# ----------------------------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------------------------
def font(size: int, bold: bool = False):
    return overlay._font(size, bold=bold)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=fnt) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def render_card(size: tuple[int, int], title: str, blocks: list[tuple[str, str]], footnote: str = "",
                kicker: str = "") -> Image.Image:
    """Academic card. blocks: (style, text) with style in {h, p, b, big, note}."""

    w, h = size
    s = h / 1080
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, round(120 * s)), fill=BAND)
    if kicker:
        d.text((round(60 * s), round(14 * s)), kicker, font=font(round(24 * s)), fill=(200, 210, 216))
    d.text((round(60 * s), round(46 * s)), title, font=font(round(44 * s), True), fill=(255, 255, 255))
    y = round(160 * s)
    margin = round(70 * s)
    for style, text in blocks:
        fs = s * (1.3 if w / h > 2 else 1.0)
        fnt = {"h": font(round(38 * fs), True), "p": font(round(32 * fs)), "b": font(round(32 * fs)),
               "big": font(round(52 * fs), True), "note": font(round(26 * fs))}[style]
        color = {"h": ACCENT, "p": INK, "b": INK, "big": INK, "note": MUTED}[style]
        indent = round(30 * s) if style == "b" else 0
        prefix = "•  " if style == "b" else ""
        lines = wrap(d, prefix + text, fnt, w - 2 * margin - indent)
        for ln in lines:
            d.text((margin + indent, y), ln, font=fnt, fill=color)
            y += round(fnt.size + 12 * fs)
        y += round(14 * fs)
    if footnote:
        fl = wrap(d, footnote, font(round(24 * s)), w - 2 * margin)
        fy = h - round(120 * s) - len(fl) * round(30 * s)
        for ln in fl:
            d.text((margin, fy), ln, font=font(round(24 * s)), fill=MUTED)
            fy += round(30 * s)
    d.rectangle((0, h - round(64 * s), w, h), fill=(33, 33, 33))
    d.text((round(30 * s), h - round(48 * s)), DISCLAIMER, font=font(round(24 * s)), fill=(215, 215, 215))
    return img


# ----------------------------------------------------------------------------------------------
# Result texts per clip (every number comes from the final analysis tables)
# ----------------------------------------------------------------------------------------------
def clip_card(clip: str, size: tuple[int, int]) -> Image.Image:
    base = clip.split("/")[-1]
    if clip == "s1_b0_vs_b2":
        scn = "S1_BALANCED"
        return render_card(size, "S1 — Resultado final com 10 seeds", [
            ("h", "Tempo fixo calibrado → Adaptativo local"),
            ("b", f"Espera {rel(scn, B0, B2, 'mean_waiting_time')}, perda de tempo {rel(scn, B0, B2, 'mean_time_loss')}, fila média {rel(scn, B0, B2, 'mean_network_queue_vehicles')}; vazão {rel(scn, B0, B2, 'throughput')}."),
            ("p", "Em S1, o adaptativo local (B2) teve melhor desempenho que o tempo fixo calibrado (B0)."),
            ("note", "Resultado específico de S1: em S2, S3 e S4 o tempo fixo calibrado foi mais competitivo."),
        ], "Variação relativa média pareada por seed (B2 vs B0); IC95% por bootstrap exclui zero nas métricas citadas. A seed 42 mostrada é apenas ilustrativa.", "Contexto científico")
    if clip == "s1_b2_vs_c1":
        scn = "S1_BALANCED"
        return render_card(size, "S1 — Resultado final com 10 seeds", [
            ("h", "Adaptativo local → Cooperativo compacto"),
            ("b", f"Com a cooperação: espera {rel(scn, B2, C1, 'mean_waiting_time')}, fila média {rel(scn, B2, C1, 'mean_network_queue_vehicles')}, conclusão {dif(scn, B2, C1, 'completion_ratio_offered')} (fração oferecida)."),
            ("p", "Em S1, o adaptativo local (B2) teve melhor desempenho que o cooperativo compacto (C1), em 10/10 seeds nas métricas de atraso."),
            ("big", "A cooperação não ajudou de forma universal."),
        ], "Variação relativa média pareada por seed (C1 vs B2). A seed 42 mostrada é apenas ilustrativa.", "Contexto científico")
    if clip == "s2_b2_vs_c1":
        scn = "S2_DIRECTIONAL_PEAK"
        return render_card(size, "S2 — Resultado final com 10 seeds", [
            ("big", "Trade-off entre métricas"),
            ("h", "Trade-off: menos fila, menor capacidade concluída"),
            ("b", f"Cooperativo vs adaptativo local — espera {rel(scn, B2, C1, 'mean_waiting_time')}, fila média {rel(scn, B2, C1, 'mean_network_queue_vehicles')} (10/10 seeds)."),
            ("b", f"Vazão {rel(scn, B2, C1, 'throughput')}; conclusão {pt(cmean(scn, B2, 'completion_ratio_offered'), 3)} → {pt(cmean(scn, C1, 'completion_ratio_offered'), 3)}; {pt(float(g(scn, B2, C1, 'never_inserted_vehicle_count')['mean_difference']), 0, True)} veículos a mais não inseridos."),
            ("note", "Tempo de viagem menor é condicional a menos viagens concluídas; nenhum controlador é apontado como vencedor."),
        ], "Variação relativa média pareada por seed (C1 vs B2). A seed 42 mostrada é apenas ilustrativa.", "Contexto científico")
    if clip == "s3_b2_vs_c1":
        scn = "S3_DEMAND_SHIFT"
        return render_card(size, "S3 — Resultado final com 10 seeds", [
            ("h", "Mudança de demanda — rede inteira"),
            ("b", f"Na rede, o adaptativo local (B2) teve melhor desempenho: com a cooperação, espera {rel(scn, B2, C1, 'mean_waiting_time')}, fila média {rel(scn, B2, C1, 'mean_network_queue_vehicles')}, área de fila pós-choque {rel(scn, B2, C1, 'post_shock_queue_auc_vehicle_seconds')}."),
            ("note", "Metodologia de S3 congelada (choque em 2100 s); nenhuma métrica nova de recuperação. O gate composto de validade foi formalizado post-hoc."),
            ("note", "Rota de referência conta outra história: ver cartão \"rede e rota\"."),
        ], "Variação relativa média pareada por seed (C1 vs B2). A seed 42 mostrada é apenas ilustrativa.", "Contexto científico")
    if clip == "s4_b2_vs_c1":
        scn = "S4_LOCAL_SATURATION"
        t = TELE
        tot = sum(v["total"] for v in t.values())
        return render_card(size, "S4 — Resultado final com 10 seeds", [
            ("big", "Cooperação ajudou sob saturação localizada"),
            ("b", f"Cooperativo vs adaptativo local: vazão {rel(scn, B2, C1, 'throughput')}, espera {rel(scn, B2, C1, 'mean_waiting_time')}, fila média {rel(scn, B2, C1, 'mean_network_queue_vehicles')} (10/10 seeds)."),
            ("b", f"Mas o atraso de partida piorou ({rel(scn, B2, C1, 'mean_depart_delay_seconds')}); saturação severa: só {pt(min(cmean(scn, c, 'completion_ratio_offered') for c in (B0, B1, B2, C1, C2)) * 100, 0)}–{pt(max(cmean(scn, c, 'completion_ratio_offered') for c in (B0, B1, B2, C1, C2)) * 100, 0)}% das viagens oferecidas concluem."),
            ("note", f"Teleports SUMO foram medidos e mantidos nos resultados ({tot:.0f} no total: B0 {t[B0]['total']:.0f}, B2 {t[B2]['total']:.0f}, demais 0)."),
        ], "Variação relativa média pareada por seed (C1 vs B2). Métricas de tempo valem para as viagens concluídas. A seed 42 mostrada é apenas ilustrativa.", "Contexto científico")
    if base in ("b0_vs_b2", "b2_vs_c1", "three_panel") and clip.startswith("reference_route"):
        return reference_card(size)
    raise KeyError(clip)


def reference_card(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = render_card(size, "Rota de referência — resultado final (10 seeds)", [
        ("p", "left1A1 → A1B1 → B1C1 → C1right1. Sequência exata de arestas planejada."),
        ("b", "S1: B0 → B2 melhora o tempo de viagem; B2 → C1 piora."),
        ("b", "S2–S4: B0 → B2 piora o tempo de viagem condicional; B2 → C1 melhora o tempo condicional."),
        ("note", "A conclusão também importa: tempos valem só para viagens concluídas."),
    ], "Tempo de viagem médio (s) e fração concluída (oferecida). Δ = variação pareada média por seed.", "Contexto científico")
    d = ImageDraw.Draw(img)
    s = h / 1080
    x0, y0 = round(70 * s), round(540 * s)
    cols = ["Cenário", "Tempo fixo calibrado", "Adaptativo local", "Coop. compacto", "Δ B0→B2 (s)", "Δ B2→C1 (s)"]
    cw = [round(x * s) for x in (130, 330, 330, 330, 340, 340)]
    fnt, fb = font(round(26 * s)), font(round(26 * s), True)
    xs = [x0]
    for c in cw[:-1]:
        xs.append(xs[-1] + c)
    d.rectangle((x0 - 10, y0 - 8, x0 + sum(cw), y0 + round(40 * s)), fill=(228, 233, 236))
    for x, c in zip(xs, cols, strict=True):
        d.text((x, y0), c, font=fb, fill=INK)
    y = y0 + round(54 * s)
    for scn in ("S1_BALANCED", "S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"):
        vals = [scn.split("_")[0]]
        for c in (B0, B2, C1):
            vals.append(f"{pt(rrm(scn, c, TT), 0)} s · concl. {pt(rrm(scn, c, CMP), 3)}")
        vals.append(pt(float(rr(scn, B0, B2, TT)["paired_mean_diff"]), 1, True))
        vals.append(pt(float(rr(scn, B2, C1, TT)["paired_mean_diff"]), 1, True))
        for x, v in zip(xs, vals, strict=True):
            d.text((x, y), v, font=fnt, fill=INK)
        y += round(46 * s)
    return img


def netroute_card(size: tuple[int, int]) -> Image.Image:
    scn = "S3_DEMAND_SHIFT"
    n = next(r for r in NVR if r["scenario"] == scn and r["comparison"] == f"{B2}->{C1}")
    rtt = rr(scn, B2, C1, TT)
    rcm = rr(scn, B2, C1, CMP)
    ncm = g(scn, B2, C1, "completion_ratio_offered")
    img = render_card(size, "S3: rede e rota contam histórias diferentes", [
        ("h", "Rede inteira — adaptativo local → cooperativo compacto"),
        ("b", f"Tempo de viagem {pt(float(n['network_mean_travel_time_diff']), 1, True)} s [{'; '.join(pt(float(v), 1) for v in n['network_mean_travel_time_ci'].strip('[]').split(','))}]; conclusão {dif(scn, B2, C1, 'completion_ratio_offered')} (IC95% exclui zero)."),
        ("p", "Na rede, o adaptativo local (B2) teve melhor desempenho que o cooperativo (C1)."),
        ("h", "Rota de referência (left1A1 → A1B1 → B1C1 → C1right1)"),
        ("b", f"Tempo de viagem {pt(float(rtt['paired_mean_diff']), 1, True)} s [{pt(float(rtt['ci95_low']), 1)}; {pt(float(rtt['ci95_high']), 1)}]; conclusão {pt(float(rcm['paired_mean_diff']), 3, True)} (IC inclui zero)."),
        ("p", "Na rota, o cooperativo (C1) reduziu o tempo de viagem condicional em relação a B2."),
        ("note", "Não é contradição automática: rede inteira e coorte da rota são populações diferentes."),
    ], "Diferenças pareadas por seed (C1 − B2), N = 10; IC95% por bootstrap. Tempos de viagem são condicionais a viagens concluídas.", "Cartão explicativo")
    return img


def s5_series() -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = {}
    for metric in ("throughput", "mean_waiting_time", "completion_ratio_offered", "mean_network_queue_vehicles"):
        out[metric] = {}
        for lab, key in (("C1", "C1_COOPERATIVE_COMPACT@{p}"), ("C2", "C2_COOPERATIVE_EXPANDED@{p}")):
            out[metric][lab] = [float(next(r for r in S5D if r["controller"] == key.format(p=p) and r["metric"] == metric)["mean"])
                                for p in ("0.00", "0.20", "0.50", "1.00")]
        out[metric]["B2"] = [float(next(r for r in S5D if r["controller"] == "B2_LOCAL_PRESSURE@REF" and r["metric"] == metric)["mean"])] * 4
    return out


def s5_card(size: tuple[int, int]) -> Image.Image:
    w, h = size
    ser = s5_series()
    fig, axes = plt.subplots(1, 3, figsize=(w / 100 * 0.93, h / 100 * 0.40), dpi=100)
    xs = [0, 20, 50, 100]
    for ax, (metric, ttl) in zip(axes, (("throughput", "Vazão (veículos concluídos)"), ("completion_ratio_offered", "Conclusão (fração oferecida)"),
                                       ("mean_waiting_time", "Espera média (s)")), strict=True):
        ax.plot(xs, ser[metric]["C1"], "-o", color="#1f6f9f", label="Cooperativo compacto (C1)", lw=2.4)
        ax.plot(xs, ser[metric]["C2"], "-s", color="#d98000", label="Cooperativo expandido (C2)", lw=2.4)
        ax.plot(xs, ser[metric]["B2"], "--", color="#5b6770", label="Adaptativo local (B2, referência)", lw=2)
        ax.set_title(ttl, fontsize=13)
        ax.set_xlabel("Perda de pacotes (%)", fontsize=11)
        ax.set_xticks(xs)
        ax.grid(alpha=0.25)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=11)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    tmp = FINAL / "summary/_s5_chart.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(tmp, dpi=100, facecolor=(1, 1, 1))
    plt.close(fig)
    sent = sum(float(r["total_messages_sent"]) for r in COMM if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    dlv = sum(float(r["total_messages_delivered"]) for r in COMM if r["experiment"] == "FINAL_S5" and float(r["packet_loss"]) == 1.0)
    img = render_card(size, "S5 — Degradação de comunicação (S2, 10 seeds)", [
        ("big", "Degradação não monotônica"),
        ("b", "Com 20% e 50% de perda, C1 e C2 tiveram vazão e conclusão maiores que com 0%; C2 teve o pior ponto com comunicação completa."),
        ("b", f"Com 100% de perda: {dlv:.0f} mensagens entregues ({f'{sent:,.0f}'.replace(',', '.')} enviadas, todas descartadas) e métricas de tráfego de C1 e C2 idênticas às de B2. Fallback operacional."),
    ], "Sem limiar de tolerância declarado e sem prova formal de segurança de sinal. Perda simulada no barramento de mensagens; não é animação de pacotes.", "Contexto científico")
    chart = Image.open(tmp).convert("RGB")
    chart = chart.resize((round(w * 0.93), round(chart.height * (w * 0.93) / chart.width)))
    img.paste(chart, (round(w * 0.035), round(h * 0.50)))
    return img


def cost_card(size: tuple[int, int]) -> Image.Image:
    w, h = size
    o = next(r for r in OVH if r["experiment"] == "FINAL_S5" and r["scenario"] == "S2_DIRECTIONAL_PEAK" and float(r["packet_loss"]) == 0.0)
    c1mb, c2mb = float(o["C1_mean_bytes_sent"]) / 1e6, float(o["C2_mean_bytes_sent"]) / 1e6
    sent = float(next(r for r in COMM if r["experiment"] == "FINAL_S5" and r["controller"] == C1 and float(r["packet_loss"]) == 0.0)["mean_messages_sent"])
    img = render_card(size, "Custo de comunicação: C1 vs C2", [
        ("b", f"Ambos enviam {int(sent):,} mensagens por run.".replace(",", ".")),
        ("big", f"C2 ≈ {pt(float(o['C2_over_C1_bytes_sent']), 1)}× o volume de comunicação do C1"),
        ("p", "No final, o maior custo de comunicação do C2 não produziu benefício geral de tráfego."),
        ("note", "Em S1–S3 o C2 teve desempenho pior que o C1; em S4 houve trade-off (menor espera e fila, maior atraso de partida)."),
    ], "Bytes enviados por run (S2, perda 0%, média de 10 seeds); mesmo número de mensagens, mensagem maior no C2.", "Contexto científico")
    d = ImageDraw.Draw(img)
    s = h / 1080
    x0, base_y = round(300 * s), round(960 * s)
    maxw = round(900 * s)
    for i, (lab, mb, col) in enumerate((("Cooperativo compacto (C1)", c1mb, (31, 111, 159)), ("Cooperativo expandido (C2)", c2mb, (217, 128, 0)))):
        y = round(590 * s) + i * round(120 * s)
        d.text((round(70 * s), y + 12), lab, font=font(round(26 * s)), fill=INK)
        bw = round(maxw * mb / max(c1mb, c2mb))
        d.rectangle((x0 + round(220 * s), y, x0 + round(220 * s) + bw, y + round(70 * s)), fill=col)
        d.text((x0 + round(220 * s) + bw + 16, y + 16), f"~{pt(mb, 0)} MB/run", font=font(round(30 * s), True), fill=INK)
    return img


def conclusion_card(size: tuple[int, int]) -> Image.Image:
    return render_card(size, "Conclusão", [
        ("p", "A cooperação não foi universalmente superior."),
        ("p", "Seu efeito dependeu do cenário."),
        ("p", "O maior benefício apareceu sob saturação localizada, enquanto em outros regimes o controle adaptativo local ou até o tempo fixo calibrado foram mais competitivos."),
        ("note", "Simulação SUMO, rede 3×3, 10 seeds por condição; resultados sob os parâmetros congelados dos controladores."),
    ], "", "Síntese dos resultados finais")


# ----------------------------------------------------------------------------------------------
# Clip composition
# ----------------------------------------------------------------------------------------------
def footer_image(width: int, scenario: str, t: float) -> Image.Image:
    f = Image.new("RGB", (width, overlay.FOOTER_HEIGHT), (33, 33, 33))
    d = ImageDraw.Draw(f)
    d.text((16, 7), f"{SCENARIO_TITLE[scenario]}   |   Seed {SEED} (demonstração)   |   Tempo da simulação: {overlay.format_clock(t)} (t = {t:.0f} s)",
           font=overlay._font(22, bold=True), fill=(255, 255, 255))
    d.text((16, 37), DISCLAIMER, font=overlay._font(18, bold=False), fill=(200, 200, 200))
    return f


def stack(pane: Image.Image, scenario: str, t: float) -> Image.Image:
    fr = Image.new("RGB", (pane.width, pane.height + overlay.FOOTER_HEIGHT))
    fr.paste(pane, (0, 0))
    fr.paste(footer_image(pane.width, scenario, t), (0, pane.height))
    return fr


def sbs(panes: list[Image.Image], scenario: str, t: float) -> Image.Image:
    gap = overlay.DIVIDER_WIDTH
    width = sum(p.width for p in panes) + gap * (len(panes) - 1)
    fr = Image.new("RGB", (width, panes[0].height + overlay.FOOTER_HEIGHT), (255, 255, 255))
    x = 0
    for p in panes:
        fr.paste(p, (x, 0))
        x += p.width + gap
    fr.paste(footer_image(width, scenario, t), (0, panes[0].height))
    return fr


def contexts_for(clip_dir: Path, spec: dict) -> dict[str, overlay.PaneContext]:
    cmp = json.loads((clip_dir / "comparison.json").read_text(encoding="utf-8"))
    scenario_path = resolve_scenario_path(spec["scenario"], SEED, REPO / "scenarios/grid_3x3")
    side = build_replay_side(scenario_path=scenario_path, controller_id=spec["a"], seed=SEED)
    geometry = load_network_geometry(side.scenario_dir / side.config.network_file)
    l2j = intersection_junctions(side.config, geometry)
    labels = cmp["camera"]["labels"]
    pts = {lab: geometry.junction_position(l2j[lab]) for lab in labels}
    poly = _reference_route_polyline(geometry) if cmp.get("reference_route") else []
    view = ViewWindow(*cmp["camera"]["view_world_m"])
    w, h = cmp["camera"]["resolution_px"]
    mk = lambda cid: overlay.PaneContext(title=NAMES[cid], controller_id=cid, view=view, width=w, height=h,  # noqa: E731
                                         label_points=pts, route_polyline=poly)
    return {"before": mk(spec["a"]), "after": mk(spec["b"])}, cmp


def write_pipe(ffmpeg: str, width: int, height: int, out: Path) -> subprocess.Popen:
    return subprocess.Popen(encode_command(ffmpeg, width=width, height=height, fps=FPS, output=out),
                            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)


def compose_clip(clip: str, keep_frames: bool = False) -> None:
    spec = PLAN["clips"][clip]
    clip_dir = FINAL / clip
    ctx, cmp = contexts_for(clip_dir, spec)
    rows = {k: read_visual_metrics(clip_dir / f"visual_metrics_{k}.csv") for k in ("before", "after")}
    n = len(rows["before"])
    start = spec["start"]
    shock = cmp.get("shock_marker")
    ffmpeg = find_ffmpeg()
    w, h = cmp["camera"]["resolution_px"]
    pane_h = h + overlay.HEADER_HEIGHT
    total_h = pane_h + overlay.FOOTER_HEIGHT
    sbs_w = 2 * w + overlay.DIVIDER_WIDTH
    outs = {"before": clip_dir / "before.mp4", "after": clip_dir / "after.mp4", "side_by_side": clip_dir / "side_by_side.mp4"}
    pipes = {"before": write_pipe(ffmpeg, w, total_h, outs["before"]), "after": write_pipe(ffmpeg, w, total_h, outs["after"]),
             "side_by_side": write_pipe(ffmpeg, sbs_w, total_h, outs["side_by_side"])}
    thumb_idx = (n - 1) // 2
    try:
        for i, (rb, ra) in enumerate(zip(rows["before"], rows["after"], strict=True)):
            step = start + i
            assert rb.simulation_step == step == ra.simulation_step
            active = bool(shock and shock["start_step"] <= step < shock["end_step"])
            panes = {}
            for side, row in (("before", rb), ("after", ra)):
                with Image.open(frame_path(clip_dir, side, i)) as raw:
                    panes[side] = overlay.compose_pane(
                        raw, ctx[side], overlay.FrameState(simulation_time_s=row.simulation_time_s, network_queue=row.network_queue,
                                                          arrived_count=row.arrived_count, shock_active=active), shock_text=SHOCK_LABEL)
            t = rb.simulation_time_s
            frames = {"before": stack(panes["before"], spec["scenario"], t), "after": stack(panes["after"], spec["scenario"], t),
                      "side_by_side": sbs([panes["before"], panes["after"]], spec["scenario"], t)}
            for k, fr in frames.items():
                pipes[k].stdin.write(fr.tobytes())
            if i == thumb_idx:
                frames["side_by_side"].save(clip_dir / "thumbnail.png")
        # end card only on the comparison video
        card = clip_card(clip, (sbs_w, total_h))
        for _ in range(END_CARD_SECONDS * FPS):
            pipes["side_by_side"].stdin.write(card.tobytes())
        card.save(clip_dir / "end_card.png")
    finally:
        for p in pipes.values():
            p.stdin.close()
        for p in pipes.values():
            p.wait()
    # traceability
    cmp.update({
        "official_seed": SEED, "seed": SEED, "official_demo_seed": True,
        "controllers": {"A_before_panel": spec["a"], "B_after_panel": spec["b"]},
        "neutral_panel_labels": {spec["a"]: NAMES[spec["a"]], spec["b"]: NAMES[spec["b"]]},
        "scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": FREEZE_SHA,
        "camera_preset": spec["camera"], "start_step": spec["start"], "end_step": spec["end"], "fps": FPS,
        "disclaimer": DISCLAIMER,
        "final_analysis_reference": {"markdown": "docs/evidencias/final-analysis/final_analysis.md",
                                     "final_analysis_json_sha256": hashlib.sha256((ANALYSIS / "final_analysis.json").read_bytes()).hexdigest(),
                                     "pairwise_csv": "docs/evidencias/final-analysis/final_pairwise_summary.csv"},
        "predeclared_plan": {"path": "artifacts/demos/final/summary/predeclared_plan.json",
                             "sha256": hashlib.sha256((FINAL / "summary/predeclared_plan.json").read_bytes()).hexdigest()},
        "composition": {"tool": "scripts/build_final_visuals.py", "replaced_recorder_default_overlays": True,
                        "reason": "neutral panel labels and the '10 seeds' disclaimer (recorder defaults say ANTES/DEPOIS and 'múltiplas seeds')",
                        "end_card_seconds": END_CARD_SECONDS, "end_card_file": "end_card.png",
                        "live_overlays": ["simulation_time", "network_queue (halting vehicles)", "arrived_vehicles"]},
        "outputs": {"before": "before.mp4", "after": "after.mp4", "side_by_side": "side_by_side.mp4", "thumbnail": "thumbnail.png",
                    "end_card": "end_card.png", "visual_metrics_before": "visual_metrics_before.csv",
                    "visual_metrics_after": "visual_metrics_after.csv"},
        "window_selection": PLAN["window_rule"],
    })
    (clip_dir / "comparison.json").write_text(json.dumps(cmp, indent=2) + "\n", encoding="utf-8")
    if not keep_frames:
        shutil.rmtree(clip_dir / "frames", ignore_errors=True)
        (clip_dir / "capture_state.json").unlink(missing_ok=True)
    print("composed", clip, n, "frames")


def three_panel() -> None:
    ref = FINAL / "reference_route"
    spec_a, spec_b = PLAN["clips"]["reference_route/b0_vs_b2"], PLAN["clips"]["reference_route/b2_vs_c1"]
    ctx_a, cmp_a = contexts_for(ref / "b0_vs_b2", spec_a)
    ctx_b, cmp_b = contexts_for(ref / "b2_vs_c1", spec_b)
    ra = {k: read_visual_metrics(ref / "b0_vs_b2" / f"visual_metrics_{k}.csv") for k in ("before", "after")}
    rb = {k: read_visual_metrics(ref / "b2_vs_c1" / f"visual_metrics_{k}.csv") for k in ("before", "after")}
    n = len(ra["before"])
    ffmpeg = find_ffmpeg()
    scale = 0.75
    pw_, ph_ = round(1280 * scale), round(720 * scale)
    out = ref / "three_panel.mp4"
    ident = 0
    sample_equal = []

    def small(p: Image.Image) -> Image.Image:
        return p.resize((round(p.width * scale), round(p.height * scale)), Image.LANCZOS)

    first = None
    frames_dir_a, frames_dir_b = ref / "b0_vs_b2", ref / "b2_vs_c1"

    def gen():
        nonlocal ident, first
        for i in range(n):
            panes = []
            for clip_dir, side, ctx, rows_ in ((frames_dir_a, "before", ctx_a["before"], ra["before"]),
                                               (frames_dir_a, "after", ctx_a["after"], ra["after"]),
                                               (frames_dir_b, "after", ctx_b["after"], rb["after"])):
                row = rows_[i]
                with Image.open(frame_path(clip_dir, side, i)) as raw:
                    panes.append(small(overlay.compose_pane(raw, ctx, overlay.FrameState(
                        simulation_time_s=row.simulation_time_s, network_queue=row.network_queue, arrived_count=row.arrived_count),
                        shock_text=SHOCK_LABEL)))
            # sync/identity check of the shared middle controller across the two recordings
            if i % 200 == 0:
                with Image.open(frame_path(frames_dir_a, "after", i)) as x, Image.open(frame_path(frames_dir_b, "before", i)) as y:
                    sample_equal.append(x.tobytes() == y.tobytes())
                assert ra["after"][i].network_queue == rb["before"][i].network_queue
            fr = sbs(panes, spec_a["scenario"], ra["before"][i].simulation_time_s)
            if i == (n - 1) // 2:
                fr.save(ref / "three_panel_thumbnail.png")
            if first is None:
                first = fr.size
            yield fr

    # prime to learn the size
    gen_it = gen()
    f0 = next(gen_it)

    def chain():
        yield f0
        yield from gen_it
        card = reference_card(f0.size)
        card.save(ref / "three_panel_end_card.png")
        for _ in range(END_CARD_SECONDS * FPS):
            yield card

    encode_frames(chain(), width=f0.width, height=f0.height, fps=FPS, output=out, ffmpeg=ffmpeg)
    cmp = {
        "scenario": spec_a["scenario"], "seed": SEED, "official_seed": SEED, "official_demo_seed": True,
        "controllers": [B0, B2, C1], "neutral_panel_labels": [NAMES[B0], NAMES[B2], NAMES[C1]],
        "camera_preset": "reference_route", "start_step": spec_a["start"], "end_step": spec_a["end"], "fps": FPS,
        "reference_route": ["left1A1", "A1B1", "B1C1", "C1right1"],
        "scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": FREEZE_SHA, "disclaimer": DISCLAIMER,
        "source_recordings": ["reference_route/b0_vs_b2", "reference_route/b2_vs_c1"],
        "shared_panel_check": {"controller": B2, "sampled_frames_pixel_identical_across_recordings": all(sample_equal),
                               "samples": len(sample_equal)},
        "scale": scale, "frames": n, "end_card_seconds": END_CARD_SECONDS,
        "final_analysis_reference": {"markdown": "docs/evidencias/final-analysis/final_analysis.md",
                                     "reference_route_csv": "docs/evidencias/final-analysis/reference_route_pairwise.csv"},
        "predeclared_plan_sha256": hashlib.sha256((FINAL / "summary/predeclared_plan.json").read_bytes()).hexdigest(),
        "outputs": {"video": "three_panel.mp4", "thumbnail": "three_panel_thumbnail.png", "end_card": "three_panel_end_card.png"},
    }
    (ref / "comparison.json").write_text(json.dumps(cmp, indent=2) + "\n", encoding="utf-8")
    thumb = Image.open(ref / "three_panel_thumbnail.png")
    thumb.save(ref / "thumbnail.png")
    print("three panel", n, "frames; shared panel identical:", all(sample_equal))


# ----------------------------------------------------------------------------------------------
def build_cards() -> None:
    size = (1920, 1080)
    (FINAL / "reference_route").mkdir(parents=True, exist_ok=True)
    (FINAL / "s5").mkdir(parents=True, exist_ok=True)
    (FINAL / "summary").mkdir(parents=True, exist_ok=True)
    reference_card(size).save(FINAL / "reference_route/reference_route_context_card.png")
    netroute_card(size).save(FINAL / "reference_route/s3_network_vs_route_card.png")
    s5_card(size).save(FINAL / "s5/s5_result_card.png")
    cost_card(size).save(FINAL / "s5/c1_c2_cost_card.png")
    conclusion_card(size).save(FINAL / "summary/conclusion_card.png")
    # static videos for the S5 and cost cards (so each "video/card" also exists as mp4)
    ffmpeg = find_ffmpeg()
    for png, mp4 in (("s5/s5_result_card.png", "s5/s5_result_card.mp4"), ("s5/c1_c2_cost_card.png", "s5/c1_c2_cost_card.mp4")):
        img = Image.open(FINAL / png).convert("RGB")
        encode_frames((img for _ in range(8 * FPS)), width=img.width, height=img.height, fps=FPS, output=FINAL / mp4, ffmpeg=ffmpeg)
    (FINAL / "s5/comparison.json").write_text(json.dumps({
        "kind": "result card derived from the FINAL N=10 analysis (no packet animation)",
        "scenario_traffic_base": "S2_DIRECTIONAL_PEAK", "seeds": "10 final seeds (card shows means); demonstration seed 42 not used for S5",
        "packet_loss_levels": [0.0, 0.2, 0.5, 1.0], "controllers": [C1, C2, B2],
        "scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": FREEZE_SHA, "disclaimer": DISCLAIMER,
        "final_analysis_reference": {"s5_controller_summary": "docs/evidencias/final-analysis/s5_controller_summary.csv",
                                     "s5_communication_summary": "docs/evidencias/final-analysis/s5_communication_summary.csv",
                                     "communication_overhead_ratio": "docs/evidencias/final-analysis/communication_overhead_ratio.csv"},
        "outputs": {"s5_card": "s5_result_card.png", "s5_video": "s5_result_card.mp4", "cost_card": "c1_c2_cost_card.png",
                    "cost_video": "c1_c2_cost_card.mp4"},
        "labels": {"s5": "Degradação não monotônica; Fallback operacional", "not_claimed": ["tolerante a 100% de perda", "prova formal de segurança"]},
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copy2(FINAL / "s5/s5_result_card.png", FINAL / "s5/thumbnail.png")
    print("cards done")


def segment_from_png(png: Path, seconds: float, out: Path, ffmpeg: str) -> None:
    img = Image.open(png).convert("RGB").resize((1920, 1080))
    encode_frames((img for _ in range(round(seconds * FPS))), width=1920, height=1080, fps=FPS, output=out, ffmpeg=ffmpeg)


def segment_from_clip(clip_dir: Path, n_frames: int, out: Path, ffmpeg: str, speed: int = 8) -> None:
    vf = (f"select='lt(n,{n_frames})',setpts=N/({FPS}*TB),setpts=PTS/{speed},fps={FPS},scale=1920:-2,"
          f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x{BAND[0]:02x}{BAND[1]:02x}{BAND[2]:02x},format=yuv420p")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(clip_dir / "side_by_side.mp4"), "-vf", vf, "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)


def build_summary() -> None:
    ffmpeg = find_ffmpeg()
    tmp = FINAL / "summary/_segments"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    size = (1920, 1080)
    problem = render_card(size, "O problema", [
        ("p", "Semáforos urbanos isolados reagem apenas ao tráfego local; tempo fixo ignora variações de demanda."),
        ("p", "Pergunta de pesquisa: a troca local de informação entre controladores descentralizados melhora o desempenho da rede, em comparação com um adaptativo local sem cooperação e com o tempo fixo, sob diferentes demandas?"),
        ("note", "Resposta não definida previamente; todas as conclusões vêm de 290 runs finais congeladas."),
    ], "", "Controle distribuído e cooperativo de semáforos urbanos")
    net = render_card(size, "Rede 3×3 multiagente (SUMO)", [
        ("b", "9 interseções semaforizadas, um agente por interseção."),
        ("b", "Controladores: tempo fixo calibrado (B0), adaptativo local simples (B1), adaptativo local por pressão (B2), cooperativo compacto (C1) e cooperativo expandido (C2)."),
        ("b", "4 cenários de demanda (S1–S4) + experimento de perda de comunicação (S5); 10 seeds por condição."),
        ("note", "Os vídeos a seguir mostram a seed 42, apenas para ilustração: cada trecho é a janela predeclarada, a 8× de velocidade."),
    ], "", "Método")
    cards = {"problem": problem, "network": net}
    for k, img in cards.items():
        img.save(tmp / f"{k}.png")
    seq: list[Path] = []
    plan: list[tuple[str, float]] = []

    def add_png(name: str, img: Image.Image, seconds: float) -> None:
        p = tmp / f"{name}.png"
        img.save(p)
        out = tmp / f"{name}.mp4"
        segment_from_png(p, seconds, out, ffmpeg)
        seq.append(out)
        plan.append((name, seconds))

    def add_clip(clip: str, name: str, card_seconds: float) -> None:
        spec = PLAN["clips"][clip]
        n = spec["end"] - spec["start"]
        out = tmp / f"{name}_clip.mp4"
        segment_from_clip(FINAL / clip, n, out, ffmpeg)
        seq.append(out)
        plan.append((f"{name}_clip", n / 8 / FPS))
        add_png(f"{name}_card", clip_card(clip, size), card_seconds)

    add_png("01_problem", problem, 5)
    add_png("02_network", net, 6)
    add_clip("s1_b0_vs_b2", "03_s1_b0_vs_b2", 5)
    add_clip("s1_b2_vs_c1", "04_s1_b2_vs_c1", 5)
    add_clip("s2_b2_vs_c1", "05_s2_b2_vs_c1", 5)
    add_clip("s3_b2_vs_c1", "06_s3_b2_vs_c1", 5)
    add_clip("s4_b2_vs_c1", "07_s4_b2_vs_c1", 6)
    # reference route: three-panel excerpt = same uniform rule
    ref_dir = FINAL / "reference_route"
    n_ref = PLAN["clips"]["reference_route/b0_vs_b2"]["end"] - PLAN["clips"]["reference_route/b0_vs_b2"]["start"]
    out = tmp / "08_reference_clip.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(ref_dir / "three_panel.mp4"), "-vf",
                    f"select='lt(n,{n_ref})',setpts=N/({FPS}*TB),setpts=PTS/8,fps={FPS},scale=1920:-2,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x374f4f,format=yuv420p",
                    "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)
    seq.append(out)
    plan.append(("08_reference_clip", n_ref / 8 / FPS))
    add_png("08_reference_card", reference_card(size), 6)
    add_png("08b_s3_network_vs_route", netroute_card(size), 5)
    add_png("09_s5", s5_card(size), 7)
    add_png("09b_cost", cost_card(size), 4)
    add_png("10_conclusion", conclusion_card(size), 8)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in seq), encoding="utf-8")
    final = FINAL / "tcc_summary.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final)], check=True)
    dur = float(subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                               capture_output=True, text=True).stdout.strip() or 0)
    (FINAL / "summary/summary_manifest.json").write_text(json.dumps({
        "video": "tcc_summary.mp4", "duration_seconds": dur, "resolution": "1920x1080", "fps": FPS,
        "segments": plan, "excerpt_rule": PLAN["summary_excerpt_rule"], "official_seed": SEED,
        "scientific_source_git_sha": SRC_SHA, "freeze_manifest_sha256": FREEZE_SHA, "disclaimer": DISCLAIMER,
        "final_analysis_reference": "docs/evidencias/final-analysis/final_analysis.md",
        "predeclared_plan_sha256": hashlib.sha256((FINAL / "summary/predeclared_plan.json").read_bytes()).hexdigest(),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Image.open(tmp / "07_s4_b2_vs_c1_card.png").save(FINAL / "summary/thumbnail.png")
    shutil.rmtree(tmp, ignore_errors=True)
    print("summary", dur, "s")


def main() -> int:
    cmd = sys.argv[1]
    if cmd == "compose":
        compose_clip(sys.argv[2], keep_frames="--keep-frames" in sys.argv)
    elif cmd == "three-panel":
        three_panel()
    elif cmd == "cards":
        build_cards()
    elif cmd == "summary":
        build_summary()
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
