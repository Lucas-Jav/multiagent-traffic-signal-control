from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

SUMO_TRAFFIC_METRICS_FILE = "sumo_traffic_metrics.json"


class SumoTripMetricsError(ValueError):
    """Raised when SUMO metric output cannot be parsed."""


@dataclass(frozen=True)
class SumoTripMetrics:
    available: bool
    trip_count: int = 0
    mean_waiting_time_seconds: float = 0.0
    mean_time_loss_seconds: float = 0.0
    mean_travel_time_seconds: float = 0.0
    mean_stops: float = 0.0
    unfinished_vehicle_policy: str = (
        "SUMO tripinfo contains completed trips only; vehicles not completed by run end "
        "are counted in manifest departure/arrival totals and excluded from trip means."
    )
    source_tripinfo_file: str | None = None
    source_statistics_file: str | None = None
    missing_reason: str | None = None


def parse_sumo_trip_metrics(
    *,
    tripinfo_path: Path,
    statistics_path: Path | None = None,
) -> SumoTripMetrics:
    if not tripinfo_path.exists():
        msg = f"SUMO tripinfo file not found: {tripinfo_path}"
        raise FileNotFoundError(msg)
    if not tripinfo_path.is_file():
        msg = f"SUMO tripinfo path is not a file: {tripinfo_path}"
        raise SumoTripMetricsError(msg)

    try:
        tree = ET.parse(tripinfo_path)
    except ET.ParseError as exc:
        msg = f"malformed SUMO tripinfo XML: {tripinfo_path}"
        raise SumoTripMetricsError(msg) from exc

    trips = tree.getroot().findall("tripinfo")
    if not trips:
        return SumoTripMetrics(
            available=True,
            trip_count=0,
            source_tripinfo_file=tripinfo_path.name,
            source_statistics_file=statistics_path.name if statistics_path is not None else None,
        )

    waiting_times: list[float] = []
    time_losses: list[float] = []
    travel_times: list[float] = []
    stops: list[float] = []
    for trip in trips:
        waiting_times.append(_required_float(trip, "waitingTime", tripinfo_path))
        time_losses.append(_required_float(trip, "timeLoss", tripinfo_path))
        travel_times.append(_required_float(trip, "duration", tripinfo_path))
        stops.append(_optional_float(trip, "waitingCount", 0.0))

    return SumoTripMetrics(
        available=True,
        trip_count=len(trips),
        mean_waiting_time_seconds=_mean(waiting_times),
        mean_time_loss_seconds=_mean(time_losses),
        mean_travel_time_seconds=_mean(travel_times),
        mean_stops=_mean(stops),
        source_tripinfo_file=tripinfo_path.name,
        source_statistics_file=statistics_path.name if statistics_path is not None else None,
    )


def missing_sumo_trip_metrics(
    *,
    tripinfo_path: Path,
    statistics_path: Path | None,
) -> SumoTripMetrics:
    return SumoTripMetrics(
        available=False,
        source_tripinfo_file=tripinfo_path.name,
        source_statistics_file=statistics_path.name if statistics_path is not None else None,
        missing_reason="SUMO output was not present when metrics were finalized.",
    )


def write_sumo_trip_metrics(path: Path, metrics: SumoTripMetrics) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _required_float(element: ET.Element, attribute: str, path: Path) -> float:
    value = element.attrib.get(attribute)
    if value is None:
        msg = f"SUMO tripinfo missing required {attribute}: {path}"
        raise SumoTripMetricsError(msg)
    try:
        return float(value)
    except ValueError as exc:
        msg = f"SUMO tripinfo attribute {attribute} must be numeric: {path}"
        raise SumoTripMetricsError(msg) from exc


def _optional_float(element: ET.Element, attribute: str, default: float) -> float:
    value = element.attrib.get(attribute)
    if value is None:
        return default
    return float(value)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
