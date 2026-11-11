"""Análise oficial da rota de referência (Prompt 56): B0_FIXED_CALIBRATED vs B2 vs C1.

    uv run python scripts/reference_route_analysis.py

Reutiliza o tripinfo B2/C1 do Pilot V2 (após verificar todo invariante de pareamento) e as 20
novas execuções ``B0_FIXED_CALIBRATED``. Grava ``artifacts/reference-route/`` e uma cópia leve
versionada em ``docs/evidencias/reference-route/``. Nenhuma simulação é iniciada aqui.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.config import load_scenario_config
from traffic_agents.experiments import reference_route as rr
from traffic_agents.experiments.run_invariants import scenario_config_sha256
from traffic_agents.experiments.runner import load_experiment_config
from traffic_agents.metrics.run_metrics import load_offered_vehicles, parse_tripinfo_records

REPO = Path(__file__).resolve().parents[1]
PILOT_DIR = REPO / "artifacts" / "experiments" / "pilot_v2"
B0_DIR = REPO / "artifacts" / "experiments" / "refroute_b0"
OUT = REPO / "artifacts" / "reference-route"
EVIDENCE = REPO / "docs" / "evidencias" / "reference-route"
SCENARIO_DIR = REPO / "scenarios" / "grid_3x3"
ROUTE_FILE_TEMPLATE = {
    "S1_BALANCED": "routes_s1_seed_{seed}.rou.xml",
    "S2_DIRECTIONAL_PEAK": "routes_s2_seed_{seed}.rou.xml",
    "S3_DEMAND_SHIFT": "routes_s3_seed_{seed}.rou.xml",
    "S4_LOCAL_SATURATION": "routes_s4_seed_{seed}.rou.xml",
}
CAMPAIGN_ROLE = "REFERENCE_ROUTE_B0_CALIBRATED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def completed_run_keys(status_path: Path) -> set[str]:
    latest: dict[str, str] = {}
    for line in status_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        latest[str(record["run_id"])] = str(record["status"])
    return {run_id for run_id, status in latest.items() if status == "COMPLETED"}


def discover_runs() -> dict[tuple[str, int, str], dict[str, Any]]:
    """(cenário, seed, controlador) -> informações da execução, do Pilot V2 (B2, C1) e das novas execuções B0."""

    runs: dict[tuple[str, int, str], dict[str, Any]] = {}
    sources = (
        (PILOT_DIR, {rr.B2, rr.C1}, "PILOT_V2_REUSED"),
        (B0_DIR, {rr.B0_CALIBRATED}, "REFERENCE_ROUTE_B0_CALIBRATED_NEW"),
    )
    for experiment_dir, controllers, source in sources:
        completed = completed_run_keys(experiment_dir / "run_status.jsonl")
        for manifest_path in sorted(experiment_dir.glob("runs/*/*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            controller = manifest["controller"]["controller_id"]
            if controller not in controllers or manifest["run_id"] not in completed:
                continue
            if manifest.get("metrics_finalized") is not True:
                continue
            key = (str(manifest["demand_profile"]), int(manifest["seed"]), controller)
            if key in runs:
                msg = f"duplicate run for {key}: {manifest_path}"
                raise RuntimeError(msg)
            runs[key] = {
                "manifest": manifest,
                "run_dir": manifest_path.parent,
                "source": source,
                "experiment_id": json.loads(
                    (experiment_dir / "manifest.json").read_text(encoding="utf-8")
                )["experiment_id"],
            }
    return runs


def expected_scenario_hashes() -> dict[tuple[str, int, str], tuple[str, str]]:
    """(cenário, seed, controlador) -> (hash que o executor registra, hash neutro ao controlador).

    Reconstrói a configuração de execução exatamente como o executor de experimentos faz a partir
    do YAML do cenário e da config do experimento, de modo que o hash do manifesto possa ser
    verificado em vez de confiado.
    """

    hashes: dict[tuple[str, int, str], tuple[str, str]] = {}
    for config_path in (
        REPO / "experiments" / "configs" / "pilot_v2.yaml",
        REPO / "experiments" / "configs" / "refroute_b0.yaml",
    ):
        for run in load_experiment_config(config_path).runs:
            scenario_config = load_scenario_config(run.scenario)
            run_config = scenario_config.model_copy(
                update={
                    "controller_id": run.controller_id,
                    "simulation": scenario_config.simulation.model_copy(
                        update={"seed": int(run.seed)}
                    ),
                    "communication": run.communication,
                },
            )
            neutral = run_config.model_copy(update={"controller_id": "NEUTRAL"})
            hashes[(run.scenario_base, int(run.seed), run.controller_id)] = (
                scenario_config_sha256(run_config),
                scenario_config_sha256(neutral),
            )
    return hashes


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=REPO
    ).stdout.strip()


def git_dirty() -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=REPO
    ).stdout
    return bool(out.strip())


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()}
            )


def fmt(value: float | None, digits: int = 1) -> str:
    return "n/d" if value is None else f"{value:.{digits}f}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = discover_runs()
    expected = {
        (s, seed, c) for s in rr.SCENARIOS for seed in rr.PILOT_SEEDS for c in rr.CONTROLLERS
    }
    missing = sorted(expected - set(runs))
    extra = sorted(set(runs) - expected)
    if missing or extra:
        print(f"CRITICAL: missing={missing} extra={extra}")
        return 2

    # --- pareamento (CRÍTICO em qualquer divergência) ---
    scenario_hashes = expected_scenario_hashes()
    pairing_report: list[dict[str, Any]] = []
    critical: list[str] = []
    for scenario in rr.SCENARIOS:
        for seed in rr.PILOT_SEEDS:
            manifests = {}
            extra_mismatches: list[str] = []
            for controller in rr.CONTROLLERS:
                manifest = dict(runs[(scenario, seed, controller)]["manifest"])
                recorded, neutral = scenario_hashes[(scenario, seed, controller)]
                if manifest["scenario_sha256"] != recorded:
                    extra_mismatches.append(
                        f"{controller}: manifest scenario_sha256 differs from the config rebuilt "
                        "from the scenario YAML"
                    )
                manifest["scenario_neutral_sha256"] = neutral
                manifests[controller] = manifest
            mismatches = rr.pairing_mismatches(manifests) + extra_mismatches
            route_path = SCENARIO_DIR / rr_route_name(scenario, seed)
            route_hash = sha256(route_path)
            if any(m["route_sha256"] != route_hash for m in manifests.values()):
                mismatches.append(f"route_sha256 differs from {rel(route_path)}")
            pairing_report.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "paired": not mismatches,
                    "mismatches": mismatches,
                    "network_sha256": manifests[rr.B2]["network_sha256"],
                    "route_sha256": manifests[rr.B2]["route_sha256"],
                    "turning_config_sha256": manifests[rr.B2]["turning_config_sha256"],
                }
            )
            critical.extend(f"{scenario}/{seed}: {m}" for m in mismatches)
    if critical:
        print("CRITICAL pairing mismatches:\n" + "\n".join(critical))
        return 3

    # --- coorte, linhas e métricas por execução ---
    vehicle_rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    values: dict[str, dict[str, dict[str, dict[int, float | None]]]] = {}
    cohort_ids: dict[tuple[str, int], dict[str, tuple[str, ...]]] = {}
    for (scenario, seed, controller), info in sorted(runs.items()):
        manifest, run_dir = info["manifest"], info["run_dir"]
        measurement = manifest["measurement"]
        offered = load_offered_vehicles(SCENARIO_DIR / rr_route_name(scenario, seed))
        cohort = rr.select_reference_cohort(
            offered,
            warmup_seconds=float(measurement["warmup_seconds"]),
            measurement_duration_seconds=float(measurement["measurement_duration_seconds"]),
        )
        trips = parse_tripinfo_records(run_dir / "sumo" / "tripinfo.xml")
        rows = rr.build_vehicle_rows(cohort, trips)
        counts = rr.population_counts(rows)
        metrics = rr.run_metrics(rows)
        cohort_ids.setdefault((scenario, seed), {})[controller] = tuple(
            v.vehicle_id for v in cohort
        )
        for metric, value in metrics.items():
            values.setdefault(scenario, {}).setdefault(metric, {}).setdefault(controller, {})[
                seed
            ] = value
        low, high = rr.SANITY_RANGES[scenario]
        seed_rows.append(
            {
                "scenario": scenario,
                "seed": seed,
                "controller": controller,
                "source": info["source"],
                **counts,
                **metrics,
                "sanity_range": f"{low}-{high}",
                "within_sanity_range": low <= counts["reference_route_offered"] <= high,
                "run_id": manifest["run_id"],
            }
        )
        for row in rows:
            vehicle_rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "controller": controller,
                    "run_id": manifest["run_id"],
                    "reference_route_id": rr.REFERENCE_ROUTE_ID,
                    **asdict(row),
                }
            )
        provenance.append(
            {
                "scenario": scenario,
                "seed": seed,
                "controller": controller,
                "source": info["source"],
                "experiment_id": info["experiment_id"],
                "run_id": manifest["run_id"],
                "run_dir": rel(run_dir),
                "manifest_sha256": sha256(run_dir / "manifest.json"),
                "tripinfo_sha256": sha256(run_dir / "sumo" / "tripinfo.xml"),
                "run_git_sha": manifest.get("git_sha"),
                "network_sha256": manifest["network_sha256"],
                "route_sha256": manifest["route_sha256"],
                "turning_config_sha256": manifest["turning_config_sha256"],
                "scenario_sha256": manifest["scenario_sha256"],
                "invariants_match_pilot": True,
            }
        )
    for key, by_controller in cohort_ids.items():
        if len({ids for ids in by_controller.values()}) != 1:
            print(f"CRITICAL: cohort differs between controllers for {key}")
            return 4

    # --- estatística ---
    pairwise: list[dict[str, Any]] = []
    for scenario in rr.SCENARIOS:
        for baseline, treatment in rr.COMPARISONS:
            for metric in rr.METRICS:
                pairwise.append(
                    rr.pairwise_comparison(
                        scenario=scenario,
                        baseline=baseline,
                        treatment=treatment,
                        metric=metric,
                        values_by_controller=values[scenario][metric],
                        seeds=rr.PILOT_SEEDS,
                    )
                )
    index = {(p["scenario"], p["baseline"], p["treatment"], p["metric"]): p for p in pairwise}

    # --- tabela para o orientador ---
    advisor: list[dict[str, Any]] = []
    for scenario in rr.SCENARIOS:

        def mean_of(controller: str, metric: str, _s: str = scenario) -> float | None:
            vals = [v for v in values[_s][metric][controller].values() if v is not None]
            return statistics.fmean(vals) if vals else None

        row: dict[str, Any] = {"scenario": scenario}
        for controller, label in (
            (rr.B0_CALIBRATED, "b0_calibrated"),
            (rr.B2, "b2"),
            (rr.C1, "c1"),
        ):
            row[f"{label}_travel_time_s"] = mean_of(controller, rr.PRIMARY_METRIC)
            row[f"{label}_completion_ratio"] = mean_of(controller, rr.COMPLETION_METRIC)
        for baseline, treatment, label in (
            (rr.B0_CALIBRATED, rr.B2, "b0_to_b2"),
            (rr.B2, rr.C1, "b2_to_c1"),
            (rr.B0_CALIBRATED, rr.C1, "b0_to_c1"),
        ):
            tt = index[(scenario, baseline, treatment, rr.PRIMARY_METRIC)]
            comp = index[(scenario, baseline, treatment, rr.COMPLETION_METRIC)]
            row[f"{label}_diff_s"] = tt["paired_mean_diff"]
            row[f"{label}_rel_diff"] = tt["relative_diff"]
            row[f"{label}_ci95_low_s"] = tt["ci95_low"]
            row[f"{label}_ci95_high_s"] = tt["ci95_high"]
            row[f"{label}_interpretation"] = rr.interpret(tt, comp)
        advisor.append(row)

    # --- arquivos ---
    definition = {
        "campaign_role": CAMPAIGN_ROLE,
        "reference_route_id": rr.REFERENCE_ROUTE_ID,
        "edge_sequence": list(rr.REFERENCE_ROUTE_EDGES),
        "logical_path": list(rr.REFERENCE_ROUTE_LOGICAL_PATH),
        "logical_mapping_source": "scenarios/grid_3x3/metadata.json traffic_light_ids",
        "sumo_to_logical": {"A1": "A4", "B1": "A5", "C1": "A6"},
        "cohort_rule": (
            "offered vehicles whose planned edge sequence EXACTLY equals edge_sequence and whose "
            "scheduled departure is in [warmup, warmup + measurement_duration); selection never "
            "uses SUMO route ids or vehicle ids"
        ),
        "trip_metric_rule": "means/medians over COMPLETED trips only; unfinished trips have no "
        "duration; completion ratios reported beside every travel-time metric",
        "controllers": list(rr.CONTROLLERS),
        "comparisons": [f"{a} -> {b}" for a, b in rr.COMPARISONS],
        "seeds": list(rr.PILOT_SEEDS),
        "scenarios": list(rr.SCENARIOS),
        "bootstrap": {
            "resamples": rr.BOOTSTRAP_RESAMPLES,
            "confidence": 0.95,
            "base_seed": rr.BOOTSTRAP_BASE_SEED,
            "seed_rule": "base_seed + crc32(scenario|baseline|treatment|metric) mod 2^32",
            "unit": "seed-level paired differences (treatment - baseline)",
        },
        "sanity_ranges_prompt54": {k: list(v) for k, v in rr.SANITY_RANGES.items()},
    }
    (OUT / "reference-route-definition.json").write_text(
        json.dumps(definition, indent=2), encoding="utf-8"
    )
    table = pa.Table.from_pylist(vehicle_rows)
    pq.write_table(table, OUT / "reference-route-runs.parquet", compression="zstd")
    write_csv(OUT / "reference-route-seed-summary.csv", seed_rows)
    write_csv(OUT / "reference-route-pairwise.csv", pairwise)
    write_csv(OUT / "reference-route-advisor-table.csv", advisor)
    write_csv(OUT / "reference-route-provenance.csv", provenance)

    deviations = [r for r in seed_rows if not r["within_sanity_range"]]
    summary = {
        "campaign_role": CAMPAIGN_ROLE,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_head": git_head(),
        "git_working_tree_dirty": git_dirty(),
        "runs": {
            "b0_calibrated_new": sum(1 for p in provenance if p["controller"] == rr.B0_CALIBRATED),
            "b2_reused_from_pilot_v2": sum(1 for p in provenance if p["controller"] == rr.B2),
            "c1_reused_from_pilot_v2": sum(1 for p in provenance if p["controller"] == rr.C1),
        },
        "pairing_valid": all(p["paired"] for p in pairing_report),
        "pairing_units_checked": len(pairing_report),
        "pairing_fields": list(rr.PAIRING_FIELDS),
        "sample_size_per_run": {
            s: sorted({r["reference_route_offered"] for r in seed_rows if r["scenario"] == s})
            for s in rr.SCENARIOS
        },
        "sanity_deviations": [
            {k: r[k] for k in ("scenario", "seed", "controller", "reference_route_offered")}
            for r in deviations
        ],
        "advisor_table": advisor,
        "metrics": list(rr.METRICS),
    }
    (OUT / "reference-route-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (OUT / "reference-route-analysis.md").write_text(
        render_markdown(summary, seed_rows, pairwise, advisor), encoding="utf-8"
    )
    copy_evidence(summary)
    print("reference-route analysis written to", OUT)
    print("pairing valid:", summary["pairing_valid"], "| sanity deviations:", len(deviations))
    return 0


def rr_route_name(scenario: str, seed: int) -> str:
    return ROUTE_FILE_TEMPLATE[scenario].format(seed=seed)


def render_markdown(
    summary: dict[str, Any],
    seed_rows: list[dict[str, Any]],
    pairwise: list[dict[str, Any]],
    advisor: list[dict[str, Any]],
) -> str:
    lines = [
        "# Experimento da rota de referência: B0 calibrado vs B2 vs C1",
        "",
        f"`campaign_role: {CAMPAIGN_ROLE}`. Evidência PRÉ-FINAL e validação de metodologia; "
        "5 seeds do Pilot V2; resultados descritivos. Não é a campanha final.",
        "",
        "- Rota (arestas SUMO): `left1A1 -> A1B1 -> B1C1 -> C1right1`.",
        "- Rota (lógica): entrada oeste -> A4 -> A5 -> A6 -> saída leste.",
        "- Coorte: veículos ofertados com essa sequência exata de arestas planejada, partida "
        "agendada em [300, 3900) s. Seleção por sequência de arestas, nunca por id de rota.",
        "- Tempo de viagem = média sobre viagens CONCLUÍDAS; viagem não concluída nunca recebe "
        "duração. A razão de conclusão é mostrada ao lado de todo tempo de viagem.",
        "- Diferença = tratamento - base (negativo = tratamento mais rápido). IC 95% por "
        "bootstrap pareado (10.000 reamostragens de seeds, RNG determinístico).",
        "",
        "## Tabela para o orientador (tempo de viagem médio da rota, segundos)",
        "",
        "| Cenário | B0 calibrado | B2 | C1 | B0 -> B2 (adaptação local) | B2 -> C1 (cooperação) "
        "| Interpretação B0 -> B2 | Interpretação B2 -> C1 |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def cell(row: dict[str, Any], label: str) -> str:
        return (
            f"{row[f'{label}_diff_s']:+.1f} s ({row[f'{label}_rel_diff'] * 100:+.1f}%) "
            f"IC95 [{row[f'{label}_ci95_low_s']:+.1f}; {row[f'{label}_ci95_high_s']:+.1f}]"
        )

    for r in advisor:
        lines.append(
            f"| {r['scenario']} "
            f"| {r['b0_calibrated_travel_time_s']:.1f} "
            f"(concl. {r['b0_calibrated_completion_ratio']:.2f}) "
            f"| {r['b2_travel_time_s']:.1f} (concl. {r['b2_completion_ratio']:.2f}) "
            f"| {r['c1_travel_time_s']:.1f} (concl. {r['c1_completion_ratio']:.2f}) "
            f"| {cell(r, 'b0_to_b2')} | {cell(r, 'b2_to_c1')} "
            f"| {r['b0_to_b2_interpretation']} | {r['b2_to_c1_interpretation']} |"
        )
    lines += [
        "",
        "## B0 calibrado vs C1 (efeito total)",
        "",
        "| Cenário | B0 -> C1 | Interpretação |",
        "|---|---|---|",
    ]
    for r in advisor:
        lines.append(
            f"| {r['scenario']} | {cell(r, 'b0_to_c1')} | {r['b0_to_c1_interpretation']} |"
        )
    lines += ["", "## Amostra (veículos da coorte por run, ofertados)", ""]
    lines += ["| Cenário | Ofertados por run | Faixa de sanidade (Prompt 54) |", "|---|---|---|"]
    for scenario in rr.SCENARIOS:
        low, high = rr.SANITY_RANGES[scenario]
        sizes = summary["sample_size_per_run"][scenario]
        lines.append(f"| {scenario} | {sizes} | {low}-{high} |")
    deviations = summary["sanity_deviations"]
    lines += ["", f"Desvios da faixa de sanidade: {len(deviations)} (run, controlador).", ""]
    lines += ["## Contagens e conclusão por seed", ""]
    lines += [
        "| Cenário | Seed | Controlador | Ofert. | Inser. | Concl. | Nunca ins. | Não concl. "
        "| TV médio | TV mediano | Espera | Perda | Paradas | Concl./ofert. | Concl./inser. |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in seed_rows:
        lines.append(
            f"| {r['scenario']} | {r['seed']} | {r['controller']} "
            f"| {r['reference_route_offered']} | {r['reference_route_departed']} "
            f"| {r['reference_route_arrived']} | {r['reference_route_never_inserted']} "
            f"| {r['reference_route_unfinished']} "
            f"| {fmt(r['reference_route_mean_travel_time_seconds'])} "
            f"| {fmt(r['reference_route_median_travel_time_seconds'])} "
            f"| {fmt(r['reference_route_mean_waiting_time_seconds'])} "
            f"| {fmt(r['reference_route_mean_time_loss_seconds'])} "
            f"| {fmt(r['reference_route_mean_stops'], 2)} "
            f"| {fmt(r['reference_route_completion_ratio_offered'], 3)} "
            f"| {fmt(r['reference_route_completion_ratio_departed'], 3)} |"
        )
    lines += ["", "## Comparações pareadas (todas as métricas)", ""]
    lines += [
        "| Cenário | Comparação | Métrica | N | Média base | Média trat. | Dif. média "
        "| Dif. mediana "
        "| Dif. relativa | IC95 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for p in pairwise:
        if p["paired_mean_diff"] is None:
            continue
        lines.append(
            f"| {p['scenario']} | {p['comparison']} | {p['metric']} | {p['n_seeds']} "
            f"| {p['baseline_mean']:.3f} | {p['treatment_mean']:.3f} "
            f"| {p['paired_mean_diff']:+.3f} | {p['paired_median_diff']:+.3f} "
            f"| {p['relative_diff'] * 100:+.1f}% "
            f"| [{p['ci95_low']:+.3f}; {p['ci95_high']:+.3f}] |"
        )
    lines += [
        "",
        "## Limitações",
        "",
        "1. Cinco seeds: ICs largos e descritivos; não são prova de superioridade.",
        "2. Tempo de viagem condicional à conclusão. No S4 (sobrecarga intencional) a conclusão é "
        "baixa e o tempo de viagem dos concluídos não representa os veículos retidos.",
        "3. Uma única rota (O-D oeste-leste por A5); não representa a rede toda.",
        "4. B2 e C1 vêm do Pilot V2 (mesmas rotas, seeds e hashes; ver proveniência); o B0 "
        "calibrado foi executado com a árvore de trabalho posterior ao Pilot V2.",
        "5. Pré-final: não substitui a campanha final nem decide contagem de seeds.",
        "",
    ]
    return "\n".join(lines)


def copy_evidence(summary: dict[str, Any]) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    names = (
        "reference-route-definition.json",
        "reference-route-runs.parquet",
        "reference-route-seed-summary.csv",
        "reference-route-pairwise.csv",
        "reference-route-advisor-table.csv",
        "reference-route-provenance.csv",
        "reference-route-summary.json",
        "reference-route-analysis.md",
    )
    for name in names:
        shutil.copyfile(OUT / name, EVIDENCE / name)
    manifest = {
        "campaign_role": CAMPAIGN_ROLE,
        "created_utc": summary["created_utc"],
        "source_dir": "artifacts/reference-route (git-ignored)",
        "script": "scripts/reference_route_analysis.py",
        "git_head": summary["git_head"],
        "git_working_tree_dirty": summary["git_working_tree_dirty"],
        "kind": "derived (tripinfo.xml of Pilot V2 B2/C1 runs and new B0_FIXED_CALIBRATED runs)",
        "files": {name: sha256(EVIDENCE / name) for name in names},
    }
    (EVIDENCE / "evidence-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(main())
