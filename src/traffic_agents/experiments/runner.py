from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from traffic_agents.config import CommunicationConfig, get_settings, load_scenario_config
from traffic_agents.simulation import SimulationRunSummary, TraCISimulationRunner

DropProbability = Annotated[float, Field(ge=0.0, le=1.0)]
CommunicationSeedPolicy = Literal["derived_from_simulation_seed_delay_drop", "explicit_rng_seed"]


class ExperimentCommunicationMatrixConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    delay_steps: Annotated[tuple[NonNegativeInt, ...], Field(min_length=1)]
    drop_probability: Annotated[tuple[DropProbability, ...], Field(min_length=1)]


class ExperimentRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: Annotated[str, Field(min_length=1)]
    scenario_base: Annotated[str, Field(min_length=1)]
    scenario: Path
    controller_id: Annotated[str, Field(min_length=1)]
    seed: NonNegativeInt = 42
    max_steps: PositiveInt | None = None
    communication_seed_policy: CommunicationSeedPolicy
    communication: CommunicationConfig


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: Annotated[str, Field(min_length=1)]
    description: str | None = None
    scenario: Path | None = None
    controllers: tuple[str, ...] = ()
    seeds: Annotated[tuple[NonNegativeInt, ...], Field(min_length=1)] = (42,)
    max_steps: PositiveInt | None = None
    matrix: ExperimentCommunicationMatrixConfig | None = None
    runs: tuple[ExperimentRunConfig, ...] = ()

    @model_validator(mode="after")
    def validate_run_shape(self) -> Self:
        if self.runs:
            run_ids = [run.run_id for run in self.runs]
            if len(set(run_ids)) != len(run_ids):
                msg = "runs must not contain duplicate run_id values"
                raise ValueError(msg)
            return self
        if self.scenario is None:
            msg = "scenario is required when runs are not configured"
            raise ValueError(msg)
        if not self.controllers:
            msg = "controllers must contain at least one controller id when runs are not configured"
            raise ValueError(msg)
        if any(not controller_id for controller_id in self.controllers):
            msg = "controllers must not contain empty controller ids"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class ExperimentRunSummary:
    experiment_id: str
    manifest_path: Path
    run_summaries: tuple[SimulationRunSummary, ...]


class ExperimentRunner:
    def __init__(
        self,
        *,
        config: ExperimentConfig,
        artifacts_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._artifacts_dir = artifacts_dir

    def run(self) -> ExperimentRunSummary:
        experiment_dir = self._experiment_dir()
        batch_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        runs_dir = experiment_dir / "runs" / batch_id
        runs_dir.mkdir(parents=True, exist_ok=True)

        summaries: list[SimulationRunSummary] = []
        records: list[tuple[str, ExperimentRunConfig | None, SimulationRunSummary]] = []

        if self._config.runs:
            for run in self._config.runs:
                scenario_config = load_scenario_config(run.scenario)
                run_config = scenario_config.model_copy(
                    update={
                        "controller_id": run.controller_id,
                        "seed": int(run.seed),
                        "communication": run.communication,
                    },
                )
                summary = TraCISimulationRunner(
                    scenario_config=run_config,
                    scenario_dir=run.scenario.parent,
                    max_steps=(
                        run.max_steps if run.max_steps is not None else self._config.max_steps
                    ),
                    controller_id=run.controller_id,
                    artifacts_dir=runs_dir,
                ).run()
                summaries.append(summary)
                records.append((run.run_id, run, summary))
        else:
            assert self._config.scenario is not None
            scenario_config = load_scenario_config(self._config.scenario)
            scenario_dir = self._config.scenario.parent
            for controller_id in self._config.controllers:
                for seed in self._config.seeds:
                    run_config = scenario_config.model_copy(
                        update={"controller_id": controller_id, "seed": int(seed)},
                    )
                    summary = TraCISimulationRunner(
                        scenario_config=run_config,
                        scenario_dir=scenario_dir,
                        max_steps=self._config.max_steps,
                        controller_id=controller_id,
                        artifacts_dir=runs_dir,
                    ).run()
                    summaries.append(summary)
                    records.append((f"{controller_id}_seed_{int(seed)}", None, summary))

        manifest_path = experiment_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                _experiment_manifest_payload(self._config, batch_id, records),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return ExperimentRunSummary(
            experiment_id=self._config.experiment_id,
            manifest_path=manifest_path,
            run_summaries=tuple(summaries),
        )

    def _experiment_dir(self) -> Path:
        artifacts_dir = self._artifacts_dir or get_settings().artifacts_dir
        return artifacts_dir / "experiments" / self._config.experiment_id


def load_experiment_config(path: Path) -> ExperimentConfig:
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)

    if not isinstance(payload, dict):
        msg = "experiment config must be a YAML mapping"
        raise ValueError(msg)

    if "scenario" in payload:
        scenario = Path(payload["scenario"])
        if not scenario.is_absolute():
            payload = payload | {"scenario": path.parent / scenario}
    if "runs" in payload:
        runs = []
        for run_payload in payload["runs"]:
            if not isinstance(run_payload, dict):
                msg = "experiment runs must be YAML mappings"
                raise ValueError(msg)
            run = dict(run_payload)
            if "scenario" in run:
                scenario = Path(run["scenario"])
                if not scenario.is_absolute():
                    run["scenario"] = path.parent / scenario
            runs.append(run)
        payload = payload | {"runs": runs}

    return ExperimentConfig.model_validate(payload)


def _experiment_manifest_payload(
    config: ExperimentConfig,
    batch_id: str,
    records: list[tuple[str, ExperimentRunConfig | None, SimulationRunSummary]],
) -> dict[str, object]:
    return {
        "experiment_id": config.experiment_id,
        "description": config.description,
        "batch_id": batch_id,
        "scenario": config.scenario.as_posix() if config.scenario is not None else None,
        "controllers": list(config.controllers),
        "seeds": [int(seed) for seed in config.seeds],
        "max_steps": config.max_steps,
        "matrix": config.matrix.model_dump(mode="json") if config.matrix is not None else None,
        "runs": [
            {
                "config_run_id": config_run_id,
                "configured_scenario": run_config.scenario.as_posix()
                if run_config is not None
                else None,
                "scenario_base": run_config.scenario_base if run_config is not None else None,
                "configured_controller_id": run_config.controller_id
                if run_config is not None
                else None,
                "configured_communication_seed_policy": run_config.communication_seed_policy
                if run_config is not None
                else None,
                "configured_communication": run_config.communication.model_dump(mode="json")
                if run_config is not None
                else None,
                "run_id": summary.run_id,
                "controller_id": summary.controller_id,
                "controller_version": summary.controller_version,
                "seed": summary.seed,
                "steps_executed": summary.steps_executed,
                "vehicles_departed": summary.vehicles_departed,
                "vehicles_arrived": summary.vehicles_arrived,
                "manifest_path": summary.manifest_path.as_posix()
                if summary.manifest_path is not None
                else None,
            }
            for config_run_id, run_config, summary in records
        ],
    }
