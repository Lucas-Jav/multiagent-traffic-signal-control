from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, Self

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

from traffic_agents.communication_seed import derive_communication_rng_seed
from traffic_agents.domain import EdgeId, IntersectionId, LaneId

DemandLevel = Literal["LOW", "MEDIUM", "HIGH"]
DemandProfileId = Literal[
    "S1_BALANCED",
    "S2_DIRECTIONAL_PEAK",
    "S3_DEMAND_SHIFT",
    "S4_LOCAL_SATURATION",
]
ControllerId = Annotated[str, Field(min_length=1)]
PhaseId = Annotated[str, Field(min_length=1)]
type VehicleRateByDemandLevel = dict[DemandLevel, PositiveFloat]


class ConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SimulationConfig(ConfigModel):
    warmup_seconds: NonNegativeFloat
    measurement_duration_seconds: PositiveFloat
    step_length: PositiveFloat
    seed: NonNegativeInt

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_duration(cls, payload: object) -> object:
        if not isinstance(payload, dict):
            return payload
        if "measurement_duration_seconds" in payload:
            return payload
        if "duration_seconds" in payload:
            migrated = dict(payload)
            migrated["measurement_duration_seconds"] = migrated.pop("duration_seconds")
            return migrated
        return payload

    @model_validator(mode="after")
    def validate_step_alignment(self) -> Self:
        total_steps = self.total_steps
        measurement_start_step = self.measurement_start_step
        measurement_end_step = self.measurement_end_step
        if measurement_start_step >= measurement_end_step:
            msg = "measurement window must contain at least one simulation step"
            raise ValueError(msg)
        if measurement_end_step > total_steps:
            msg = "measurement_end_step must be lower than or equal to total_steps"
            raise ValueError(msg)
        return self

    @property
    def duration_seconds(self) -> float:
        return float(self.measurement_duration_seconds)

    @property
    def total_duration_seconds(self) -> float:
        return float(self.warmup_seconds + self.measurement_duration_seconds)

    @property
    def warmup_steps(self) -> int:
        return int(self.warmup_seconds / self.step_length)

    @property
    def measurement_steps(self) -> int:
        return int(self.measurement_duration_seconds / self.step_length)

    @property
    def total_steps(self) -> int:
        return self.warmup_steps + self.measurement_steps

    @property
    def measurement_start_step(self) -> int:
        return self.warmup_steps

    @property
    def measurement_end_step(self) -> int:
        return self.measurement_start_step + self.measurement_steps

    def is_warmup_step(self, step_index: int) -> bool:
        return step_index < self.measurement_start_step

    def is_measurement_step(self, step_index: int) -> bool:
        return self.measurement_start_step <= step_index < self.measurement_end_step


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


class DemandScheduleWindowConfig(ConfigModel):
    window_id: Annotated[str, Field(min_length=1)]
    begin_seconds: NonNegativeFloat
    end_seconds: PositiveFloat
    description: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        if self.end_seconds <= self.begin_seconds:
            msg = "schedule window end_seconds must be greater than begin_seconds"
            raise ValueError(msg)
        return self


class TurningRatiosConfig(ConfigModel):
    """Probabilidade de cada movimento em cada junção semaforizada.

    Para demanda baseada em ``entries``, essas razões conduzem o gerador de rotas com seed
    (um passeio aleatório de conversões entre junções, de cada entrada de borda até uma saída
    de borda), portanto moldam os movimentos que os veículos de fato realizam. O padrão é a
    distribuição aprovada do protocolo V1 (S1: 0,70 em frente, 0,15 esquerda, 0,15 direita).
    """

    straight: NonNegativeFloat = 0.70
    left: NonNegativeFloat = 0.15
    right: NonNegativeFloat = 0.15

    @model_validator(mode="after")
    def validate_total(self) -> Self:
        total = self.straight + self.left + self.right
        if abs(total - 1.0) > 0.000001:
            msg = "turning ratios must sum to 1.0"
            raise ValueError(msg)
        return self


class EntryDemandConfig(ConfigModel):
    """Demanda injetada em uma aresta de entrada de borda e roteada por razões de conversão.

    ``begin_seconds``/``end_seconds`` são segundos absolutos de simulação (warmup incluído).
    ``turning_ratios`` opcionalmente substitui as razões do nível do cenário para esta entrada.
    ``via_intersection_id`` (um id de interseção do projeto, como ``A5``) faz todo veículo
    desta demanda seguir primeiro um caminho legal mais curto até essa interseção e depois
    continuar com o passeio por razões de conversão; é usado para construir convergência
    deliberada (choque do S3, hotspot do S4).
    ``group`` rotula o papel da demanda (por exemplo ``base``, ``dominant``, ``residual``,
    ``shock``, ``hotspot``) e é registrado nos metadados de rota.
    """

    demand_id: Annotated[str, Field(min_length=1)]
    entry_edge_id: EdgeId
    begin_seconds: NonNegativeFloat
    end_seconds: PositiveFloat
    vehicles_per_hour: VehicleRateByDemandLevel
    turning_ratios: TurningRatiosConfig | None = None
    via_intersection_id: IntersectionId | None = None
    group: Annotated[str, Field(min_length=1)] = "base"

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        if self.end_seconds <= self.begin_seconds:
            msg = "end_seconds must be greater than begin_seconds"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_demand_levels(self) -> Self:
        if set(self.vehicles_per_hour) != {"LOW", "MEDIUM", "HIGH"}:
            msg = "vehicles_per_hour must define LOW, MEDIUM, and HIGH"
            raise ValueError(msg)
        return self

    def rate_for(self, demand_level: DemandLevel) -> float:
        return self.vehicles_per_hour[demand_level]


class TrafficDemandConfig(ConfigModel):
    """Definição da demanda de tráfego.

    Exatamente uma forma de demanda é usada:

    * ``entries``: taxas por entrada de borda roteadas pelas razões de conversão (com seed,
      determinístico). Esta é a forma usada pelos cenários V1.
    * ``flows``: fluxos explícitos de origem/destino roteados pelo ``duarouter`` do SUMO
      (forma legada; as razões de conversão são apenas metadados nesta forma).
    """

    demand_profile: DemandProfileId
    demand_level: DemandLevel
    turning_ratios: TurningRatiosConfig = Field(default_factory=TurningRatiosConfig)
    schedule: tuple[DemandScheduleWindowConfig, ...] = ()
    flows: tuple[FlowDefinitionConfig, ...] = ()
    entries: tuple[EntryDemandConfig, ...] = ()
    shock_start_seconds: PositiveFloat | None = None

    @model_validator(mode="after")
    def validate_demand_form(self) -> Self:
        if bool(self.flows) == bool(self.entries):
            msg = "traffic must define exactly one of flows or entries"
            raise ValueError(msg)
        if self.entries:
            demand_ids = [entry.demand_id for entry in self.entries]
            if len(set(demand_ids)) != len(demand_ids):
                msg = "entries must not contain duplicate demand_id values"
                raise ValueError(msg)
        return self

    @property
    def uses_turning_ratio_routing(self) -> bool:
        return bool(self.entries)


class CommunicationConfig(ConfigModel):
    delay_steps: NonNegativeInt = 0
    drop_probability: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    rng_seed: NonNegativeInt | None = None
    max_message_age_steps: NonNegativeInt = 1

    def resolved_rng_seed(self, simulation_seed: int) -> int:
        if self.rng_seed is not None:
            return int(self.rng_seed)
        return derive_communication_rng_seed(
            simulation_seed=simulation_seed,
            delay_steps=int(self.delay_steps),
            drop_probability=float(self.drop_probability),
        )


class TracingConfig(ConfigModel):
    """Rastreamento opcional para depuração.

    As métricas científicas nunca dependem desses rastros: a telemetria canônica é produzida
    pelo executor da simulação para todo controlador. ``intersection_trace`` reativa o CSV
    legado por movimento produzido pelo controlador (``intersection_trace.csv``), apenas
    para depuração.
    """

    agent_decisions: bool = False
    agents: tuple[IntersectionId, ...] = ()
    intersection_trace: bool = False


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
    simulation: SimulationConfig
    controller_id: ControllerId
    traffic: TrafficDemandConfig
    communication: CommunicationConfig = Field(default_factory=CommunicationConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    intersections: Annotated[tuple[IntersectionConfig, ...], Field(min_length=1)]

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_simulation_fields(cls, payload: object) -> object:
        if not isinstance(payload, dict):
            return payload
        if "simulation" in payload:
            return payload

        legacy_fields = {"duration_seconds", "warmup_seconds", "step_length", "seed"}
        if not legacy_fields.issubset(payload):
            return payload

        migrated: dict[str, Any] = dict(payload)
        migrated["simulation"] = {
            "duration_seconds": migrated.pop("duration_seconds"),
            "warmup_seconds": migrated.pop("warmup_seconds"),
            "step_length": migrated.pop("step_length"),
            "seed": migrated.pop("seed"),
        }
        return migrated

    @model_validator(mode="after")
    def validate_traffic_windows(self) -> Self:
        for flow in self.traffic.flows:
            if flow.end_seconds > self.total_duration_seconds:
                msg = (
                    "traffic flow end_seconds must be lower than or equal to "
                    "total_simulation_duration_seconds"
                )
                raise ValueError(msg)
        for entry in self.traffic.entries:
            if entry.end_seconds > self.total_duration_seconds:
                msg = (
                    "traffic entry end_seconds must be lower than or equal to "
                    "total_simulation_duration_seconds"
                )
                raise ValueError(msg)
        for window in self.traffic.schedule:
            if window.end_seconds > self.total_duration_seconds:
                msg = (
                    "traffic schedule window end_seconds must be lower than or "
                    "equal to total_simulation_duration_seconds"
                )
                raise ValueError(msg)
        return self.validate_shock_definition()

    def validate_shock_definition(self) -> Self:
        shock_start = self.traffic.shock_start_seconds
        if self.traffic.demand_profile == "S3_DEMAND_SHIFT":
            if shock_start is None:
                msg = "S3_DEMAND_SHIFT requires traffic.shock_start_seconds"
                raise ValueError(msg)
            expected = self.warmup_seconds + 0.5 * self.measurement_duration_seconds
            if abs(shock_start - expected) > 1e-6:
                msg = (
                    "S3_DEMAND_SHIFT shock_start_seconds must be at 50% of the measurement "
                    f"window (warmup_seconds + measurement_duration_seconds / 2 = {expected})"
                )
                raise ValueError(msg)
        elif shock_start is not None:
            msg = "traffic.shock_start_seconds is only valid for S3_DEMAND_SHIFT"
            raise ValueError(msg)
        return self

    @property
    def shock_start_step(self) -> int | None:
        shock_start = self.traffic.shock_start_seconds
        return None if shock_start is None else int(shock_start / self.step_length)

    @property
    def shock_start_measurement_offset_seconds(self) -> float | None:
        shock_start = self.traffic.shock_start_seconds
        return None if shock_start is None else float(shock_start - self.warmup_seconds)

    @property
    def duration_seconds(self) -> float:
        return self.simulation.duration_seconds

    @property
    def measurement_duration_seconds(self) -> float:
        return float(self.simulation.measurement_duration_seconds)

    @property
    def total_duration_seconds(self) -> float:
        return self.simulation.total_duration_seconds

    @property
    def warmup_seconds(self) -> float:
        return float(self.simulation.warmup_seconds)

    @property
    def step_length(self) -> float:
        return float(self.simulation.step_length)

    @property
    def seed(self) -> int:
        return int(self.simulation.seed)

    @property
    def measurement_start_step(self) -> int:
        return self.simulation.measurement_start_step

    @property
    def measurement_end_step(self) -> int:
        return self.simulation.measurement_end_step

    @property
    def total_simulation_steps(self) -> int:
        return self.simulation.total_steps

    def is_warmup_step(self, step_index: int) -> bool:
        return self.simulation.is_warmup_step(step_index)

    def is_measurement_step(self, step_index: int) -> bool:
        return self.simulation.is_measurement_step(step_index)

    @property
    def legacy_duration_seconds(self) -> float:
        return self.duration_seconds


def load_scenario_config(path: Path) -> ScenarioConfig:
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    if not isinstance(payload, dict):
        msg = "scenario config must be a YAML mapping"
        raise ValueError(msg)

    return ScenarioConfig.model_validate(payload)


def validate_scenario_config(path: Path) -> ScenarioConfig:
    return load_scenario_config(path)
