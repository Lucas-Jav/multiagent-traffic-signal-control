"""Sessão do SUMO GUI usada para capturar frames, conduzida pelo executor de simulação do projeto.

O executor (``TraCISimulationRunner``) é reutilizado sem alterações: o timing do controlador
(``before_simulation_step`` / ``simulationStep`` / ``after_simulation_step``), a seed, a rede e
os arquivos de rotas são exatamente os usados nos experimentos. Este módulo apenas adiciona
comportamento do lado da GUI:

* uma visão somente leitura do arquivo de configurações da GUI e do tamanho da janela na linha
  de comando;
* solicitações de captura de tela, que o SUMO atende ao FIM do próximo ``simulationStep``;
* uma barreira que espera esse arquivo de captura antes que qualquer outro comando TraCI seja
  emitido, de modo que o frame renderizado nunca dispute com comandos do controlador executados
  após o passo.

Nada disso realimenta a simulação: apenas altera o tempo de relógio de parede.
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
    """Lançada quando o SUMO não entrega uma captura de tela solicitada."""


def wait_for_stable_file(
    path: Path, *, timeout_seconds: float = SCREENSHOT_TIMEOUT_SECONDS
) -> None:
    """Bloqueia até ``path`` existir e seu tamanho parar de mudar (escrita completa)."""

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
    """Proxy da conexão TraCI: ``simulationStep`` também espera uma captura de tela pendente."""

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
    """``TraCISimulationRunner`` em modo GUI com suporte a captura de tela determinística."""

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
        """A conexão TraCI bruta (somente consultas de leitura e chamadas de GUI)."""

        if self._inner_connection is None:
            msg = "replay runner has not been started"
            raise RuntimeError(msg)
        return self._inner_connection

    def frame_for_view(self, view: ViewWindow, *, width: int, height: int) -> None:
        """Enquadra o retângulo do mundo ``view`` em toda captura de tela seguinte."""

        assert self._view_id is not None
        self._shot_size = (width, height)
        self.traci_connection.gui.setBoundary(
            self._view_id, view.min_x, view.min_y, view.max_x, view.max_y
        )

    def request_screenshot(self, path: Path) -> None:
        """Pede ao SUMO uma captura de tela do estado ao fim do PRÓXIMO passo de simulação."""

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
