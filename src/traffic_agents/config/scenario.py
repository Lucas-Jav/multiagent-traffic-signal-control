from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    model_validator,
)

from traffic_agents.domain import EdgeId, IntersectionId, LaneId

DemandLevel = Literal["LOW", "MEDIUM", "HIGH"]
DemandProfileId = Literal["S1_BALANCED"]
ControllerId = Annotated[str, Field(min_length=1)]
PhaseId = Annotated[str, Field(min_length=1)]
type VehicleRateByDemandLevel = dict[DemandLevel, PositiveFloat]


class ConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SimulationConfig(ConfigModel):
    duration_seconds: PositiveFloat
    warmup_seconds: NonNegativeFloat
    step_length: PositiveFloat
    seed: NonNegativeInt

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        if self.warmup_seconds >= self.duration_seconds:
            msg = "warmup_seconds must be lower than duration_seconds"
            raise ValueError(msg)
        return self


class FlowDefinitionConfig(ConfigModel):
    flow_id: Annotated[str, Field(min_length=1)]
    origin_edge_id: EdgeId
    destination_edge_id: EdgeId
    begin_seconds: NonNegativeFloat
    end_seconds: PositiveFloat
    vehicles_per_hour: VehicleRateByDemandLevel

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        if self.end_seconds <= self.begin_seconds:
            msg = "end_seconds must be greater than begin_seconds"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_demand_levels(self) -> Self:
        expected_levels = {"LOW", "MEDIUM", "HIGH"}
        actual_levels = set(self.vehicles_per_hour)
        if actual_levels != expected_levels:
            msg = "vehicles_per_hour must define LOW, MEDIUM, and HIGH"
            raise ValueError(msg)
        return self

    def rate_for(self, demand_level: DemandLevel) -> float:
        return self.vehicles_per_hour[demand_level]


class TurningRatiosConfig(ConfigModel):
    straight: NonNegativeFloat = 0.60
    left: NonNegativeFloat = 0.20
    right: NonNegativeFloat = 0.20

    @model_validator(mode="after")
    def validate_total(self) -> Self:
        total = self.straight + self.left + self.right
        if abs(total - 1.0) > 0.000001:
            msg = "turning ratios must sum to 1.0"
            raise ValueError(msg)
        return self


class TrafficDemandConfig(ConfigModel):
    demand_profile: DemandProfileId
    demand_level: DemandLevel
    turning_ratios: TurningRatiosConfig = Field(default_factory=TurningRatiosConfig)
    flows: Annotated[tuple[FlowDefinitionConfig, ...], Field(min_length=1)]


class IntersectionConfig(ConfigModel):
    intersection_id: IntersectionId
    incoming_lanes: Annotated[tuple[LaneId, ...], Field(min_length=1)]
    outgoing_lanes: Annotated[tuple[LaneId, ...], Field(min_length=1)]
    phases: Annotated[tuple[PhaseId, ...], Field(min_length=1)]


class ScenarioConfig(ConfigModel):
    scenario_id: Annotated[str, Field(min_length=1)]
    network_file: Annotated[
        Path,
        Field(description="Path to the network file, relative to scenario.yaml."),
    ]
    route_file: Annotated[
        Path,
        Field(description="Path to the route file, relative to scenario.yaml."),
    ]
    duration_seconds: PositiveFloat
    warmup_seconds: NonNegativeFloat
    step_length: PositiveFloat
    seed: NonNegativeInt
    controller_id: ControllerId
    traffic: TrafficDemandConfig
    intersections: Annotated[tuple[IntersectionConfig, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_simulation_window(self) -> Self:
        SimulationConfig(
            duration_seconds=self.duration_seconds,
            warmup_seconds=self.warmup_seconds,
            step_length=self.step_length,
            seed=self.seed,
        )
        return self

    @property
    def simulation(self) -> SimulationConfig:
        return SimulationConfig(
            duration_seconds=self.duration_seconds,
            warmup_seconds=self.warmup_seconds,
            step_length=self.step_length,
            seed=self.seed,
        )


def load_scenario_config(path: Path) -> ScenarioConfig:
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    if not isinstance(payload, dict):
        msg = "scenario config must be a YAML mapping"
        raise ValueError(msg)

    return ScenarioConfig.model_validate(payload)


def validate_scenario_config(path: Path) -> ScenarioConfig:
    return load_scenario_config(path)
