from __future__ import annotations

from pathlib import Path

import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.simulation import SumoEnvironmentInfo, TraCISimulationRunner


class FakeSimulation:
    def __init__(self) -> None:
        self.departed_numbers = [2, 1]
        self.arrived_numbers = [0, 1]

    def getDepartedNumber(self) -> int:  # noqa: N802
        return self.departed_numbers.pop(0)

    def getArrivedNumber(self) -> int:  # noqa: N802
        return self.arrived_numbers.pop(0)


class FakeConnection:
    def __init__(self) -> None:
        self.simulation = FakeSimulation()
        self.steps = 0
        self.adaptive_adjustments = 0

    def simulationStep(self) -> None:  # noqa: N802
        self.steps += 1


class FakeTraCI:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.started_commands: list[list[str]] = []
        self.closed = False
        self.switched_label: str | None = None

    def start(self, command: list[str], *, label: str) -> None:
        self.started_commands.append(command)

    def getConnection(self, label: str) -> FakeConnection:  # noqa: N802
        return self.connection

    def switch(self, label: str) -> None:
        self.switched_label = label

    def close(self, wait: bool) -> None:
        assert wait is False
        self.closed = True


def make_scenario_config(duration_seconds: int = 2) -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=duration_seconds,
        warmup_seconds=0,
        step_length=1.0,
        seed=42,
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
                    "end_seconds": 2,
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
                "incoming_lanes": ["left1A1_0"],
                "outgoing_lanes": ["A1left1_0"],
                "phases": ["north_south", "east_west"],
            }
        ],
    )


def make_sumo_info(tmp_path: Path) -> SumoEnvironmentInfo:
    sumo_home = tmp_path / "sumo"
    tools_dir = sumo_home / "tools"
    bin_dir = sumo_home / "bin"
    tools_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    sumo_binary = bin_dir / "sumo.exe"
    sumo_binary.write_text("", encoding="utf-8")
    return SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=sumo_binary,
        sumo_gui_binary=bin_dir / "sumo-gui.exe",
        version="1.27.1",
    )


def make_scenario_dir(tmp_path: Path) -> Path:
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "network.net.xml").write_text("<net/>", encoding="utf-8")
    (scenario_dir / "routes_s1_seed_42.rou.xml").write_text("<routes/>", encoding="utf-8")
    return scenario_dir


def test_traci_runner_runs_headless_steps_and_collects_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(),
        scenario_dir=make_scenario_dir(tmp_path),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 2
    assert summary.controller_id == "B0_FIXED"
    assert summary.controller_version
    assert summary.vehicles_departed == 3
    assert summary.vehicles_arrived == 1
    assert fake_traci.connection.adaptive_adjustments == 0
    assert fake_traci.closed is True
    assert fake_traci.switched_label == "test-simulation"
    command = fake_traci.started_commands[0]
    assert command[0].endswith("sumo.exe")
    assert "--net-file" in command
    assert "--route-files" in command
    assert "--start" not in command


def test_traci_runner_can_use_gui_binary_and_step_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    sumo_info = make_sumo_info(tmp_path)
    sumo_info.sumo_gui_binary.write_text("", encoding="utf-8")

    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(duration_seconds=10),
        scenario_dir=make_scenario_dir(tmp_path),
        sumo_info=sumo_info,
        label="test-simulation",
        use_gui=True,
        max_steps=2,
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 2
    command = fake_traci.started_commands[0]
    assert command[0].endswith("sumo-gui.exe")
    assert "--start" in command


def test_traci_runner_stops_safely_when_step_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")

    def raise_on_step() -> None:
        raise RuntimeError("step failed")

    fake_traci.connection.simulationStep = raise_on_step  # type: ignore[method-assign]
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(duration_seconds=1),
        scenario_dir=make_scenario_dir(tmp_path),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    with pytest.raises(RuntimeError, match="step failed"):
        runner.run()

    assert fake_traci.closed is True


def test_traci_runner_writes_run_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(),
        scenario_dir=make_scenario_dir(tmp_path),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        artifacts_dir=tmp_path / "artifacts" / "runs",
    )

    summary = runner.run()

    assert summary.manifest_path is not None
    manifest = summary.manifest_path.read_text(encoding="utf-8")
    assert '"controller_id": "B0_FIXED"' in manifest
    assert '"demand_profile": "S1_BALANCED"' in manifest
    assert '"seed": 42' in manifest
    assert '"metrics_finalized": false' in manifest


@pytest.mark.sumo
def test_real_sumo_simulation_smoke() -> None:
    scenario_path = Path("scenarios/grid_3x3/scenario.yaml")
    from traffic_agents.config import load_scenario_config

    runner = TraCISimulationRunner(
        scenario_config=load_scenario_config(scenario_path),
        scenario_dir=scenario_path.parent,
        label="integration-sumo-smoke",
    )

    summary = runner.run()

    assert summary.steps_executed == 3600
    assert summary.vehicles_departed > 0
    assert summary.vehicles_arrived > 0
