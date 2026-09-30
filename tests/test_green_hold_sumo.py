from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from traffic_agents.config import ScenarioConfig
from traffic_agents.controllers import LocalPressureConfig, LocalPressureController
from traffic_agents.simulation.sumo_environment import detect_sumo_environment

GRID_DIR = Path("scenarios/grid_3x3")
MAX_GREEN = 40.0
STEPS = 260
SEED = 7

ROUTES = """<routes>
    <vType id="passenger" length="5.00" minGap="2.50" maxSpeed="13.89"
           accel="2.6" decel="4.5" sigma="0.5"/>
    <route id="we" edges="left1A1 A1B1 B1C1 C1right1"/>
    <vehicle id="v0" type="passenger" route="we" depart="200" departSpeed="max"/>
</routes>
"""


def _scenario_config() -> ScenarioConfig:
    base = yaml.safe_load((GRID_DIR / "scenario.yaml").read_text(encoding="utf-8"))
    return ScenarioConfig.model_validate(
        {
            "scenario_id": "grid_3x3",
            "network_file": "network.net.xml",
            "route_file": "routes.rou.xml",
            "simulation": {
                "warmup_seconds": 0,
                "measurement_duration_seconds": STEPS,
                "step_length": 1.0,
                "seed": SEED,
            },
            "controller_id": "B2_LOCAL_PRESSURE",
            "traffic": {
                "demand_profile": "S1_BALANCED",
                "demand_level": "LOW",
                "flows": [
                    {
                        "flow_id": "west_to_east_middle",
                        "origin_edge_id": "left1A1",
                        "destination_edge_id": "C1right1",
                        "begin_seconds": 0,
                        "end_seconds": STEPS,
                        "vehicles_per_hour": {"LOW": 1, "MEDIUM": 2, "HIGH": 3},
                    }
                ],
            },
            "intersections": base["intersections"],
        }
    )


def _run_controller(
    tmp_path: Path, *, debug_telemetry_enabled: bool
) -> tuple[dict[str, list[tuple[int, float]]], LocalPressureController]:
    import traci

    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    shutil.copy(GRID_DIR / "network.net.xml", scenario_dir / "network.net.xml")
    shutil.copy(GRID_DIR / "metadata.json", scenario_dir / "metadata.json")
    (scenario_dir / "routes.rou.xml").write_text(ROUTES, encoding="utf-8")
    scenario_config = _scenario_config()

    controller = LocalPressureController(
        config=LocalPressureConfig(min_green_seconds=10.0, max_green_seconds=MAX_GREEN),
        debug_telemetry_enabled=debug_telemetry_enabled,
    )
    controller.configure(scenario_config=scenario_config, scenario_dir=scenario_dir)

    info = detect_sumo_environment()
    label = "green-hold-smoke"
    traci.start(
        [
            str(info.sumo_binary),
            "-n",
            str(scenario_dir / "network.net.xml"),
            "-r",
            str(scenario_dir / "routes.rou.xml"),
            "--step-length",
            "1",
            "--seed",
            str(SEED),
            "--no-step-log",
            "--no-warnings",
            "--end",
            str(STEPS + 5),
        ],
        label=label,
    )
    connection: Any = traci.getConnection(label)
    tls_ids = list(connection.trafficlight.getIDList())
    observed: dict[str, list[tuple[int, float]]] = {tls_id: [] for tls_id in tls_ids}
    try:
        for _ in range(STEPS):
            controller.before_simulation_step(connection)
            connection.simulationStep()
            for tls_id in tls_ids:
                observed[tls_id].append(
                    (
                        int(connection.trafficlight.getPhase(tls_id)),
                        float(connection.trafficlight.getSpentDuration(tls_id)),
                    )
                )
    finally:
        traci.switch(label)
        traci.close(False)
    return observed, controller


def _green_lengths(series: list[tuple[int, float]]) -> list[int]:
    """Length in seconds of every green phase that started and ended inside the run."""
    green = {0, 3, 6, 9}
    lengths: list[int] = []
    current: int | None = None
    length = 0
    started_inside = False
    for phase, _spent in series:
        if phase != current:
            if current in green and started_inside:
                lengths.append(length)
            started_inside = current is not None
            current, length = phase, 0
        length += 1
    return lengths


@pytest.mark.sumo
def test_adaptive_controller_holds_green_beyond_twenty_seconds_up_to_max_green(
    tmp_path: Path,
) -> None:
    observed, controller = _run_controller(tmp_path, debug_telemetry_enabled=False)

    all_lengths = [length for series in observed.values() for length in _green_lengths(series)]
    assert all_lengths, "expected completed green phases"
    # SUMO's static program keeps greens at 18/20 s; KEEP_PHASE must hold them longer.
    assert max(all_lengths) > 20
    # ... but never beyond the configured max_green (one step of observation slack).
    assert max(all_lengths) <= MAX_GREEN + 1
    # yellow/all-red are preserved: after any green comes the next program phase.
    for series in observed.values():
        previous = None
        for phase, _spent in series:
            if previous is not None and phase != previous:
                assert phase == (previous + 1) % 12
            previous = phase
    # the debug telemetry switch gates only record building, not phase control
    assert controller.pop_step_telemetry_records() == ()


@pytest.mark.sumo
def test_debug_telemetry_flag_default_keeps_records(tmp_path: Path) -> None:
    _observed, controller = _run_controller(tmp_path, debug_telemetry_enabled=True)

    assert len(controller.pop_step_telemetry_records()) > 0
