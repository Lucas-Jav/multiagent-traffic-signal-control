from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, Any

from traffic_agents.communication import grid_3x3_communication_topology
from traffic_agents.config import get_settings, load_scenario_config
from traffic_agents.controllers import build_controller
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    json_sha256,
    movement_model_sha256,
    phase_plan_sha256,
    route_generator_config_sha256,
    turning_config_sha256,
)
from traffic_agents.simulation.sumo_environment import (
    SumoEnvironmentInfo,
    detect_sumo_environment,
)
from traffic_agents.simulation.sumo_runner import _detect_git_sha
from traffic_agents.traffic_model import (
    MOVEMENT_MODEL_VERSION,
    PHASE_PLAN_VERSION,
    load_grid_traffic_models,
)

if TYPE_CHECKING:
    from traffic_agents.experiments.runner import ExperimentConfig


class ExperimentFreezeError(ValueError):
    """Raised when an experiment cannot be frozen or no longer matches its freeze."""


@dataclass(frozen=True)
class FreezeResult:
    experiment_id: str
    freeze_dir: Path
    experiment_config_path: Path
    checksums_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class FrozenExperimentConfig:
    experiment_id: str
    freeze_dir: Path
    checksums: Mapping[str, Any]
    manifest: Mapping[str, Any]

    @property
    def experiment_config_sha256(self) -> str:
        value = self.checksums.get("experiment_config_sha256")
        if not isinstance(value, str):
            msg = "frozen checksums missing experiment_config_sha256"
            raise ExperimentFreezeError(msg)
        return value

    def validate(self) -> None:
        for entry in _mapping_entries(self.checksums.get("files")):
            path = Path(_required_string(entry, "path"))
            expected = _required_string(entry, "sha256")
            if not path.exists():
                msg = f"frozen file is missing: {path}"
                raise ExperimentFreezeError(msg)
            actual = file_sha256(path)
            if actual != expected:
                label = _required_string(entry, "label")
                msg = f"frozen checksum mismatch for {label}: {path}"
                raise ExperimentFreezeError(msg)

        for entry in _mapping_entries(self.checksums.get("derived")):
            actual = _derived_checksum(entry)
            expected = _required_string(entry, "sha256")
            if actual != expected:
                label = _required_string(entry, "label")
                msg = f"frozen checksum mismatch for {label}"
                raise ExperimentFreezeError(msg)

    def run_manifest_fields(self) -> dict[str, str]:
        return {
            "experiment_config_sha256": self.experiment_config_sha256,
        }


def freeze_experiment_config(
    config_path: Path,
    *,
    final: bool = False,
    artifacts_dir: Path | None = None,
    sumo_info: SumoEnvironmentInfo | None = None,
) -> FreezeResult:
    from traffic_agents.experiments.runner import load_experiment_config

    config_path = config_path.resolve()
    config = load_experiment_config(config_path)
    experiment_dir = _experiment_dir(config, artifacts_dir)
    if final and experiment_dir.exists():
        msg = (
            "--final requires a new experiment id; "
            f"artifact path already exists: {experiment_dir}"
        )
        raise ExperimentFreezeError(msg)

    dirty = is_working_tree_dirty(Path.cwd())
    if final and dirty:
        msg = "--final freeze requires a clean Git working tree"
        raise ExperimentFreezeError(msg)

    active_sumo_info = sumo_info or detect_sumo_environment()
    freeze_dir = experiment_dir / "frozen"
    freeze_dir.mkdir(parents=True, exist_ok=True)

    frozen_experiment_path = freeze_dir / "experiment.yaml"
    copyfile(config_path, frozen_experiment_path)

    checksums = build_freeze_checksums(config=config, config_path=config_path)
    missing_files = _missing_configured_files(checksums)
    if final and missing_files:
        missing = ", ".join(missing_files)
        msg = f"--final freeze requires all configured files to exist: {missing}"
        raise ExperimentFreezeError(msg)

    manifest = {
        "experiment_id": config.experiment_id,
        "frozen_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_sha": _detect_git_sha(Path.cwd()),
        "working_tree_dirty": dirty,
        "sumo_version": active_sumo_info.version,
        "python_version": platform.python_version(),
        "final": final,
        "experiment_config_source": str(config_path),
        "checksums": checksums,
    }

    checksums_path = freeze_dir / "checksums.json"
    manifest_path = freeze_dir / "freeze_manifest.json"
    checksums_path.write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    return FreezeResult(
        experiment_id=config.experiment_id,
        freeze_dir=freeze_dir,
        experiment_config_path=frozen_experiment_path,
        checksums_path=checksums_path,
        manifest_path=manifest_path,
    )


def build_freeze_checksums(
    *,
    config: ExperimentConfig,
    config_path: Path,
) -> dict[str, object]:
    scenario_paths = _scenario_paths(config)
    file_entries: list[dict[str, str]] = [
        _file_entry("experiment_config", config_path),
    ]
    derived_entries: list[dict[str, str]] = []
    missing_files: list[str] = []

    for scenario_path in scenario_paths:
        scenario_config = load_scenario_config(scenario_path)
        scenario_dir = scenario_path.parent
        file_entries.append(_file_entry("scenario_config", scenario_path))

        network_path = scenario_dir / scenario_config.network_file
        network_entry = _optional_file_entry("network_file", network_path)
        if network_entry is None:
            missing_files.append(str(network_path.resolve()))
        else:
            file_entries.append(network_entry)

        route_path = scenario_dir / scenario_config.route_file
        route_entry = _optional_file_entry("route_file", route_path)
        if route_entry is not None:
            file_entries.append(route_entry)
        else:
            missing_files.append(str(route_path.resolve()))
        route_metadata_path = _route_metadata_path(route_path)
        route_metadata_entry = _optional_file_entry("route_generator_metadata", route_metadata_path)
        if route_metadata_entry is not None:
            file_entries.append(route_metadata_entry)

        traffic_models = load_grid_traffic_models(
            scenario_config=scenario_config,
            scenario_dir=scenario_dir,
        )
        turning_ratios = {
            key: float(value)
            for key, value in scenario_config.traffic.turning_ratios.model_dump().items()
        }
        scenario_id = scenario_path.as_posix()
        derived_entries.extend(
            [
                {
                    "label": "route_generator_config",
                    "scenario_path": scenario_id,
                    "sha256": route_generator_config_sha256(scenario_config),
                },
                {
                    "label": "phase_plan",
                    "scenario_path": scenario_id,
                    "version": PHASE_PLAN_VERSION,
                    "sha256": phase_plan_sha256(traffic_models),
                },
                {
                    "label": "movement_model_config",
                    "scenario_path": scenario_id,
                    "version": MOVEMENT_MODEL_VERSION,
                    "sha256": movement_model_sha256(traffic_models),
                },
                {
                    "label": "turning_ratio_config",
                    "scenario_path": scenario_id,
                    "sha256": turning_config_sha256(turning_ratios),
                },
            ]
        )

    derived_entries.append(
        {
            "label": "communication_topology",
            "topology_id": "grid_3x3",
            "sha256": grid_3x3_communication_topology().topology_hash,
        }
    )
    for controller_id in _controller_ids(config):
        derived_entries.append(
            {
                "label": "controller_config",
                "controller_id": controller_id,
                "sha256": _controller_config_sha256(controller_id),
            }
        )

    experiment_config_sha256 = file_sha256(config_path)
    return {
        "experiment_id": config.experiment_id,
        "experiment_config_sha256": experiment_config_sha256,
        "missing_files": missing_files,
        "files": file_entries,
        "derived": derived_entries,
    }


def load_frozen_experiment_config(
    *,
    config: ExperimentConfig,
    artifacts_dir: Path | None = None,
) -> FrozenExperimentConfig | None:
    freeze_dir = _experiment_dir(config, artifacts_dir) / "frozen"
    if not freeze_dir.exists():
        return None
    return load_frozen_experiment_config_from_dir(freeze_dir)


def load_frozen_experiment_config_from_dir(freeze_dir: Path) -> FrozenExperimentConfig:
    checksums_path = freeze_dir / "checksums.json"
    manifest_path = freeze_dir / "freeze_manifest.json"
    if not checksums_path.exists() or not manifest_path.exists():
        msg = f"incomplete frozen experiment directory: {freeze_dir}"
        raise ExperimentFreezeError(msg)

    checksums = _read_json_mapping(checksums_path)
    manifest = _read_json_mapping(manifest_path)
    experiment_id = _required_string(checksums, "experiment_id")
    return FrozenExperimentConfig(
        experiment_id=experiment_id,
        freeze_dir=freeze_dir,
        checksums=checksums,
        manifest=manifest,
    )


def is_working_tree_dirty(repo_path: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return True
    return bool(completed.stdout.strip())


def _experiment_dir(config: ExperimentConfig, artifacts_dir: Path | None) -> Path:
    base_dir = artifacts_dir or get_settings().artifacts_dir
    return base_dir / "experiments" / config.experiment_id


def _scenario_paths(config: ExperimentConfig) -> tuple[Path, ...]:
    paths: list[Path] = []
    if config.scenario is not None:
        paths.append(config.scenario)
    paths.extend(run.scenario for run in config.runs)
    return tuple(dict.fromkeys(path.resolve() for path in paths))


def _controller_ids(config: ExperimentConfig) -> tuple[str, ...]:
    controller_ids = list(config.controllers)
    controller_ids.extend(run.controller_id for run in config.runs)
    return tuple(dict.fromkeys(controller_ids))


def _file_entry(label: str, path: Path) -> dict[str, str]:
    if not path.exists():
        msg = f"{label} file not found: {path}"
        raise FileNotFoundError(msg)
    return {
        "label": label,
        "path": str(path.resolve()),
        "sha256": file_sha256(path),
    }


def _optional_file_entry(label: str, path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    return _file_entry(label, path)


def _route_metadata_path(route_path: Path) -> Path:
    if route_path.name.endswith(".rou.xml"):
        return route_path.with_name(route_path.name.replace(".rou.xml", ".metadata.json"))
    return route_path.with_suffix(".metadata.json")


def _controller_config_sha256(controller_id: str) -> str:
    controller = build_controller(controller_id)
    return json_sha256(controller.manifest_metadata())


def _missing_configured_files(checksums: Mapping[str, object]) -> tuple[str, ...]:
    value = checksums.get("missing_files", [])
    if not isinstance(value, list):
        msg = "missing_files must be a list"
        raise ExperimentFreezeError(msg)
    return tuple(str(item) for item in value)


def _derived_checksum(entry: Mapping[str, Any]) -> str:
    label = _required_string(entry, "label")
    if label == "communication_topology":
        return grid_3x3_communication_topology().topology_hash
    if label == "controller_config":
        return _controller_config_sha256(_required_string(entry, "controller_id"))

    scenario_path = Path(_required_string(entry, "scenario_path"))
    scenario_config = load_scenario_config(scenario_path)
    if label == "route_generator_config":
        return route_generator_config_sha256(scenario_config)
    if label == "turning_ratio_config":
        turning_ratios = {
            key: float(value)
            for key, value in scenario_config.traffic.turning_ratios.model_dump().items()
        }
        return turning_config_sha256(turning_ratios)

    traffic_models = load_grid_traffic_models(
        scenario_config=scenario_config,
        scenario_dir=scenario_path.parent,
    )
    if label == "phase_plan":
        return phase_plan_sha256(traffic_models)
    if label == "movement_model_config":
        return movement_model_sha256(traffic_models)

    msg = f"unsupported frozen derived checksum: {label}"
    raise ExperimentFreezeError(msg)


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"expected JSON object: {path}"
        raise ExperimentFreezeError(msg)
    return payload


def _mapping_entries(value: object) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, list):
        msg = "frozen checksums entries must be lists"
        raise ExperimentFreezeError(msg)
    for entry in value:
        if not isinstance(entry, dict):
            msg = "frozen checksum entry must be an object"
            raise ExperimentFreezeError(msg)
        yield entry


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        msg = f"missing required frozen field: {field}"
        raise ExperimentFreezeError(msg)
    return value
