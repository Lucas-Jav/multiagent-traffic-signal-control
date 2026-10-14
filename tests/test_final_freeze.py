from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from analysis.statistics import DEFAULT_CONTROLLER_PAIRS
from traffic_agents.experiments import final_freeze as ff
from traffic_agents.experiments.freeze_hashing import (
    FreezePreconditions,
    WorkingTreeSource,
    canonical_sha256,
    compute_scientific_tree,
    manifest_file_sha256,
    raw_byte_sha256,
    write_manifest_checksum,
)
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
    # Raw bytes depend on the checkout line endings; the canonical hash is the authority.
    assert canonical_sha256(plan_path.read_bytes()) == ff.B0_CANONICAL_SHA256
    assert file_sha256(plan_path) in {
        "a950d82d1d59562766b183c096477f39215f0de8a905960b223a7a6fcef1f0fe",
        raw_byte_sha256(plan_path.read_bytes()),
    }


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


SYNTHETIC_SOURCE_SHA = "5" * 40  # the real SHA is supplied at freeze time; tests never need one


def _synthetic_preconditions() -> FreezePreconditions:
    """Preconditions as they would be on a clean tree whose source tree equals the current one."""

    tree = compute_scientific_tree(ff.scientific_spec(), WorkingTreeSource(REPO))
    return FreezePreconditions(
        head_sha="6" * 40,
        scientific_source_git_sha=SYNTHETIC_SOURCE_SHA,
        working_tree_dirty_at_input_inspection=False,
        source_is_ancestor_of_head=True,
        source_exists=True,
        scientific_tree_sha256=tree.sha256,
        source_scientific_tree_sha256=tree.sha256,
        scientific_changes_since_source=(),
        tree=tree,
    )


@pytest.fixture(scope="module")
def fresh_manifest(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, object], Path]:
    """Schema-2 manifest built in memory (nothing is written into the repository)."""

    manifest = ff.build_freeze_manifest(
        REPO, generated_at="2026-01-01T00:00:00Z", preconditions=_synthetic_preconditions()
    )
    path = tmp_path_factory.mktemp("manifest") / "final-freeze-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest, path


def test_no_scientific_source_sha_is_hardcoded() -> None:
    assert not hasattr(ff, "SCIENTIFIC_SOURCE_GIT_SHA")
    superseded = "0abd7be"
    for relative in ("src", "scripts"):
        for path in (REPO / relative).rglob("*.py"):
            assert superseded not in path.read_text(encoding="utf-8"), path


def test_manifest_source_sha_comes_from_the_validated_input(
    fresh_manifest: tuple[dict[str, object], Path],
) -> None:
    manifest, _ = fresh_manifest
    identity = manifest["identity"]
    assert identity["scientific_source_git_sha"] == SYNTHETIC_SOURCE_SHA
    assert identity["freeze_tooling_git_sha"] == "6" * 40


def test_manifest_content_and_schema(fresh_manifest: tuple[dict[str, object], Path]) -> None:
    manifest, _ = fresh_manifest
    assert manifest["schema_version"] == 2
    assert manifest["seeds"]["count"] == 10
    assert manifest["expected_run_counts"]["total"] == 290
    assert manifest["scenario_freeze"]["s4_teleport_policy"] == "ALLOW_AND_MEASURE"
    assert manifest["scenario_freeze"]["s3_shock_start_seconds"] == 2100
    assert manifest["reference_route"]["edge_sequence"] == [
        "left1A1",
        "A1B1",
        "B1C1",
        "C1right1",
    ]
    identity = manifest["identity"]
    assert identity["scientific_tree_unchanged_from_source"] is True
    assert identity["scientific_tree_sha256"] == identity["source_scientific_tree_sha256"]
    assert identity["git_working_tree_dirty_at_input_inspection"] is False
    schema = manifest["scientific_hash_schema"]
    assert schema["text"] == "CANONICAL_TEXT_LF_V1"
    assert schema["metadata"] == "SCIENTIFIC_METADATA_V1"
    assert schema["tree"] == "SCIENTIFIC_TREE_V1"
    b0 = manifest["b0_identity"]
    assert b0["plan_file_raw_sha256"] and b0["plan_file_canonical_sha256"]
    hashes = manifest["scientific_input_hashes"]
    assert hashes["network_sha256"] and hashes["network_raw_sha256"]
    for value in hashes.values():
        assert value
    env = manifest["environment"]
    for key in ("python_version", "sumo_version", "traci_version", "uv_lock_sha256"):
        assert env[key]


def test_fresh_manifest_hashes_verify(fresh_manifest: tuple[dict[str, object], Path]) -> None:
    manifest, _ = fresh_manifest
    assert ff.verify_manifest_hashes(REPO, manifest) == []


def test_verify_requires_an_existing_source_commit(
    fresh_manifest: tuple[dict[str, object], Path],
) -> None:
    _, path = fresh_manifest
    problems = ff.verify_freeze_manifest(REPO, path)
    assert any("does not exist" in problem for problem in problems)


def test_manifest_does_not_embed_its_own_hash(
    fresh_manifest: tuple[dict[str, object], Path],
) -> None:
    _, path = fresh_manifest
    checksum_path = write_manifest_checksum(path)
    digest = manifest_file_sha256(path)
    assert checksum_path.read_text(encoding="utf-8") == f"{digest}  {path.name}\n"
    assert digest not in path.read_text(encoding="utf-8")


def test_legacy_manifest_is_rejected_for_verification() -> None:
    problems = ff.verify_freeze_manifest(REPO, MANIFEST)
    committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if committed["schema_version"] == 2:
        assert not any("legacy manifest" in problem for problem in problems)
    else:
        assert len(problems) == 1 and "legacy manifest" in problems[0]


def test_verify_detects_a_changed_frozen_config(
    fresh_manifest: tuple[dict[str, object], Path],
) -> None:
    manifest, _ = fresh_manifest
    tampered = json.loads(json.dumps(manifest))
    tampered["scientific_input_hashes"]["main_campaign_config_sha256"] = "0" * 64
    problems = ff.verify_manifest_hashes(REPO, tampered)
    assert len(problems) == 1 and problems[0].startswith("main_campaign_config_sha256")


def test_verify_detects_a_changed_scientific_tree(
    fresh_manifest: tuple[dict[str, object], Path],
) -> None:
    manifest, _ = fresh_manifest
    tampered = json.loads(json.dumps(manifest))
    tampered["identity"]["scientific_tree_sha256"] = "0" * 64
    problems = ff.verify_manifest_hashes(REPO, tampered)
    assert len(problems) == 1 and problems[0].startswith("scientific_tree_sha256")


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
