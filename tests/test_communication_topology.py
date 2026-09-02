from __future__ import annotations

import pytest

from traffic_agents.agents import AgentRegistry
from traffic_agents.communication import (
    GRID_3X3_COMMUNICATION_TOPOLOGY_ID,
    CommunicationTopologyError,
    MessageBus,
    MessageBusError,
    grid_3x3_communication_topology,
)
from traffic_agents.domain import AgentObservation, TrafficLightAction


class FakeController:
    def decide(self, observation: AgentObservation) -> TrafficLightAction:
        return TrafficLightAction.keep_phase()


def test_grid_3x3_communication_topology_is_symmetric() -> None:
    topology = grid_3x3_communication_topology()

    assert topology.topology_id == GRID_3X3_COMMUNICATION_TOPOLOGY_ID
    for source in topology.agent_ids:
        for destination in topology.neighbors_of(source):
            assert topology.can_communicate(destination, source)


def test_grid_3x3_corner_agents_have_degree_two() -> None:
    topology = grid_3x3_communication_topology()

    assert {
        agent_id: len(topology.neighbors_of(agent_id)) for agent_id in ("A1", "A3", "A7", "A9")
    } == {
        "A1": 2,
        "A3": 2,
        "A7": 2,
        "A9": 2,
    }


def test_grid_3x3_edge_agents_have_degree_three() -> None:
    topology = grid_3x3_communication_topology()

    assert {
        agent_id: len(topology.neighbors_of(agent_id)) for agent_id in ("A2", "A4", "A6", "A8")
    } == {
        "A2": 3,
        "A4": 3,
        "A6": 3,
        "A8": 3,
    }


def test_grid_3x3_center_agent_has_degree_four() -> None:
    topology = grid_3x3_communication_topology()

    assert topology.neighbors_of("A5") == ("A2", "A4", "A6", "A8")
    assert len(topology.neighbors_of("A5")) == 4


def test_agent_registry_uses_explicit_communication_topology() -> None:
    registry = AgentRegistry.for_grid_3x3(lambda _intersection_id: FakeController())

    assert registry.neighbor_ids_for("A1") == ("A2", "A4")
    assert registry.neighbor_ids_for("A5") == ("A2", "A4", "A6", "A8")
    assert registry.can_query_agent("A1", "A2")
    assert not registry.can_query_agent("A1", "A9")


def test_topology_rejects_queries_to_non_neighbors() -> None:
    topology = grid_3x3_communication_topology()

    with pytest.raises(CommunicationTopologyError, match="not allowed"):
        topology.require_can_communicate("A1", "A9")


def test_topology_rejects_unknown_agent_queries() -> None:
    topology = grid_3x3_communication_topology()

    with pytest.raises(CommunicationTopologyError, match="unknown communication agent"):
        topology.neighbors_of("A10")


def test_message_bus_rejects_publish_outside_communication_topology() -> None:
    topology = grid_3x3_communication_topology()
    bus = MessageBus(destinations=topology.agent_ids, topology=topology)

    bus.publish(source="A1", destination="A2", created_step=0, payload={"ok": True})
    with pytest.raises(MessageBusError, match="not allowed"):
        bus.publish(source="A1", destination="A9", created_step=0, payload={"ok": False})


def test_topology_has_stable_hash_for_future_manifest_registration() -> None:
    topology = grid_3x3_communication_topology()

    assert len(topology.topology_hash) == 64
    assert topology.topology_hash == grid_3x3_communication_topology().topology_hash
