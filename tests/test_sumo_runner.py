from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

import traffic_agents.simulation.sumo_runner as sumo_runner
from traffic_agents.communication import (
    MessageBus,
    MessageBusConfig,
    grid_3x3_communication_topology,
)
from traffic_agents.communication_seed import derive_communication_rng_seed
from traffic_agents.config import ScenarioConfig, TracingConfig
from traffic_agents.experiments import RunInvariantValidationError
from traffic_agents.experiments.run_invariants import (
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
)
from traffic_agents.metrics import StepTelemetryRecord
from traffic_agents.simulation import SumoEnvironmentInfo, TraCISimulationRunner
from traffic_agents.traffic_model import MOVEMENT_MODEL_VERSION, PHASE_PLAN_VERSION


class FakeSimulation:
    def __init__(
        self,
        departed_numbers: list[int] | None = None,
        arrived_numbers: list[int] | None = None,
    ) -> None:
        self.departed_numbers = departed_numbers or [2, 1]
        self.arrived_numbers = arrived_numbers or [0, 1]

    def getDepartedNumber(self) -> int:  # noqa: N802
        return self.departed_numbers.pop(0)

    def getArrivedNumber(self) -> int:  # noqa: N802
        return self.arrived_numbers.pop(0)


class FakeConnection:
    def __init__(
        self,
        departed_numbers: list[int] | None = None,
        arrived_numbers: list[int] | None = None,
    ) -> None:
        self.simulation = FakeSimulation(
            departed_numbers=departed_numbers,
            arrived_numbers=arrived_numbers,
        )
        self.steps = 0
        self.adaptive_adjustments = 0

    def simulationStep(self) -> None:  # noqa: N802
        self.steps += 1


class FakeTraCI:
    def __init__(
        self,
        departed_numbers: list[int] | None = None,
        arrived_numbers: list[int] | None = None,
    ) -> None:
        self.connection = FakeConnection(
            departed_numbers=departed_numbers,
            arrived_numbers=arrived_numbers,
        )
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
                internal_lane_persistence_events=0,
                clearance_violations=0,
                turn_completion_count=0.0,
                movement_queue_mean=1.0,
                movement_queue_max=1,
            ),
        )


class FakeCountingController:
    controller_id = "COUNTING_FAKE"
    controller_version = "0.1.0"

    def __init__(self) -> None:
        self.before_calls = 0
        self.after_calls = 0

    def before_simulation_step(self, connection: FakeConnection) -> None:
        self.before_calls += 1

    def after_simulation_step(self, connection: FakeConnection) -> None:
        self.after_calls += 1

    def manifest_metadata(self) -> dict[str, str | bool]:
        return {
            "controller_id": self.controller_id,
            "controller_version": self.controller_version,
            "adaptive_adjustments_enabled": True,
        }


class FakeMessageBusController(FakeCountingController):
    controller_id = "MESSAGE_BUS_FAKE"

    def __init__(self) -> None:
        super().__init__()
        self.bus = MessageBus(
            destinations=("A1", "A2"),
            config=MessageBusConfig(delay_steps=1, simulation_seed=42),
        )
        self.delivered_messages = 0

    def before_simulation_step(self, connection: FakeConnection) -> None:
        step = self.before_calls
        super().before_simulation_step(connection)
        self.bus.publish(
            source="A1",
            destination="A2",
            created_step=step,
            payload={"queue": step},
        )
        self.delivered_messages += len(self.bus.receive(destination="A2", current_step=step))


def make_scenario_config(
    *,
    duration_seconds: int = 2,
    warmup_seconds: int = 0,
) -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id="grid_3x3",
        network_file="network.net.xml",
        route_file="routes_s1_seed_42.rou.xml",
        duration_seconds=duration_seconds,
        warmup_seconds=warmup_seconds,
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
                    "end_seconds": duration_seconds,
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


def make_scenario_dir(
    tmp_path: Path,
    scenario_config: ScenarioConfig | None = None,
) -> Path:
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
    route_path = scenario_dir / "routes_s1_seed_42.rou.xml"
    route_path.write_text("<routes/>", encoding="utf-8")
    scenario_config = scenario_config or make_scenario_config()
    (scenario_dir / "routes_s1_seed_42.metadata.json").write_text(
        json.dumps(
            {
                "scenario_id": scenario_config.scenario_id,
                "seed": scenario_config.seed,
                "config_hash": route_generator_config_sha256(scenario_config),
                "scenario_hash": route_artifact_scenario_sha256(scenario_config),
                "route_hash": _sha256(route_path),
                "network_hash": _sha256(scenario_dir / "network.net.xml"),
                "generated_at": "2026-01-01T00:00:00Z",
                "generator_version": "test",
            }
        ),
        encoding="utf-8",
    )
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
    assert summary.measurement_steps_executed == 2
    assert summary.controller_id == "B0_FIXED"
    assert summary.controller_version
    assert summary.vehicles_departed == 3
    assert summary.vehicles_arrived == 1
    assert summary.total_vehicles_departed == 3
    assert summary.total_vehicles_arrived == 1
    assert summary.measurement_start_step == 0
    assert summary.measurement_end_step == 2
    assert summary.total_simulation_steps == 2
    assert fake_traci.connection.adaptive_adjustments == 0
    assert fake_traci.closed is True
    assert fake_traci.switched_label == "test-simulation"
    command = fake_traci.started_commands[0]
    assert command[0].endswith("sumo.exe")
    assert "--net-file" in command
    assert "--route-files" in command
    assert "--start" not in command


def test_traci_runner_excludes_warmup_from_summary_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(
        departed_numbers=[10, 20, 30, 40, 50],
        arrived_numbers=[1, 2, 3, 4, 5],
    )
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    scenario_config = make_scenario_config(duration_seconds=3, warmup_seconds=2)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 5
    assert summary.measurement_start_step == 2
    assert summary.measurement_end_step == 5
    assert summary.total_simulation_steps == 5
    assert summary.measurement_steps_executed == 3
    assert summary.vehicles_departed == 120
    assert summary.vehicles_arrived == 12
    assert summary.total_vehicles_departed == 150
    assert summary.total_vehicles_arrived == 15


def test_traci_runner_boundary_step_starts_measurement_after_warmup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(
        departed_numbers=[10, 20, 30],
        arrived_numbers=[1, 2, 3],
    )
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    scenario_config = make_scenario_config(duration_seconds=3, warmup_seconds=2)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        max_steps=3,
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 3
    assert summary.measurement_steps_executed == 1
    assert summary.vehicles_departed == 30
    assert summary.vehicles_arrived == 3
    assert summary.total_vehicles_departed == 60
    assert summary.total_vehicles_arrived == 6


def test_traci_runner_can_stop_inside_warmup_without_measurement_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(
        departed_numbers=[10, 20],
        arrived_numbers=[1, 2],
    )
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    scenario_config = make_scenario_config(duration_seconds=3, warmup_seconds=2)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        max_steps=2,
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 2
    assert summary.measurement_steps_executed == 0
    assert summary.vehicles_departed == 0
    assert summary.vehicles_arrived == 0
    assert summary.total_vehicles_departed == 30
    assert summary.total_vehicles_arrived == 3


def test_controller_continues_operating_during_warmup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(
        departed_numbers=[0, 0, 0],
        arrived_numbers=[0, 0, 0],
    )
    controller = FakeCountingController()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    monkeypatch.setattr(sumo_runner, "build_controller", lambda _controller_id: controller)

    scenario_config = make_scenario_config(duration_seconds=1, warmup_seconds=2)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    summary = runner.run()

    assert summary.steps_executed == 3
    assert summary.measurement_steps_executed == 1
    assert controller.before_calls == 3
    assert controller.after_calls == 3


def test_message_bus_continues_operating_during_warmup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(
        departed_numbers=[0, 0, 0],
        arrived_numbers=[0, 0, 0],
    )
    controller = FakeMessageBusController()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )
    monkeypatch.setattr(sumo_runner, "build_controller", lambda _controller_id: controller)

    scenario_config = make_scenario_config(duration_seconds=1, warmup_seconds=2)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-simulation",
        write_manifest=False,
    )

    runner.run()

    assert controller.bus.metrics.messages_sent == 3
    assert controller.bus.metrics.messages_delivered == 2
    assert controller.delivered_messages == 2


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

    scenario_config = make_scenario_config(duration_seconds=10)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
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
    scenario_config = make_scenario_config(duration_seconds=1)
    scenario_dir = make_scenario_dir(tmp_path, scenario_config)
    viewsettings_path = scenario_dir / "viewsettings.xml"
    viewsettings_path.write_text("<viewsettings/>", encoding="utf-8")

    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
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
    scenario_config = make_scenario_config(duration_seconds=1)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
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
    scenario_config = make_scenario_config(duration_seconds=1)
    scenario_dir = make_scenario_dir(tmp_path, scenario_config)
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
        scenario_config=scenario_config,
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
        collect_network_telemetry=False,
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
    assert manifest["run_mode"] == "SIMULATION"
    assert manifest["python_version"]
    assert manifest["sumo_version"] == "1.27.1"
    assert manifest["git_sha"] is None or isinstance(manifest["git_sha"], str)
    assert manifest["metrics_finalized"] is False
    assert manifest["warmup_seconds"] == 0.0
    assert manifest["measurement_start_step"] == 0
    assert manifest["measurement_end_step"] == 2
    assert manifest["total_simulation_steps"] == 2
    assert len(manifest["scenario_sha256"]) == 64
    assert manifest["network_sha256"] == _sha256(scenario_dir / "network.net.xml")
    assert manifest["route_sha256"] == _sha256(scenario_dir / "routes_s1_seed_42.rou.xml")
    assert manifest["phase_plan_version"] == PHASE_PLAN_VERSION
    assert len(manifest["phase_plan_sha256"]) == 64
    assert manifest["movement_model_version"] == MOVEMENT_MODEL_VERSION
    assert len(manifest["movement_model_sha256"]) == 64
    assert manifest["turning_ratios"] == {"straight": 0.7, "left": 0.15, "right": 0.15}
    assert len(manifest["turning_config_sha256"]) == 64
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
    assert manifest["measurement"] == {
        "warmup_seconds": 0.0,
        "measurement_duration_seconds": 2.0,
        "measurement_start_step": 0,
        "measurement_end_step": 2,
        "total_simulation_steps": 2,
    }
    assert manifest["simulation"]["measurement_steps_executed"] == 2
    assert manifest["performance_file"] == "performance.json"
    performance_path = summary.manifest_path.parent / manifest["performance_file"]
    performance = json.loads(performance_path.read_text(encoding="utf-8"))
    assert performance["run_id"] == summary.run_id
    assert performance["controller"] == "B0_FIXED"
    assert performance["simulation_steps"] == 2
    assert performance["wall_time_seconds"] >= 0.0
    assert performance["steps_per_second"] >= 0.0
    assert performance["controller_decision_p50_ms"] == 0.0
    assert performance["controller_decision_p95_ms"] == 0.0
    assert performance["controller_decision_mean_ms"] == 0.0
    assert performance["controller_decision_max_ms"] == 0.0
    assert performance["message_bus_time_ms"] == 0.0
    assert performance["trace_enabled"] is False
    assert performance["sumo_mode"] == "headless"
    assert manifest["communication_topology_sha256"] == (
        grid_3x3_communication_topology().topology_hash
    )
    assert len(manifest["network_sha256"]) == 64
    assert len(manifest["route_sha256"]) == 64
    assert len(manifest["communication_topology_sha256"]) == 64


def test_traci_runner_writes_demo_run_mode_to_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI()
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )

    scenario_config = make_scenario_config(duration_seconds=1)
    runner = TraCISimulationRunner(
        collect_network_telemetry=False,
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-demo-simulation",
        artifacts_dir=tmp_path / "artifacts" / "demos",
        run_mode="DEMO",
    )

    summary = runner.run()

    assert summary.manifest_path is not None
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_mode"] == "DEMO"


def test_traci_runner_can_stream_step_telemetry_without_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI(departed_numbers=[0], arrived_numbers=[0])
    consumed_records: list[tuple[StepTelemetryRecord, ...]] = []
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

    scenario_config = make_scenario_config(duration_seconds=1)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=make_scenario_dir(tmp_path, scenario_config),
        sumo_info=make_sumo_info(tmp_path),
        label="test-demo-telemetry",
        write_manifest=False,
        step_telemetry_consumer=consumed_records.append,
    )

    summary = runner.run()

    assert summary.manifest_path is None
    assert len(consumed_records) == 1
    assert consumed_records[0][0].intersection_id == "A1"


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
    scenario_config = make_scenario_config(duration_seconds=1).model_copy(
        update={"tracing": TracingConfig(intersection_trace=True)}
    )
    scenario_dir = make_scenario_dir(tmp_path, scenario_config)
    runner = TraCISimulationRunner(
        collect_network_telemetry=False,
        scenario_config=scenario_config,
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
    assert rows[0]["internal_lane_persistence_events"] == "0"
    assert rows[0]["clearance_violations"] == "0"
    assert rows[0]["turn_completion_count"] == "0.0"
    assert rows[0]["movement_queue_mean"] == "1.0"
    assert rows[0]["is_warmup"] == "False"
    assert rows[0]["movement_queue_max"] == "1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.sumo
def test_real_sumo_simulation_smoke(tmp_path: Path) -> None:
    scenario_path = Path("scenarios/grid_3x3/scenario.yaml")
    from traffic_agents.config import load_scenario_config

    scenario_config = load_scenario_config(scenario_path)
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=scenario_path.parent,
        label="integration-sumo-smoke",
        max_steps=scenario_config.measurement_start_step + 60,
        artifacts_dir=tmp_path / "runs",
    )

    summary = runner.run()

    assert summary.steps_executed == scenario_config.measurement_start_step + 60
    assert summary.measurement_steps_executed == 60
    assert summary.vehicles_departed > 0
    assert summary.manifest_path is not None
    run_dir = summary.manifest_path.parent
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics_finalized"] is True
    assert (run_dir / "run_metrics.json").exists()
    assert (run_dir / "lane_telemetry.parquet").exists()
    assert (run_dir / "junction_telemetry.parquet").exists()
