"""Annotation rules for the replay: S3 shock marker and the deterministic reference vehicle.

Both rules read official scenario / route artifacts. Nothing here depends on simulation outcomes,
so the annotations can never favour a controller.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments.reference_route import matches_reference_route
from traffic_agents.metrics.run_metrics import OfferedVehicle

SHOCK_LABEL = "CHOQUE DE DEMANDA"
SHOCK_MARKER_SECONDS = 20.0

REFERENCE_VEHICLE_RULE = (
    "first offered vehicle, ordered by (scheduled_depart, vehicle_id), whose planned edge sequence "
    "is exactly the reference route and whose scheduled_depart is at or after "
    "max(measurement_start, recording_start); independent of any simulation outcome"
)


@dataclass(frozen=True)
class ShockMarker:
    """Step window (inclusive start, exclusive end) in which the shock banner is displayed."""

    start_step: int
    end_step: int

    def is_active(self, step_index: int) -> bool:
        return self.start_step <= step_index < self.end_step


def shock_marker_for(config: ScenarioConfig) -> ShockMarker | None:
    """Marker anchored on the official ``traffic.shock_start_seconds`` (S3 only)."""

    start_step = config.shock_start_step
    if start_step is None:
        return None
    duration_steps = max(1, math.ceil(SHOCK_MARKER_SECONDS / config.step_length))
    return ShockMarker(start_step=start_step, end_step=start_step + duration_steps)


def select_reference_vehicle(
    offered: Sequence[OfferedVehicle],
    *,
    earliest_depart_seconds: float,
) -> OfferedVehicle | None:
    """Deterministic reference vehicle to highlight (never chosen by travel-time outcome)."""

    eligible = [
        vehicle
        for vehicle in offered
        if matches_reference_route(vehicle.route)
        and vehicle.scheduled_depart >= earliest_depart_seconds
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda vehicle: (vehicle.scheduled_depart, vehicle.vehicle_id))
