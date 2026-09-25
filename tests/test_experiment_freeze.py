from __future__ import annotations

import json
from pathlib import Path

import pytest

import traffic_agents.experiments.freeze as freeze
from traffic_agents.experiments.freeze import (
    ExperimentFreezeError,
    freeze_experiment_config,
    load_frozen_experiment_config_from_dir,
)
from traffic_agents.experiments.runner import ExperimentRunner, load_experiment_config
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


def test_modified_route_changes_hash(tmp_path: Path) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    config = load_experiment_config(config_path)
    original = freeze.build_freeze_checksums(config=config, config_path=config_path)

    route_path = tmp_path / "scenario" / "routes_s1_seed_42.rou.xml"
    route_path.write_text("<routes><vehicle id='changed'/></routes>", encoding="utf-8")
    modified = freeze.build_freeze_checksums(config=config, config_path=config_path)

    assert _file_hash(modified, "route_file") != _file_hash(original, "route_file")


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
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text(
        '{"config_hash":"abc"}\n',
        encoding="utf-8",
    )
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
    return config_path
