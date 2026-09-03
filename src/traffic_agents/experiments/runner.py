from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from traffic_agents.config import get_settings, load_scenario_config
from traffic_agents.simulation import SimulationRunSummary, TraCISimulationRunner


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: Annotated[str, Field(min_length=1)]
    scenario: Path
    controllers: Annotated[tuple[str, ...], Field(min_length=1)]
    seeds: Annotated[tuple[NonNegativeInt, ...], Field(min_length=1)] = (42,)
    max_steps: PositiveInt | None = None

    @model_validator(mode="after")
    def validate_controllers(self) -> Self:
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

        scenario_config = load_scenario_config(self._config.scenario)
        scenario_dir = self._config.scenario.parent
        summaries: list[SimulationRunSummary] = []

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

        manifest_path = experiment_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                _experiment_manifest_payload(self._config, batch_id, summaries),
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

    return ExperimentConfig.model_validate(payload)


def _experiment_manifest_payload(
    config: ExperimentConfig,
    batch_id: str,
    summaries: list[SimulationRunSummary],
) -> dict[str, object]:
    return {
        "experiment_id": config.experiment_id,
        "batch_id": batch_id,
        "scenario": config.scenario.as_posix(),
        "controllers": list(config.controllers),
        "seeds": [int(seed) for seed in config.seeds],
        "max_steps": config.max_steps,
        "runs": [
            {
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
            for summary in summaries
        ],
    }
