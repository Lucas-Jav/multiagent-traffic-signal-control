"""Render the TCC academic content (Prompt 65) from templates + the validated FINAL N=10 analysis.

    python scripts/build_tcc_content.py

Reads scripts/tcc_content_templates/*.md, evaluates every {{ expression }} against artifacts/final-analysis/,
writes docs/tcc-final-content/*.md, the claims-traceability file and a validation report.
No simulation is run; no scientific artifact is modified.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcc_content_lib as L  # noqa: E402

REPO = L.REPO
TPL = REPO / "scripts/tcc_content_templates"
OUT = REPO / "docs/tcc-final-content"
VAL = REPO / "artifacts/tcc-content-validation"
OUT.mkdir(parents=True, exist_ok=True)
VAL.mkdir(parents=True, exist_ok=True)

ORDER = ["01-resumo", "02-abstract", "03-introducao-ajustes", "04-fundamentacao-ajustes", "05-metodologia", "06-desenvolvimento",
         "07-validacao-experimental", "08-resultados", "09-discussao", "10-limitacoes", "11-trabalhos-futuros", "12-conclusao",
         "13-figure-table-placement", "14-advisor-checklist-final"]
CITE = "[CITAÇÃO NECESSÁRIA]"


def fig_for(e: dict) -> str:
    a, comp, scn = e.get("artifact", ""), e.get("comparison", ""), e.get("scenario", "")
    if a.startswith("final_pairwise_summary"):
        if comp == f"{L.B2}→{L.C1}":
            extra = {L.S2: "FIG06", L.S3: "FIG07/FIG08", L.S4: "FIG09/FIG10"}.get(scn, "")
            return "FIG04, FIG05, TABLE03" + (f", {extra}" if extra else "")
        if comp == f"{L.B0}→{L.B2}":
            return "FIG03, FIG19"
        if comp == f"{L.C1}→{L.C2}":
            return "FIG17"
        return "FIG05 (classificação)"
    if a.startswith("final_scenario_pair_classification"):
        return "FIG05, FIG19"
    if a.startswith("final_controller_summary"):
        return "FIG02"
    if a.startswith("reference_route"):
        return "FIG11, FIG12, TABLE04"
    if a.startswith("network_vs_reference_route"):
        return "FIG13"
    if a.startswith("s5_controller") or a.startswith("s5_pairwise") or a.startswith("s5_results"):
        return "FIG14, FIG14B, FIG15, TABLE05"
    if a.startswith("s5_communication") or a.startswith("communication"):
        return "FIG16, FIG17, TABLE06"
    if a.startswith("pilot_vs_final"):
        return "FIG18, FIG18B"
    if "teleports" in a:
        return "FIG10"
    return "—"


def main() -> int:
    rendered: dict[str, str] = {}
    for name in ORDER:
        text = (TPL / f"{name}.md").read_text(encoding="utf-8")
        rendered[name] = L.render(text, name)
    # [CITAÇÃO NECESSÁRIA] counts, then outline
    counts = {n: t.count(CITE) for n, t in rendered.items() if t.count(CITE)}
    L.NS["CITE_TOTAL"] = str(sum(counts.values()))
    L.NS["CITE_BY_FILE"] = ", ".join(f"`{n}`: {c}" for n, c in counts.items())
    # real citation slots = markers outside blockquote (">") header/instruction notes
    slots = {n: sum(ln.count(CITE) for ln in t.splitlines() if not ln.lstrip().startswith(">")) for n, t in rendered.items()}
    slots = {n: c for n, c in slots.items() if c}
    L.NS["CITE_SLOTS"] = str(sum(slots.values()))
    L.NS["CITE_SLOTS_BY_FILE"] = ", ".join(f"`{n}`: {c}" for n, c in slots.items())
    L.NS["CITE_NOTES"] = str(sum(counts.values()) - sum(slots.values()))
    outline = L.render((TPL / "00-outline-final.md").read_text(encoding="utf-8"), "00-outline-final")
    rendered = {"00-outline-final": outline, **rendered}
    # the outline text itself mentions the marker; recount excluding it
    for name, text in rendered.items():
        (OUT / f"{name}.md").write_text(text, encoding="utf-8")

    # ---- claims traceability ---------------------------------------------------------------------------
    seen: set[tuple] = set()
    rows_by_file: dict[str, list[dict]] = {}
    for e in L.LOG:
        key = (e["file"], e["expression"])
        if key in seen:
            continue
        seen.add(key)
        rows_by_file.setdefault(e["file"], []).append(e)
    lines = [
        "# Rastreabilidade das afirmações (claims traceability)",
        "",
        "> Gerado programaticamente: cada valor numérico do conteúdo acadêmico foi avaliado a partir de `artifacts/final-analysis/`",
        "> (análise final validada, N = 10) no momento da geração. Colunas: afirmação (valor no texto), arquivo de origem do dado, cenário,",
        "> comparação de controladores, métrica, N, figura/tabela correspondente e o arquivo onde a afirmação aparece. As cópias versionadas das",
        "> tabelas-fonte estão em `docs/evidencias/final-analysis/`. Identidade científica: fonte `176178e36eeafb329a5a1350161be61cf97902b0`;",
        "> manifesto `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec`.",
        "",
        "## A. Afirmações científicas qualitativas (classificação por cenário)",
        "",
        "| Afirmação | Fonte | Cenário | Comparação | Métrica | N | Figura/Tabela |",
        "|---|---|---|---|---|---|---|",
    ]
    qual = [
        ("S1: B2 favorecido sobre B0 e C1", L.S1), ("S2: B2 → C1 é trade-off", L.S2), ("S3: B2 favorecido sobre C1; B0 favorecido sobre B2", L.S3),
        ("S4: C1 favorecido sobre B2 (métricas de congestionamento)", L.S4)]
    for txt, scn in qual:
        lines.append(f"| {txt} | `final_scenario_pair_classification.csv` | {L.SC_PT[scn]} | B2 → C1 / B0 → B2 | classificação (serviço × atraso/fila) | 10 pares | FIG04, FIG05, FIG19, TABLE03 |")
    extra = [
        ("B0 favorecido sobre B2 em S2, S3 e S4; B2 favorecido em S1", "`final_scenario_pair_classification.csv`", "S1–S4", "B0 → B2", "classificação", "10 pares", "FIG03, FIG19"),
        ("O efeito da cooperação depende do cenário (sem superioridade geral)", "`final_analysis.md`/`final_analysis.json`", "S1–S4", "B2 → C1", "classificação", "10 pares", "FIG19, FIG20"),
        ("Degradação da comunicação não monotônica; 100% de perda iguala B2", "`s5_pairwise.csv`, `s5_results.parquet`", "S5 (tráfego S2)", "C1, C2 vs 0% e vs B2", "vazão e demais métricas de tráfego", "10 seeds", "FIG14, FIG15, TABLE05"),
        ("Rede e rota em S3 apontam direções diferentes", "`network_vs_reference_route_direction.csv`", L.SC_PT[L.S3], "B2 → C1", "tempo de viagem", "10 pares", "FIG13"),
        ("Teleports em S4: concentrados no B0; nenhuma execução excluída", "`final_analysis.json` (s4_teleports)", L.SC_PT[L.S4], "B0, B2, B1, C1, C2", "sumo_teleports_total", "10 por controlador", "FIG10"),
        ("S3: critério composto de validade é refinamento post-hoc", "`docs/methodology/scenario-validity-gates.md`", L.SC_PT[L.S3], "—", "validade do cenário", "Pilot V2 (5 seeds do B0)", "—"),
        ("B0 final = EMPIRICAL_FIXED_TIME (ciclo 84 s, DEMAND_PROPORTIONAL, ALTERNATE, offsets 0/42 s); não Webster", "`docs/methodology/fixed-time-calibration.md`; `experiments/fixed_time/b0_fixed_calibrated.json`", "calibração (seeds 101/1009/2029; validação 3011/4021/5003)", "—", "plano de tempo fixo", "—", "TABLE01"),
        ("Direção persistiu em 50/51 comparações; nenhuma conclusão central revertida", "`pilot_vs_final.csv`", "S1–S4", "B2 → C1 (piloto vs final)", "diferença relativa", "piloto 5 / final 10", "FIG18, FIG18B"),
    ]
    for r in extra:
        lines.append("| " + " | ".join(r) + " |")
    lines += ["", "## B. Afirmações numéricas (valores gerados a partir dos artefatos)", ""]
    for name in ["00-outline-final", *ORDER]:
        entries = rows_by_file.get(name, [])
        if not entries:
            continue
        lines += [f"### `{name}.md`", "", "| Valor no texto | Fonte (artefato) | Cenário | Comparação | Métrica | N | Figura/Tabela |", "|---|---|---|---|---|---|---|"]
        for e in entries:
            if e.get("kind", "").startswith("table"):
                val = "(tabela completa)"
            elif e.get("artifact") is None:
                continue
            else:
                val = e["value"].replace("|", "/")
            lines.append(f"| {val} | `{e.get('artifact', '')}` | {e.get('scenario', '')} | {e.get('comparison', '')} | {e.get('metric', '')} | {e.get('N', '')} | {fig_for(e)} |")
        lines.append("")
    (OUT / "15-claims-traceability.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- validation (prompt §49) ----------------------------------------------------------------------------
    report = validate(rendered)
    (VAL / "content_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("expected_values", "details")}, indent=1, ensure_ascii=False))
    bad = [k for k, v in report["expected_values"].items() if not v["ok"]]
    print("expected values failing:", bad or "none")
    return 0 if report["TCC_CONTENT_READY"] else 1


def validate(rendered: dict[str, str]) -> dict:
    chk: dict[str, object] = {}
    allt = "\n".join(rendered.values())
    chk["no_unresolved_placeholders"] = "{{" not in allt and "}}" not in allt
    # independent recomputation of the reference-route means from per-run results (not from the summary CSV)
    by: dict[tuple, list[float]] = {}
    for r in L.RR_RUNS:
        if r["metric"] in (L.TT, L.CMP) and r["value"] is not None:
            by.setdefault((r["scenario"], r["controller"], r["metric"]), []).append(r["value"])
    prompt_values = {  # values listed in the Prompt 65 text (S1..S4; travel s / completion)
        (L.S1, L.B0): (129.2, 0.977), (L.S1, L.B2): (116.7, 0.971), (L.S1, L.C1): (139.8, 0.964),
        (L.S2, L.B0): (129.3, 0.967), (L.S2, L.B2): (322.4, 0.673), (L.S2, L.C1): (283.0, 0.649),
        (L.S3, L.B0): (226.7, 0.858), (L.S3, L.B2): (278.7, 0.817), (L.S3, L.C1): (232.5, 0.826),
        (L.S4, L.B0): (370.2, 0.899), (L.S4, L.B2): (1165.4, 0.202), (L.S4, L.C1): (779.9, 0.293)}
    exp: dict[str, dict] = {}
    for (scn, c), (tt, cm) in prompt_values.items():
        v1 = sum(by[(scn, c, L.TT)]) / len(by[(scn, c, L.TT)])
        v2 = sum(by[(scn, c, L.CMP)]) / len(by[(scn, c, L.CMP)])
        n = len(by[(scn, c, L.TT)])
        ok = round(v1, 1) == tt and round(v2, 3) == cm and n == 10
        exp[f"route_{scn[:2]}_{c[:2]}"] = {"expected": [tt, cm], "from_runs": [round(v1, 1), round(v2, 3)], "N": n, "text_has_values": L.pt(tt, 1) in rendered["08-resultados"] and L.pt(cm, 3) in rendered["08-resultados"], "ok": ok}
    checks = {
        "S1 waiting B2→C1": (L.rel(L.S1, L.B2, L.C1, "mean_waiting_time"), "+35,0%"), "S1 queue B2→C1": (L.rel(L.S1, L.B2, L.C1, "mean_network_queue_vehicles"), "+34,2%"),
        "S2 waiting": (L.rel(L.S2, L.B2, L.C1, "mean_waiting_time"), "−15,2%"), "S2 queue": (L.rel(L.S2, L.B2, L.C1, "mean_network_queue_vehicles"), "−18,3%"),
        "S2 throughput": (L.rel(L.S2, L.B2, L.C1, "throughput"), "−5,7%"), "S2 completion pp": (L.pp(L.S2, L.B2, L.C1), "−4,9 p.p."),
        "S3 AUC B0→B2": (L.rel(L.S3, L.B0, L.B2, "post_shock_queue_auc_vehicle_seconds"), "+14,5%"),
        "S4 throughput": (L.rel(L.S4, L.B2, L.C1, "throughput"), "+8,8%"), "S4 waiting": (L.rel(L.S4, L.B2, L.C1, "mean_waiting_time"), "−19,5%"),
        "S4 queue": (L.rel(L.S4, L.B2, L.C1, "mean_network_queue_vehicles"), "−17,3%"),
        "route S4 B0→B2 completion": (L.rrpp(L.S4, L.B0, L.B2), "−69,7 p.p."), "route S4 B2→C1 completion": (L.rrpp(L.S4, L.B2, L.C1), "+9,1 p.p."),
        "route S1 B2→C1 travel": (L.rrd(L.S1, L.B2, L.C1), "+23,2"), "route S3 B2→C1 travel": (L.rrd(L.S3, L.B2, L.C1), "−46,2"),
        "S5 C1 20% throughput": (L.s5rel(L.C1, 0.2, "throughput"), "+8,6%"), "S5 C1 50%": (L.s5rel(L.C1, 0.5, "throughput"), "+10,3%"),
        "S5 C2 20%": (L.s5rel(L.C2, 0.2, "throughput"), "+15,9%"), "S5 C2 50%": (L.s5rel(L.C2, 0.5, "throughput"), "+19,5%"),
        "S5 100% equal B2": (L.eq_b2(), "380/380"), "S5 drop 20% min": (L.drop_ratio(0.2, "min"), "19,9%"), "S5 drop 20% max": (L.drop_ratio(0.2, "max"), "20,2%"),
        "S5 drop 50% min": (L.drop_ratio(0.5, "min"), "49,7%"), "S5 drop 50% max": (L.drop_ratio(0.5, "max"), "50,2%"),
        "S5 100% sent": (L.total100("sent"), "1.872.000"), "S5 100% dropped": (L.total100("dropped"), "1.872.000"), "S5 100% delivered": (L.total100("delivered"), "0"),
        "teleports total": (L.tele(None, "total"), "31"), "teleports B0": (L.tele(L.B0, "total"), "28"), "teleports B2": (L.tele(L.B2, "total"), "3"),
        "teleports runs": (L.tele(None, "runs"), "11"), "C2/C1 bytes (1 decimal)": (L.ratio_bytes(d=1), "2,3"),
        "pilot S4 throughput": (L.pvf(L.S4, "throughput", "pilot_rel_diff", pct_=True), "+12,0%"), "final S4 throughput": (L.pvf(L.S4, "throughput", "final_rel_diff", pct_=True), "+8,8%"),
        "direction persisted": (L.direction_persisted(), "50/51"), "tests passed": (L.tests("pytest_passed"), "744"),
        "S4 not completing": (L.pct_not_completing(L.S4), "65–72%"),
    }
    for k, (got, want) in checks.items():
        exp[k] = {"expected": want, "got": got, "ok": got == want}
    chk["expected_values"] = exp
    # semantic checks
    def has(name, *needles):
        return all(n in rendered[name] for n in needles)
    chk["S3_post_hoc_disclosed"] = all("post-hoc" in rendered[f] for f in ("05-metodologia", "08-resultados", "10-limitacoes", "12-conclusao"))
    chk["S4_teleports_disclosed"] = all("teleport" in rendered[f].lower() for f in ("05-metodologia", "08-resultados", "10-limitacoes"))
    chk["conditional_metrics_disclosed"] = all("condicion" in rendered[f] for f in ("05-metodologia", "08-resultados", "09-discussao", "10-limitacoes"))
    chk["reference_route_integrated"] = has("05-metodologia", "left1A1 → A1B1 → B1C1 → C1right1") and has("08-resultados", "left1A1 → A1B1 → B1C1 → C1right1") and has("12-conclusao", "Rota de referência")
    chk["S5_described_over_S2"] = "não é um quinto perfil de demanda" in rendered["05-metodologia"].lower() and "tráfego s2" in rendered["08-resultados"].lower()
    chk["no_historical_B0_id_in_results"] = not any(re.search(r"B0_FIXED(?!_CALIBRATED)", rendered[f]) for f in ("08-resultados", "09-discussao", "12-conclusao"))
    hist_lines = []
    for f in rendered:
        ls = rendered[f].splitlines()
        for i, ln in enumerate(ls):
            if re.search(r"B0_FIXED(?!_CALIBRATED)|98 s", ln):
                ctx = " ".join(ls[max(0, i - 1): i + 3]).lower()
                if "histór" not in ctx and "antigo" not in ctx:
                    hist_lines.append(ln)
    chk["historical_B0_mentions_labeled"] = not hist_lines
    chk["historical_B0_unlabeled_lines"] = hist_lines[:5]
    pilot_files = Counter(e["file"] for e in L.LOG if str(e.get("artifact", "")).startswith("pilot_vs_final"))
    chk["pilot_numbers_only_in_allowed_files"] = set(pilot_files) <= {"08-resultados", "12-conclusao", "00-outline-final", "07-validacao-experimental"}
    chk["pilot_numbers_files"] = dict(pilot_files)
    n_vals = Counter(str(e.get("N", "")) for e in L.LOG if str(e.get("artifact", "")).startswith(("final_pairwise", "final_controller", "reference_route", "s5_")))
    chk["final_entries_N_values"] = dict(n_vals)
    chk["final_entries_use_N10"] = set(n_vals) <= {"10", "20", "50", "10 pares", "10 seeds"}
    causal = [m.group(0) for f in ("08-resultados", "12-conclusao") for m in re.finditer(r"(devido a|causado por|por causa d|provocado por|porque)", rendered[f])]
    chk["no_causal_wording_in_results_conclusion"] = not causal
    chk["S5_mechanism_labeled_hypothesis"] = "não testada" in rendered["09-discussao"] and "Possível explicação" in rendered["09-discussao"]
    chk["S5_no_tolerance_claim"] = "Não foi possível identificar um limiar monotônico" in rendered["08-resultados"]
    forbidden = []
    for w in ("provou", "sempre ", "resolveu", "é melhor", "universalmente superior"):
        for f in rendered:
            t = rendered[f].lower()
            for m in re.finditer(re.escape(w), t):
                before = t[max(0, m.start() - 90): m.start()]
                if w == "universalmente superior" and "não" in before:
                    continue
                forbidden.append((f, w))
    chk["forbidden_wording_hits"] = forbidden
    chk["no_predictive_ml_claim_for_system"] = not any(re.search(r"sistema (implementado )?[^.\n]{0,40}(preditivo|aprendizado de máquina|aprendizado por reforço)", ln, re.I) and "não" not in ln.lower() for ln in allt.splitlines())
    chk["title_scope_valid"] = "CONTROLE DISTRIBUÍDO E COOPERATIVO DE SEMÁFOROS URBANOS" in rendered["01-resumo"] and "reativo" in rendered["03-introducao-ajustes"]
    rq = "Em uma rede urbana simulada, a troca local de informações entre controladores semafóricos descentralizados melhora o desempenho da rede em comparação com um controlador adaptativo local sem cooperação e com controle de tempo fixo, sob diferentes condições de demanda?"
    chk["research_question_verbatim"] = rq in re.sub(r"\s+", " ", rendered["03-introducao-ajustes"].replace(">", " ")) and rq in re.sub(r"\s+", " ", rendered["12-conclusao"].replace(">", " "))
    chk["test_count_is_actual"] = L.TESTS.get("pytest_passed") == 744
    all_expected = all(v["ok"] for v in exp.values())
    flags = ["no_unresolved_placeholders", "S3_post_hoc_disclosed", "S4_teleports_disclosed", "conditional_metrics_disclosed", "reference_route_integrated", "S5_described_over_S2",
             "no_historical_B0_id_in_results", "historical_B0_mentions_labeled", "pilot_numbers_only_in_allowed_files", "final_entries_use_N10", "no_causal_wording_in_results_conclusion",
             "S5_mechanism_labeled_hypothesis", "S5_no_tolerance_claim", "no_predictive_ml_claim_for_system", "title_scope_valid", "research_question_verbatim", "test_count_is_actual"]
    chk["failed_flags"] = [f for f in flags if not chk[f]] + ([] if not chk["forbidden_wording_hits"] else ["forbidden_wording_hits"])
    chk["FINAL_NUMBERS_MATCH_ANALYSIS"] = all_expected
    chk["TCC_CONTENT_READY"] = all_expected and not chk["failed_flags"]
    chk["files"] = sorted(rendered)
    return chk


if __name__ == "__main__":
    raise SystemExit(main())
