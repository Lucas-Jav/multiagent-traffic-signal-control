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
from traffic_agents.experiments.legacy_artifact_hashes import (
    LEGACY_NETWORK_CANONICAL_BY_RAW,
    LEGACY_ROUTE_CANONICAL_BY_RAW,
)
from traffic_agents.experiments.repo_paths import (
    RepositoryPathError,
    resolve_repo_relative,
    resolve_repository_root,
    to_repo_relative_posix,
)
from traffic_agents.experiments.route_artifacts import (
    route_metadata_path,
    validate_route_artifacts,
)
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    json_sha256,
    movement_model_sha256,
    phase_plan_sha256,
    route_generator_config_sha256,
    scenario_turning_config_sha256,
)
from traffic_agents.experiments.text_hashing import (
    CANONICAL_TEXT_SCHEMA,
    HashingError,
    canonical_sha256,
    is_text_path,
    raw_byte_sha256,
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


# Schema 1: raw ``sha256`` only. Schema 2 adds ``raw_byte_sha256`` / ``canonical_sha256`` /
# ``hash_schema`` per text file; the canonical hash (``CANONICAL_TEXT_LF_V1``) is then the
# authoritative, line-ending independent identity. Binary files keep the raw hash only.
# Schema 3 (current) also makes paths repository-portable: ``relative_path`` (POSIX, relative to
# the git top-level) replaces the machine-specific absolute ``path`` / ``scenario_path``.
# Schemas 1 and 2 keep their absolute paths (verified as before, non-portable by construction).
CHECKSUMS_SCHEMA_VERSION = 3
PORTABLE_SCHEMA_MIN_VERSION = 3

# Trusted canonical identities of legacy (schema 1) records, keyed by the RAW hash they recorded.
# Only artifacts whose canonical identity is known from committed content appear here, so a raw
# mismatch is never accepted unconditionally.
_TRUSTED_LEGACY_CANONICAL: Mapping[str, str] = {
    **LEGACY_ROUTE_CANONICAL_BY_RAW,
    **LEGACY_NETWORK_CANONICAL_BY_RAW,
}


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
    repository_root: Path | None = None

    @property
    def schema_version(self) -> int:
        value = self.checksums.get("schema_version", 1)
        return int(value) if isinstance(value, int) else 1

    @property
    def is_portable(self) -> bool:
        return self.schema_version >= PORTABLE_SCHEMA_MIN_VERSION

    @property
    def experiment_config_sha256(self) -> str:
        value = self.checksums.get("experiment_config_sha256")
        if not isinstance(value, str):
            msg = "frozen checksums missing experiment_config_sha256"
            raise ExperimentFreezeError(msg)
        return value

    def validate(self, repository_root: Path | None = None) -> None:
        root = self._root(repository_root)
        for entry in _mapping_entries(self.checksums.get("files")):
            path = _entry_path(entry, root, portable=self.is_portable)
            if not path.exists():
                msg = f"frozen file is missing: {_display_path(entry)}"
                raise ExperimentFreezeError(msg)
            if not _file_matches_entry(path, entry):
                label = _required_string(entry, "label")
                msg = f"frozen checksum mismatch for {label}: {_display_path(entry)}"
                raise ExperimentFreezeError(msg)

        for entry in _mapping_entries(self.checksums.get("derived")):
            actual = _derived_checksum(entry, root, portable=self.is_portable)
            expected = _required_string(entry, "sha256")
            if actual != expected:
                label = _required_string(entry, "label")
                msg = f"frozen checksum mismatch for {label}"
                raise ExperimentFreezeError(msg)

    def _root(self, explicit: Path | None) -> Path | None:
        """Repository root for portable records: explicit, configured, or resolved by git."""

        if not self.is_portable:
            return None
        if explicit is not None:
            return explicit
        if self.repository_root is not None:
            return self.repository_root
        for anchor in (self.freeze_dir, Path.cwd()):
            try:
                return resolve_repository_root(anchor)
            except RepositoryPathError:
                continue
        msg = "cannot resolve the repository root to verify a portable freeze"
        raise ExperimentFreezeError(msg)

    def run_manifest_fields(self) -> dict[str, str]:
        fields = {"experiment_config_sha256": self.experiment_config_sha256}
        canonical = self.checksums.get("experiment_config_canonical_sha256")
        if isinstance(canonical, str):
            fields["experiment_config_canonical_sha256"] = canonical
        return fields


def freeze_experiment_config(
    config_path: Path,
    *,
    final: bool = False,
    artifacts_dir: Path | None = None,
    sumo_info: SumoEnvironmentInfo | None = None,
) -> FreezeResult:
    from traffic_agents.experiments.runner import load_experiment_config

    config_path = config_path.resolve()
    repository_root = _repository_root_for(config_path)
    config = load_experiment_config(config_path)
    experiment_dir = _experiment_dir(config, artifacts_dir)
    if final and experiment_dir.exists():
        msg = (
            f"--final requires a new experiment id; artifact path already exists: {experiment_dir}"
        )
        raise ExperimentFreezeError(msg)

    dirty = is_working_tree_dirty(repository_root)
    if final and dirty:
        msg = "--final freeze requires a clean Git working tree"
        raise ExperimentFreezeError(msg)

    active_sumo_info = sumo_info or detect_sumo_environment()
    freeze_dir = experiment_dir / "frozen"
    freeze_dir.mkdir(parents=True, exist_ok=True)

    frozen_experiment_path = freeze_dir / "experiment.yaml"
    copyfile(config_path, frozen_experiment_path)

    checksums = build_freeze_checksums(
        config=config, config_path=config_path, repository_root=repository_root
    )
    missing_files = _missing_configured_files(checksums)
    if final and missing_files:
        missing = ", ".join(missing_files)
        msg = f"--final freeze requires all configured files to exist: {missing}"
        raise ExperimentFreezeError(msg)

    manifest = {
        "experiment_id": config.experiment_id,
        "frozen_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_sha": _detect_git_sha(repository_root),
        "working_tree_dirty": dirty,
        "sumo_version": active_sumo_info.version,
        "python_version": platform.python_version(),
        "final": final,
        "experiment_config_source": to_repo_relative_posix(config_path, repository_root),
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
    repository_root: Path | None = None,
) -> dict[str, object]:
    root = repository_root or _repository_root_for(config_path)
    scenario_paths = _scenario_paths(config)
    file_entries: list[dict[str, str]] = [
        _file_entry("experiment_config", config_path, root),
    ]
    derived_entries: list[dict[str, str]] = []
    missing_files: list[str] = []

    for scenario_path in scenario_paths:
        scenario_config = load_scenario_config(scenario_path)
        scenario_dir = scenario_path.parent
        validate_route_artifacts(
            scenario_config=scenario_config,
            scenario_dir=scenario_dir,
        )
        file_entries.append(_file_entry("scenario_config", scenario_path, root))

        network_path = scenario_dir / scenario_config.network_file
        network_entry = _optional_file_entry("network_file", network_path, root)
        if network_entry is None:
            missing_files.append(_relative_or_error(network_path, root))
        else:
            file_entries.append(network_entry)

        route_path = scenario_dir / scenario_config.route_file
        route_entry = _optional_file_entry("route_file", route_path, root)
        if route_entry is not None:
            file_entries.append(route_entry)
        else:
            missing_files.append(_relative_or_error(route_path, root))
        metadata_path = route_metadata_path(route_path)
        route_metadata_entry = _optional_file_entry("route_generator_metadata", metadata_path, root)
        if route_metadata_entry is not None:
            file_entries.append(route_metadata_entry)

        traffic_models = load_grid_traffic_models(
            scenario_config=scenario_config,
            scenario_dir=scenario_dir,
        )
        scenario_id = _relative_or_error(scenario_path, root)
        derived_entries.extend(
            [
                {
                    "label": "route_generator_config",
                    "scenario_relative_path": scenario_id,
                    "sha256": route_generator_config_sha256(scenario_config),
                },
                {
                    "label": "phase_plan",
                    "scenario_relative_path": scenario_id,
                    "version": PHASE_PLAN_VERSION,
                    "sha256": phase_plan_sha256(traffic_models),
                },
                {
                    "label": "movement_model_config",
                    "scenario_relative_path": scenario_id,
                    "version": MOVEMENT_MODEL_VERSION,
                    "sha256": movement_model_sha256(traffic_models),
                },
                {
                    "label": "turning_ratio_config",
                    "scenario_relative_path": scenario_id,
                    "sha256": scenario_turning_config_sha256(scenario_config),
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
        "schema_version": CHECKSUMS_SCHEMA_VERSION,
        "hash_schema": CANONICAL_TEXT_SCHEMA,
        "experiment_id": config.experiment_id,
        "experiment_config_sha256": experiment_config_sha256,
        "experiment_config_canonical_sha256": canonical_sha256(config_path.read_bytes()),
        "missing_files": missing_files,
        "files": file_entries,
        "derived": derived_entries,
    }


def load_frozen_experiment_config(
    *,
    config: ExperimentConfig,
    artifacts_dir: Path | None = None,
    repository_root: Path | None = None,
) -> FrozenExperimentConfig | None:
    freeze_dir = _experiment_dir(config, artifacts_dir) / "frozen"
    if not freeze_dir.exists():
        return None
    return load_frozen_experiment_config_from_dir(freeze_dir, repository_root=repository_root)


def load_frozen_experiment_config_from_dir(
    freeze_dir: Path,
    *,
    repository_root: Path | None = None,
) -> FrozenExperimentConfig:
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
        repository_root=repository_root,
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


def _repository_root_for(path: Path) -> Path:
    try:
        return resolve_repository_root(path)
    except RepositoryPathError as exc:
        raise ExperimentFreezeError(str(exc)) from exc


def _relative_or_error(path: Path, repository_root: Path) -> str:
    try:
        return to_repo_relative_posix(path, repository_root)
    except RepositoryPathError as exc:
        raise ExperimentFreezeError(str(exc)) from exc


def _file_entry(label: str, path: Path, repository_root: Path) -> dict[str, str]:
    if not path.exists():
        msg = f"{label} file not found: {path}"
        raise FileNotFoundError(msg)
    data = path.read_bytes()
    raw = raw_byte_sha256(data)
    entry = {
        "label": label,
        "relative_path": _relative_or_error(path, repository_root),
        "sha256": raw,  # legacy key (raw), kept for older readers
        "raw_byte_sha256": raw,
    }
    if is_text_path(path.name):
        entry["canonical_sha256"] = canonical_sha256(data)
        entry["hash_schema"] = CANONICAL_TEXT_SCHEMA
    return entry


def _entry_path(entry: Mapping[str, Any], repository_root: Path | None, *, portable: bool) -> Path:
    """Local file of a record. Portable records resolve inside the repository only."""

    if not portable:
        return Path(_required_string(entry, "path"))
    if "path" in entry or repository_root is None:
        msg = f"portable freeze record must use relative_path only: {sorted(entry)}"
        raise ExperimentFreezeError(msg)
    try:
        return resolve_repo_relative(repository_root, entry.get("relative_path"))
    except RepositoryPathError as exc:
        raise ExperimentFreezeError(str(exc)) from exc


def _display_path(entry: Mapping[str, Any]) -> str:
    return str(entry.get("relative_path") or entry.get("path"))


def _file_matches_entry(path: Path, entry: Mapping[str, Any]) -> bool:
    """Verify a frozen file independent of line endings, never by blind canonical acceptance.

    * schema 2 text entry: the canonical hash recorded in the freeze must match;
    * otherwise (legacy record or binary file): the raw hash must match, or - text only - the file's
      canonical hash must equal the trusted canonical identity known for the recorded raw hash.
    """

    data = path.read_bytes()
    recorded_canonical = entry.get("canonical_sha256")
    try:
        if isinstance(recorded_canonical, str) and recorded_canonical:
            return canonical_sha256(data) == recorded_canonical
        expected_raw = _required_string(entry, "sha256")
        if raw_byte_sha256(data) == expected_raw:
            return True
        if not is_text_path(path.name):
            return False
        trusted = _TRUSTED_LEGACY_CANONICAL.get(expected_raw)
        return trusted is not None and canonical_sha256(data) == trusted
    except HashingError:
        return False


def _optional_file_entry(label: str, path: Path, repository_root: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    return _file_entry(label, path, repository_root)


def _controller_config_sha256(controller_id: str) -> str:
    controller = build_controller(controller_id)
    return json_sha256(controller.manifest_metadata())


def _missing_configured_files(checksums: Mapping[str, object]) -> tuple[str, ...]:
    value = checksums.get("missing_files", [])
    if not isinstance(value, list):
        msg = "missing_files must be a list"
        raise ExperimentFreezeError(msg)
    return tuple(str(item) for item in value)


def _derived_checksum(
    entry: Mapping[str, Any], repository_root: Path | None, *, portable: bool
) -> str:
    label = _required_string(entry, "label")
    if label == "communication_topology":
        return grid_3x3_communication_topology().topology_hash
    if label == "controller_config":
        return _controller_config_sha256(_required_string(entry, "controller_id"))

    if portable:
        if "scenario_path" in entry or repository_root is None:
            msg = "portable freeze record must use scenario_relative_path only"
            raise ExperimentFreezeError(msg)
        try:
            scenario_path = resolve_repo_relative(
                repository_root, entry.get("scenario_relative_path")
            )
        except RepositoryPathError as exc:
            raise ExperimentFreezeError(str(exc)) from exc
    else:
        scenario_path = Path(_required_string(entry, "scenario_path"))
    scenario_config = load_scenario_config(scenario_path)
    if label == "route_generator_config":
        return route_generator_config_sha256(scenario_config)
    if label == "turning_ratio_config":
        return scenario_turning_config_sha256(scenario_config)

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
