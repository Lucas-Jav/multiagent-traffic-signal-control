from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from traffic_agents.config import CommunicationConfig
from traffic_agents.experiments.runner import ExperimentRunner, load_experiment_config
from traffic_agents.simulation import SimulationRunSummary


class FakeSimulationConfig:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    def model_copy(self, *, update: dict[str, object]) -> FakeSimulationConfig:
        self.updates.append(update)
        return self


class FakeScenarioConfig:
    def __init__(self) -> None:
        self.simulation = FakeSimulationConfig()
        self.updates: list[dict[str, object]] = []

    def model_copy(self, *, update: dict[str, object]) -> FakeScenarioConfig:
        self.updates.append(update)
        return self


def test_load_experiment_config_resolves_relative_scenario_path(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "experiment.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
experiment_id: smoke
scenario: ../scenarios/grid_3x3/scenario.yaml
controllers:
  - B0_FIXED
seeds:
  - 42
max_steps: 10
""".strip(),
        encoding="utf-8",
    )

    config = load_experiment_config(config_path)

    assert config.scenario == (
        tmp_path / "configs" / ".." / "scenarios" / "grid_3x3" / "scenario.yaml"
    )


def test_load_experiment_config_resolves_explicit_run_scenario_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "experiment.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
experiment_id: s5
runs:
  - run_id: s5_c1_delay0_drop0
    scenario_base: S2_DIRECTIONAL_PEAK
    scenario: ../scenarios/grid_3x3/scenario_s2_directional_peak.yaml
    controller_id: C1_COOPERATIVE_COMPACT
    seed: 42
    communication_seed_policy: derived_from_simulation_seed_delay_drop
    communication:
      delay_steps: 0
      drop_probability: 0.0
      rng_seed: null
      max_message_age_steps: 1
""".strip(),
        encoding="utf-8",
    )

    config = load_experiment_config(config_path)

    assert config.runs[0].scenario == (
        tmp_path / "configs" / ".." / "scenarios" / "grid_3x3" / "scenario_s2_directional_peak.yaml"
    )


def test_experiment_runner_writes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text("scenario", encoding="utf-8")
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
experiment_id: smoke
scenario: scenario.yaml
controllers:
  - B0_FIXED
seeds:
  - 42
max_steps: 10
""".strip(),
        encoding="utf-8",
    )
    config = load_experiment_config(config_path)

    scenario_config = FakeScenarioConfig()
    monkeypatch.setattr(
        "traffic_agents.experiments.runner.load_scenario_config",
        lambda _path: scenario_config,
    )

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            self._kwargs = kwargs

        def run(self) -> SimulationRunSummary:
            return SimulationRunSummary(
                started_at="2026-01-01T00:00:00Z",
                ended_at="2026-01-01T00:00:01Z",
                run_id="run-1",
                manifest_path=Path("artifacts/runs/run-1/manifest.json"),
                scenario_id="grid_3x3",
                controller_id="B0_FIXED",
                controller_version="0.1.0",
                demand_profile="S1_BALANCED",
                seed=42,
                steps_executed=10,
                vehicles_departed=1,
                vehicles_arrived=1,
                wall_time_seconds=0.1,
            )

    monkeypatch.setattr("traffic_agents.experiments.runner.TraCISimulationRunner", FakeRunner)

    summary = ExperimentRunner(config=config, artifacts_dir=tmp_path / "artifacts").run()

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "smoke"
    assert manifest["runs"][0]["controller_id"] == "B0_FIXED"
    assert scenario_config.simulation.updates == [{"seed": 42}]


def test_experiment_runner_applies_explicit_run_communication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text("scenario", encoding="utf-8")
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """
experiment_id: s5
runs:
  - run_id: s5_c1_delay3_drop010
    scenario_base: S2_DIRECTIONAL_PEAK
    scenario: scenario.yaml
    controller_id: C1_COOPERATIVE_COMPACT
    seed: 42
    max_steps: 15
    communication_seed_policy: derived_from_simulation_seed_delay_drop
    communication:
      delay_steps: 3
      drop_probability: 0.10
      rng_seed: null
      max_message_age_steps: 1
""".strip(),
        encoding="utf-8",
    )
    config = load_experiment_config(config_path)

    scenario_config = FakeScenarioConfig()
    monkeypatch.setattr(
        "traffic_agents.experiments.runner.load_scenario_config",
        lambda _path: scenario_config,
    )

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            self._kwargs = kwargs

        def run(self) -> SimulationRunSummary:
            assert self._kwargs["controller_id"] == "C1_COOPERATIVE_COMPACT"
            assert self._kwargs["max_steps"] == 15
            return SimulationRunSummary(
                started_at="2026-01-01T00:00:00Z",
                ended_at="2026-01-01T00:00:01Z",
                run_id="run-1",
                manifest_path=Path("artifacts/runs/run-1/manifest.json"),
                scenario_id="grid_3x3",
                controller_id="C1_COOPERATIVE_COMPACT",
                controller_version="0.1.0",
                demand_profile="S2_DIRECTIONAL_PEAK",
                seed=42,
                steps_executed=15,
                vehicles_departed=1,
                vehicles_arrived=1,
                wall_time_seconds=0.1,
            )

    monkeypatch.setattr("traffic_agents.experiments.runner.TraCISimulationRunner", FakeRunner)

    summary = ExperimentRunner(config=config, artifacts_dir=tmp_path / "artifacts").run()

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    communication = cast(CommunicationConfig, scenario_config.updates[0]["communication"])
    assert communication.delay_steps == 3
    assert communication.drop_probability == 0.10
    assert communication.max_message_age_steps == 1
    assert scenario_config.simulation.updates == [{"seed": 42}]
    assert manifest["runs"][0]["config_run_id"] == "s5_c1_delay3_drop010"
    assert manifest["runs"][0]["configured_communication"] == {
        "delay_steps": 3,
        "drop_probability": 0.10,
        "rng_seed": None,
        "max_message_age_steps": 1,
    }
