from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from traffic_agents.config import ScenarioConfig
from traffic_agents.metrics import (
    JUNCTION_TELEMETRY_FILE,
    LANE_TELEMETRY_FILE,
    MetricsFinalizationError,
    NetworkTelemetryCollector,
    NetworkTelemetryError,
)
from traffic_agents.simulation import SumoEnvironmentInfo, TraCISimulationRunner

INCOMING_LANES = ("top1A1_0", "right1A1_0", "bottom1A1_0", "left1A1_0")


class FakeLaneApi:
    """Scripted lane sensors: ``queues[lane_id]`` is the halting count per sampled step."""

    def __init__(self, queues: dict[str, list[int]]) -> None:
        self.queues = queues
        self.step = 0

    def getLastStepHaltingNumber(self, lane_id: str) -> int:  # noqa: N802
        series = self.queues.get(lane_id, [0])
        return series[min(self.step, len(series) - 1)]

    def getLastStepVehicleNumber(self, lane_id: str) -> int:  # noqa: N802
        return self.getLastStepHaltingNumber(lane_id) + 1

    def getLastStepOccupancy(self, lane_id: str) -> float:  # noqa: N802
        return 50.0

    def getLastStepMeanSpeed(self, lane_id: str) -> float:  # noqa: N802
        return 2.5

    def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]:  # noqa: N802
        return ()


class FakeTrafficLightApi:
    def getPhase(self, tls_id: str) -> int:  # noqa: N802
        return 3

    def getSpentDuration(self, tls_id: str) -> float:  # noqa: N802
        return 4.0


class FakeSimulationApi:
    def __init__(self) -> None:
        self.time = 0.0
        self.departed = 1
        self.arrived = 0

    def getTime(self) -> float:  # noqa: N802
        return self.time

    def getDepartedNumber(self) -> int:  # noqa: N802
        return self.departed

    def getArrivedNumber(self) -> int:  # noqa: N802
        return self.arrived


class FakeTelemetryConnection:
    def __init__(self, queues: dict[str, list[int]]) -> None:
        self.lane = FakeLaneApi(queues)
        self.trafficlight = FakeTrafficLightApi()
        self.simulation = FakeSimulationApi()

    def simulationStep(self) -> None:  # noqa: N802
        self.lane.step += 1
        self.simulation.time += 1.0


class FakeTraCI:
    def __init__(self, queues: dict[str, list[int]]) -> None:
        self.connection = FakeTelemetryConnection(queues)
        self.closed = False

    def start(self, command: list[str], *, label: str) -> None:
        return None

    def getConnection(self, label: str) -> FakeTelemetryConnection:  # noqa: N802
        return self.connection

    def switch(self, label: str) -> None:
        return None

    def close(self, wait: bool) -> None:
        self.closed = True


def scenario_config(*, duration_seconds: int = 4, warmup_seconds: int = 1) -> ScenarioConfig:
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
                    "vehicles_per_hour": {"LOW": 1, "MEDIUM": 2, "HIGH": 3},
                }
            ],
        },
        intersections=[
            {
                "intersection_id": "A1",
                "incoming_lanes": list(INCOMING_LANES),
                "outgoing_lanes": ["A1top1_0", "A1right1_0", "A1bottom1_0", "A1left1_0"],
                "phases": ["north_south", "east_west"],
            }
        ],
    )


def scenario_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "scenario"
    directory.mkdir()
    (directory / "network.net.xml").write_text(
        """
<net>
  <junction id="J1" type="traffic_light" intLanes=":J1_0 :J1_1"/>
  <tlLogic id="J1" type="static" programID="0" offset="0">
    <phase duration="10" state="G"/>
    <phase duration="3" state="y"/>
    <phase duration="2" state="r"/>
  </tlLogic>
</net>
""".strip(),
        encoding="utf-8",
    )
    (directory / "metadata.json").write_text(
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
    return directory


def test_lane_queue_is_recorded_once_per_physical_lane(tmp_path: Path) -> None:
    connection = FakeTelemetryConnection({INCOMING_LANES[0]: [7, 7, 7]})
    collector = NetworkTelemetryCollector(
        connection=connection,
        scenario_config=scenario_config(),
        scenario_dir=scenario_dir(tmp_path),
        expected_steps=3,
    )

    for step in range(3):
        connection.simulationStep()
        collector.record(step)
    lane_path, junction_path = collector.write(tmp_path / "out")

    lanes = pq.read_table(lane_path).to_pydict()
    junctions = pq.read_table(junction_path).to_pydict()
    assert lane_path.name == LANE_TELEMETRY_FILE
    assert junction_path.name == JUNCTION_TELEMETRY_FILE
    # 3 steps x 4 unique incoming lanes, never one row per movement.
    assert len(lanes["queue"]) == 12
    assert sorted(set(lanes["lane_id"])) == sorted(INCOMING_LANES)
    per_step = [
        sum(q for s, q in zip(lanes["step_index"], lanes["queue"], strict=True) if s == step)
        for step in range(3)
    ]
    assert per_step == [7, 7, 7]
    # One physical lane queue of 7 vehicles is 7 vehicles for the intersection, not 21.
    assert junctions["intersection_total_queue"] == [7, 7, 7]
    assert junctions["tls_phase"] == [3, 3, 3]
    assert junctions["internal_vehicle_count"] == [0, 0, 0]


def test_junction_telemetry_counts_persistence_once_per_intersection(tmp_path: Path) -> None:
    class InternalLaneApi(FakeLaneApi):
        def getLastStepVehicleIDs(self, lane_id: str) -> tuple[str, ...]:  # noqa: N802
            return ("v1", "v2") if lane_id == ":J1_0" else ()

    connection = FakeTelemetryConnection({INCOMING_LANES[0]: [0]})
    connection.lane = InternalLaneApi({INCOMING_LANES[0]: [0]})
    collector = NetworkTelemetryCollector(
        connection=connection,
        scenario_config=scenario_config(),
        scenario_dir=scenario_dir(tmp_path),
        expected_steps=3,
    )
    for step in range(3):
        collector.record(step)
    _, junction_path = collector.write(tmp_path / "out")

    junctions = pq.read_table(junction_path).to_pydict()
    assert junctions["internal_vehicle_count"] == [2, 2, 2]
    assert junctions["junction_entries"] == [2, 0, 0]
    # persistence: vehicles present in two consecutive steps, one row per intersection-step.
    assert junctions["internal_lane_persistence_events"] == [0, 2, 2]


def test_collector_rejects_lane_shared_by_two_intersections(tmp_path: Path) -> None:
    config = scenario_config()
    payload = config.model_dump(mode="json")
    payload["intersections"].append(
        {
            "intersection_id": "A2",
            "incoming_lanes": [INCOMING_LANES[0]],
            "outgoing_lanes": ["x_0"],
            "phases": ["north_south", "east_west"],
        }
    )
    directory = scenario_dir(tmp_path)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    metadata["traffic_light_ids"]["A2"] = "J1"
    (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(NetworkTelemetryError, match="more than one intersection"):
        NetworkTelemetryCollector(
            connection=FakeTelemetryConnection({}),
            scenario_config=ScenarioConfig.model_validate(payload),
            scenario_dir=directory,
            expected_steps=1,
        )


def _install_fake_traci(
    monkeypatch: pytest.MonkeyPatch,
    fake_traci: FakeTraCI,
) -> None:
    monkeypatch.setenv("SUMO_HOME", "")
    monkeypatch.setattr(
        "traffic_agents.simulation.sumo_runner.importlib.import_module",
        lambda module_name: fake_traci if module_name == "traci" else None,
    )


def _sumo_info(tmp_path: Path) -> SumoEnvironmentInfo:
    sumo_home = tmp_path / "sumo"
    (sumo_home / "tools").mkdir(parents=True, exist_ok=True)
    (sumo_home / "bin").mkdir(parents=True, exist_ok=True)
    binary = sumo_home / "bin" / "sumo.exe"
    binary.write_text("", encoding="utf-8")
    return SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=binary,
        sumo_gui_binary=sumo_home / "bin" / "sumo-gui.exe",
        version="1.27.1",
    )


def _runner_scenario_dir(tmp_path: Path, config: ScenarioConfig) -> Path:
    import hashlib

    from traffic_agents.experiments.run_invariants import (
        route_artifact_scenario_sha256,
        route_generator_config_sha256,
    )

    directory = scenario_dir(tmp_path)
    route_path = directory / "routes_s1_seed_42.rou.xml"
    route_path.write_text("<routes/>", encoding="utf-8")
    (directory / "routes_s1_seed_42.metadata.json").write_text(
        json.dumps(
            {
                "scenario_id": config.scenario_id,
                "seed": config.seed,
                "config_hash": route_generator_config_sha256(config),
                "scenario_hash": route_artifact_scenario_sha256(config),
                "route_hash": hashlib.sha256(route_path.read_bytes()).hexdigest(),
                "network_hash": hashlib.sha256(
                    (directory / "network.net.xml").read_bytes()
                ).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return directory


def test_fixed_time_baseline_gets_the_same_telemetry_as_adaptive_controllers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_traci = FakeTraCI({INCOMING_LANES[1]: [2, 3, 4, 5]})
    _install_fake_traci(monkeypatch, fake_traci)
    config = scenario_config()
    runner = TraCISimulationRunner(
        scenario_config=config,
        scenario_dir=_runner_scenario_dir(tmp_path, config),
        sumo_info=_sumo_info(tmp_path),
        label="b0-telemetry",
        artifacts_dir=tmp_path / "artifacts",
        finalize_metrics=False,
    )

    summary = runner.run()

    assert summary.controller_id == "B0_FIXED"
    assert summary.manifest_path is not None
    run_dir = summary.manifest_path.parent
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["network_telemetry_files"] == [LANE_TELEMETRY_FILE, JUNCTION_TELEMETRY_FILE]
    lanes = pq.read_table(run_dir / LANE_TELEMETRY_FILE).to_pydict()
    assert len(lanes["queue"]) == config.total_simulation_steps * len(INCOMING_LANES)
    assert lanes["is_warmup"][:4] == [True] * 4
    assert lanes["is_warmup"][-4:] == [False] * 4
    # B0 has no controller-produced trace and no debug movement CSV by default.
    assert not (run_dir / "intersection_trace.csv").exists()
    assert "intersection_trace_file" not in manifest
    assert manifest["metrics_finalized"] is False


def test_metrics_finalization_failure_is_visible_and_not_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The fake SUMO writes no tripinfo/statistics, so finalization cannot succeed.
    fake_traci = FakeTraCI({INCOMING_LANES[0]: [1, 1, 1, 1]})
    _install_fake_traci(monkeypatch, fake_traci)
    config = scenario_config()
    artifacts_dir = tmp_path / "artifacts"
    runner = TraCISimulationRunner(
        scenario_config=config,
        scenario_dir=_runner_scenario_dir(tmp_path, config),
        sumo_info=_sumo_info(tmp_path),
        label="finalization-failure",
        artifacts_dir=artifacts_dir,
    )

    with pytest.raises(MetricsFinalizationError, match="metrics finalization failed"):
        runner.run()

    manifests = list(artifacts_dir.glob("*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["metrics_finalized"] is False
    assert manifest["metrics_finalization_error"]["type"] == "MetricsFinalizationError"
    assert not (manifests[0].parent / "run_metrics.json").exists()


def test_finalize_requires_telemetry_and_manifest(tmp_path: Path) -> None:
    config = scenario_config()

    with pytest.raises(ValueError, match="finalize_metrics requires"):
        TraCISimulationRunner(
            scenario_config=config,
            scenario_dir=_runner_scenario_dir(tmp_path, config),
            sumo_info=_sumo_info(tmp_path),
            label="invalid",
            collect_network_telemetry=False,
            finalize_metrics=True,
        )


def test_controllers_do_not_build_debug_telemetry_unless_requested(tmp_path: Path) -> None:
    from traffic_agents.config import TracingConfig

    config = scenario_config().model_copy(update={"controller_id": "B2_LOCAL_PRESSURE"})
    directory = _runner_scenario_dir(tmp_path, config)
    default_runner = TraCISimulationRunner(
        scenario_config=config,
        scenario_dir=directory,
        sumo_info=_sumo_info(tmp_path),
        label="debug-off",
        collect_network_telemetry=False,
        finalize_metrics=False,
    )
    assert getattr(default_runner.controller, "debug_telemetry_enabled") is False  # noqa: B009

    traced = config.model_copy(update={"tracing": TracingConfig(intersection_trace=True)})
    traced_runner = TraCISimulationRunner(
        scenario_config=traced,
        scenario_dir=directory,
        sumo_info=_sumo_info(tmp_path),
        label="debug-on",
        collect_network_telemetry=False,
        finalize_metrics=False,
    )
    assert getattr(traced_runner.controller, "debug_telemetry_enabled") is True  # noqa: B009
