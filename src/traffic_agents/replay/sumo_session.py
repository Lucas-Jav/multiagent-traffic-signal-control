"""SUMO GUI session used to capture frames, driven by the project's own simulation runner.

The runner (``TraCISimulationRunner``) is reused unchanged: controller timing
(``before_simulation_step`` / ``simulationStep`` / ``after_simulation_step``), seed, network and
route files are exactly the ones used in experiments. This module only adds GUI-side behaviour:

* a read-only view of the GUI settings file and window size on the command line;
* screenshot requests, which SUMO satisfies at the END of the next ``simulationStep``;
* a gate that waits for that screenshot file before any further TraCI command is issued, so the
  rendered frame can never race with controller commands executed after the step.

None of this feeds back into the simulation: it only changes wall-clock time.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from traffic_agents.config import ScenarioConfig
from traffic_agents.replay.camera import ViewWindow
from traffic_agents.simulation import TraCISimulationRunner

SCREENSHOT_TIMEOUT_SECONDS = 120.0
_POLL_SECONDS = 0.01


class ScreenshotError(RuntimeError):
    """Raised when SUMO does not deliver a requested screenshot."""


def wait_for_stable_file(
    path: Path, *, timeout_seconds: float = SCREENSHOT_TIMEOUT_SECONDS
) -> None:
    """Block until ``path`` exists and its size stopped changing (fully written)."""

    deadline = time.monotonic() + timeout_seconds
    last_size = -1
    while time.monotonic() < deadline:
        if path.exists():
            size = path.stat().st_size
            if size > 0 and size == last_size:
                return
            last_size = size
        time.sleep(_POLL_SECONDS)
    msg = f"screenshot was not written within {timeout_seconds:.0f}s: {path}"
    raise ScreenshotError(msg)


class _GatedConnection:
    """TraCI connection proxy: ``simulationStep`` also waits for a pending screenshot."""

    def __init__(self, inner: Any, after_step: Callable[[], None]) -> None:
        self._inner = inner
        self._after_step = after_step

    def simulationStep(self, step: float = 0.0) -> Any:  # noqa: N802 (TraCI API name)
        result = self._inner.simulationStep(step)
        self._after_step()
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class ReplayRunner(TraCISimulationRunner):
    """``TraCISimulationRunner`` in GUI mode with deterministic screenshot support."""

    def __init__(
        self,
        *,
        scenario_config: ScenarioConfig,
        scenario_dir: Path,
        controller_id: str,
        gui_settings_path: Path | None,
        window_size: tuple[int, int],
        label: str,
    ) -> None:
        self._gui_settings_path = gui_settings_path
        self._window_size = window_size
        self._pending_screenshot: Path | None = None
        self._view_id: str | None = None
        self._shot_size = window_size
        self._inner_connection: Any = None
        super().__init__(
            scenario_config=scenario_config,
            scenario_dir=scenario_dir,
            controller_id=controller_id,
            label=label,
            use_gui=True,
            write_manifest=False,
            collect_network_telemetry=False,
            finalize_metrics=False,
            run_mode="DEMO",
        )

    def _sumo_command(self) -> list[str]:
        command = super()._sumo_command()
        if self._gui_settings_path is not None:
            if "--gui-settings-file" in command:
                command[command.index("--gui-settings-file") + 1] = str(self._gui_settings_path)
            else:
                command.extend(["--gui-settings-file", str(self._gui_settings_path)])
        width, height = self._window_size
        command.extend(["--window-size", f"{width},{height}"])
        return command

    def start(self) -> None:
        super().start()
        self._inner_connection = self._connection
        self._connection = cast(Any, _GatedConnection(self._inner_connection, self._await_pending))
        views = self._inner_connection.gui.getIDList()
        if not views:
            msg = "SUMO GUI exposes no view"
            raise ScreenshotError(msg)
        self._view_id = str(views[0])

    @property
    def traci_connection(self) -> Any:
        """The raw TraCI connection (read-only queries and GUI calls only)."""

        if self._inner_connection is None:
            msg = "replay runner has not been started"
            raise RuntimeError(msg)
        return self._inner_connection

    def frame_for_view(self, view: ViewWindow, *, width: int, height: int) -> None:
        """Frame the world rectangle ``view`` in every following screenshot."""

        assert self._view_id is not None
        self._shot_size = (width, height)
        self.traci_connection.gui.setBoundary(
            self._view_id, view.min_x, view.min_y, view.max_x, view.max_y
        )

    def request_screenshot(self, path: Path) -> None:
        """Ask SUMO for a screenshot of the state at the end of the NEXT simulation step."""

        assert self._view_id is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        self._pending_screenshot = path
        width, height = self._shot_size
        self.traci_connection.gui.screenshot(self._view_id, str(path), width, height)

    def _await_pending(self) -> None:
        pending = self._pending_screenshot
        if pending is None:
            return
        wait_for_stable_file(pending)
        self._pending_screenshot = None
