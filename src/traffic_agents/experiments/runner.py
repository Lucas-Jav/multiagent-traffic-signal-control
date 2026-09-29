from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from traffic_agents.config import CommunicationConfig, get_settings, load_scenario_config
from traffic_agents.experiments.freeze import FrozenExperimentConfig
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
        frozen_config: FrozenExperimentConfig | None = None,
        resume: bool = False,
        retry_failed: bool = False,
    ) -> None:
        self._config = config
        self._artifacts_dir = artifacts_dir
        self._frozen_config = frozen_config
        self._resume = resume
        self._retry_failed = retry_failed

    def run(self) -> ExperimentRunSummary:
        if self._frozen_config is not None:
            self._frozen_config.validate()

        experiment_dir = self._experiment_dir()
        experiment_dir.mkdir(parents=True, exist_ok=True)
        status_path = experiment_dir / "run_status.jsonl"
        if self._resume:
            _mark_interrupted_running_statuses(status_path)
        latest_statuses = _latest_statuses(status_path) if self._resume else {}

        batch_id = _unique_id()
        runs_dir = experiment_dir / "runs" / batch_id
        runs_dir.mkdir(parents=True, exist_ok=False)

        summaries: list[SimulationRunSummary] = []
        records: list[dict[str, object]] = []

        for spec in self._iter_run_specs():
            previous = latest_statuses.get(spec["run_key"])
            if previous is not None and previous.get("status") == "COMPLETED":
                records.append(previous)
                continue
            if (
                previous is not None
                and previous.get("status") == "FAILED"
                and not self._retry_failed
            ):
                records.append(previous)
                continue

            run_id = _run_id_for_spec(spec)
            started_at = _utc_now()
            running_record = _status_record(
                spec,
                run_id=run_id,
                status="RUNNING",
                started_at=started_at,
                finished_at=None,
                artifact_path=(runs_dir / run_id).as_posix(),
            )
            _append_status(status_path, running_record)
            try:
                summary = TraCISimulationRunner(
                    scenario_config=spec["scenario_config"],
                    scenario_dir=spec["scenario_path"].parent,
                    max_steps=spec["max_steps"],
                    controller_id=spec["controller_id"],
                    artifacts_dir=runs_dir,
                    run_mode="EXPERIMENT",
                    run_manifest_extra=self._run_manifest_extra(),
                    run_id=run_id,
                ).run()
            except Exception as exc:
                failed_record = _status_record(
                    spec,
                    run_id=run_id,
                    status="FAILED",
                    started_at=started_at,
                    finished_at=_utc_now(),
                    artifact_path=(runs_dir / run_id).as_posix(),
                    failure_type=type(exc).__name__,
                    failure_message=str(exc),
                )
                _append_status(status_path, failed_record)
                records.append(failed_record)
                continue

            completed_record = _status_record(
                spec,
                run_id=summary.run_id,
                status="COMPLETED",
                started_at=summary.started_at,
                finished_at=summary.ended_at,
                artifact_path=summary.manifest_path.parent.as_posix()
                if summary.manifest_path is not None
                else None,
                summary=summary,
            )
            _append_status(status_path, completed_record)
            summaries.append(summary)
            records.append(completed_record)

        manifest_path = experiment_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                _experiment_manifest_payload(self._config, batch_id, records, status_path),
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

    def _run_manifest_extra(self) -> dict[str, object]:
        if self._frozen_config is None:
            return {}
        return dict(self._frozen_config.run_manifest_fields())

    def _iter_run_specs(self) -> tuple[dict[str, Any], ...]:
        specs: list[dict[str, Any]] = []
        if self._config.runs:
            for run in self._config.runs:
                scenario_config = load_scenario_config(run.scenario)
                run_config = scenario_config.model_copy(
                    update={
                        "controller_id": run.controller_id,
                        "simulation": scenario_config.simulation.model_copy(
                            update={"seed": int(run.seed)}
                        ),
                        "communication": run.communication,
                    },
                )
                specs.append(
                    {
                        "config_run_id": run.run_id,
                        "scenario_base": run.scenario_base,
                        "scenario_path": run.scenario,
                        "scenario_config": run_config,
                        "controller_id": run.controller_id,
                        "seed": int(run.seed),
                        "max_steps": (
                            run.max_steps if run.max_steps is not None else self._config.max_steps
                        ),
                        "run_config": run,
                        "run_key": f"{run.scenario}:{run.seed}:{run.controller_id}",
                    }
                )
            return tuple(specs)

        assert self._config.scenario is not None
        scenario_config = load_scenario_config(self._config.scenario)
        for controller_id in self._config.controllers:
            for seed in self._config.seeds:
                run_config = scenario_config.model_copy(
                    update={
                        "controller_id": controller_id,
                        "simulation": scenario_config.simulation.model_copy(
                            update={"seed": int(seed)}
                        ),
                    },
                )
                specs.append(
                    {
                        "config_run_id": f"{controller_id}_seed_{int(seed)}",
                        "scenario_base": scenario_config.traffic.demand_profile,
                        "scenario_path": self._config.scenario,
                        "scenario_config": run_config,
                        "controller_id": controller_id,
                        "seed": int(seed),
                        "max_steps": self._config.max_steps,
                        "run_config": None,
                        "run_key": f"{self._config.scenario}:{int(seed)}:{controller_id}",
                    }
                )
        return tuple(specs)


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
    records: list[dict[str, object]],
    status_path: Path,
) -> dict[str, object]:
    completed_count = sum(1 for record in records if record.get("status") == "COMPLETED")
    failed_count = sum(1 for record in records if record.get("status") == "FAILED")
    return {
        "experiment_id": config.experiment_id,
        "description": config.description,
        "batch_id": batch_id,
        "scenario": config.scenario.as_posix() if config.scenario is not None else None,
        "controllers": list(config.controllers),
        "seeds": [int(seed) for seed in config.seeds],
        "max_steps": config.max_steps,
        "matrix": config.matrix.model_dump(mode="json") if config.matrix is not None else None,
        "run_status_file": status_path.as_posix(),
        "completed_count": completed_count,
        "failed_count": failed_count,
        "pending_count": 0,
        "runs": records,
    }


def _status_record(
    spec: dict[str, Any],
    *,
    run_id: str,
    status: Literal["RUNNING", "COMPLETED", "FAILED", "INTERRUPTED"],
    started_at: str | None,
    finished_at: str | None,
    artifact_path: str | None,
    failure_type: str | None = None,
    failure_message: str | None = None,
    summary: SimulationRunSummary | None = None,
) -> dict[str, object]:
    run_config = spec.get("run_config")
    record: dict[str, object] = {
        "run_key": spec["run_key"],
        "config_run_id": spec["config_run_id"],
        "run_id": run_id,
        "scenario_id": spec["scenario_config"].scenario_id,
        "scenario_base": spec["scenario_base"],
        "configured_scenario": spec["scenario_path"].as_posix(),
        "controller_id": spec["controller_id"],
        "configured_controller_id": spec["controller_id"],
        "seed": spec["seed"],
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "artifact_path": artifact_path,
        "failure_type": failure_type,
        "failure_message": failure_message,
    }
    if isinstance(run_config, ExperimentRunConfig):
        record["configured_communication_seed_policy"] = run_config.communication_seed_policy
        record["configured_communication"] = run_config.communication.model_dump(mode="json")
    else:
        record["configured_communication_seed_policy"] = None
        record["configured_communication"] = None
    if summary is not None:
        record.update(
            {
                "controller_version": summary.controller_version,
                "steps_executed": summary.steps_executed,
                "vehicles_departed": summary.vehicles_departed,
                "vehicles_arrived": summary.vehicles_arrived,
                "manifest_path": summary.manifest_path.as_posix()
                if summary.manifest_path is not None
                else None,
            }
        )
    return record


def _append_status(path: Path, record: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")


def _latest_statuses(path: Path) -> dict[object, dict[str, object]]:
    if not path.exists():
        return {}
    latest: dict[object, dict[str, object]] = {}
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                latest[payload.get("run_key")] = payload
    return latest


def _mark_interrupted_running_statuses(path: Path) -> None:
    for record in tuple(_latest_statuses(path).values()):
        if record.get("status") != "RUNNING":
            continue
        interrupted = dict(record)
        interrupted["status"] = "INTERRUPTED"
        interrupted["finished_at"] = _utc_now()
        interrupted["failure_type"] = "InterruptedPreviousRun"
        interrupted["failure_message"] = "Previous process left this run in RUNNING state."
        _append_status(path, interrupted)


def _run_id_for_spec(spec: Mapping[str, Any]) -> str:
    scenario_config = spec["scenario_config"]
    return (
        f"{_unique_id()}_{scenario_config.scenario_id}_{spec['controller_id']}_"
        f"{scenario_config.traffic.demand_profile}_seed_{spec['seed']}"
    )


def _unique_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S_%fZ')}_{uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
