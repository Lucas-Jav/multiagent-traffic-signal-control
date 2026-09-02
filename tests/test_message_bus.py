from __future__ import annotations

import json

import pytest

from traffic_agents.communication import (
    MessageBus,
    MessageBusConfig,
    MessageBusError,
    serialize_message,
)


def test_publish_records_message_and_metrics() -> None:
    bus = MessageBus(destinations=("A1", "A2"))

    message = bus.publish(
        source="A1",
        destination="A2",
        created_step=12,
        payload={"queue": 7},
    )

    assert message.message_id == "A1:0"
    assert message.source == "A1"
    assert message.destination == "A2"
    assert message.created_step == 12
    assert message.sequence == 0
    assert message.payload == {"queue": 7}
    assert bus.metrics.messages_sent == 1
    assert bus.metrics.messages_delivered == 0
    assert bus.pending_count("A2") == 1


def test_receive_delivers_available_messages_once() -> None:
    bus = MessageBus(destinations=("A1", "A2"))
    published = bus.publish(
        source="A1",
        destination="A2",
        created_step=0,
        payload={"phase": "phase_0"},
    )

    delivered = bus.receive(destination="A2", current_step=0)
    delivered_again = bus.receive(destination="A2", current_step=0)

    assert delivered == (published,)
    assert delivered_again == ()
    assert bus.metrics.messages_delivered == 1
    assert bus.pending_count("A2") == 0


def test_delivery_order_is_deterministic_by_delivery_step_and_sequence() -> None:
    bus = MessageBus(
        destinations=("A1", "A2"),
        config=MessageBusConfig(delay_steps=2),
    )
    first = bus.publish(source="A1", destination="A2", created_step=0, payload={"n": 1})
    second = bus.publish(source="A1", destination="A2", created_step=0, payload={"n": 2})
    third = bus.publish(source="A1", destination="A2", created_step=1, payload={"n": 3})

    assert bus.receive(destination="A2", current_step=1) == ()
    assert bus.receive(destination="A2", current_step=3) == (first, second, third)


def test_publish_rejects_invalid_destination() -> None:
    bus = MessageBus(destinations=("A1", "A2"))

    with pytest.raises(MessageBusError, match="invalid message destination"):
        bus.publish(
            source="A1",
            destination="A3",
            created_step=0,
            payload={"queue": 1},
        )

    assert bus.metrics.messages_sent == 0


def test_serialized_size_uses_deterministic_utf8_json() -> None:
    bus = MessageBus(destinations=("A1", "A2"))
    message = bus.publish(
        source="A1",
        destination="A2",
        created_step=5,
        payload={"z": 1, "a": {"b": True}},
    )
    expected_serialization = json.dumps(
        message.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    assert serialize_message(message) == expected_serialization
    assert bus.metrics.serialized_bytes == len(expected_serialization)


def test_message_uses_simulation_step_instead_of_wall_clock_timestamp() -> None:
    bus = MessageBus(destinations=("A1", "A2"))

    message = bus.publish(
        source="A1",
        destination="A2",
        created_step=42,
        payload={"state_timestamp": 123.5},
    )

    assert message.created_step == 42
    assert not hasattr(message, "timestamp")


def test_stale_messages_are_discarded_without_delivery() -> None:
    bus = MessageBus(
        destinations=("A1", "A2"),
        config=MessageBusConfig(stale_after_steps=1),
    )
    bus.publish(source="A1", destination="A2", created_step=0, payload={"queue": 3})

    assert bus.receive(destination="A2", current_step=2) == ()
    assert bus.metrics.messages_delivered == 0
    assert bus.metrics.stale_messages == 1
