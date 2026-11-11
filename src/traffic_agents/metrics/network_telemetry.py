"""Telemetria de tráfego canônica e independente do controlador.

O executor da simulação amostra este coletor após cada passo de simulação, para todo
controlador (incluindo ``B0_FIXED``), de modo que todos os controladores passam exatamente pelo
mesmo pipeline de medição. Controladores não participam da produção das métricas científicas
de tráfego.

Duas tabelas Parquet comprimidas são gravadas por execução:

``lane_telemetry.parquet``
    Uma linha por (passo, lane de entrada única): ``queue`` (veículos parados do SUMO),
    ``vehicle_count``, ``occupancy`` (fração), ``mean_speed``. Uma lane física aparece
    exatamente uma vez por passo, portanto somas sobre lanes nunca são duplicadas.

``junction_telemetry.parquet``
    Uma linha por (passo, interseção): índice da fase ativa do semáforo e tempo decorrido,
    contagens de veículos em lanes internas, entradas/saídas, ``internal_lane_persistence_events``
    e ``intersection_total_queue`` (soma das filas das lanes de entrada únicas).

Convenção de amostragem: a amostra do passo ``i`` é lida logo após o ``simulationStep()`` de
número ``i`` (tempo de simulação ``(i + 1) * step_length``); ``timestamp`` armazena esse tempo.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from traffic_agents.config import ScenarioConfig
from traffic_agents.metrics.step_telemetry import JunctionFlowTracker

LANE_TELEMETRY_FILE = "lane_telemetry.parquet"
JUNCTION_TELEMETRY_FILE = "junction_telemetry.parquet"
NETWORK_TELEMETRY_VERSION = "network-telemetry-v1"


class NetworkTelemetryError(RuntimeError):
    """Lançada quando a telemetria canônica não pode ser coletada ou gravada."""


class _LaneApi(Protocol):
    def getLastStepHaltingNumber(self, lane_id: str) -> int: ...  # noqa: N802

    def getLastStepVehicleNumber(self, lane_id: str) -> int: ...  # noqa: N802

    def getLastStepOccupancy(self, lane_id: str) -> float: ...  # noqa: N802

    def getLastStepMeanSpeed(self, lane_id: str) -> float: ...  # noqa: N802

    def getLastStepVehicleIDs(self, lane_id: str) -> Sequence[str]: ...  # noqa: N802


class _TrafficLightApi(Protocol):
    def getPhase(self, tls_id: str) -> int: ...  # noqa: N802

    def getSpentDuration(self, tls_id: str) -> float: ...  # noqa: N802


class _SimulationApi(Protocol):
    def getTime(self) -> float: ...  # noqa: N802


class NetworkTelemetryConnection(Protocol):
    lane: _LaneApi
    trafficlight: _TrafficLightApi
    simulation: _SimulationApi


class NetworkTelemetrySink(Protocol):
    """O que o executor precisa de um coletor de telemetria."""

    def record(self, step_index: int) -> None: ...

    def write(self, directory: Path) -> tuple[Path, ...]: ...


@dataclass(frozen=True)
class TelemetryLane:
    lane_id: str
    edge_id: str
    intersection_id: str


def load_traffic_light_ids(metadata_path: Path) -> dict[str, str]:
    payload: Any = json.loads(metadata_path.read_text(encoding="utf-8"))
    traffic_light_ids = payload.get("traffic_light_ids") if isinstance(payload, dict) else None
    if not isinstance(traffic_light_ids, dict):
        msg = f"traffic_light_ids mapping not found in {metadata_path}"
        raise NetworkTelemetryError(msg)
    return {str(key): str(value) for key, value in traffic_light_ids.items()}


def load_internal_lane_ids(network_path: Path) -> dict[str, tuple[str, ...]]:
    root = ET.parse(network_path).getroot()
    return {
        str(junction.attrib["id"]): tuple(junction.attrib.get("intLanes", "").split())
        for junction in root.findall("junction")
        if junction.attrib.get("type") == "traffic_light"
    }


def edge_id_of_lane(lane_id: str) -> str:
    return lane_id.rsplit("_", maxsplit=1)[0]


class NetworkTelemetryCollector:
    """Amostra o estado de lanes de entrada únicas e de junção para toda interseção."""

    def __init__(
        self,
        *,
        connection: NetworkTelemetryConnection,
        scenario_config: ScenarioConfig,
        scenario_dir: Path,
        expected_steps: int,
    ) -> None:
        self._connection = connection
        self._scenario_config = scenario_config
        traffic_light_ids = load_traffic_light_ids(scenario_dir / "metadata.json")
        internal_lanes = load_internal_lane_ids(scenario_dir / scenario_config.network_file)

        self._intersections: list[str] = []
        self._tls_ids: list[str] = []
        self._internal_lanes: list[tuple[str, ...]] = []
        self._lanes: list[TelemetryLane] = []
        self._lane_slices: list[tuple[int, int]] = []
        for intersection in scenario_config.intersections:
            intersection_id = intersection.intersection_id
            tls_id = traffic_light_ids.get(intersection_id)
            if tls_id is None:
                msg = f"traffic light id not configured for intersection {intersection_id}"
                raise NetworkTelemetryError(msg)
            start = len(self._lanes)
            for lane_id in intersection.incoming_lanes:
                self._lanes.append(
                    TelemetryLane(
                        lane_id=str(lane_id),
                        edge_id=edge_id_of_lane(str(lane_id)),
                        intersection_id=str(intersection_id),
                    )
                )
            self._lane_slices.append((start, len(self._lanes)))
            self._intersections.append(str(intersection_id))
            self._tls_ids.append(tls_id)
            self._internal_lanes.append(internal_lanes.get(tls_id, ()))

        unique_lane_ids = {lane.lane_id for lane in self._lanes}
        if len(unique_lane_ids) != len(self._lanes):
            msg = "an incoming lane is assigned to more than one intersection"
            raise NetworkTelemetryError(msg)

        steps = max(int(expected_steps), 1)
        lane_count = len(self._lanes)
        junction_count = len(self._intersections)
        self._steps: list[int] = []
        self._timestamps: list[float] = []
        self._lane_queue = np.zeros((steps, lane_count), dtype=np.int16)
        self._lane_vehicles = np.zeros((steps, lane_count), dtype=np.int16)
        self._lane_occupancy = np.zeros((steps, lane_count), dtype=np.float32)
        self._lane_speed = np.zeros((steps, lane_count), dtype=np.float32)
        self._tls_phase = np.zeros((steps, junction_count), dtype=np.int16)
        self._tls_elapsed = np.zeros((steps, junction_count), dtype=np.float32)
        self._internal_count = np.zeros((steps, junction_count), dtype=np.int16)
        self._entries = np.zeros((steps, junction_count), dtype=np.int16)
        self._exits = np.zeros((steps, junction_count), dtype=np.int16)
        self._persistence = np.zeros((steps, junction_count), dtype=np.int16)
        self._junction_tracker = JunctionFlowTracker()

    @property
    def lane_ids(self) -> tuple[str, ...]:
        return tuple(lane.lane_id for lane in self._lanes)

    @property
    def samples(self) -> int:
        return len(self._steps)

    def record(self, step_index: int) -> None:
        row = len(self._steps)
        if row >= self._lane_queue.shape[0]:
            self._grow(row + 1024)
        connection = self._connection
        lane_api = connection.lane
        for column, lane in enumerate(self._lanes):
            self._lane_queue[row, column] = lane_api.getLastStepHaltingNumber(lane.lane_id)
            self._lane_vehicles[row, column] = lane_api.getLastStepVehicleNumber(lane.lane_id)
            self._lane_occupancy[row, column] = lane_api.getLastStepOccupancy(lane.lane_id) / 100.0
            self._lane_speed[row, column] = lane_api.getLastStepMeanSpeed(lane.lane_id)
        for column, tls_id in enumerate(self._tls_ids):
            self._tls_phase[row, column] = connection.trafficlight.getPhase(tls_id)
            self._tls_elapsed[row, column] = connection.trafficlight.getSpentDuration(tls_id)
            vehicle_ids: set[str] = set()
            for lane_id in self._internal_lanes[column]:
                vehicle_ids.update(lane_api.getLastStepVehicleIDs(lane_id))
            metrics = self._junction_tracker.update_from_vehicle_ids(
                intersection_id=self._intersections[column],
                current_vehicle_ids=frozenset(vehicle_ids),
            )
            self._internal_count[row, column] = metrics.internal_vehicle_count
            self._entries[row, column] = metrics.entries
            self._exits[row, column] = metrics.exits
            self._persistence[row, column] = metrics.internal_lane_persistence_events
        self._steps.append(int(step_index))
        self._timestamps.append(float(connection.simulation.getTime()))

    def _grow(self, new_size: int) -> None:
        for name in (
            "_lane_queue",
            "_lane_vehicles",
            "_lane_occupancy",
            "_lane_speed",
            "_tls_phase",
            "_tls_elapsed",
            "_internal_count",
            "_entries",
            "_exits",
            "_persistence",
        ):
            array: np.ndarray[Any, Any] = getattr(self, name)
            grown = np.zeros((new_size, array.shape[1]), dtype=array.dtype)
            grown[: array.shape[0]] = array
            setattr(self, name, grown)

    def write(self, directory: Path) -> tuple[Path, ...]:
        directory.mkdir(parents=True, exist_ok=True)
        sample_count = len(self._steps)
        if sample_count == 0:
            msg = "no telemetry samples were recorded"
            raise NetworkTelemetryError(msg)
        lane_path = directory / LANE_TELEMETRY_FILE
        junction_path = directory / JUNCTION_TELEMETRY_FILE
        pq.write_table(self._lane_table(sample_count), lane_path, compression="zstd")
        pq.write_table(self._junction_table(sample_count), junction_path, compression="zstd")
        return (lane_path, junction_path)

    def _warmup_flags(self, sample_count: int) -> np.ndarray[Any, Any]:
        steps = np.asarray(self._steps, dtype=np.int32)
        return steps < self._scenario_config.measurement_start_step

    def _lane_table(self, sample_count: int) -> pa.Table:
        lane_count = len(self._lanes)
        steps = np.repeat(np.asarray(self._steps, dtype=np.int32), lane_count)
        timestamps = np.repeat(np.asarray(self._timestamps, dtype=np.float64), lane_count)
        warmup = np.repeat(self._warmup_flags(sample_count), lane_count)
        lane_index = np.tile(np.arange(lane_count, dtype=np.int32), sample_count)

        def dictionary(values: list[str], indices: np.ndarray[Any, Any]) -> pa.Array:
            unique = sorted(set(values))
            mapping = {value: position for position, value in enumerate(unique)}
            remapped = np.asarray([mapping[value] for value in values], dtype=np.int32)
            return pa.DictionaryArray.from_arrays(
                pa.array(remapped[indices], type=pa.int32()),
                pa.array(unique, type=pa.string()),
            )

        return pa.table(
            {
                "step_index": pa.array(steps),
                "timestamp": pa.array(timestamps),
                "is_warmup": pa.array(warmup),
                "lane_id": dictionary([lane.lane_id for lane in self._lanes], lane_index),
                "approach_edge_id": dictionary([lane.edge_id for lane in self._lanes], lane_index),
                "intersection_id": dictionary(
                    [lane.intersection_id for lane in self._lanes], lane_index
                ),
                "queue": pa.array(self._lane_queue[:sample_count].reshape(-1)),
                "vehicle_count": pa.array(self._lane_vehicles[:sample_count].reshape(-1)),
                "occupancy": pa.array(self._lane_occupancy[:sample_count].reshape(-1)),
                "mean_speed": pa.array(self._lane_speed[:sample_count].reshape(-1)),
            }
        )

    def _junction_table(self, sample_count: int) -> pa.Table:
        junction_count = len(self._intersections)
        steps = np.repeat(np.asarray(self._steps, dtype=np.int32), junction_count)
        timestamps = np.repeat(np.asarray(self._timestamps, dtype=np.float64), junction_count)
        warmup = np.repeat(self._warmup_flags(sample_count), junction_count)
        intersection_index = np.tile(np.arange(junction_count, dtype=np.int32), sample_count)
        intersection_total = np.stack(
            [
                self._lane_queue[:sample_count, start:end].sum(axis=1, dtype=np.int32)
                for start, end in self._lane_slices
            ],
            axis=1,
        ).astype(np.int16)
        return pa.table(
            {
                "step_index": pa.array(steps),
                "timestamp": pa.array(timestamps),
                "is_warmup": pa.array(warmup),
                "intersection_id": pa.DictionaryArray.from_arrays(
                    pa.array(intersection_index, type=pa.int32()),
                    pa.array(self._intersections, type=pa.string()),
                ),
                "tls_phase": pa.array(self._tls_phase[:sample_count].reshape(-1)),
                "phase_elapsed": pa.array(self._tls_elapsed[:sample_count].reshape(-1)),
                "internal_vehicle_count": pa.array(self._internal_count[:sample_count].reshape(-1)),
                "junction_entries": pa.array(self._entries[:sample_count].reshape(-1)),
                "junction_exits": pa.array(self._exits[:sample_count].reshape(-1)),
                "internal_lane_persistence_events": pa.array(
                    self._persistence[:sample_count].reshape(-1)
                ),
                "intersection_total_queue": pa.array(intersection_total.reshape(-1)),
            }
        )
