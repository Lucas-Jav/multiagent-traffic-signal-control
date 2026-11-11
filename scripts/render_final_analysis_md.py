"""Renderiza artifacts/final-analysis/final_analysis.md a partir dos CSVs da análise e copia a
evidência leve para docs/evidencias/final-analysis/. Lê apenas saídas da análise; não executa simulação."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import statistics
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts/final-analysis"
EVID = REPO / "docs/evidencias/final-analysis"
SCEN = ["S1_BALANCED", "S2_DIRECTIONAL_PEAK", "S3_DEMAND_SHIFT", "S4_LOCAL_SATURATION"]
B0, B1, B2, C1, C2 = ("B0_FIXED_CALIBRATED", "B1_LOCAL_ADAPTIVE", "B2_LOCAL_PRESSURE",
                      "C1_COOPERATIVE_COMPACT", "C2_COOPERATIVE_EXPANDED")
SHORT = {B0: "B0", B1: "B1", B2: "B2", C1: "C1", C2: "C2"}


def rd(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(x, d=2, pct=False, sign=False):
    if x in ("", None, "nan", "None"):
        return "n/a"
    v = float(x)
    if pct:
        return f"{v * 100:+.1f}%" if sign else f"{v * 100:.1f}%"
    return f"{v:+.{d}f}" if sign else f"{v:.{d}f}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


PW = rd("final_pairwise_summary.csv")
SUPP = rd("supplementary_B0_vs_cooperative_exploratory.csv")
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
OVH = rd("communication_overhead_ratio.csv")
PVF = rd("pilot_vs_final.csv")
N10 = rd("n10_variability.csv")
TELE = rd("s4_teleports_by_run.csv")
VAL = json.loads((OUT / "analysis-validation.json").read_text())
ANA = json.loads((OUT / "final_analysis.json").read_text())


def g(scn, a, b, metric):
    return next(r for r in PW if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b and r["metric"] == metric)


def gs(scn, a, b, metric):
    return next(r for r in SUPP if r["scenario"] == scn and r["baseline"] == a and r["treatment"] == b and r["metric"] == metric)


def dmean(scn, ctrl, metric, key="mean"):
    return next(float(r[key]) for r in DESC if r["scenario"] == scn and r["controller"] == ctrl and r["metric"] == metric)


def ci(r):
    return f"[{num(r['ci95_low'], 2)}; {num(r['ci95_high'], 2)}]"


def cell(r, d=2, rel=True):
    base = f"{num(r['mean_difference'], d, sign=True)} ({num(r['relative_difference_of_means'], pct=True, sign=True)}) {ci(r)}" if rel and r["relative_difference_of_means"] not in ("", None) else f"{num(r['mean_difference'], d, sign=True)} {ci(r)}"
    return base


KEYM = [("throughput", 1), ("completion_ratio_offered", 3), ("departure_ratio", 3), ("mean_waiting_time", 1),
        ("mean_time_loss", 1), ("mean_travel_time", 1), ("mean_network_queue_vehicles", 1),
        ("max_network_queue_vehicles", 1), ("mean_stops", 2), ("mean_depart_delay_seconds", 1),
        ("never_inserted_vehicle_count", 1), ("unfinished_in_network_count", 1), ("sumo_teleports_total", 2)]
EFFECT = {"TREATMENT_BETTER": "tratamento melhor", "BASELINE_BETTER": "baseline melhor",
          "NO_CLEAR_DIFFERENCE": "sem diferença clara", "DIFFERENT": "diferente"}


def descriptive_tables() -> str:
    parts = []
    for s in SCEN:
        rows = []
        for c in (B0, B1, B2, C1, C2):
            row = [SHORT[c]]
            for m, d in KEYM:
                mean, sd = dmean(s, c, m), dmean(s, c, m, "std")
                row.append(f"{mean:.{d}f} ± {sd:.{d}f}")
            rows.append(row)
        parts.append(f"**{s}** (N=10 seeds; média ± desvio-padrão)\n\n" + md_table(["Ctrl"] + [m for m, _ in KEYM], rows))
    return "\n\n".join(parts)


def pair_table(a, b, metrics=KEYM) -> str:
    rows = []
    for s in SCEN:
        for m, d in metrics:
            r = g(s, a, b, m)
            rows.append([s.split("_")[0], m, num(r["baseline_mean"], d), num(r["treatment_mean"], d), cell(r, d),
                         f"{r['seeds_treatment_favourable']}/{r['n_pairs']}" if r["seeds_treatment_favourable"] not in ("", None) else "n/a",
                         EFFECT[r["effect"]]])
    return md_table(["Cen.", "Métrica", f"{SHORT[a]} média", f"{SHORT[b]} média", "dif. (trat.−base) (rel.) IC95%", "seeds favoráveis", "efeito"], rows)


def class_table(pairs) -> str:
    rows = []
    for s in SCEN:
        row = [s]
        for a, b in pairs:
            c = next(x for x in CLS if x["scenario"] == s and x["baseline"] == a and x["treatment"] == b)
            row.append(c["classification"].replace("_COOPERATIVE_COMPACT", "").replace("_LOCAL_PRESSURE", "").replace("_FIXED_CALIBRATED", "").replace("_COOPERATIVE_EXPANDED", "").replace("_LOCAL_ADAPTIVE", ""))
        rows.append(row)
    return md_table(["Cenário"] + [f"{SHORT[a]} → {SHORT[b]}" for a, b in pairs], rows)


def reference_table() -> str:
    rows = []
    for s in SCEN:
        def m(c, k):
            return next(float(r["mean"]) for r in RRS if r["scenario"] == s and r["controller"] == c and r["metric"] == k)

        def p(a, b, k):
            return next(r for r in RRP if r["scenario"] == s and r["baseline"] == a and r["treatment"] == b and r["metric"] == k)
        t02, t21 = p(B0, B2, "reference_route_mean_travel_time_seconds"), p(B2, C1, "reference_route_mean_travel_time_seconds")
        c02, c21 = p(B0, B2, "reference_route_completion_ratio_offered"), p(B2, C1, "reference_route_completion_ratio_offered")
        rows.append([
            s.split("_")[0],
            f"{m(B0, 'reference_route_mean_travel_time_seconds'):.1f}", f"{m(B0, 'reference_route_completion_ratio_offered'):.3f}",
            f"{m(B2, 'reference_route_mean_travel_time_seconds'):.1f}", f"{m(B2, 'reference_route_completion_ratio_offered'):.3f}",
            f"{m(C1, 'reference_route_mean_travel_time_seconds'):.1f}", f"{m(C1, 'reference_route_completion_ratio_offered'):.3f}",
            f"{float(t02['paired_mean_diff']):+.1f} s; compl. {float(c02['paired_mean_diff']) * 100:+.1f} p.p.",
            f"[{float(t02['ci95_low']):+.1f}; {float(t02['ci95_high']):+.1f}]",
            f"{float(t21['paired_mean_diff']):+.1f} s; compl. {float(c21['paired_mean_diff']) * 100:+.1f} p.p.",
            f"[{float(t21['ci95_low']):+.1f}; {float(t21['ci95_high']):+.1f}]",
        ])
    return md_table(["Cen.", "B0 viagem (s)", "B0 concl.", "B2 viagem (s)", "B2 concl.", "C1 viagem (s)", "C1 concl.",
                     "B0→B2 (viagem; concl.)", "IC95% viagem", "B2→C1 (viagem; concl.)", "IC95% viagem"], rows)


def reference_cohort_table() -> str:
    rows = []
    for r in RRC:
        rows.append([r["scenario"].split("_")[0], SHORT[r["controller"]], f"{float(r['mean_reference_route_offered']):.1f}",
                     f"{float(r['mean_reference_route_departed']):.1f}", f"{float(r['mean_reference_route_arrived']):.1f}",
                     f"{float(r['mean_reference_route_never_inserted']):.1f}", f"{float(r['mean_reference_route_unfinished']):.1f}"])
    return md_table(["Cen.", "Ctrl", "coorte oferecida", "partiu", "chegou", "nunca inserida", "inacabada"], rows)


def reference_detail_table() -> str:
    rows = []
    for s in SCEN:
        for c in (B0, B2, C1):
            def m(k, _c=c, _s=s):
                x = next(r for r in RRS if r["scenario"] == _s and r["controller"] == _c and r["metric"] == k)
                return float(x["mean"]), float(x["median"])
            tt, ttm = m("reference_route_mean_travel_time_seconds")[0], m("reference_route_median_travel_time_seconds")[0]
            rows.append([s.split("_")[0], SHORT[c], f"{tt:.1f}", f"{ttm:.1f}",
                         f"{m('reference_route_mean_waiting_time_seconds')[0]:.1f}", f"{m('reference_route_mean_time_loss_seconds')[0]:.1f}",
                         f"{m('reference_route_mean_stops')[0]:.2f}", f"{m('reference_route_completion_ratio_offered')[0]:.3f}",
                         f"{m('reference_route_completion_ratio_departed')[0]:.3f}"])
    return md_table(["Cen.", "Ctrl", "viagem média (s)", "viagem mediana (s)", "espera (s)", "perda de tempo (s)", "paradas", "concl. / oferecida", "concl. / partida"], rows)


def nvr_table() -> str:
    rows = [[r["scenario"].split("_")[0], r["comparison"].replace("_FIXED_CALIBRATED", "").replace("_LOCAL_PRESSURE", "").replace("_COOPERATIVE_COMPACT", ""),
             f"{float(r['network_mean_travel_time_diff']):+.1f} {r['network_mean_travel_time_ci']}",
             f"{float(r['route_mean_travel_time_diff']):+.1f} {r['route_mean_travel_time_ci']}",
             f"{float(r['network_completion_diff']) * 100:+.1f}", f"{float(r['route_completion_diff']) * 100:+.1f}"] for r in NVR]
    return md_table(["Cen.", "Comparação", "rede: Δ viagem (s) IC95%", "rota: Δ viagem (s) IC95%", "rede: Δ concl. (p.p.)", "rota: Δ concl. (p.p.)"], rows)


S5K = [("throughput", 1), ("completion_ratio_offered", 3), ("departure_ratio", 3), ("mean_waiting_time", 1),
       ("mean_time_loss", 1), ("mean_travel_time", 1), ("mean_network_queue_vehicles", 1),
       ("max_network_queue_vehicles", 1), ("mean_stops", 2), ("mean_depart_delay_seconds", 1),
       ("never_inserted_vehicle_count", 1), ("unfinished_in_network_count", 1)]
LAB = [(B2, "B2 (ref.)", "B2_LOCAL_PRESSURE@REF")] + [(c, f"{SHORT[c]} {int(p * 100)}%", f"{c}@{p:.2f}") for c in (C1, C2) for p in (0.0, 0.2, 0.5, 1.0)]


def s5_desc_table() -> str:
    rows = []
    for _, lab, key in LAB:
        row = [lab]
        for m, d in S5K:
            x = next(r for r in S5D if r["controller"] == key and r["metric"] == m)
            row.append(f"{float(x['mean']):.{d}f} ± {float(x['std']):.{d}f}")
        rows.append(row)
    return md_table(["Condição"] + [m for m, _ in S5K], rows)


def s5_pair(family, base, treat, m):
    return next(r for r in S5P if r["family"] == family and r["baseline"] == base and r["treatment"] == treat and r["metric"] == m)


def s5_degradation_table() -> str:
    rows = []
    for c in (C1, C2):
        for p in (0.2, 0.5, 1.0):
            for m, d in (("throughput", 1), ("completion_ratio_offered", 3), ("departure_ratio", 3), ("mean_waiting_time", 1),
                         ("mean_time_loss", 1), ("mean_travel_time", 1), ("mean_network_queue_vehicles", 1),
                         ("max_network_queue_vehicles", 1), ("mean_stops", 2), ("never_inserted_vehicle_count", 1)):
                r = s5_pair("DEGRADATION_VS_0", f"{c}@0.00", f"{c}@{p:.2f}", m)
                rows.append([SHORT[c], f"0%→{int(p * 100)}%", m, num(r["baseline_mean"], d), num(r["treatment_mean"], d), cell(r, d),
                             EFFECT[r["effect"]]])
    return md_table(["Ctrl", "Mudança", "Métrica", "média 0%", "média nível", "dif. abs. (rel.) IC95%", "efeito (dir. = melhor em lado do nível)"], rows)


def s5_vs_b2_table() -> str:
    rows = []
    for c in (C1, C2):
        for p in (0.0, 0.2, 0.5, 1.0):
            for m, d in (("throughput", 1), ("completion_ratio_offered", 3), ("mean_waiting_time", 1), ("mean_time_loss", 1),
                         ("mean_travel_time", 1), ("mean_network_queue_vehicles", 1), ("never_inserted_vehicle_count", 1)):
                r = s5_pair("VS_B2_REFERENCE", f"{B2}@REF", f"{c}@{p:.2f}", m)
                rows.append([SHORT[c], f"{int(p * 100)}%", m, num(r["baseline_mean"], d), num(r["treatment_mean"], d), cell(r, d), EFFECT[r["effect"]]])
    return md_table(["Ctrl", "Perda", "Métrica", "B2 média", "Ctrl média", "dif. (Ctrl−B2) (rel.) IC95%", "efeito"], rows)


def s5_c1c2_table() -> str:
    rows = []
    for p in (0.0, 0.2, 0.5, 1.0):
        for m, d in (("throughput", 1), ("completion_ratio_offered", 3), ("mean_waiting_time", 1), ("mean_time_loss", 1),
                     ("mean_travel_time", 1), ("mean_network_queue_vehicles", 1), ("never_inserted_vehicle_count", 1)):
            r = s5_pair("C1_VS_C2", f"{C1}@{p:.2f}", f"{C2}@{p:.2f}", m)
            rows.append([f"{int(p * 100)}%", m, num(r["baseline_mean"], d), num(r["treatment_mean"], d), cell(r, d), EFFECT[r["effect"]]])
    return md_table(["Perda", "Métrica", "C1 média", "C2 média", "dif. (C2−C1) (rel.) IC95%", "efeito"], rows)


def comm_table() -> str:
    rows = []
    for r in COMM:
        if r["experiment"] == "FINAL_S5":
            rows.append([SHORT[r["controller"]], f"{int(float(r['packet_loss']) * 100)}%", f"{float(r['mean_messages_sent']):.0f}",
                         f"{float(r['mean_messages_delivered']):.0f}", f"{float(r['mean_messages_dropped']):.0f}", f"{float(r['mean_messages_stale']):.0f}",
                         f"{float(r['mean_bytes_sent']) / 1e6:.2f}", f"{float(r['mean_bytes_delivered']) / 1e6:.2f}",
                         f"{float(r['observed_drop_ratio_min']) * 100:.2f}–{float(r['observed_drop_ratio_max']) * 100:.2f}%",
                         f"{float(r['mean_mean_message_age_steps']):.2f}/{float(r['mean_max_message_age_steps']):.0f}"])
    return md_table(["Ctrl", "Perda", "msgs enviadas/run", "entregues", "descartadas", "obsoletas", "MB enviados", "MB entregues", "taxa de descarte obs. (min–max)", "idade média/máx (passos)"], rows)


def overhead_table() -> str:
    rows = [[r["experiment"], r["scenario"].split("_")[0], f"{int(float(r['packet_loss']) * 100)}%", f"{float(r['C2_over_C1_messages_sent']):.3f}",
             f"{float(r['C1_mean_bytes_sent']) / 1e6:.2f}", f"{float(r['C2_mean_bytes_sent']) / 1e6:.2f}", f"{float(r['C2_over_C1_bytes_sent']):.2f}×"] for r in OVH]
    return md_table(["Experimento", "Cen.", "Perda", "C2/C1 mensagens", "C1 MB/run", "C2 MB/run", "C2/C1 bytes"], rows)


def pilot_table() -> str:
    rows = []
    for s in SCEN:
        for m in ("throughput", "completion_ratio_offered", "mean_waiting_time", "mean_time_loss", "mean_network_queue_vehicles", "max_network_queue_vehicles"):
            r = next(x for x in PVF if x["scenario"] == s and x["metric"] == m)
            d = 3 if "ratio" in m else 1
            rows.append([s.split("_")[0], m, f"{num(r['pilot_mean_diff_C1_minus_B2'], d, sign=True)} [{num(r['pilot_ci95_low'], d)}; {num(r['pilot_ci95_high'], d)}]",
                         f"{num(r['final_mean_diff_C1_minus_B2'], d, sign=True)} [{num(r['final_ci95_low'], d)}; {num(r['final_ci95_high'], d)}]",
                         "sim" if r["direction_persisted"] == "True" else "não", num(r["ci_width_ratio_final_over_pilot"], 2),
                         num(r["effect_magnitude_ratio_final_over_pilot"], 2), EFFECT[r["pilot_effect"]] if r["pilot_effect"] in EFFECT else r["pilot_effect"],
                         EFFECT[r["final_effect"]] if r["final_effect"] in EFFECT else r["final_effect"]])
    return md_table(["Cen.", "Métrica", "Piloto N=5: Δ C1−B2 [IC95%]", "Final N=10: Δ C1−B2 [IC95%]", "direção persistiu", "largura IC final/piloto", "|efeito| final/piloto", "veredicto piloto", "veredicto final"], rows)


def main() -> None:
    n_total = VAL["TOTAL_FINAL_SCIENTIFIC_RUNS_ANALYZED"]
    tele = ANA["s4_teleports"]["per_controller"]
    tele_runs = sum(v["runs_with_teleports"] for v in tele.values())
    tele_total = sum(v["total"] for v in tele.values())
    ch = [r for r in PVF if r["verdict_changed"] == "True"]
    persisted = sum(r["direction_persisted"] == "True" for r in PVF if r["pilot_mean_diff_C1_minus_B2"] not in ("0", "0.0"))
    first5_same = sum(r["final_first5_identical_to_pilot"] == "True" for r in PVF)
    # razões de largura por cenário (apenas métricas-chave de serviço/atraso)
    wr = {}
    for s in SCEN:
        vals = [float(r["ci_width_ratio_final_over_pilot"]) for r in PVF if r["scenario"] == s and r["ci_width_ratio_final_over_pilot"] not in ("", "None") and r["metric"] in ("throughput", "completion_ratio_offered", "mean_waiting_time", "mean_time_loss", "mean_network_queue_vehicles", "max_network_queue_vehicles", "mean_travel_time")]
        wr[s] = statistics.median(vals)
    mg = {}
    for s in SCEN:
        vals = [float(r["effect_magnitude_ratio_final_over_pilot"]) for r in PVF if r["scenario"] == s and r["effect_magnitude_ratio_final_over_pilot"] not in ("", "None") and r["metric"] in ("throughput", "completion_ratio_offered", "mean_waiting_time", "mean_time_loss", "mean_network_queue_vehicles", "max_network_queue_vehicles", "mean_travel_time")]
        mg[s] = statistics.median(vals)

    def C(scn, a, b, m):
        return g(scn, a, b, m)

    def rel(scn, a, b, m):
        return num(C(scn, a, b, m)["relative_difference_of_means"], pct=True, sign=True)

    def seeds(scn, a, b, m):
        r = C(scn, a, b, m)
        return f"{r['seeds_treatment_favourable']}/{r['n_pairs']}"

    s5vb = lambda p, c, m: s5_pair("VS_B2_REFERENCE", f"{B2}@REF", f"{c}@{p:.2f}", m)  # noqa: E731
    s5dg = lambda p, c, m: s5_pair("DEGRADATION_VS_0", f"{c}@0.00", f"{c}@{p:.2f}", m)  # noqa: E731

    md = f"""# Análise científica final — FINAL_MAIN (200 runs) + FINAL_S5 (90 runs)

> Gerado por `scripts/final_analysis.py` + `scripts/render_final_analysis_md.py`. Nenhuma simulação foi executada;
> nenhum artefato bruto foi alterado. Todos os números vêm das tabelas CSV/parquet desta pasta e são rastreáveis até
> `run_id` / `run_path` em `final_metrics.parquet`. Linguagem: "os resultados indicam", "nas condições simuladas".

## 0. Identidade e população

| Item | Valor |
|---|---|
| `SCIENTIFIC_SOURCE_GIT_SHA` | `176178e36eeafb329a5a1350161be61cf97902b0` |
| `SCIENTIFIC_TREE_SHA256` | `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff` |
| `FREEZE_MANIFEST_SHA256` | `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec` |
| Runs analisadas | {n_total} (FINAL_MAIN {VAL['FINAL_MAIN_RUNS_ANALYZED']}; FINAL_S5 {VAL['FINAL_S5_RUNS_ANALYZED']}) |
| Observação duplicada / run de piloto / calibração / replay incluída | 0 / 0 / 0 / 0 |
| Long paths (S5 C2, seeds 10007/12011/16001) | {VAL['LONG_PATH_S5_IDENTITIES_INCLUDED']} identidades incluídas uma única vez; {VAL['runs_readable']} runs legíveis |
| Bootstrap | percentil, 10 000 reamostragens, semente 20260910 (`analysis/statistics.py`); rota de referência: semente-base 20260930 por rótulo (`reference_route.py`) |

**Proveniência dos retries (S5).** `S5_RETRIED = 12`: falha de infraestrutura (limite de 260 caracteres de caminho no Windows ao gravar
`junction_telemetry.parquet`) em `C2_COOPERATIVE_EXPANDED`, seeds 10007, 12011 e 16001, perdas 0/20/50/100%. Foram refeitas com
`--resume --retry-failed` (mesmo código/config/freeze; execução a partir de unidade `subst` curta). Tentativas falhas não geraram
resultados; cada identidade científica contribui **uma** vez (N continua 10 seeds por condição). Detalhe: `artifacts/final-s5/retry-log.json`.
Na análise, os arquivos brutos são abertos com o prefixo de caminho estendido `\\\\?\\` (somente leitura; nada foi renomeado, movido ou regravado).

## 1. Método (congelado)

- Unidade pareada: **cenário + seed**; diferença = tratamento − baseline. N = 10 pares por comparação.
- IC95% = bootstrap percentil das diferenças pareadas (plano estatístico congelado). Não foram usados testes de hipótese nem valores-p.
- Diferença relativa = diferença média / média do baseline (plano congelado); a média das razões por par (implementação congelada) fica em `final_pairwise_summary.csv`.
- Classificação (regra fixada antes de examinar resultados): por métrica-chave, "melhor" só se o IC95% exclui 0 naquele sentido.
  Métricas de serviço: `throughput`, `completion_ratio_offered`, `departure_ratio`. Métricas de atraso/fila: `mean_waiting_time`, `mean_time_loss`, `mean_network_queue_vehicles`.
  Rótulo do cenário: `TRADE_OFF` se há metrica favorável a um lado e outra favorável ao outro; senão o lado melhor; senão `NO_CLEAR_DIFFERENCE`.
  `mean_travel_time` não entra na votação por ser condicional a viagens concluídas.
- **Regra de métricas condicionais.** `mean_waiting_time`, `mean_time_loss` e `mean_travel_time` só existem para viagens concluídas;
  sempre são lidas junto de `departure_ratio`, `completion_ratio_offered`, `never_inserted_vehicle_count` e `unfinished_in_network_count`
  (colunas `ctx_*` e `conditional_warning` em `final_pairwise_summary.csv`).
- Nenhum outlier ou seed foi removido. A regra 1,5×IQR do código congelado sinalizou {ANA['outliers_flagged_not_removed']} observações (todas mantidas; `final_outliers_flagged_not_removed.csv`).
- Verificações de consistência: valores recalculados batem com o agregado congelado `combined_metrics.parquet` ({VAL['combined_metrics_crosscheck']['values_checked']} valores, {VAL['combined_metrics_crosscheck']['mismatches']} divergências);
  as 30 runs do S5 a 0% de perda e a referência B2 reproduzem **exatamente** as runs correspondentes de S2 no FINAL_MAIN (30/30 idênticas), o que indica execução determinística.

## 2. Resultados descritivos (N = 10 por controlador/cenário)

Tabela completa (N, média, mediana, desvio-padrão, IQR, mín., máx. de todas as métricas): `final_controller_summary.csv`.

{descriptive_tables()}

## 3. Comparação primária: B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT

B2 e C1 pertencem à mesma família de pressão local; C1 acrescenta informação compacta dos vizinhos.

Classificação por cenário (todas as comparações congeladas):

{class_table([(B2, C1), (B0, B2), (B0, B1), (C1, C2)])}

{pair_table(B2, C1)}

## 4. Comparações secundárias

### 4.1 B0_FIXED_CALIBRATED vs B2_LOCAL_PRESSURE (efeito da adaptação por pressão local)

{pair_table(B0, B2)}

Pós-choque (S3, `post_shock_queue_auc_vehicle_seconds`): B0 {dmean('S3_DEMAND_SHIFT', B0, 'post_shock_queue_auc_vehicle_seconds'):.0f}, B1 {dmean('S3_DEMAND_SHIFT', B1, 'post_shock_queue_auc_vehicle_seconds'):.0f},
B2 {dmean('S3_DEMAND_SHIFT', B2, 'post_shock_queue_auc_vehicle_seconds'):.0f}, C1 {dmean('S3_DEMAND_SHIFT', C1, 'post_shock_queue_auc_vehicle_seconds'):.0f}, C2 {dmean('S3_DEMAND_SHIFT', C2, 'post_shock_queue_auc_vehicle_seconds'):.0f} veículo·s;
B0→B2 {cell(g('S3_DEMAND_SHIFT', B0, B2, 'post_shock_queue_auc_vehicle_seconds'), 0)}; B2→C1 {cell(g('S3_DEMAND_SHIFT', B2, C1, 'post_shock_queue_auc_vehicle_seconds'), 0)}.

### 4.2 B0_FIXED_CALIBRATED vs B1_LOCAL_ADAPTIVE

{pair_table(B0, B1)}

### 4.3 C1_COOPERATIVE_COMPACT vs C2_COOPERATIVE_EXPANDED

{pair_table(C1, C2)}

### 4.4 Complementar exploratório: B0 vs C1/C2 (fora da lista de comparações congeladas)

A pergunta de pesquisa compara a cooperação também com o tempo fixo; B0×C1 não está entre as comparações congeladas da rede.
Calculado com o mesmo estimador congelado e **marcado como exploratório** (`supplementary_B0_vs_cooperative_exploratory.csv`);
não é usado para a classificação principal.

{md_table(['Cen.', 'Métrica', 'B0 média', 'C1 média', 'dif. (C1−B0) (rel.) IC95%', 'efeito'], [[s.split('_')[0], m, num(gs(s, B0, C1, m)['baseline_mean'], d), num(gs(s, B0, C1, m)['treatment_mean'], d), cell(gs(s, B0, C1, m), d), EFFECT[gs(s, B0, C1, m)['effect']]] for s in SCEN for m, d in (('throughput', 1), ('completion_ratio_offered', 3), ('mean_waiting_time', 1), ('mean_time_loss', 1), ('mean_network_queue_vehicles', 1))])}

## 5. Leitura por cenário

### S1 — Balanceado
- Tempo fixo calibrado (B0): espera média {dmean('S1_BALANCED', B0, 'mean_waiting_time'):.1f} s, conclusão {dmean('S1_BALANCED', B0, 'completion_ratio_offered'):.3f}, sem veículos nunca inseridos.
- Adaptação local: B0→B2 reduz espera ({rel('S1_BALANCED', B0, B2, 'mean_waiting_time')}), perda de tempo ({rel('S1_BALANCED', B0, B2, 'mean_time_loss')}) e fila média ({rel('S1_BALANCED', B0, B2, 'mean_network_queue_vehicles')}); vazão praticamente igual ({rel('S1_BALANCED', B0, B2, 'throughput')}). Classificação: B2 melhor. B0→B1: sem diferença clara (apenas menos paradas).
- Cooperação: B2→C1 **piora** espera ({rel('S1_BALANCED', B2, C1, 'mean_waiting_time')}), fila média ({rel('S1_BALANCED', B2, C1, 'mean_network_queue_vehicles')}) e conclusão ({num(C('S1_BALANCED', B2, C1, 'completion_ratio_offered')['mean_difference'], 3, sign=True)}), com 0/10 seeds favoráveis no atraso. Classificação: B2 melhor.
- Piloto V2 (N=5) mostrava a mesma direção (ver §10); sem agrupamento de amostras.

### S2 — Pico direcional
- B0 mantém conclusão {dmean('S2_DIRECTIONAL_PEAK', B0, 'completion_ratio_offered'):.3f} e vazão {dmean('S2_DIRECTIONAL_PEAK', B0, 'throughput'):.0f}; B2 cai para {dmean('S2_DIRECTIONAL_PEAK', B2, 'completion_ratio_offered'):.3f} e {dmean('S2_DIRECTIONAL_PEAK', B2, 'throughput'):.0f}, com {dmean('S2_DIRECTIONAL_PEAK', B2, 'never_inserted_vehicle_count'):.0f} veículos nunca inseridos por run (B0: {dmean('S2_DIRECTIONAL_PEAK', B0, 'never_inserted_vehicle_count'):.0f}). B0 é melhor que B2 e que B1 em atraso/fila; vazão de B1 não difere claramente de B0.
- B2→C1 é um **trade-off**: C1 reduz espera ({rel('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_waiting_time')}), perda de tempo ({rel('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_time_loss')}), fila média ({rel('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_network_queue_vehicles')}) e tempo de viagem ({rel('S2_DIRECTIONAL_PEAK', B2, C1, 'mean_travel_time')}) em 10/10 seeds, mas reduz vazão ({rel('S2_DIRECTIONAL_PEAK', B2, C1, 'throughput')}), conclusão ({num(C('S2_DIRECTIONAL_PEAK', B2, C1, 'completion_ratio_offered')['mean_difference'], 3, sign=True)}) e partida ({num(C('S2_DIRECTIONAL_PEAK', B2, C1, 'departure_ratio')['mean_difference'], 3, sign=True)}), e deixa {num(C('S2_DIRECTIONAL_PEAK', B2, C1, 'never_inserted_vehicle_count')['mean_difference'], 1, sign=True)} veículos a mais fora da rede.
- **Aviso de sobrevivência:** o menor tempo de viagem condicional de C1 não é evidência de melhora, porque menos viagens partem e concluem (a fila de entrada cresce). As métricas de atraso valem para os veículos que entraram.

### S3 — Mudança de demanda
- Metodologia S3 congelada (choque em 2100 s; `post_shock_queue_auc_vehicle_seconds`); nenhuma métrica de recuperação nova foi criada.
- B0 é melhor que B2 (conclusão, partida, atraso, fila) e que B1 (partida, atraso, fila), e na área de fila pós-choque (B0→B2 {rel('S3_DEMAND_SHIFT', B0, B2, 'post_shock_queue_auc_vehicle_seconds')}; B0→B1 {rel('S3_DEMAND_SHIFT', B0, B1, 'post_shock_queue_auc_vehicle_seconds')}); a vazão total não difere claramente entre B0 e B2.
- B2→C1: B2 melhor em todas as métricas-chave; área pós-choque {rel('S3_DEMAND_SHIFT', B2, C1, 'post_shock_queue_auc_vehicle_seconds')} com C1 (0/10 seeds favoráveis). C2 piora fortemente (área {rel('S3_DEMAND_SHIFT', C1, C2, 'post_shock_queue_auc_vehicle_seconds')} sobre C1).
- **Limitação preservada:** o gate composto de validade do S3 foi formalizado após a inspeção diagnóstica do Pilot V2; é um refinamento metodológico *post-hoc*. Todas as 50 runs de S3 têm `shock_start_seconds = 2100` e horizonte completo.

### S4 — Saturação localizada
- Regime de saturação severa: conclusão entre {min(dmean('S4_LOCAL_SATURATION', c, 'completion_ratio_offered') for c in (B0,B1,B2,C1,C2)):.2f} e {max(dmean('S4_LOCAL_SATURATION', c, 'completion_ratio_offered') for c in (B0,B1,B2,C1,C2)):.2f}; ≈{min(dmean('S4_LOCAL_SATURATION', c, 'never_inserted_vehicle_count') for c in (B0,B1,B2,C1,C2)):.0f}–{max(dmean('S4_LOCAL_SATURATION', c, 'never_inserted_vehicle_count') for c in (B0,B1,B2,C1,C2)):.0f} veículos por run nunca são inseridos, conforme o controlador. As métricas de tempo valem para uma minoria de viagens (regra condicional).
- B2→C1: C1 melhor em vazão ({rel('S4_LOCAL_SATURATION', B2, C1, 'throughput')}), conclusão, espera ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_waiting_time')}), perda de tempo ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_time_loss')}), fila média ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_network_queue_vehicles')}), tempo de viagem ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_travel_time')}) e paradas ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_stops')}), em 10/10 seeds; `departure_ratio` sem diferença clara; o atraso de partida **piora** ({rel('S4_LOCAL_SATURATION', B2, C1, 'mean_depart_delay_seconds')}). Classificação: C1 melhor. Efeito em vazão menor que no piloto (+12,0% → {rel('S4_LOCAL_SATURATION', B2, C1, 'throughput')}).
- B0 (exploratório e congelado B0→B2/B1): B0 tem vazão e conclusão maiores que B1/B2; B0 vs C1 tem vazão maior (B0), espera menor (B0), mas fila média menor com C1 ({num(gs('S4_LOCAL_SATURATION', B0, C1, 'mean_network_queue_vehicles')['relative_difference_of_means'], pct=True, sign=True)}).
- C1→C2: trade-off (C2 menor espera {rel('S4_LOCAL_SATURATION', C1, C2, 'mean_waiting_time')} e fila {rel('S4_LOCAL_SATURATION', C1, C2, 'mean_network_queue_vehicles')}, vazão {rel('S4_LOCAL_SATURATION', C1, C2, 'throughput')}; porém menor `departure_ratio` e maior atraso de partida {rel('S4_LOCAL_SATURATION', C1, C2, 'mean_depart_delay_seconds')}).
- Variabilidade entre seeds: coeficiente de variação da espera (10 seeds) B2 {next(float(r['cv_all10']) for r in N10 if r['scenario']=='S4_LOCAL_SATURATION' and r['controller']==B2 and r['metric']=='mean_waiting_time'):.3f}, C1 {next(float(r['cv_all10']) for r in N10 if r['scenario']=='S4_LOCAL_SATURATION' and r['controller']==C1 and r['metric']=='mean_waiting_time'):.3f}; as seeds 6–10 reduziram a largura do IC de vazão (ver §10). Efeitos por seed em `paired_differences` de `final_pairwise_summary.csv`.

**Teleports em S4 (`ALLOW_AND_MEASURE`, nenhum excluído).** {tele_runs} das 50 runs S4 tiveram teleports ({tele_total:.0f} no total):
B0 {tele[B0]['total']:.0f} (em {tele[B0]['runs_with_teleports']}/10 runs, máx. {tele[B0]['max']:.0f}), B2 {tele[B2]['total']:.0f} ({tele[B2]['runs_with_teleports']}/10, seed {tele[B2]['seeds_with_teleports']}), B1/C1/C2 0. Em S1–S3: 0 teleports.
Os teleports estão em B0 (o controlador de maior vazão em S4) e quase ausentes nos demais; devem ser lidos junto da severidade da congestão, e não como falha (`s4_teleports_by_run.csv`).

## 6. Rota de referência oficial (`left1A1 → A1B1 → B1C1 → C1right1`, N = 10)

Coorte: veículos oferecidos cuja **sequência de arestas planejada** é exatamente a rota e cujo depart programado está na janela de medição
(o id de rota do SUMO nunca é usado). Estatística congelada de `reference_route.py`; evidência do N=5 antigo **não** reutilizada.

{reference_table()}

Contexto da coorte (médias por run):

{reference_cohort_table()}

Métricas completas por cenário/controlador (média e mediana de viagem, espera, perda de tempo, paradas, conclusão):

{reference_detail_table()}

- **B0→B2 (adaptação, rota):** S1 menor tempo de viagem ({num(next(r for r in RRP if r['scenario']=='S1_BALANCED' and r['baseline']==B0 and r['treatment']==B2 and r['metric']=='reference_route_mean_travel_time_seconds')['paired_mean_diff'],1,sign=True)} s); em S2, S3 e S4 o tempo de viagem condicional **aumenta** e a conclusão cai (S4: −69,7 p.p.), ou seja, a coorte de B2 é bem menor/mais seletiva — ler com cautela.
- **B2→C1 (cooperação, rota):** S1 pior (+23 s); S2/S3/S4 menor tempo de viagem condicional, mas com conclusão sem diferença clara em S2/S3 e maior em S4 (+9,1 p.p.).
- Em S2 e S4 a coorte de B2/C1 é parcial (nunca inseridos: S2 ≈28–32 de 109; S4 ≈126–142 de 200) enquanto B0 insere quase toda a coorte; comparações de tempo são condicionais a viagens concluídas.

**Rede × rota.** Direções por cenário (rede = todas as viagens; rota = coorte exata):

{nvr_table()}

Em S3, B2→C1 **piora** o tempo de viagem da rede (+15,9 s) mas **melhora** o da rota de referência (−46,2 s). Isto não é contradição automática:
rede e coorte são populações diferentes (a coorte é só a corrente oeste→leste A4–A5–A6; o choque de S3 entra pela borda oeste via A5, o que pode torná-la mais sensível, mas isso não foi testado aqui).
B0→B2 e B2→C1 são efeitos distintos (adaptação vs. cooperação) e não devem ser agregados em um único efeito.

## 7. S5 — Degradação de comunicação (tráfego-base S2_DIRECTIONAL_PEAK, atraso 0)

Estrutura: C1 e C2 com perda 0/20/50/100% (N=10 cada), B2 uma referência por seed (N=10, reutilizada nas comparações pareadas por seed; sem duplicação).

**Validade da comunicação (fatos de validação, não conclusões de tráfego):**
0%: zero descartes; 20%: taxa observada {min(float(r['observed_drop_ratio_min']) for r in COMM if r['experiment']=='FINAL_S5' and float(r['packet_loss'])==0.2)*100:.1f}–{max(float(r['observed_drop_ratio_max']) for r in COMM if r['experiment']=='FINAL_S5' and float(r['packet_loss'])==0.2)*100:.1f}%;
50%: {min(float(r['observed_drop_ratio_min']) for r in COMM if r['experiment']=='FINAL_S5' and float(r['packet_loss'])==0.5)*100:.1f}–{max(float(r['observed_drop_ratio_max']) for r in COMM if r['experiment']=='FINAL_S5' and float(r['packet_loss'])==0.5)*100:.1f}%;
100%: {ANA['s5_total_at_100_percent_loss']['sent']:,} enviadas, {ANA['s5_total_at_100_percent_loss']['dropped']:,} descartadas, {ANA['s5_total_at_100_percent_loss']['delivered']} entregues, {ANA['s5_total_at_100_percent_loss']['bytes_delivered']} bytes entregues.

{comm_table()}

### 7.1 Desempenho (N=10, média ± desvio-padrão)

{s5_desc_table()}

### 7.2 Degradação em relação a 0% (pareado por seed)

{s5_degradation_table()}

### 7.3 C1 e C2 vs B2 (referência única por seed)

{s5_vs_b2_table()}

### 7.4 C1 vs C2 por nível de perda

{s5_c1c2_table()}

### 7.5 Leitura de robustez (apenas do que os dados mostram)
- **Não houve degradação monotônica.** Em C1, a perda de 20% e 50% **aumentou** vazão ({num(s5dg(0.2, C1, 'throughput')['relative_difference_of_means'], pct=True, sign=True)} e {num(s5dg(0.5, C1, 'throughput')['relative_difference_of_means'], pct=True, sign=True)}) e conclusão em relação a 0%, com atraso de partida/nunca inseridos menores, enquanto a fila média e as paradas pioraram levemente; em C2, a perda de 20% e 50% melhorou fortemente vazão ({num(s5dg(0.2, C2, 'throughput')['relative_difference_of_means'], pct=True, sign=True)} e {num(s5dg(0.5, C2, 'throughput')['relative_difference_of_means'], pct=True, sign=True)}), espera e conclusão, em 10/10 seeds. O C2 com informação completa (0%) é o pior ponto de C2.
- **Perda moderada (20–50%)**: C1 e C2 ficam próximos ou melhores que B2 em serviço (vazão/conclusão) e melhores em atraso/fila (S2). Mecanismos explicativos **não foram testados** e não são afirmados aqui.
- **Perda total (100%)**: as 20 runs cooperativas terminaram, com métricas finalizadas e 0 mensagens entregues. Em todas as 20, as métricas de tráfego de C1 e C2 foram **idênticas** às do B2 da mesma seed (diferenças exatamente 0), consistente com o comportamento de recuo local do controlador cooperativo (`local_pressure_controller_id = B2_LOCAL_PRESSURE` no manifesto). Isto é uma observação empírica; não há prova formal aqui.
- Não é declarado limiar de tolerância a perda: há apenas quatro níveis, e o efeito não é monotônico.
- `FALLBACK_OPERATIONAL = YES` refere-se a operação sem mensagens entregues (simulação conclui, métricas finalizadas). **Não** é verificação formal de segurança de sinal: ela é sustentada separadamente pelo `PhaseSafetyManager` inalterado e pelos testes de software.

## 8. Custo de comunicação: C1 vs C2

{overhead_table()}

- C1 e C2 enviam o **mesmo número** de mensagens por run (93 600), mas a mensagem de C2 tem ≈751 bytes contra ≈324 bytes de C1, ou seja ≈2,3× mais bytes enviados.
- Desempenho: C2 é pior que C1 em S1, S2 e S3 (conclusão, atraso e filas; ex.: S1 espera {rel('S1_BALANCED', C1, C2, 'mean_waiting_time')}, S3 espera {rel('S3_DEMAND_SHIFT', C1, C2, 'mean_waiting_time')}); em S4 há trade-off (menor espera/fila, maior atraso de partida e menor `departure_ratio`). No S5, C1 é melhor ou igual a C2 em todos os níveis: a 0% e 20% em serviço e atraso; a 50% só em serviço (atraso sem diferença clara); a 100% idênticos (ver §7.4).
- **Resposta:** a comunicação expandida **não** trouxe benefício de tráfego suficiente para justificar ≈2,3× mais bytes nas condições simuladas; o benefício restringe-se a atraso/fila em S4, com custo em partida. Resposta: *sem benefício claro / dependente do cenário*.

## 9. Resumo por pergunta

{md_table(['Pergunta', 'Resposta apoiada pelos dados'], [
['Primária B2 vs C1', 'Dependente do cenário: C1 melhor só em S4; B2 melhor em S1 e S3; trade-off em S2.'],
['B0 vs B2', 'B2 melhor em S1; B0 melhor em S2, S3 e S4 (mais forte em S2/S4).'],
['B0 vs B1', 'Sem diferença clara em S1; B0 melhor em S2, S3 e S4.'],
['C1 vs C2', 'C1 melhor em S1–S3; trade-off em S4; C2 ≈2,3× bytes.'],
])}

## 10. Piloto V2 (N=5) vs Final (N=10) — comparação metodológica, sem agrupar

Como as 5 primeiras seeds do Final são as do Piloto, **não** há N=15. Reexecutar essas 5 seeds no Final reproduziu **exatamente**
as diferenças do Piloto em {first5_same}/{len(PVF)} (cenário × métrica) comparações, e os valores por run coincidem (diferença máx. 0,0 excluindo métricas de tempo de relógio). Logo, o que o Final acrescenta são as seeds 6–10 (6841, 8089, 10007, 12011, 16001).

{pilot_table()}

- Direção da diferença C1−B2: persistiu em {persisted}/{len([r for r in PVF if r['pilot_mean_diff_C1_minus_B2'] not in ('0','0.0')])} comparações com diferença não nula; veredito (IC) mudou em {len(ch)}: {', '.join(f"{r['scenario'].split('_')[0]} {r['metric']}" for r in ch) or 'nenhuma'}.
- Largura mediana do IC (final/piloto, métricas de serviço/atraso): {', '.join(f"{s.split('_')[0]} {wr[s]:.2f}" for s in SCEN)}; só vazão: {', '.join(f"{s.split('_')[0]} {float(next(r for r in PVF if r['scenario']==s and r['metric']=='throughput')['ci_width_ratio_final_over_pilot']):.2f}" for s in SCEN)}.
- Razão mediana |efeito| final/piloto: {', '.join(f"{s.split('_')[0]} {mg[s]:.2f}" for s in SCEN)} (valores < 1: efeito estimado menor com N=10; > 1: maior).
- **Valor de N=10 (retrospectivo, não é nova regra de parada):** nenhuma direção mudou; os ICs de vazão estreitaram em S2, S3 e S4 (razões acima) e os de atraso/fila mudaram pouco na maioria dos cenários; o efeito de vazão em S4 foi estimado menor com N=10 (piloto +12,0% → final {rel('S4_LOCAL_SATURATION', B2, C1, 'throughput')}), evitando superestimação. N=10 foi útil por precisão e por checagem de superestimação, não por inversão de conclusão.

## 11. Resposta à pergunta de pesquisa

**Expectativa inicial.** O protocolo não definiu a resposta esperada; a hipótese de trabalho implícita no título (controle distribuído e cooperativo) era que a troca local de informação melhora o desempenho em relação ao adaptativo local sem cooperação e ao tempo fixo. O Pilot V2 já indicava resultado misto (MIXED), com benefício aparente da cooperação restrito ao regime saturado (S4). A hipótese original não é reescrita.

**Observação final.**
- Cooperação vs adaptativo local (C1 vs B2): *depende do cenário* — benefício em S4, piora em S1 e S3, trade-off em S2.
- Cooperação vs tempo fixo (B0 × C1, exploratório): B0 teve menor espera/fila em S1, e maior vazão/conclusão e menor espera em S2–S4; em S4 o C1 teve fila média menor. Não há evidência de superioridade geral da cooperação sobre B0.
- Adaptação local vs tempo fixo (B0 vs B2/B1): B2 melhor só em S1; em S2–S4 B0 melhor.
- Comunicação mais rica (C2) não melhora o desempenho de modo geral e custa ≈2,3× em bytes.

Os resultados indicam, portanto, que o efeito da cooperação **variou por cenário** e **não** sustentam superioridade geral da cooperação.
Expectativa "cooperação ajuda sob congestão": confirmada apenas em S4 (e com piora no atraso de partida); expectativa "adaptação local supera o tempo fixo em todos os cenários": **não** observada (apenas S1).

## 12. Resultados inesperados ou contraintuitivos
1. O tempo fixo calibrado (B0) superou B1 e B2 em S2, S3 e S4 (e B2 deixou ≈212 veículos/run fora da rede em S2).
2. C2 (comunicação expandida) foi muito pior que C1 em S1–S3 (espera +187%/+121% sobre C1 em S1/S3).
3. S5 **não monotônico**: perdas de 20–50% melhoraram C1/C2 em vazão/conclusão em relação a 0%.
4. Com 100% de perda, C1 e C2 reproduziram exatamente o B2 em todas as métricas de tráfego.
5. Em S3, B2→C1 piora a rede e melhora a rota de referência.
6. Teleports de S4 concentrados em B0 (28 de {tele_total:.0f}), o controlador de maior vazão em S4.

## 13. Limitações reforçadas pelos resultados
- Uma única rede 3×3 simulada em SUMO; sem validação em campo; sem generalização para outras topologias.
- N=10 seeds por condição; IC por bootstrap de 10 diferenças pareadas pode ser anti-conservador; sem correção para múltiplas métricas/comparações; sem valores-p.
- Resultados valem para os parâmetros congelados dos controladores; B0 passou por calibração dedicada, conforme o congelamento.
- S3: validade pelo gate composto *post-hoc*.
- S4: regime de saturação severa, com ≈65–72% das viagens oferecidas não concluídas e teleports mensurados (não excluídos); métricas de tempo são condicionais.
- S2/S4: métricas de tempo condicionais a coortes parciais; atraso de partida e veículos nunca inseridos devem acompanhar qualquer leitura.
- S5 usa só S2, atraso 0 e 4 níveis de perda; sem limiar de tolerância; mecanismos do efeito não testados.
- A comparação B0×C1 de rede é exploratória (fora do plano congelado).
- 12 runs de S5 precisaram de retry por limite de caminho do Windows (infraestrutura); resultados idênticos aos esperados por execução determinística, mas as tentativas falhas existem nos logs.

## 14. Alegações NÃO sustentadas
- Superioridade geral/universal da cooperação, de qualquer controlador ou "da IA".
- Causa dos efeitos (por que perdas moderadas melhoram C1/C2 em S2; por que B2 é fraco em S2).
- Limiar de tolerância a perda de pacotes.
- Verificação formal de segurança de sinal a partir dos artefatos.
- Generalização para tráfego real, outras redes, outras demandas ou outros atrasos de comunicação.
- Ganho de C2 que justifique o custo de comunicação.

## 15. Rastreabilidade
- `final_metrics.parquet`: cada observação com `experiment`, `scenario`, `controller`, `seed`, `packet_loss`, `run_id`, `run_path`, `config_run_id`, `attempts`, hashes de cenário/rota/rede, `scientific_source_git_sha` e `freeze_manifest_sha256`.
- Pares por seed: `paired_seeds` / `paired_differences` em `final_pairwise_summary.csv`, `s5_pairwise.csv`, `reference_route_pairwise.csv`.
- Validação: `analysis-validation.json` (população exata 200+90, sem duplicatas, sem piloto/calibração/replay, `LONG_PATH_S5_IDENTITIES_INCLUDED = 12/12`).
"""
    (OUT / "final_analysis.md").write_text(md, encoding="utf-8")

    # evidência leve
    EVID.mkdir(parents=True, exist_ok=True)
    for name in ["final_controller_summary.csv", "final_pairwise_summary.csv", "final_scenario_pair_classification.csv",
                 "reference_route_pairwise.csv", "reference_route_summary.csv", "reference_route_cohort_summary.csv",
                 "network_vs_reference_route_direction.csv", "s5_pairwise.csv", "s5_controller_summary.csv",
                 "s5_pair_classification.csv", "s5_communication_summary.csv", "communication_overhead_ratio.csv",
                 "communication_by_run.csv", "pilot_vs_final.csv", "n10_variability.csv", "s4_teleports_by_run.csv",
                 "supplementary_B0_vs_cooperative_exploratory.csv", "final_outliers_flagged_not_removed.csv",
                 "final_analysis.json", "analysis-validation.json", "final_analysis.md"]:
        shutil.copy2(OUT / name, EVID / name)
    t = pq.read_table(OUT / "final_metrics.parquet", columns=["experiment", "scenario", "controller", "seed", "packet_loss", "condition",
                                                              "run_id", "run_path", "config_run_id", "attempts"]).to_pylist()
    idx = sorted({tuple(x.values()) for x in t})
    with (EVID / "run_index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["experiment", "scenario", "controller", "seed", "packet_loss", "condition", "run_id", "run_path", "config_run_id", "attempts"])
        w.writerows(idx)
    manifest = {"scientific_source_git_sha": "176178e36eeafb329a5a1350161be61cf97902b0",
                "freeze_manifest_sha256": "de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec",
                "runs_indexed": len(idx),
                "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EVID.iterdir()) if p.is_file() and p.name != "evidence-manifest.json"},
                "note": "lightweight derived evidence only; raw artifacts stay in the git-ignored artifacts/ tree"}
    (EVID / "evidence-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("rendered", len(md), "chars;", len(idx), "runs indexed")


if __name__ == "__main__":
    main()
