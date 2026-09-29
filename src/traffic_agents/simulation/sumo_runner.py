from __future__ import annotations

import importlib
import json
import os
import platform
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, cast
from uuid import uuid4

from traffic_agents.config import ScenarioConfig, get_settings
from traffic_agents.controllers import (
    CooperativeCompactController,
    FixedTimeController,
    LocalAdaptiveController,
    LocalPressureController,
    build_controller,
)
from traffic_agents.domain import IntersectionId
from traffic_agents.experiments.run_invariants import (
    RunInvariantFingerprint,
    build_run_invariant_fingerprint,
    validate_run_inputs,
)
from traffic_agents.metrics import (
    AGENT_TRACE_FILE,
    PERFORMANCE_FILE,
    SUMO_TRAFFIC_METRICS_FILE,
    AgentDecisionTraceSettings,
    AgentDecisionTraceWriter,
    ControllerPerformanceTimings,
    StepTelemetryRecord,
    append_step_telemetry,
    build_performance_payload,
    missing_sumo_trip_metrics,
    parse_sumo_trip_metrics,
    write_performance_json,
    write_sumo_trip_metrics,
)
from traffic_agents.simulation.sumo_environment import SumoEnvironmentInfo, detect_sumo_environment
from traffic_agents.simulation.traci_sensor_adapter import (
    TraCISensorAdapter,
    TraCISensorConnection,
    TrafficSensorProvider,
)


@dataclass(frozen=True)
class SimulationRunSummary:
    started_at: str
    ended_at: str
    run_id: str
    manifest_path: Path | None
    scenario_id: str
    controller_id: str
    controller_version: str
    demand_profile: str
    seed: int
    steps_executed: int
    vehicles_departed: int
    vehicles_arrived: int
    wall_time_seconds: float
    measurement_start_step: int = 0
    measurement_end_step: int = 0
    total_simulation_steps: int = 0
    measurement_steps_executed: int = 0
    total_vehicles_departed: int = 0
    total_vehicles_arrived: int = 0


class SimulationRunner(Protocol):
    def start(self) -> None: ...

    def step(self) -> None: ...

    def stop(self) -> None: ...

    def run(self) -> SimulationRunSummary: ...


class _TraCISimulation(Protocol):
    def getDepartedNumber(self) -> int: ...  # noqa: N802

    def getArrivedNumber(self) -> int: ...  # noqa: N802


class _TraCIConnection(Protocol):
    simulation: _TraCISimulation

    def simulationStep(self) -> None: ...  # noqa: N802


class _TraCIModule(Protocol):
    def start(self, command: list[str], *, label: str) -> None: ...

    def getConnection(self, label: str) -> _TraCIConnection: ...  # noqa: N802

    def switch(self, label: str) -> None: ...

    def close(self, wait: bool) -> None: ...


class _TelemetryProducer(Protocol):
    def pop_step_telemetry_records(self) -> tuple[StepTelemetryRecord, ...]: ...


class _PerformanceTimingsProducer(Protocol):
    def performance_timings(self) -> ControllerPerformanceTimings: ...


class _CommunicationMetricsProducer(Protocol):
    def communication_metrics(self) -> dict[str, object]: ...


class TraCISimulationRunner:
    def __init__(
        self,
        *,
        scenario_config: ScenarioConfig,
        scenario_dir: Path,
        sumo_info: SumoEnvironmentInfo | None = None,
        label: str | None = None,
        use_gui: bool = False,
        step_delay_seconds: float = 0.0,
        max_steps: int | None = None,
        controller_id: str | None = None,
        artifacts_dir: Path | None = None,
        write_manifest: bool = True,
        run_mode: Literal["SIMULATION", "EXPERIMENT", "DEMO"] = "SIMULATION",
        run_manifest_extra: Mapping[str, object] | None = None,
        step_telemetry_consumer: Callable[[tuple[StepTelemetryRecord, ...]], None] | None = None,
        run_id: str | None = None,
    ) -> None:
        if step_delay_seconds < 0:
            msg = "step_delay_seconds must be non-negative"
            raise ValueError(msg)
        if max_steps is not None and max_steps <= 0:
            msg = "max_steps must be positive"
            raise ValueError(msg)

        self._scenario_config = scenario_config
        self._scenario_dir = scenario_dir
        self._sumo_info = sumo_info or detect_sumo_environment()
        self._controller = build_controller(controller_id or scenario_config.controller_id)
        if isinstance(
            self._controller,
            LocalAdaptiveController | LocalPressureController | CooperativeCompactController,
        ):
            self._controller.configure(
                scenario_config=scenario_config,
                scenario_dir=scenario_dir,
            )
        self._label = label or f"traffic-agents-{uuid4()}"
        self._use_gui = use_gui
        self._step_delay_seconds = step_delay_seconds
        self._max_steps = max_steps
        self._artifacts_dir = artifacts_dir
        self._write_manifest = write_manifest
        self._run_mode = run_mode
        self._run_manifest_extra = dict(run_manifest_extra or {})
        self._step_telemetry_consumer = step_telemetry_consumer
        self._configured_run_id = run_id
        self._active_run_dir: Path | None = None
        self._telemetry_path: Path | None = None
        self._agent_trace_path: Path | None = None
        self._performance_path: Path | None = None
        self._sumo_dir: Path | None = None
        self._tripinfo_path: Path | None = None
        self._statistics_path: Path | None = None
        self._sumo_metrics_path: Path | None = None
        self._run_invariant_fingerprint: RunInvariantFingerprint | None = None
        self._traci: _TraCIModule | None = None
        self._connection: _TraCIConnection | None = None
        self._started = False
        self._steps_executed = 0
        self._vehicles_departed = 0
        self._vehicles_arrived = 0
        self._measurement_steps_executed = 0
        self._total_vehicles_departed = 0
        self._total_vehicles_arrived = 0
        self._result_collector_time_ms = 0.0

    def start(self) -> None:
        if self._started:
            return

        self._run_invariant_fingerprint = validate_run_inputs(
            scenario_config=self._scenario_config,
            scenario_dir=self._scenario_dir,
        )
        traci = _import_traci(self._sumo_info)
        command = self._sumo_command()
        traci.start(command, label=self._label)
        self._traci = traci
        self._connection = traci.getConnection(self._label)
        self._started = True

    def step(self) -> None:
        connection = self._require_connection()
        self._controller.before_simulation_step(connection)
        connection.simulationStep()
        simulation = connection.simulation
        step_index = self._steps_executed
        departed = int(simulation.getDepartedNumber())
        arrived = int(simulation.getArrivedNumber())
        self._steps_executed += 1
        self._total_vehicles_departed += departed
        self._total_vehicles_arrived += arrived
        if self._scenario_config.is_measurement_step(step_index):
            self._measurement_steps_executed += 1
            self._vehicles_departed += departed
            self._vehicles_arrived += arrived
        self._controller.after_simulation_step(connection)
        self._write_step_telemetry()

    def stop(self) -> None:
        if not self._started:
            return

        traci = self._traci
        try:
            if traci is not None:
                traci.switch(self._label)
                traci.close(False)
        finally:
            self._connection = None
            self._traci = None
            self._started = False

    def run(self) -> SimulationRunSummary:
        run_id = self._build_run_id()
        self._prepare_run_artifacts(run_id)
        self._configure_agent_decision_tracing(run_id)
        started_at = _utc_now()
        start_time = time.perf_counter()
        try:
            self.start()
            for _ in range(self._target_steps()):
                self.step()
                if self._step_delay_seconds > 0:
                    time.sleep(self._step_delay_seconds)
        finally:
            self.stop()

        wall_time_seconds = time.perf_counter() - start_time
        summary = SimulationRunSummary(
            started_at=started_at,
            ended_at=_utc_now(),
            run_id=run_id,
            manifest_path=None,
            scenario_id=self._scenario_config.scenario_id,
            controller_id=self._controller.controller_id,
            controller_version=self._controller.controller_version,
            demand_profile=self._scenario_config.traffic.demand_profile,
            seed=self._scenario_config.seed,
            steps_executed=self._steps_executed,
            vehicles_departed=self._vehicles_departed,
            vehicles_arrived=self._vehicles_arrived,
            wall_time_seconds=wall_time_seconds,
            measurement_start_step=self._scenario_config.measurement_start_step,
            measurement_end_step=self._scenario_config.measurement_end_step,
            total_simulation_steps=self._scenario_config.total_simulation_steps,
            measurement_steps_executed=self._measurement_steps_executed,
            total_vehicles_departed=self._total_vehicles_departed,
            total_vehicles_arrived=self._total_vehicles_arrived,
        )
        self._write_performance(summary)
        self._write_sumo_metrics()
        if self._write_manifest:
            return self._write_run_manifest(summary)
        return summary

    def make_sensor_provider(
        self,
        *,
        traffic_light_ids: Mapping[IntersectionId, str],
    ) -> TrafficSensorProvider:
        return TraCISensorAdapter(
            connection=cast(TraCISensorConnection, self._require_connection()),
            intersections=self._scenario_config.intersections,
            traffic_light_ids=traffic_light_ids,
            step_length=self._scenario_config.step_length,
        )

    @property
    def controller(self) -> object:
        return self._controller

    def _sumo_command(self) -> list[str]:
        network_path = self._scenario_dir / self._scenario_config.network_file
        route_path = self._scenario_dir / self._scenario_config.route_file

        if not network_path.exists():
            msg = f"Network file not found: {network_path}"
            raise FileNotFoundError(msg)
        if not route_path.exists():
            msg = f"Route file not found: {route_path}"
            raise FileNotFoundError(msg)

        binary = self._sumo_info.sumo_gui_binary if self._use_gui else self._sumo_info.sumo_binary
        command = [
            str(binary),
            "--net-file",
            str(network_path),
            "--route-files",
            str(route_path),
            "--step-length",
            f"{self._scenario_config.step_length:g}",
            "--seed",
            str(self._scenario_config.seed),
            "--no-step-log",
            "--quit-on-end",
        ]
        if self._tripinfo_path is not None:
            command.extend(["--tripinfo-output", str(self._tripinfo_path)])
        if self._statistics_path is not None:
            command.extend(["--statistic-output", str(self._statistics_path)])
        if self._use_gui:
            gui_settings_path = self._scenario_dir / "viewsettings.xml"
            if gui_settings_path.exists():
                command.extend(["--gui-settings-file", str(gui_settings_path)])
            command.append("--start")
        return command

    def _target_steps(self) -> int:
        scenario_steps = self._scenario_config.total_simulation_steps
        if self._max_steps is None:
            return scenario_steps
        return min(scenario_steps, self._max_steps)

    def _require_connection(self) -> _TraCIConnection:
        if self._connection is None:
            msg = "Simulation has not been started"
            raise RuntimeError(msg)
        return self._connection

    def _build_run_id(self) -> str:
        if self._configured_run_id is not None:
            return self._configured_run_id
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
        suffix = uuid4().hex[:8]
        return (
            f"{timestamp}_{suffix}_{self._scenario_config.scenario_id}_"
            f"{self._controller.controller_id}_"
            f"{self._scenario_config.traffic.demand_profile}_"
            f"seed_{self._scenario_config.seed}"
        )

    def _write_run_manifest(self, summary: SimulationRunSummary) -> SimulationRunSummary:
        manifest_dir = self._active_run_dir or self._manifest_dir(summary.run_id)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.json"
        summary_with_manifest = SimulationRunSummary(
            started_at=summary.started_at,
            ended_at=summary.ended_at,
            run_id=summary.run_id,
            manifest_path=manifest_path,
            scenario_id=summary.scenario_id,
            controller_id=summary.controller_id,
            controller_version=summary.controller_version,
            demand_profile=summary.demand_profile,
            seed=summary.seed,
            steps_executed=summary.steps_executed,
            vehicles_departed=summary.vehicles_departed,
            vehicles_arrived=summary.vehicles_arrived,
            wall_time_seconds=summary.wall_time_seconds,
            measurement_start_step=summary.measurement_start_step,
            measurement_end_step=summary.measurement_end_step,
            total_simulation_steps=summary.total_simulation_steps,
            measurement_steps_executed=summary.measurement_steps_executed,
            total_vehicles_departed=summary.total_vehicles_departed,
            total_vehicles_arrived=summary.total_vehicles_arrived,
        )
        manifest_path.write_text(
            json.dumps(
                _manifest_payload(
                    summary_with_manifest,
                    self._controller,
                    self._scenario_config,
                    self._scenario_dir,
                    self._sumo_info,
                    self._run_mode,
                    self._run_invariant_fingerprint,
                    self._run_manifest_extra,
                    self._telemetry_path.name
                    if self._telemetry_path is not None and self._telemetry_path.exists()
                    else None,
                    self._agent_trace_path.name
                    if self._agent_trace_path is not None and self._agent_trace_path.exists()
                    else None,
                    self._performance_path.name
                    if self._performance_path is not None and self._performance_path.exists()
                    else None,
                    self._sumo_metrics_path.name
                    if self._sumo_metrics_path is not None and self._sumo_metrics_path.exists()
                    else None,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_with_manifest

    def _manifest_dir(self, run_id: str) -> Path:
        artifacts_dir = self._artifacts_dir or get_settings().artifacts_dir / "runs"
        return artifacts_dir / run_id

    def _prepare_run_artifacts(self, run_id: str) -> None:
        self._active_run_dir = None
        self._telemetry_path = None
        self._agent_trace_path = None
        self._performance_path = None
        self._sumo_dir = None
        self._tripinfo_path = None
        self._statistics_path = None
        self._sumo_metrics_path = None
        trace_settings = AgentDecisionTraceSettings.from_config(
            getattr(self._scenario_config, "tracing", None)
        )
        if not self._write_manifest and not trace_settings.enabled:
            return
        self._active_run_dir = self._manifest_dir(run_id)
        self._active_run_dir.mkdir(parents=True, exist_ok=False)
        if self._write_manifest:
            self._telemetry_path = self._active_run_dir / "intersection_trace.csv"
            self._performance_path = self._active_run_dir / PERFORMANCE_FILE
            self._sumo_dir = self._active_run_dir / "sumo"
            self._sumo_dir.mkdir()
            self._tripinfo_path = self._sumo_dir / "tripinfo.xml"
            self._statistics_path = self._sumo_dir / "statistics.xml"
            self._sumo_metrics_path = self._active_run_dir / SUMO_TRAFFIC_METRICS_FILE
        if trace_settings.enabled:
            self._agent_trace_path = self._active_run_dir / AGENT_TRACE_FILE
            self._performance_path = self._active_run_dir / PERFORMANCE_FILE

    def _configure_agent_decision_tracing(self, run_id: str) -> None:
        configure_tracing = getattr(self._controller, "configure_agent_decision_tracing", None)
        if not callable(configure_tracing):
            return
        trace_settings = AgentDecisionTraceSettings.from_config(
            getattr(self._scenario_config, "tracing", None)
        )
        if not trace_settings.enabled or self._agent_trace_path is None:
            configure_tracing(None)
            return
        configure_tracing(
            AgentDecisionTraceWriter(
                run_id=run_id,
                path=self._agent_trace_path,
                settings=trace_settings,
            )
        )

    def _write_step_telemetry(self) -> None:
        if self._telemetry_path is None and self._step_telemetry_consumer is None:
            return
        started_at = time.perf_counter()
        producer = self._controller
        pop_records = getattr(producer, "pop_step_telemetry_records", None)
        if not callable(pop_records):
            return
        try:
            records = cast(_TelemetryProducer, producer).pop_step_telemetry_records()
            if self._step_telemetry_consumer is not None:
                self._step_telemetry_consumer(records)
            if self._telemetry_path is not None:
                append_step_telemetry(self._telemetry_path, records)
        finally:
            self._result_collector_time_ms += (time.perf_counter() - started_at) * 1000

    def _write_performance(self, summary: SimulationRunSummary) -> None:
        if self._performance_path is None:
            return
        trace_settings = AgentDecisionTraceSettings.from_config(
            getattr(self._scenario_config, "tracing", None)
        )
        payload = build_performance_payload(
            run_id=summary.run_id,
            controller=summary.controller_id,
            simulation_steps=summary.steps_executed,
            wall_time_seconds=summary.wall_time_seconds,
            controller_timings=self._controller_performance_timings(),
            trace_enabled=trace_settings.enabled,
            result_collector_time_ms=self._result_collector_time_ms,
            use_gui=self._use_gui,
            communication_metrics=self._controller_communication_metrics(),
        )
        write_performance_json(self._performance_path, payload)

    def _write_sumo_metrics(self) -> None:
        if self._sumo_metrics_path is None or self._tripinfo_path is None:
            return
        if self._tripinfo_path.exists():
            metrics = parse_sumo_trip_metrics(
                tripinfo_path=self._tripinfo_path,
                statistics_path=self._statistics_path,
            )
        else:
            metrics = missing_sumo_trip_metrics(
                tripinfo_path=self._tripinfo_path,
                statistics_path=self._statistics_path,
            )
        write_sumo_trip_metrics(self._sumo_metrics_path, metrics)

    def _controller_performance_timings(self) -> ControllerPerformanceTimings:
        performance_timings = getattr(self._controller, "performance_timings", None)
        if not callable(performance_timings):
            return ControllerPerformanceTimings()
        return cast(_PerformanceTimingsProducer, self._controller).performance_timings()

    def _controller_communication_metrics(self) -> dict[str, object] | None:
        communication_metrics = getattr(self._controller, "communication_metrics", None)
        if not callable(communication_metrics):
            return None
        return cast(_CommunicationMetricsProducer, self._controller).communication_metrics()


def _manifest_payload(
    summary: SimulationRunSummary,
    controller: (
        FixedTimeController
        | LocalAdaptiveController
        | LocalPressureController
        | CooperativeCompactController
    ),
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
    sumo_info: SumoEnvironmentInfo,
    run_mode: Literal["SIMULATION", "EXPERIMENT", "DEMO"] = "SIMULATION",
    run_invariant_fingerprint: RunInvariantFingerprint | None = None,
    extra_fields: Mapping[str, object] | None = None,
    intersection_trace_file: str | None = None,
    agent_trace_file: str | None = None,
    performance_file: str | None = None,
    sumo_metrics_file: str | None = None,
) -> dict[str, object]:
    fingerprint = run_invariant_fingerprint or build_run_invariant_fingerprint(
        scenario_config=scenario_config,
        scenario_dir=scenario_dir,
    )
    payload: dict[str, object] = {
        "run_id": summary.run_id,
        "scenario_id": summary.scenario_id,
        "demand_profile": summary.demand_profile,
        "seed": summary.seed,
        "run_mode": run_mode,
        "python_version": platform.python_version(),
        "sumo_version": sumo_info.version,
        "git_sha": _detect_git_sha(Path.cwd()),
        **fingerprint.manifest_fields(),
        "started_at": summary.started_at,
        "ended_at": summary.ended_at,
        "controller": controller.manifest_metadata(),
        "warmup_seconds": float(scenario_config.warmup_seconds),
        "measurement_start_step": int(scenario_config.measurement_start_step),
        "measurement_end_step": int(scenario_config.measurement_end_step),
        "total_simulation_steps": int(scenario_config.total_simulation_steps),
        "communication": {
            "delay_steps": int(scenario_config.communication.delay_steps),
            "drop_probability": float(scenario_config.communication.drop_probability),
            "rng_seed": scenario_config.communication.resolved_rng_seed(int(scenario_config.seed)),
            "max_message_age_steps": int(scenario_config.communication.max_message_age_steps),
        },
        "measurement": {
            "warmup_seconds": float(scenario_config.warmup_seconds),
            "measurement_duration_seconds": float(scenario_config.measurement_duration_seconds),
            "measurement_start_step": int(scenario_config.measurement_start_step),
            "measurement_end_step": int(scenario_config.measurement_end_step),
            "total_simulation_steps": int(scenario_config.total_simulation_steps),
        },
        "simulation": {
            "steps_executed": summary.steps_executed,
            "measurement_steps_executed": summary.measurement_steps_executed,
            "vehicles_departed": summary.vehicles_departed,
            "vehicles_arrived": summary.vehicles_arrived,
            "total_vehicles_departed": summary.total_vehicles_departed,
            "total_vehicles_arrived": summary.total_vehicles_arrived,
            "wall_time_seconds": summary.wall_time_seconds,
        },
        "metrics_finalized": False,
        "sumo_outputs": {
            "tripinfo": "sumo/tripinfo.xml",
            "statistics": "sumo/statistics.xml",
            "trip_metrics_definition": (
                "waitingTime, timeLoss, duration and waitingCount are parsed from SUMO "
                "tripinfo completed-trip records."
            ),
            "unfinished_vehicle_policy": (
                "Completed trips are averaged; vehicles not completed by run end remain "
                "visible through departed/arrived counts."
            ),
        },
    }
    if extra_fields:
        payload.update(dict(extra_fields))
    if intersection_trace_file is not None:
        payload["intersection_trace_file"] = intersection_trace_file
    if agent_trace_file is not None:
        payload["agent_trace_file"] = agent_trace_file
    if performance_file is not None:
        payload["performance_file"] = performance_file
    if sumo_metrics_file is not None:
        payload["sumo_traffic_metrics_file"] = sumo_metrics_file
    communication_metrics = getattr(controller, "communication_metrics", None)
    if callable(communication_metrics):
        payload["communication_metrics"] = communication_metrics()
    return payload


def _import_traci(sumo_info: SumoEnvironmentInfo) -> _TraCIModule:
    if sumo_info.sumo_home is None:
        msg = "SUMO_HOME is required to import TraCI"
        raise RuntimeError(msg)

    tools_path = sumo_info.sumo_home / "tools"
    if not tools_path.exists():
        msg = f"SUMO tools directory not found: {tools_path}"
        raise FileNotFoundError(msg)

    os.environ["SUMO_HOME"] = str(sumo_info.sumo_home)
    tools_path_text = str(tools_path)
    if tools_path_text not in sys.path:
        sys.path.insert(0, tools_path_text)

    return cast(_TraCIModule, importlib.import_module("traci"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _detect_git_sha(start_path: Path) -> str | None:
    git_dir = _find_git_dir(start_path)
    if git_dir is None:
        return None

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return None

    head = head_path.read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = head.removeprefix("ref: ").strip()
        ref_path = git_dir / ref
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip() or None
        return _read_packed_ref(git_dir / "packed-refs", ref)

    return head or None


def _find_git_dir(start_path: Path) -> Path | None:
    for candidate in (start_path, *start_path.parents):
        git_path = candidate / ".git"
        if git_path.is_dir():
            return git_path
        if git_path.is_file():
            gitdir = git_path.read_text(encoding="utf-8").strip()
            if gitdir.startswith("gitdir: "):
                resolved = (candidate / gitdir.removeprefix("gitdir: ").strip()).resolve()
                if resolved.is_dir():
                    return resolved
    return None


def _read_packed_ref(path: Path, ref: str) -> str | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "^")):
                continue
            sha, _, packed_ref = stripped.partition(" ")
            if packed_ref == ref:
                return sha
    return None
