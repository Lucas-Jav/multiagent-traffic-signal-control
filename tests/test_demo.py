from __future__ import annotations

from pathlib import Path

import pytest

import traffic_agents.demo as demo
from traffic_agents.config import ScenarioConfig
from traffic_agents.controllers import build_controller
from traffic_agents.controllers.cooperative_compact import CooperativeCompactController
from traffic_agents.controllers.fixed_time import FixedTimeController
from traffic_agents.controllers.local_pressure import LocalPressureController
from traffic_agents.simulation import SimulationRunSummary


def make_scenario_config() -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=60,
        warmup_seconds=0,
        step_length=1.0,
        seed=1,
        controller_id="B0_FIXED",
        traffic={
            "demand_profile": "S1_BALANCED",
            "demand_level": "MEDIUM",
            "flows": [
                {
                    "flow_id": "west_to_east_middle",
                    "origin_edge_id": "left1A1",
                    "destination_edge_id": "C1right1",
                    "begin_seconds": 0,
                    "end_seconds": 60,
                    "vehicles_per_hour": {
                        "LOW": 1,
                        "MEDIUM": 2,
                        "HIGH": 3,
                    },
                }
            ],
        },
        intersections=[
            {
                "intersection_id": "A1",
                "incoming_lanes": [
                    "top1A1_0",
                    "right1A1_0",
                    "bottom1A1_0",
                    "left1A1_0",
                ],
                "outgoing_lanes": [
                    "A1top1_0",
                    "A1right1_0",
                    "A1bottom1_0",
                    "A1left1_0",
                ],
                "phases": ["north_south", "east_west"],
            }
        ],
    )


def test_demo_scenario_aliases_resolve_to_existing_experiment_configs() -> None:
    for scenario_id, path in demo.SCENARIO_ALIASES.items():
        assert demo.resolve_demo_scenario_path(scenario_id) == path
        assert path.exists()


def test_run_demo_uses_same_scenario_loader_and_traci_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_paths: list[Path] = []
    runner_calls: list[dict[str, object]] = []

    def fake_load_scenario_config(path: Path) -> ScenarioConfig:
        loaded_paths.append(path)
        return make_scenario_config()

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            runner_calls.append(kwargs)

        @property
        def controller(self) -> object:
            return object()

        def run(self) -> SimulationRunSummary:
            return SimulationRunSummary(
                started_at="2026-01-01T00:00:00Z",
                ended_at="2026-01-01T00:00:01Z",
                run_id="demo-run",
                manifest_path=None,
                scenario_id="grid_3x3",
                controller_id="B2_LOCAL_PRESSURE",
                controller_version="0.1.0",
                demand_profile="S1_BALANCED",
                seed=42,
                steps_executed=5,
                vehicles_departed=0,
                vehicles_arrived=0,
                wall_time_seconds=0.1,
            )

    monkeypatch.setattr(demo, "load_scenario_config", fake_load_scenario_config)
    monkeypatch.setattr(demo, "TraCISimulationRunner", FakeRunner)

    result = demo.run_demo(
        demo.DemoConfig(
            scenario="S2_DIRECTIONAL_PEAK",
            controller_id="B2_LOCAL_PRESSURE",
            seed=42,
            focus_agent="A5",
            speed_factor=20.0,
            max_steps=5,
        )
    )

    assert result.scenario_path == demo.SCENARIO_ALIASES["S2_DIRECTIONAL_PEAK"]
    assert loaded_paths == [demo.SCENARIO_ALIASES["S2_DIRECTIONAL_PEAK"]]
    assert len(runner_calls) == 1
    call = runner_calls[0]
    scenario_config = call["scenario_config"]
    assert isinstance(scenario_config, ScenarioConfig)
    assert scenario_config.controller_id == "B2_LOCAL_PRESSURE"
    assert scenario_config.seed == 42
    assert call["scenario_dir"] == demo.SCENARIO_ALIASES["S2_DIRECTIONAL_PEAK"].parent
    assert call["use_gui"] is True
    assert call["step_delay_seconds"] == 0.05
    assert call["max_steps"] == 5
    assert call["controller_id"] == "B2_LOCAL_PRESSURE"
    assert call["write_manifest"] is False
    assert call["run_mode"] == "DEMO"
    assert callable(call["step_telemetry_consumer"])
    assert result.summary.controller_id == "B2_LOCAL_PRESSURE"


def test_demo_write_artifact_uses_demo_artifact_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_calls: list[dict[str, object]] = []

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            runner_calls.append(kwargs)

        def run(self) -> SimulationRunSummary:
            return SimulationRunSummary(
                started_at="2026-01-01T00:00:00Z",
                ended_at="2026-01-01T00:00:01Z",
                run_id="demo-run",
                manifest_path=Path("artifacts/demos/demo-run/manifest.json"),
                scenario_id="grid_3x3",
                controller_id="B0_FIXED",
                controller_version="0.1.0",
                demand_profile="S1_BALANCED",
                seed=42,
                steps_executed=1,
                vehicles_departed=0,
                vehicles_arrived=0,
                wall_time_seconds=0.1,
            )

    monkeypatch.setattr(demo, "load_scenario_config", lambda _path: make_scenario_config())
    monkeypatch.setattr(demo, "TraCISimulationRunner", FakeRunner)

    demo.run_demo(
        demo.DemoConfig(
            scenario="S1_BALANCED",
            controller_id="B0_FIXED",
            seed=42,
            write_artifact=True,
        )
    )

    call = runner_calls[0]
    assert call["write_manifest"] is True
    assert call["run_mode"] == "DEMO"
    assert Path(call["artifacts_dir"]).parts[-1] == "demos"


def test_demo_controller_ids_are_resolved_by_same_controller_registry() -> None:
    assert isinstance(build_controller("B0_FIXED"), FixedTimeController)
    assert isinstance(build_controller("B2_LOCAL_PRESSURE"), LocalPressureController)
    assert isinstance(
        build_controller("C1_COOPERATIVE_COMPACT"),
        CooperativeCompactController,
    )


def test_demo_module_has_no_alternate_decision_logic() -> None:
    source = Path("src/traffic_agents/demo.py").read_text(encoding="utf-8")

    assert "build_controller" not in source
    assert ".decide(" not in source
    assert "PhaseSafetyManager" not in source


def test_run_demo_rejects_invalid_gui_speed_factor() -> None:
    with pytest.raises(demo.DemoConfigurationError, match="speed_factor"):
        demo.run_demo(
            demo.DemoConfig(
                scenario="S1_BALANCED",
                controller_id="B0_FIXED",
                seed=42,
                speed_factor=0,
            )
        )
