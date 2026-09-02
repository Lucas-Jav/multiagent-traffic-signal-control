from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from traffic_agents.config import IntersectionConfig, ScenarioConfig
from traffic_agents.domain import EdgeId, IntersectionId, LaneId, MovementId

if TYPE_CHECKING:
    from traffic_agents.controllers.phase_safety import PhaseDefinition

Direction = Literal["north", "east", "south", "west"]
TurnType = Literal["straight", "left", "right"]
PhaseKindName = Literal["GREEN", "YELLOW", "INTERGREEN"]

DIRECTION_ORDER: tuple[Direction, ...] = ("north", "east", "south", "west")


@dataclass(frozen=True)
class Movement:
    movement_id: MovementId
    intersection_id: IntersectionId
    traffic_light_id: str
    from_direction: Direction
    to_direction: Direction
    turn_type: TurnType
    incoming_lane_id: LaneId
    outgoing_lane_id: LaneId
    incoming_edge_id: EdgeId
    outgoing_edge_id: EdgeId
    link_index: int


@dataclass(frozen=True)
class PhasePlan:
    phase_id: str
    phase_name: str
    phase_index: int
    kind: PhaseKindName
    duration_seconds: float
    movement_ids: tuple[MovementId, ...]


@dataclass(frozen=True)
class IntersectionTrafficModel:
    intersection_id: IntersectionId
    traffic_light_id: str
    movements: tuple[Movement, ...]
    conflicts: Mapping[MovementId, tuple[MovementId, ...]]
    phases: tuple[PhaseDefinition, ...]

    @property
    def phase_plan(self) -> tuple[PhasePlan, ...]:
        movements_by_id = {movement.movement_id: movement for movement in self.movements}
        return tuple(
            PhasePlan(
                phase_id=phase.phase_id,
                phase_name=_phase_name(phase, movements_by_id),
                phase_index=phase.phase_index,
                kind=_phase_kind(phase.signal_state),
                duration_seconds=phase.duration_seconds,
                movement_ids=phase.movement_ids,
            )
            for phase in self.phases
        )


@dataclass(frozen=True)
class PhaseTimingConfig:
    min_green_seconds: float
    yellow_seconds: float
    all_red_seconds: float
    max_green_seconds: float


def load_grid_traffic_models(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
) -> dict[IntersectionId, IntersectionTrafficModel]:
    network_path = scenario_dir / scenario_config.network_file
    metadata_path = scenario_dir / "metadata.json"
    traffic_light_ids = _load_traffic_light_ids(metadata_path)
    tree = ET.parse(network_path)
    root = tree.getroot()

    return {
        intersection.intersection_id: _build_intersection_traffic_model(
            root=root,
            intersection=intersection,
            traffic_light_id=traffic_light_ids[intersection.intersection_id],
        )
        for intersection in scenario_config.intersections
    }


def validate_traffic_models(
    models: Mapping[IntersectionId, IntersectionTrafficModel],
    *,
    timing: PhaseTimingConfig,
) -> None:
    if timing.min_green_seconds < 0:
        msg = "min_green_seconds must be non-negative"
        raise ValueError(msg)
    if timing.yellow_seconds < 0:
        msg = "yellow_seconds must be non-negative"
        raise ValueError(msg)
    if timing.all_red_seconds < 0:
        msg = "all_red_seconds must be non-negative"
        raise ValueError(msg)
    if timing.max_green_seconds <= 0:
        msg = "max_green_seconds must be positive"
        raise ValueError(msg)

    for model in models.values():
        _validate_no_conflicting_green_movements(model)
        _validate_phase_timing(model, timing)


def _build_intersection_traffic_model(
    *,
    root: ET.Element,
    intersection: IntersectionConfig,
    traffic_light_id: str,
) -> IntersectionTrafficModel:
    movements = _build_movements(root, intersection, traffic_light_id)
    conflicts = _build_conflict_matrix(root, traffic_light_id, movements)
    phases = _build_phase_definitions(root, traffic_light_id, movements)
    return IntersectionTrafficModel(
        intersection_id=intersection.intersection_id,
        traffic_light_id=traffic_light_id,
        movements=movements,
        conflicts=conflicts,
        phases=phases,
    )


def _build_movements(
    root: ET.Element,
    intersection: IntersectionConfig,
    traffic_light_id: str,
) -> tuple[Movement, ...]:
    incoming_lanes = _direction_map(intersection.incoming_lanes)
    outgoing_lanes = _direction_map(intersection.outgoing_lanes)
    connections_by_edges = {
        (connection.attrib["from"], connection.attrib["to"]): connection
        for connection in root.findall("connection")
        if connection.attrib.get("tl") == traffic_light_id
        and "linkIndex" in connection.attrib
        and "from" in connection.attrib
        and "to" in connection.attrib
    }

    movements: list[Movement] = []
    for from_direction, incoming_lane_id in incoming_lanes.items():
        incoming_edge_id = _edge_id_from_lane_id(incoming_lane_id)
        for to_direction, outgoing_lane_id in outgoing_lanes.items():
            if to_direction == from_direction:
                continue

            outgoing_edge_id = _edge_id_from_lane_id(outgoing_lane_id)
            connection = connections_by_edges.get((incoming_edge_id, outgoing_edge_id))
            if connection is None:
                continue

            movement_id = _movement_id(
                intersection.intersection_id,
                from_direction,
                to_direction,
            )
            movements.append(
                Movement(
                    movement_id=movement_id,
                    intersection_id=intersection.intersection_id,
                    traffic_light_id=traffic_light_id,
                    from_direction=from_direction,
                    to_direction=to_direction,
                    turn_type=_turn_type(from_direction, to_direction),
                    incoming_lane_id=incoming_lane_id,
                    outgoing_lane_id=outgoing_lane_id,
                    incoming_edge_id=incoming_edge_id,
                    outgoing_edge_id=outgoing_edge_id,
                    link_index=int(connection.attrib["linkIndex"]),
                )
            )

    return tuple(sorted(movements, key=lambda movement: movement.link_index))


def _build_conflict_matrix(
    root: ET.Element,
    traffic_light_id: str,
    movements: tuple[Movement, ...],
) -> dict[MovementId, tuple[MovementId, ...]]:
    requests = _junction_requests(root, traffic_light_id)
    conflicts: dict[MovementId, set[MovementId]] = {
        movement.movement_id: set() for movement in movements
    }
    movements_by_link_index = {movement.link_index: movement for movement in movements}

    for movement in movements:
        request = requests.get(movement.link_index)
        if request is None:
            continue
        for other_link_index, other_movement in movements_by_link_index.items():
            if other_movement.movement_id == movement.movement_id:
                continue
            if other_movement.incoming_edge_id == movement.incoming_edge_id:
                continue
            if _request_marks_conflict(request, other_link_index):
                conflicts[movement.movement_id].add(other_movement.movement_id)
                conflicts[other_movement.movement_id].add(movement.movement_id)

    return {
        movement_id: tuple(sorted(conflicting_ids))
        for movement_id, conflicting_ids in conflicts.items()
    }


def _build_phase_definitions(
    root: ET.Element,
    traffic_light_id: str,
    movements: tuple[Movement, ...],
) -> tuple[PhaseDefinition, ...]:
    from traffic_agents.controllers.phase_safety import PhaseDefinition

    traffic_light_program = root.find(f"./tlLogic[@id='{traffic_light_id}']")
    if traffic_light_program is None:
        msg = f"traffic-light program not found: {traffic_light_id}"
        raise ValueError(msg)

    phases: list[PhaseDefinition] = []
    for phase_index, phase in enumerate(traffic_light_program.findall("phase")):
        signal_state = phase.attrib["state"]
        movement_ids = tuple(
            movement.movement_id
            for movement in movements
            if movement.link_index < len(signal_state)
            and signal_state[movement.link_index] in {"G", "g"}
        )
        phases.append(
            PhaseDefinition(
                phase_id=f"phase_{phase_index}",
                phase_index=phase_index,
                signal_state=signal_state,
                duration_seconds=float(phase.attrib["duration"]),
                movement_ids=movement_ids,
            )
        )

    return tuple(phases)


def _validate_no_conflicting_green_movements(model: IntersectionTrafficModel) -> None:
    for phase in model.phases:
        if _phase_kind(phase.signal_state) != "GREEN":
            continue

        movement_ids = phase.movement_ids
        for index, movement_id in enumerate(movement_ids):
            conflicts = set(model.conflicts[movement_id])
            for other_movement_id in movement_ids[index + 1 :]:
                if other_movement_id in conflicts:
                    msg = (
                        f"phase {phase.phase_id} at {model.intersection_id} contains "
                        f"conflicting movements: {movement_id}, {other_movement_id}"
                    )
                    raise ValueError(msg)


def _validate_phase_timing(
    model: IntersectionTrafficModel,
    timing: PhaseTimingConfig,
) -> None:
    phases = model.phases
    for index, phase in enumerate(phases):
        if _phase_kind(phase.signal_state) != "GREEN":
            continue
        if phase.duration_seconds < timing.min_green_seconds:
            msg = f"green phase {phase.phase_id} at {model.intersection_id} is below min green"
            raise ValueError(msg)
        if phase.duration_seconds > timing.max_green_seconds:
            msg = f"green phase {phase.phase_id} at {model.intersection_id} exceeds max green"
            raise ValueError(msg)

        yellow_phase = phases[(index + 1) % len(phases)]
        if _phase_kind(yellow_phase.signal_state) != "YELLOW":
            msg = (
                f"green phase {phase.phase_id} at {model.intersection_id} is not followed by yellow"
            )
            raise ValueError(msg)
        if yellow_phase.duration_seconds < timing.yellow_seconds:
            msg = f"yellow phase {yellow_phase.phase_id} at {model.intersection_id} is too short"
            raise ValueError(msg)

        if timing.all_red_seconds <= 0:
            continue
        clearance_phase = phases[(index + 2) % len(phases)]
        if _phase_kind(clearance_phase.signal_state) != "INTERGREEN":
            msg = (
                f"yellow phase {yellow_phase.phase_id} at {model.intersection_id} "
                "is not followed by all-red clearance"
            )
            raise ValueError(msg)
        if clearance_phase.duration_seconds < timing.all_red_seconds:
            msg = (
                f"all-red phase {clearance_phase.phase_id} at {model.intersection_id} is too short"
            )
            raise ValueError(msg)


def _load_traffic_light_ids(path: Path) -> dict[IntersectionId, str]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    traffic_light_ids = payload.get("traffic_light_ids") if isinstance(payload, dict) else None
    if not isinstance(traffic_light_ids, dict):
        msg = f"traffic_light_ids mapping not found in {path}"
        raise ValueError(msg)
    return {
        intersection_id: traffic_light_id
        for intersection_id, traffic_light_id in traffic_light_ids.items()
        if isinstance(intersection_id, str) and isinstance(traffic_light_id, str)
    }


def _direction_map(lane_ids: tuple[LaneId, ...]) -> dict[Direction, LaneId]:
    if len(lane_ids) != len(DIRECTION_ORDER):
        msg = "grid traffic model requires lanes ordered as north, east, south, west"
        raise ValueError(msg)
    return dict(zip(DIRECTION_ORDER, lane_ids, strict=True))


def _edge_id_from_lane_id(lane_id: LaneId) -> EdgeId:
    return lane_id.rsplit("_", 1)[0]


def _movement_id(
    intersection_id: IntersectionId,
    from_direction: Direction,
    to_direction: Direction,
) -> MovementId:
    return f"{intersection_id}:{from_direction}_to_{to_direction}"


def _turn_type(from_direction: Direction, to_direction: Direction) -> TurnType:
    from_index = DIRECTION_ORDER.index(from_direction)
    to_index = DIRECTION_ORDER.index(to_direction)
    delta = (to_index - from_index) % len(DIRECTION_ORDER)
    if delta == 2:
        return "straight"
    if delta == 1:
        return "left"
    if delta == 3:
        return "right"
    msg = f"invalid movement from {from_direction} to {to_direction}"
    raise ValueError(msg)


def _junction_requests(root: ET.Element, traffic_light_id: str) -> dict[int, ET.Element]:
    junction = root.find(f"./junction[@id='{traffic_light_id}']")
    if junction is None:
        msg = f"junction not found: {traffic_light_id}"
        raise ValueError(msg)
    return {
        int(request.attrib["index"]): request
        for request in junction.findall("request")
        if "index" in request.attrib
    }


def _request_marks_conflict(request: ET.Element, link_index: int) -> bool:
    return _request_bit(request.attrib.get("foes", ""), link_index) or _request_bit(
        request.attrib.get("response", ""),
        link_index,
    )


def _request_bit(bitset: str, link_index: int) -> bool:
    return 0 <= link_index < len(bitset) and bitset[link_index] == "1"


def _phase_kind(signal_state: str) -> PhaseKindName:
    if any(signal in {"y", "Y"} for signal in signal_state):
        return "YELLOW"
    if any(signal in {"G", "g"} for signal in signal_state):
        return "GREEN"
    return "INTERGREEN"


def _phase_name(
    phase: PhaseDefinition,
    movements_by_id: Mapping[MovementId, Movement],
) -> str:
    kind = _phase_kind(phase.signal_state)
    if kind == "GREEN":
        from_directions = {
            movements_by_id[movement_id].from_direction
            for movement_id in phase.movement_ids
            if movement_id in movements_by_id
        }
        if len(from_directions) == 1:
            direction = next(iter(from_directions)).upper()
            return f"PHASE_{direction}_APPROACH"
        return f"PHASE_COMPATIBLE_MOVEMENTS_{phase.phase_index}"
    if kind == "YELLOW":
        return f"PHASE_YELLOW_AFTER_{phase.phase_index - 1}"
    return f"PHASE_ALL_RED_AFTER_{phase.phase_index - 2}"
