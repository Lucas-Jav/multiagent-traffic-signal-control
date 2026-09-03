from __future__ import annotations

import json
from pathlib import Path

import pytest

from traffic_agents.experiments.runner import ExperimentRunner, load_experiment_config
from traffic_agents.simulation import SimulationRunSummary


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

    monkeypatch.setattr(
        "traffic_agents.experiments.runner.load_scenario_config",
        lambda _path: type(
            "FakeScenarioConfig",
            (),
            {
                "model_copy": lambda self, *, update: self,
            },
        )(),
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
