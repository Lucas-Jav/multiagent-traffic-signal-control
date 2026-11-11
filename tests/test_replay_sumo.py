"""Isolamento científico: capturar frames não deve alterar a simulação (requer SUMO GUI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from traffic_agents.config import load_scenario_config
from traffic_agents.replay.camera import ViewWindow
from traffic_agents.replay.sumo_session import ReplayRunner
from traffic_agents.simulation import TraCISimulationRunner

REPO = Path(__file__).resolve().parents[1]
SCENARIO = REPO / "scenarios" / "grid_3x3" / "scenario_s4_local_saturation_seed_42.yaml"
STEPS = 80


def _state(connection: object) -> tuple[object, ...]:
    vehicle = connection.vehicle  # type: ignore[attr-defined]
    ids = sorted(vehicle.getIDList())
    return (
        connection.simulation.getTime(),  # type: ignore[attr-defined]
        tuple(
            (v, round(vehicle.getLanePosition(v), 6), round(vehicle.getSpeed(v), 6)) for v in ids
        ),
        tuple(
            connection.trafficlight.getRedYellowGreenState(t)  # type: ignore[attr-defined]
            for t in sorted(connection.trafficlight.getIDList())  # type: ignore[attr-defined]
        ),
    )


@pytest.mark.sumo
def test_screenshots_and_highlight_do_not_change_simulation(tmp_path: Path) -> None:
    config = load_scenario_config(SCENARIO).model_copy(
        update={"controller_id": "C1_COOPERATIVE_COMPACT"}
    )

    headless = TraCISimulationRunner(
        scenario_config=config,
        scenario_dir=SCENARIO.parent,
        write_manifest=False,
        collect_network_telemetry=False,
        finalize_metrics=False,
    )
    expected = []
    headless.start()
    try:
        for _ in range(STEPS):
            headless.step()
            expected.append(_state(headless._connection))
    finally:
        headless.stop()

    replay = ReplayRunner(
        scenario_config=config,
        scenario_dir=SCENARIO.parent,
        controller_id="C1_COOPERATIVE_COMPACT",
        gui_settings_path=REPO / "config" / "demo_viewsettings.xml",
        window_size=(640, 360),
        label="replay-isolation-test",
    )
    actual = []
    replay.start()
    try:
        replay.frame_for_view(ViewWindow(0, 0, 640, 360), width=640, height=360)
        for step in range(STEPS):
            if step >= STEPS - 20:
                replay.request_screenshot(tmp_path / f"{step:06d}.png")
            replay.step()
            connection = replay.traci_connection
            actual.append(_state(connection))
            ids = connection.vehicle.getIDList()
            if ids:
                connection.vehicle.highlight(ids[0], (255, 0, 200, 255), 14.0)
    finally:
        replay.stop()

    assert actual == expected
    assert len(list(tmp_path.glob("*.png"))) == 20
