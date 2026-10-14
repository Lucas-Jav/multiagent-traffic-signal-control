from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import traffic_agents.experiments.freeze as freeze
from traffic_agents.config import load_scenario_config
from traffic_agents.experiments.freeze import (
    ExperimentFreezeError,
    freeze_experiment_config,
    load_frozen_experiment_config_from_dir,
)
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
)
from traffic_agents.experiments.runner import ExperimentRunner, load_experiment_config
from traffic_agents.experiments.text_hashing import canonical_sha256
from traffic_agents.simulation import SumoEnvironmentInfo


def test_freeze_checksums_are_stable(tmp_path: Path) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    sumo_info = _sumo_info(tmp_path)

    first = freeze_experiment_config(
        config_path,
        artifacts_dir=tmp_path / "artifacts",
        sumo_info=sumo_info,
    )
    first_checksums = json.loads(first.checksums_path.read_text(encoding="utf-8"))

    second = freeze_experiment_config(
        config_path,
        artifacts_dir=tmp_path / "artifacts",
        sumo_info=sumo_info,
    )
    second_checksums = json.loads(second.checksums_path.read_text(encoding="utf-8"))

    assert first_checksums == second_checksums
    assert len(first_checksums["experiment_config_sha256"]) == 64


def test_modified_experiment_config_changes_hash(tmp_path: Path) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    config = load_experiment_config(config_path)
    original = freeze.build_freeze_checksums(config=config, config_path=config_path)

    config_path.write_text(config_path.read_text(encoding="utf-8") + "\n# changed\n")
    modified = freeze.build_freeze_checksums(config=config, config_path=config_path)

    assert modified["experiment_config_sha256"] != original["experiment_config_sha256"]


def test_modified_route_fails_route_artifact_validation(tmp_path: Path) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    config = load_experiment_config(config_path)

    route_path = tmp_path / "scenario" / "routes_s1_seed_42.rou.xml"
    route_path.write_text("<routes><vehicle id='changed'/></routes>", encoding="utf-8")

    with pytest.raises(ValueError, match="route_hash"):
        freeze.build_freeze_checksums(config=config, config_path=config_path)


def test_final_freeze_rejects_dirty_tree_via_mock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    monkeypatch.setattr(freeze, "is_working_tree_dirty", lambda _repo_path: True)

    with pytest.raises(ExperimentFreezeError, match="clean Git working tree"):
        freeze_experiment_config(
            config_path,
            final=True,
            artifacts_dir=tmp_path / "artifacts",
            sumo_info=_sumo_info(tmp_path),
        )


def test_experiment_runner_rejects_frozen_route_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    result = freeze_experiment_config(
        config_path,
        artifacts_dir=tmp_path / "artifacts",
        sumo_info=_sumo_info(tmp_path),
    )
    frozen_config = load_frozen_experiment_config_from_dir(result.freeze_dir)
    config = load_experiment_config(config_path)

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("simulation must not start after freeze mismatch")

    monkeypatch.setattr("traffic_agents.experiments.runner.TraCISimulationRunner", FakeRunner)
    route_path = tmp_path / "scenario" / "routes_s1_seed_42.rou.xml"
    route_path.write_text("<routes><vehicle id='changed'/></routes>", encoding="utf-8")

    with pytest.raises(ExperimentFreezeError, match="route_file"):
        ExperimentRunner(
            aggregate_metrics=False,
            config=config,
            artifacts_dir=tmp_path / "artifacts",
            frozen_config=frozen_config,
        ).run()


def _file_hash(checksums: dict[str, object], label: str) -> str:
    files = checksums["files"]
    assert isinstance(files, list)
    for entry in files:
        assert isinstance(entry, dict)
        if entry["label"] == label:
            value = entry["sha256"]
            assert isinstance(value, str)
            return value
    raise AssertionError(f"missing checksum label: {label}")


def _sumo_info(tmp_path: Path) -> SumoEnvironmentInfo:
    sumo_home = tmp_path / "sumo"
    bin_dir = sumo_home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    sumo_binary = bin_dir / "sumo.exe"
    sumo_gui_binary = bin_dir / "sumo-gui.exe"
    sumo_binary.write_text("", encoding="utf-8")
    sumo_gui_binary.write_text("", encoding="utf-8")
    return SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=sumo_binary,
        sumo_gui_binary=sumo_gui_binary,
        version="1.27.1",
    )


def _write_experiment_fixture(tmp_path: Path) -> Path:
    # Freeze identities are repository-relative, so the fixture lives in a (throw-away) git repo.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text(
        """
<net>
  <junction id="J1"/>
  <tlLogic id="J1" type="static" programID="0" offset="0">
    <phase duration="10" state="G"/>
    <phase duration="3" state="y"/>
    <phase duration="2" state="r"/>
  </tlLogic>
</net>
""".strip(),
        encoding="utf-8",
    )
    (scenario_dir / "metadata.json").write_text(
        json.dumps(
            {
                "phase_min_green_seconds": 10.0,
                "phase_yellow_seconds": 3.0,
                "phase_all_red_seconds": 2.0,
                "phase_max_green_seconds": 60.0,
                "traffic_light_ids": {"A1": "J1"},
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "routes_s1_seed_42.rou.xml").write_text("<routes/>", encoding="utf-8")
    (scenario_dir / "scenario.yaml").write_text(
        """
scenario_id: grid_3x3
network_file: network.net.xml
route_file: routes_s1_seed_42.rou.xml
duration_seconds: 2
warmup_seconds: 0
step_length: 1.0
seed: 42
controller_id: B0_FIXED
traffic:
  demand_profile: S1_BALANCED
  demand_level: MEDIUM
  turning_ratios:
    straight: 0.6
    left: 0.2
    right: 0.2
  flows:
    - flow_id: west_to_east_middle
      origin_edge_id: left1A1
      destination_edge_id: C1right1
      begin_seconds: 0
      end_seconds: 2
      vehicles_per_hour:
        LOW: 1
        MEDIUM: 2
        HIGH: 3
intersections:
  - intersection_id: A1
    incoming_lanes:
      - top1A1_0
      - right1A1_0
      - bottom1A1_0
      - left1A1_0
    outgoing_lanes:
      - A1top1_0
      - A1right1_0
      - A1bottom1_0
      - A1left1_0
    phases:
      - north_south
      - east_west
""".strip(),
        encoding="utf-8",
    )
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
experiment_id: freeze_smoke
scenario: scenario/scenario.yaml
controllers:
  - B0_FIXED
seeds:
  - 42
max_steps: 1
""".strip(),
        encoding="utf-8",
    )
    scenario_config = load_scenario_config(scenario_dir / "scenario.yaml")
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text(
        json.dumps(
            {
                "scenario_id": scenario_config.scenario_id,
                "seed": scenario_config.seed,
                "config_hash": route_generator_config_sha256(scenario_config),
                "scenario_hash": route_artifact_scenario_sha256(scenario_config),
                "route_hash": file_sha256(scenario_dir / "routes_s1_seed_42.rou.xml"),
                "network_hash": file_sha256(scenario_dir / "network.net.xml"),
                "generated_at": "2026-01-01T00:00:00Z",
                "generator_version": "test",
            }
        ),
        encoding="utf-8",
    )
    return config_path


# --- cross-platform (LF/CRLF) verification, CANONICAL_TEXT_LF_V1 ---------------------------
def _to_crlf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))


def _to_lf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _freeze_fixture(tmp_path: Path) -> tuple[Path, Path]:
    config_path = _write_experiment_fixture(tmp_path)
    result = freeze_experiment_config(
        config_path, artifacts_dir=tmp_path / "artifacts", sumo_info=_sumo_info(tmp_path)
    )
    return config_path, result.freeze_dir


def _frozen_paths(freeze_dir: Path, root: Path) -> list[Path]:
    checksums = json.loads((freeze_dir / "checksums.json").read_text(encoding="utf-8"))
    return [root / entry["relative_path"] for entry in checksums["files"]]


def test_new_freeze_records_raw_and_canonical_hashes(tmp_path: Path) -> None:
    _, freeze_dir = _freeze_fixture(tmp_path)
    checksums = json.loads((freeze_dir / "checksums.json").read_text(encoding="utf-8"))
    assert checksums["schema_version"] == 3
    assert checksums["hash_schema"] == "CANONICAL_TEXT_LF_V1"
    assert len(checksums["experiment_config_canonical_sha256"]) == 64
    for entry in checksums["files"]:
        assert entry["raw_byte_sha256"] == entry["sha256"]  # legacy key kept
        assert entry["canonical_sha256"] and entry["hash_schema"] == "CANONICAL_TEXT_LF_V1"
    fields = load_frozen_experiment_config_from_dir(freeze_dir).run_manifest_fields()
    assert set(fields) == {"experiment_config_sha256", "experiment_config_canonical_sha256"}


def test_freeze_created_with_lf_verifies_after_crlf_checkout(tmp_path: Path) -> None:
    _, freeze_dir = _freeze_fixture(tmp_path)
    paths = _frozen_paths(freeze_dir, tmp_path)
    for path in paths:
        _to_lf(path)
    load_frozen_experiment_config_from_dir(freeze_dir).validate()
    for path in paths:
        _to_crlf(path)
    load_frozen_experiment_config_from_dir(freeze_dir).validate()


def _record_canonical_artifact_hashes(tmp_path: Path) -> None:
    """New-style route metadata: canonical hashes authorise either line-ending representation."""

    scenario_dir = tmp_path / "scenario"
    metadata_path = scenario_dir / "routes_s1_seed_42.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["route_canonical_sha256"] = canonical_sha256(
        (scenario_dir / "routes_s1_seed_42.rou.xml").read_bytes()
    )
    metadata["network_canonical_sha256"] = canonical_sha256(
        (scenario_dir / "network.net.xml").read_bytes()
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def test_freeze_created_with_crlf_verifies_after_lf_checkout(tmp_path: Path) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    _record_canonical_artifact_hashes(tmp_path)
    config = load_experiment_config(config_path)
    lf_paths = [
        tmp_path / entry["relative_path"]
        for entry in freeze.build_freeze_checksums(config=config, config_path=config_path)["files"]  # type: ignore[union-attr]
    ]
    for path in lf_paths:
        _to_lf(path)
    lf = freeze.build_freeze_checksums(config=config, config_path=config_path)
    for path in lf_paths:
        _to_crlf(path)
    crlf = freeze.build_freeze_checksums(config=config, config_path=config_path)
    lf_files, crlf_files = lf["files"], crlf["files"]
    assert [e["raw_byte_sha256"] for e in lf_files] != [e["raw_byte_sha256"] for e in crlf_files]  # type: ignore[union-attr]
    assert [e["canonical_sha256"] for e in lf_files] == [e["canonical_sha256"] for e in crlf_files]  # type: ignore[union-attr]
    freeze_dir = tmp_path / "frozen"
    freeze_dir.mkdir()
    (freeze_dir / "checksums.json").write_text(json.dumps(crlf), encoding="utf-8")
    (freeze_dir / "freeze_manifest.json").write_text("{}", encoding="utf-8")
    for path in lf_paths:
        _to_lf(path)
    load_frozen_experiment_config_from_dir(freeze_dir).validate()


def test_real_content_change_is_still_rejected(tmp_path: Path) -> None:
    config_path, freeze_dir = _freeze_fixture(tmp_path)
    for path in _frozen_paths(freeze_dir, tmp_path):
        _to_crlf(path)
    config_path.write_text(config_path.read_text(encoding="utf-8") + "# changed\n")
    with pytest.raises(ExperimentFreezeError, match="experiment_config"):
        load_frozen_experiment_config_from_dir(freeze_dir).validate()


def test_whitespace_change_is_a_content_change(tmp_path: Path) -> None:
    config_path, freeze_dir = _freeze_fixture(tmp_path)
    config_path.write_bytes(config_path.read_bytes().rstrip(b"\r\n") + b" ")
    with pytest.raises(ExperimentFreezeError, match="experiment_config"):
        load_frozen_experiment_config_from_dir(freeze_dir).validate()
