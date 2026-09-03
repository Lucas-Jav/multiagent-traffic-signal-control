from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

import traffic_agents.simulation.sumo_runner as sumo_runner
from traffic_agents.communication import grid_3x3_communication_topology
from traffic_agents.communication_seed import derive_communication_rng_seed
from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments import RunInvariantValidationError
from traffic_agents.metrics import StepTelemetryRecord
from traffic_agents.simulation import SumoEnvironmentInfo, TraCISimulationRunner
from traffic_agents.traffic_model import MOVEMENT_MODEL_VERSION, PHASE_PLAN_VERSION


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


class FakeTelemetryController:
    controller_id = "TELEMETRY_FAKE"
    controller_version = "0.1.0"

    def before_simulation_step(self, connection: FakeConnection) -> None:
        return None

    def after_simulation_step(self, connection: FakeConnection) -> None:
        return None

    def manifest_metadata(self) -> dict[str, str | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": True,
        }

    def pop_step_telemetry_records(self) -> tuple[StepTelemetryRecord, ...]:
        return (
            StepTelemetryRecord(
                step_index=0,
                timestamp=0.0,
                intersection_id="A1",
                movement_id="A1:north_to_south",
                approach_id="top0A2",
                queue=1,
                occupancy=0.2,
                speed=3.0,
                current_phase="phase_0",
                phase_elapsed=4.0,
                requested_phase="phase_3",
                actual_phase="phase_1",
                safety_override=True,
                turn_count_straight=0.6,
                turn_count_left=0.2,
                turn_count_right=0.2,
                junction_entries=1,
                junction_exits=0,
                junction_blocking_events=0,
                clearance_violations=0,
                turn_completion_count=0.0,
                movement_queue_mean=1.0,
                movement_queue_max=1,
            ),
        )


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


def test_traci_runner_loads_scenario_viewsettings_for_gui(
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
    scenario_dir = make_scenario_dir(tmp_path)
    viewsettings_path = scenario_dir / "viewsettings.xml"
    viewsettings_path.write_text("<viewsettings/>", encoding="utf-8")

    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(duration_seconds=1),
        scenario_dir=scenario_dir,
        sumo_info=sumo_info,
        label="test-simulation",
        use_gui=True,
        write_manifest=False,
    )

    runner.run()

    command = fake_traci.started_commands[0]
    assert "--gui-settings-file" in command
    assert str(viewsettings_path) in command


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


def test_traci_runner_fails_fast_before_traci_start_on_invalid_run_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    scenario_dir = make_scenario_dir(tmp_path)
    (scenario_dir / "metadata.json").write_text(
        json.dumps(
            {
                "phase_min_green_seconds": 10.0,
                "phase_yellow_seconds": 4.0,
                "phase_all_red_seconds": 2.0,
                "phase_max_green_seconds": 60.0,
                "traffic_light_ids": {"A1": "J1"},
            }
        ),
        encoding="utf-8",
    )
    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(duration_seconds=1),
        scenario_dir=scenario_dir,
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    with pytest.raises(RunInvariantValidationError, match="invalid phase plan"):
        runner.run()

    assert fake_traci.started_commands == []
    assert fake_traci.closed is False


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

    scenario_dir = make_scenario_dir(tmp_path)
    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(),
        scenario_dir=scenario_dir,
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        artifacts_dir=tmp_path / "artifacts" / "runs",
    )

    summary = runner.run()

    assert summary.manifest_path is not None
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))

    assert manifest["controller"]["controller_id"] == "B0_FIXED"
    assert manifest["demand_profile"] == "S1_BALANCED"
    assert manifest["seed"] == 42
    assert manifest["python_version"]
    assert manifest["sumo_version"] == "1.27.1"
    assert manifest["git_sha"] is None or isinstance(manifest["git_sha"], str)
    assert manifest["metrics_finalized"] is False
    assert len(manifest["scenario_sha256"]) == 64
    assert manifest["network_sha256"] == _sha256(scenario_dir / "network.net.xml")
    assert manifest["route_sha256"] == _sha256(scenario_dir / "routes_s1_seed_42.rou.xml")
    assert manifest["phase_plan_version"] == PHASE_PLAN_VERSION
    assert len(manifest["phase_plan_sha256"]) == 64
    assert manifest["movement_model_version"] == MOVEMENT_MODEL_VERSION
    assert manifest["turning_ratios"] == {"straight": 0.6, "left": 0.2, "right": 0.2}
    assert manifest["communication"] == {
        "delay_steps": 0,
        "drop_probability": 0.0,
        "rng_seed": derive_communication_rng_seed(
            simulation_seed=42,
            delay_steps=0,
            drop_probability=0.0,
        ),
        "max_message_age_steps": 1,
    }
    assert manifest["communication_topology_sha256"] == (
        grid_3x3_communication_topology().topology_hash
    )
    assert len(manifest["network_sha256"]) == 64
    assert len(manifest["route_sha256"]) == 64
    assert len(manifest["communication_topology_sha256"]) == 64


def test_traci_runner_writes_intersection_trace_for_telemetry_controller(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    monkeypatch.setattr(
        sumo_runner,
        "build_controller",
        lambda _controller_id: FakeTelemetryController(),
    )
    scenario_dir = make_scenario_dir(tmp_path)
    runner = TraCISimulationRunner(
        scenario_config=make_scenario_config(duration_seconds=1),
        scenario_dir=scenario_dir,
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        artifacts_dir=tmp_path / "artifacts" / "runs",
    )

    summary = runner.run()

    assert summary.manifest_path is not None
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    trace_path = summary.manifest_path.parent / manifest["intersection_trace_file"]
    with trace_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["intersection_id"] == "A1"
    assert rows[0]["movement_id"] == "A1:north_to_south"
    assert rows[0]["requested_phase"] == "phase_3"
    assert rows[0]["actual_phase"] == "phase_1"
    assert rows[0]["safety_override"] == "True"
    assert rows[0]["junction_blocking_events"] == "0"
    assert rows[0]["clearance_violations"] == "0"
    assert rows[0]["turn_completion_count"] == "0.0"
    assert rows[0]["movement_queue_mean"] == "1.0"
    assert rows[0]["movement_queue_max"] == "1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
