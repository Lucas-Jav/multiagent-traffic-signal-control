from pathlib import Path

import pytest

from traffic_agents.__main__ import main
from traffic_agents.config import get_settings
from traffic_agents.simulation import SimulationRunSummary


def test_main_prints_application_name_and_environment(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()

    main()

    assert capsys.readouterr().out == "Traffic Multi-Agent Control\nenvironment=test\n"
    get_settings.cache_clear()


def test_simulation_run_subcommand_invokes_runner(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_path = _write_scenario(tmp_path)
    runner_calls: list[dict[str, object]] = []

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            runner_calls.append(kwargs)

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

    monkeypatch.setattr("traffic_agents.__main__.TraCISimulationRunner", FakeRunner)

    exit_code = main(
        [
            "simulation",
            "run",
            "--scenario",
            str(scenario_path),
            "--controller",
            "B0_FIXED",
            "--seed",
            "42",
            "--max-steps",
            "10",
        ]
    )

    assert exit_code == 0
    assert len(runner_calls) == 1
    call = runner_calls[0]
    assert call["scenario_dir"] == scenario_path.parent
    assert call["controller_id"] == "B0_FIXED"
    assert call["max_steps"] == 10
    assert f"manifest={Path('artifacts/runs/run-1/manifest.json')}" in capsys.readouterr().out


def test_experiment_run_subcommand_invokes_runner(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    class FakeExperimentRunner:
        def __init__(self, *, config: object) -> None:
            self._config = config

        def run(self) -> object:
            return type(
                "FakeSummary",
                (),
                {
                    "experiment_id": "smoke",
                    "run_summaries": (),
                    "manifest_path": Path("artifacts/experiments/smoke/manifest.json"),
                },
            )()

    monkeypatch.setattr("traffic_agents.__main__.ExperimentRunner", FakeExperimentRunner)

    exit_code = main(["experiment", "run", "--config", str(config_path)])

    assert exit_code == 0
    assert "experiment_id=smoke" in capsys.readouterr().out


def test_experiment_report_subcommand_invokes_report_generator(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "smoke"

    def fake_generate_experiment_report(path: Path) -> object:
        assert path == experiment_folder
        return type(
            "FakeReport",
            (),
            {
                "figures_dir": experiment_folder / "figures",
                "generated_files": (experiment_folder / "figures" / "waiting_time.png",),
            },
        )()

    monkeypatch.setattr(
        "traffic_agents.__main__.generate_experiment_report",
        fake_generate_experiment_report,
    )
    monkeypatch.setattr(
        "traffic_agents.__main__.generate_experiment_summary",
        lambda _path: type(
            "FakeSummary",
            (),
            {"summary_path": experiment_folder / "summary.md"},
        )(),
    )

    exit_code = main(["experiment", "report", str(experiment_folder)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert f"figures_dir={experiment_folder / 'figures'}" in output
    assert f"figure={experiment_folder / 'figures' / 'waiting_time.png'}" in output
    assert f"summary={experiment_folder / 'summary.md'}" in output


def test_experiment_summary_subcommand_invokes_summary_generator(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_folder = tmp_path / "artifacts" / "experiments" / "smoke"

    def fake_generate_experiment_summary(path: Path) -> object:
        assert path == experiment_folder
        return type(
            "FakeSummary",
            (),
            {"summary_path": experiment_folder / "summary.md"},
        )()

    monkeypatch.setattr(
        "traffic_agents.__main__.generate_experiment_summary",
        fake_generate_experiment_summary,
    )

    exit_code = main(["experiment", "summary", str(experiment_folder)])

    assert exit_code == 0
    assert f"summary={experiment_folder / 'summary.md'}" in capsys.readouterr().out


def _write_scenario(tmp_path: Path) -> Path:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        """
scenario_id: grid_3x3
network_file: network.net.xml
route_file: routes_s1_seed_42.rou.xml
duration_seconds: 60
warmup_seconds: 0
step_length: 1.0
seed: 1
controller_id: B0_FIXED
traffic:
  demand_profile: S1_BALANCED
  demand_level: MEDIUM
  flows:
    - flow_id: west_to_east_middle
      origin_edge_id: left1A1
      destination_edge_id: C1right1
      begin_seconds: 0
      end_seconds: 60
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
    return scenario_path
