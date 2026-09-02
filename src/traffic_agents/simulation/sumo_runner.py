from __future__ import annotations

import importlib
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from traffic_agents.config import ScenarioConfig
from traffic_agents.simulation.sumo_environment import SumoEnvironmentInfo, detect_sumo_environment


@dataclass(frozen=True)
class SimulationRunSummary:
    started_at: str
    ended_at: str
    steps_executed: int
    vehicles_departed: int
    vehicles_arrived: int
    wall_time_seconds: float


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
        self._label = label or f"traffic-agents-{uuid4()}"
        self._use_gui = use_gui
        self._step_delay_seconds = step_delay_seconds
        self._max_steps = max_steps
        self._traci: _TraCIModule | None = None
        self._connection: _TraCIConnection | None = None
        self._started = False
        self._steps_executed = 0
        self._vehicles_departed = 0
        self._vehicles_arrived = 0

    def start(self) -> None:
        if self._started:
            return

        traci = _import_traci(self._sumo_info)
        command = self._sumo_command()
        traci.start(command, label=self._label)
        self._traci = traci
        self._connection = traci.getConnection(self._label)
        self._started = True

    def step(self) -> None:
        connection = self._require_connection()
        connection.simulationStep()
        simulation = connection.simulation
        self._steps_executed += 1
        self._vehicles_departed += int(simulation.getDepartedNumber())
        self._vehicles_arrived += int(simulation.getArrivedNumber())

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
        return SimulationRunSummary(
            started_at=started_at,
            ended_at=_utc_now(),
            steps_executed=self._steps_executed,
            vehicles_departed=self._vehicles_departed,
            vehicles_arrived=self._vehicles_arrived,
            wall_time_seconds=wall_time_seconds,
        )

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
        if self._use_gui:
            command.append("--start")
        return command

    def _target_steps(self) -> int:
        scenario_steps = int(
            self._scenario_config.duration_seconds / self._scenario_config.step_length
        )
        if self._max_steps is None:
            return scenario_steps
        return min(scenario_steps, self._max_steps)

    def _require_connection(self) -> _TraCIConnection:
        if self._connection is None:
            msg = "Simulation has not been started"
            raise RuntimeError(msg)
        return self._connection


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
