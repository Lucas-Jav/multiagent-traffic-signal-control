"""Números ao vivo por passo exibidos no overlay do vídeo (apenas anotação).

Esses valores NÃO são métricas científicas e nunca alimentam nenhuma análise: o pipeline oficial
de métricas (``traffic_agents.metrics``) permanece intocado. São consultas TraCI somente leitura
emitidas após cada passo, portanto não podem influenciar a simulação.

* ``network_queue``: veículos parados (velocidade abaixo de 0,1 m/s) em todas as arestas não
  internas.
* ``arrived_count`` / ``departed_count``: contagens acumuladas desde o passo de simulação 0.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VISUAL_METRICS_COLUMNS: tuple[str, ...] = (
    "simulation_step",
    "simulation_time_s",
    "network_queue",
    "arrived_count",
    "departed_count",
)


@dataclass(frozen=True)
class VisualMetricsRow:
    simulation_step: int
    simulation_time_s: float
    network_queue: int
    arrived_count: int
    departed_count: int


class VisualMetricsCollector:
    """Acumula contagens de chegados/partidos e amostra o total de veículos parados."""

    def __init__(self, edge_ids: Sequence[str]) -> None:
        self._edge_ids = tuple(edge_ids)
        self._arrived = 0
        self._departed = 0

    def update_counts(self, connection: Any) -> None:
        """Chame uma vez após TODO passo de simulação para que as contagens acumuladas fiquem
        completas.
        """

        simulation = connection.simulation
        self._arrived += int(simulation.getArrivedNumber())
        self._departed += int(simulation.getDepartedNumber())

    def sample(self, connection: Any, *, step_index: int) -> VisualMetricsRow:
        edge = connection.edge
        queue = sum(int(edge.getLastStepHaltingNumber(edge_id)) for edge_id in self._edge_ids)
        return VisualMetricsRow(
            simulation_step=step_index,
            simulation_time_s=float(connection.simulation.getTime()),
            network_queue=queue,
            arrived_count=self._arrived,
            departed_count=self._departed,
        )


def write_visual_metrics(path: Path, rows: Iterable[VisualMetricsRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(VISUAL_METRICS_COLUMNS)
        for row in rows:
            writer.writerow([getattr(row, name) for name in VISUAL_METRICS_COLUMNS])


def read_visual_metrics(path: Path) -> list[VisualMetricsRow]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != VISUAL_METRICS_COLUMNS:
            msg = f"unexpected visual metrics columns in {path}: {reader.fieldnames}"
            raise ValueError(msg)
        return [
            VisualMetricsRow(
                simulation_step=int(record["simulation_step"]),
                simulation_time_s=float(record["simulation_time_s"]),
                network_queue=int(record["network_queue"]),
                arrived_count=int(record["arrived_count"]),
                departed_count=int(record["departed_count"]),
            )
            for record in reader
        ]
