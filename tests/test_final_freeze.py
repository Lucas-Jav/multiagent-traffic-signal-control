from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from analysis.statistics import DEFAULT_CONTROLLER_PAIRS
from traffic_agents.experiments import final_freeze as ff
from traffic_agents.experiments.run_invariants import file_sha256
from traffic_agents.experiments.runner import load_experiment_config

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / ff.FREEZE_DOCS_DIR / "final-freeze-manifest.json"


def test_seeds_are_the_approved_ten() -> None:
    assert ff.FINAL_SEEDS == (42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001)
    assert ff.FINAL_SEEDS[:5] == ff.PILOT_V2_SEEDS
    assert len(set(ff.FINAL_SEEDS)) == 10


def test_controllers_exclude_historical_b0() -> None:
    assert ff.B0_FINAL == "B0_FIXED_CALIBRATED"
    assert set(ff.FINAL_CONTROLLERS).isdisjoint(ff.HISTORICAL_CONTROLLERS)
    assert len(ff.FINAL_CONTROLLERS) == 5


def test_run_counts_and_unique_identities() -> None:
    main, s5 = ff.main_runs(), ff.s5_runs()
    assert (len(main), len(s5), len(main) + len(s5)) == (200, 90, 290)
    runs = (*main, *s5)
    assert len({run.run_id for run in runs}) == 290
    assert len({run.identity for run in runs}) == 290


def test_s5_b2_runs_once_per_seed() -> None:
    s5 = ff.s5_runs()
    b2 = Counter(run.seed for run in s5 if run.controller_id == "B2_LOCAL_PRESSURE")
    assert b2 == dict.fromkeys(ff.FINAL_SEEDS, 1)
    for controller in ff.S5_COOPERATIVE_CONTROLLERS:
        drops = sorted(
            run.drop_probability for run in s5 if run.controller_id == controller and run.seed == 42
        )
        assert drops == [0.0, 0.2, 0.5, 1.0]
    assert {run.delay_steps for run in s5} == {0}
    assert {run.scenario_base for run in s5} == {"S2_DIRECTIONAL_PEAK"}


def test_campaign_validates_without_simulation() -> None:
    report = ff.validate_final_campaign(REPO)
    assert report["total_run_count"] == 290
    assert report["duplicate_run_identities"] == 0


def test_committed_configs_match_generator_and_load() -> None:
    for relative, payload in (
        (ff.MAIN_CONFIG_RELATIVE_PATH, ff.main_config_payload()),
        (ff.S5_CONFIG_RELATIVE_PATH, ff.s5_config_payload()),
    ):
        assert (REPO / relative).read_text(encoding="utf-8") == ff.render_config_yaml(payload)
        config = load_experiment_config(REPO / relative)
        assert config.campaign_role == "FINAL_SCIENTIFIC"
        assert "timestamp" not in config.experiment_id
    assert len(load_experiment_config(REPO / ff.MAIN_CONFIG_RELATIVE_PATH).runs) == 200
    assert len(load_experiment_config(REPO / ff.S5_CONFIG_RELATIVE_PATH).runs) == 90


def test_b0_plan_identity_and_hash() -> None:
    plan_path = REPO / ff.B0_PLAN_RELATIVE_PATH
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["plan_id"] == "fx_c84_demand_proportional_alternate"
    assert (plan["cycle_seconds"], plan["yellow_seconds"], plan["all_red_seconds"]) == (84, 3, 2)
    assert file_sha256(plan_path) == (
        "a950d82d1d59562766b183c096477f39215f0de8a905960b223a7a6fcef1f0fe"
    )


def test_comparisons_match_analysis_defaults() -> None:
    assert ff.PRIMARY_COMPARISON == ("B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT")
    assert ff.FINAL_CONTROLLER_PAIRS == DEFAULT_CONTROLLER_PAIRS
    assert len(ff.FINAL_CONTROLLER_PAIRS) == 4


def test_required_metrics_are_defined() -> None:
    assert ff._validate_metric_identity() == []


def test_statistical_plan_records_bootstrap_seed() -> None:
    plan = ff.statistical_plan()
    assert plan["bootstrap"]["analysis_rng_seed"] == 20260910
    assert plan["bootstrap"]["resamples"] == 10_000
    assert plan["paired_comparison_unit"] == "scenario + seed"


def test_committed_manifest_is_complete_and_verifies() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["seeds"]["count"] == 10
    assert manifest["expected_run_counts"] == {
        "main": 200,
        "s5": 90,
        "total": 290,
        "excluded": manifest["expected_run_counts"]["excluded"],
    }
    assert manifest["scenario_freeze"]["s4_teleport_policy"] == "ALLOW_AND_MEASURE"
    assert manifest["scenario_freeze"]["s3_shock_start_seconds"] == 2100
    assert manifest["reference_route"]["edge_sequence"] == [
        "left1A1",
        "A1B1",
        "B1C1",
        "C1right1",
    ]
    env = manifest["environment"]
    for key in ("git_sha", "python_version", "sumo_version", "traci_version", "uv_lock_sha256"):
        assert env[key]
    for value in manifest["scientific_input_hashes"].values():
        assert value
    assert ff.verify_freeze_manifest(REPO) == []


def test_verify_detects_a_changed_frozen_config(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["scientific_input_hashes"]["main_campaign_config_sha256"] = "0" * 64
    tampered = tmp_path / "manifest.json"
    tampered.write_text(json.dumps(manifest), encoding="utf-8")
    problems = ff.verify_freeze_manifest(REPO, tampered)
    assert len(problems) == 1 and problems[0].startswith("main_campaign_config_sha256")


def test_fairness_hash_ignores_controller_id() -> None:
    rows = ff.run_matrix_rows(REPO)
    by_cell: dict[tuple[str, int], set[str]] = {}
    for row in rows:
        if row["campaign"] != ff.MAIN_EXPERIMENT_ID:
            continue
        by_cell.setdefault((str(row["scenario_base"]), int(str(row["seed"]))), set()).add(
            str(row["scenario_neutral_sha256"])
        )
    assert len(by_cell) == 40
    assert all(len(hashes) == 1 for hashes in by_cell.values())


@pytest.mark.parametrize("seed", ff.EXTENSION_SEEDS)
def test_extension_seed_artifacts_exist(seed: int) -> None:
    scenario_dir = REPO / ff.SCENARIO_DIR_RELATIVE
    for scenario in ff.MAIN_SCENARIOS:
        assert (scenario_dir / ff.scenario_file_name(scenario, seed)).exists()
