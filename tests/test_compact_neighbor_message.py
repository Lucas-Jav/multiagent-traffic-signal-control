from __future__ import annotations

from typing import cast

import pytest

from traffic_agents.communication import (
    CompactNeighborMessageFactory,
    MessageBus,
    compact_message_payload,
    grid_3x3_communication_topology,
    serialize_message,
)
from traffic_agents.controllers import PhaseDefinition
from traffic_agents.domain import AgentObservation, IntersectionState
from traffic_agents.traffic_model import Direction, IntersectionTrafficModel, Movement, TurnType


def make_movement(
    movement_id: str,
    *,
    from_direction: str,
    to_direction: str,
    turn_type: str,
    incoming_lane_id: str,
    outgoing_lane_id: str,
    outgoing_edge_id: str,
    link_index: int,
) -> Movement:
    return Movement(
        movement_id=movement_id,
        intersection_id="A4",
        traffic_light_id="A4",
        from_direction=cast(Direction, from_direction),
        to_direction=cast(Direction, to_direction),
        turn_type=cast(TurnType, turn_type),
        incoming_lane_id=incoming_lane_id,
        outgoing_lane_id=outgoing_lane_id,
        incoming_edge_id=incoming_lane_id.rsplit("_", 1)[0],
        outgoing_edge_id=outgoing_edge_id,
        link_index=link_index,
    )


def make_traffic_model() -> IntersectionTrafficModel:
    movements = (
        make_movement(
            "A4:north_to_east",
            from_direction="north",
            to_direction="east",
            turn_type="left",
            incoming_lane_id="north_in_0",
            outgoing_lane_id="A4A5_0",
            outgoing_edge_id="A4A5",
            link_index=0,
        ),
        make_movement(
            "A4:south_to_east",
            from_direction="south",
            to_direction="east",
            turn_type="right",
            incoming_lane_id="south_in_0",
            outgoing_lane_id="A4A5_0",
            outgoing_edge_id="A4A5",
            link_index=1,
        ),
        make_movement(
            "A4:west_to_east",
            from_direction="west",
            to_direction="east",
            turn_type="straight",
            incoming_lane_id="west_in_0",
            outgoing_lane_id="A4A5_0",
            outgoing_edge_id="A4A5",
            link_index=2,
        ),
        make_movement(
            "A4:east_to_north",
            from_direction="east",
            to_direction="north",
            turn_type="right",
            incoming_lane_id="east_in_0",
            outgoing_lane_id="A4A1_0",
            outgoing_edge_id="A4A1",
            link_index=3,
        ),
    )
    return IntersectionTrafficModel(
        intersection_id="A4",
        traffic_light_id="A4",
        movements=movements,
        conflicts={movement.movement_id: () for movement in movements},
        phases=(
            PhaseDefinition(
                phase_id="phase_to_A5",
                phase_index=0,
                signal_state="GGGr",
                duration_seconds=20.0,
                movement_ids=(
                    "A4:north_to_east",
                    "A4:south_to_east",
                    "A4:west_to_east",
                ),
            ),
            PhaseDefinition(
                phase_id="phase_to_A1",
                phase_index=1,
                signal_state="rrrG",
                duration_seconds=20.0,
                movement_ids=("A4:east_to_north",),
            ),
        ),
    )


def make_observation() -> AgentObservation:
    return AgentObservation(
        state=IntersectionState(
            intersection_id="A4",
            timestamp=123.5,
            current_phase="phase_to_A5",
            phase_elapsed=8.0,
            incoming_queue={
                "north_in_0": 10,
                "south_in_0": 20,
                "west_in_0": 30,
                "east_in_0": 99,
            },
            incoming_occupancy={
                "north_in_0": 0.1,
                "south_in_0": 0.2,
                "west_in_0": 0.3,
                "east_in_0": 0.9,
            },
            incoming_speed={
                "north_in_0": 10.0,
                "south_in_0": 9.0,
                "west_in_0": 8.0,
                "east_in_0": 1.0,
            },
            outgoing_occupancy={
                "A4A5_0": 0.25,
                "A4A1_0": 0.75,
            },
            arrival_rate={
                "north_in": 1.0,
                "south_in": 2.0,
                "west_in": 3.0,
                "east_in": 9.0,
            },
        )
    )


def make_factory() -> CompactNeighborMessageFactory:
    return CompactNeighborMessageFactory(
        traffic_model=make_traffic_model(),
        topology=grid_3x3_communication_topology(),
    )


def test_compact_neighbor_message_is_deterministic() -> None:
    factory = make_factory()
    kwargs = {
        "observation": make_observation(),
        "destination": "A5",
        "created_step": 42,
        "sequence": 7,
    }

    first = factory.build(**kwargs)
    second = factory.build(**kwargs)

    assert first == second
    assert serialize_message(first) == serialize_message(second)


def test_compact_neighbor_message_is_destination_specific() -> None:
    message = make_factory().build(
        observation=make_observation(),
        destination="A5",
        created_step=42,
        sequence=0,
    )

    assert message.destination == "A5"
    assert message.downstream_occupancy == pytest.approx(0.25)
    assert message.outgoing_queue_summary == {
        "straight": pytest.approx(18.0),
        "left": pytest.approx(2.0),
        "right": pytest.approx(4.0),
    }
    assert compact_message_payload(message)["outgoing_queue_summary"] == {
        "straight": 18.0,
        "left": 2.0,
        "right": 4.0,
    }


def test_compact_neighbor_message_does_not_include_global_or_full_state_fields() -> None:
    message = make_factory().build(
        observation=make_observation(),
        destination="A5",
        created_step=42,
        sequence=0,
    )
    serialized = serialize_message(message).decode("utf-8")

    assert "incoming_queue" not in serialized
    assert "incoming_occupancy" not in serialized
    assert "incoming_speed" not in serialized
    assert "outgoing_occupancy" not in serialized
    assert "neighbor_states" not in serialized
    assert "messages" not in serialized


def test_compact_neighbor_message_treats_turning_demand_to_neighbor() -> None:
    message = make_factory().build(
        observation=make_observation(),
        destination="A5",
        created_step=42,
        sequence=0,
    )

    assert message.arrival_trend == pytest.approx(2.4)
    assert message.outgoing_pressure == pytest.approx(23.9)


def test_compact_neighbor_message_preserves_simulation_timestamp() -> None:
    message = make_factory().build(
        observation=make_observation(),
        destination="A5",
        created_step=42,
        sequence=0,
    )

    assert message.source_timestamp == pytest.approx(123.5)
    assert message.created_step == 42


def test_compact_message_serialized_bytes_are_recorded_by_bus() -> None:
    topology = grid_3x3_communication_topology()
    bus = MessageBus(destinations=topology.agent_ids, topology=topology)
    message = make_factory().build(
        observation=make_observation(),
        destination="A5",
        created_step=42,
        sequence=0,
    )

    scheduled_message = bus.publish_compact(message)

    assert scheduled_message.scheduled_delivery_step == 42
    assert scheduled_message.delivered_step is None
    assert bus.metrics.serialized_bytes == len(serialize_message(scheduled_message))
