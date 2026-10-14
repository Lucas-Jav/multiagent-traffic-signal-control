"""Experiment freezes identify files by repository-relative POSIX paths (location independent)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
from test_experiment_freeze import _sumo_info, _write_experiment_fixture

import traffic_agents.experiments.freeze as freeze
from traffic_agents.experiments.freeze import (
    ExperimentFreezeError,
    FrozenExperimentConfig,
    freeze_experiment_config,
    load_frozen_experiment_config_from_dir,
)
from traffic_agents.experiments.repo_paths import (
    RepositoryPathError,
    absolute_paths_in,
    resolve_repo_relative,
    resolve_repository_root,
    to_repo_relative_posix,
    validate_relative_posix,
)
from traffic_agents.experiments.runner import load_experiment_config

REPO = Path(__file__).resolve().parents[1]
FINAL_CONFIGS = {
    "final_main": REPO / "experiments" / "configs" / "final_main.yaml",
    "final_s5_packet_loss": REPO / "experiments" / "configs" / "final_s5_packet_loss.yaml",
}


def _to_crlf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))


def _to_lf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _freeze(root: Path) -> Path:
    config_path = _write_experiment_fixture(root)
    result = freeze_experiment_config(
        config_path, artifacts_dir=root / "artifacts", sumo_info=_sumo_info(root)
    )
    return result.freeze_dir


def _text_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts and path.suffix in {".yaml", ".xml", ".json"}
    ]


# --- path policy ---------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad",
    [
        "",
        "/etc/passwd",
        "C:/Users/x/file.yaml",
        "C:\\Users\\x\\file.yaml",
        "c:relative.yaml",
        "\\\\server\\share\\file.yaml",
        "//server/share/file.yaml",
        "../outside.yaml",
        "experiments/../../outside.yaml",
        "experiments/./final_main.yaml",
        "experiments//final_main.yaml",
        "experiments\\configs\\final_main.yaml",
        "experiments/configs/",
        "a\x00b",
    ],
)
def test_unsafe_relative_paths_are_rejected(bad: str) -> None:
    with pytest.raises(RepositoryPathError):
        validate_relative_posix(bad)


def test_non_string_paths_are_rejected() -> None:
    for bad in (None, 7, ["a"]):
        with pytest.raises(RepositoryPathError):
            validate_relative_posix(bad)


def test_safe_relative_path_is_accepted() -> None:
    assert validate_relative_posix("experiments/configs/final_main.yaml") == PurePosixPath(
        "experiments/configs/final_main.yaml"
    )


def test_windows_paths_serialize_as_forward_slash_relative_paths() -> None:
    windows_root = PureWindowsPath(r"C:\projetos\repo")
    windows_file = PureWindowsPath(r"C:\projetos\repo\experiments\configs\final_main.yaml")
    serialized = windows_file.relative_to(windows_root).as_posix()
    assert serialized == "experiments/configs/final_main.yaml"
    assert "\\" not in serialized
    validate_relative_posix(serialized)


def test_local_paths_serialize_without_backslashes(tmp_path: Path) -> None:
    nested = tmp_path / "experiments" / "configs"
    nested.mkdir(parents=True)
    target = nested / "x.yaml"
    target.write_text("a: 1\n", encoding="utf-8")
    assert to_repo_relative_posix(target, tmp_path) == "experiments/configs/x.yaml"


def test_path_outside_the_repository_cannot_be_serialized(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("a: 1\n", encoding="utf-8")
    with pytest.raises(RepositoryPathError, match="outside the repository"):
        to_repo_relative_posix(outside, repo)


def test_symlink_escaping_the_repository_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    secret = tmp_path / "secret.yaml"
    secret.write_text("a: 1\n", encoding="utf-8")
    link = repo / "link.yaml"
    try:
        os.symlink(secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this system")
    with pytest.raises(RepositoryPathError, match="escapes"):
        resolve_repo_relative(repo, "link.yaml")


def test_absolute_path_scanner() -> None:
    assert absolute_paths_in({"a": ["x/y", {"b": "C:\\x"}], "c": "/etc", "d": "\\\\h\\s"}) == [
        "/a[1]/b: C:\\x",
        "/c: /etc",
        "/d: \\\\h\\s",
    ]
    assert absolute_paths_in({"a": "experiments/configs/x.yaml", "sha": "ab" * 32}) == []


# --- portable freeze records ---------------------------------------------------------------------
def test_new_freeze_contains_no_absolute_paths(tmp_path: Path) -> None:
    freeze_dir = _freeze(tmp_path)
    for name in ("checksums.json", "freeze_manifest.json"):
        payload = json.loads((freeze_dir / name).read_text(encoding="utf-8"))
        assert absolute_paths_in(payload) == [], name
    checksums = json.loads((freeze_dir / "checksums.json").read_text(encoding="utf-8"))
    assert checksums["schema_version"] == 3
    for entry in checksums["files"]:
        assert "path" not in entry
        validate_relative_posix(entry["relative_path"])
        assert (tmp_path / entry["relative_path"]).exists()
    for entry in checksums["derived"]:
        assert "scenario_path" not in entry
    text = (freeze_dir / "checksums.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in text and tmp_path.as_posix() not in text


def test_freeze_verifies_after_the_repository_is_moved(tmp_path: Path) -> None:
    repo_a = tmp_path / "location_a"
    repo_a.mkdir()
    freeze_dir_a = _freeze(repo_a)
    load_frozen_experiment_config_from_dir(freeze_dir_a).validate()

    repo_b = tmp_path / "somewhere" / "else" / "entirely" / "location_b"
    repo_b.parent.mkdir(parents=True)
    shutil.copytree(repo_a, repo_b)
    shutil.rmtree(repo_a)  # the original location no longer exists
    freeze_dir_b = repo_b / freeze_dir_a.relative_to(repo_a)
    assert resolve_repository_root(freeze_dir_b) == repo_b.resolve()
    load_frozen_experiment_config_from_dir(freeze_dir_b).validate()


@pytest.mark.parametrize("convert", [_to_crlf, _to_lf], ids=["to-crlf", "to-lf"])
def test_moved_repository_with_line_ending_change_verifies(tmp_path: Path, convert: object) -> None:
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    freeze_dir_a = _freeze(repo_a)
    repo_b = tmp_path / "b" / "deeper"
    repo_b.parent.mkdir()
    shutil.copytree(repo_a, repo_b)
    for path in _text_files(repo_b):
        if "artifacts" not in path.parts:  # the frozen inputs, not the freeze record itself
            convert(path)  # type: ignore[operator]
    load_frozen_experiment_config_from_dir(repo_b / freeze_dir_a.relative_to(repo_a)).validate()


def test_moved_repository_still_rejects_a_real_content_change(tmp_path: Path) -> None:
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    freeze_dir_a = _freeze(repo_a)
    repo_b = tmp_path / "b"
    shutil.copytree(repo_a, repo_b)
    config_b = repo_b / "experiment.yaml"
    for path in _text_files(repo_b):
        if "artifacts" not in path.parts:
            _to_crlf(path)
    assert config_b.exists()
    config_b.write_text(config_b.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    with pytest.raises(ExperimentFreezeError, match="experiment_config"):
        load_frozen_experiment_config_from_dir(repo_b / freeze_dir_a.relative_to(repo_a)).validate()


def test_a_cloned_repository_verifies(tmp_path: Path) -> None:
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    freeze_dir_a = _freeze(repo_a)
    env = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(repo_a)]
    subprocess.run([*env, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*env, "commit", "-q", "-m", "freeze"], check=True, capture_output=True)
    repo_b = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(repo_a), str(repo_b)], check=True)
    load_frozen_experiment_config_from_dir(repo_b / freeze_dir_a.relative_to(repo_a)).validate()


# --- repository root resolution ------------------------------------------------------------------
def test_freeze_and_verification_work_from_a_subdirectory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _write_experiment_fixture(tmp_path)
    subdir = tmp_path / "scenario"
    monkeypatch.chdir(subdir)
    assert resolve_repository_root(Path.cwd()) == tmp_path.resolve()
    result = freeze_experiment_config(
        config_path, artifacts_dir=tmp_path / "artifacts", sumo_info=_sumo_info(tmp_path)
    )
    checksums = json.loads(result.checksums_path.read_text(encoding="utf-8"))
    assert {e["relative_path"] for e in checksums["files"]} >= {
        "experiment.yaml",
        "scenario/network.net.xml",
    }
    load_frozen_experiment_config_from_dir(result.freeze_dir).validate()


def test_verification_from_an_unrelated_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    freeze_dir = _freeze(repo)
    elsewhere = tmp_path / "unrelated"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    load_frozen_experiment_config_from_dir(freeze_dir).validate()


def test_freeze_outside_a_git_repository_is_refused(tmp_path: Path) -> None:
    config = tmp_path / "experiment.yaml"
    config.write_text("experiment_id: x\n", encoding="utf-8")
    with pytest.raises(ExperimentFreezeError, match="not inside a git repository"):
        freeze._repository_root_for(config)


# --- hostile records -----------------------------------------------------------------------------
def _portable(entry: dict[str, str], root: Path) -> FrozenExperimentConfig:
    return FrozenExperimentConfig(
        experiment_id="t",
        freeze_dir=root,
        checksums={"schema_version": 3, "files": [entry], "derived": []},
        manifest={},
        repository_root=root,
    )


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.yaml",
        "a/../../outside.yaml",
        "/etc/passwd",
        "C:/Windows/win.ini",
        "C:\\Windows\\win.ini",
        "\\\\server\\share\\x.yaml",
        "//server/share/x.yaml",
        "sub\\file.yaml",
    ],
)
def test_crafted_portable_record_cannot_read_outside_the_repository(
    tmp_path: Path, bad_path: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "outside.yaml").write_text("a: 1\n", encoding="utf-8")
    entry = {"label": "experiment_config", "relative_path": bad_path, "sha256": "0" * 64}
    with pytest.raises(ExperimentFreezeError):
        _portable(entry, repo).validate()


def test_portable_schema_rejects_an_absolute_path_field(tmp_path: Path) -> None:
    target = tmp_path / "a.yaml"
    target.write_text("a: 1\n", encoding="utf-8")
    entry = freeze._file_entry("experiment_config", target, tmp_path)
    entry["path"] = str(target)
    with pytest.raises(ExperimentFreezeError, match="relative_path only"):
        _portable(entry, tmp_path).validate()


def test_scientific_input_outside_the_repository_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("a: 1\n", encoding="utf-8")
    with pytest.raises(ExperimentFreezeError, match="outside the repository"):
        freeze._file_entry("experiment_config", outside, repo)


# --- legacy absolute-path records still verify (not portable by construction) ---------------
def test_legacy_absolute_path_records_are_still_verified(tmp_path: Path) -> None:
    target = tmp_path / "a.yaml"
    target.write_text("a: 1\n", encoding="utf-8")
    from traffic_agents.experiments.text_hashing import canonical_sha256, raw_byte_sha256

    data = target.read_bytes()
    schema1 = {"label": "x", "path": str(target), "sha256": raw_byte_sha256(data)}
    schema2 = schema1 | {"canonical_sha256": canonical_sha256(data)}
    for entry, schema in ((schema1, None), (schema2, 2)):
        checksums: dict[str, object] = {"files": [entry], "derived": []}
        if schema:
            checksums["schema_version"] = schema
        FrozenExperimentConfig("t", Path("."), checksums, {}).validate()
    target.write_text("a: 2\n", encoding="utf-8")
    with pytest.raises(ExperimentFreezeError):
        FrozenExperimentConfig("t", Path("."), {"files": [schema1], "derived": []}, {}).validate()


def test_legacy_record_that_is_missing_keeps_failing(tmp_path: Path) -> None:
    entry = {"label": "x", "path": str(tmp_path / "gone.yaml"), "sha256": "0" * 64}
    with pytest.raises(ExperimentFreezeError, match="missing"):
        FrozenExperimentConfig("t", Path("."), {"files": [entry], "derived": []}, {}).validate()


# --- the real final campaign configs -------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(FINAL_CONFIGS))
def test_final_campaign_freeze_is_portable(name: str) -> None:
    config_path = FINAL_CONFIGS[name]
    config = load_experiment_config(config_path)
    checksums = freeze.build_freeze_checksums(config=config, config_path=config_path)
    new_freeze_contains_absolute_paths = bool(absolute_paths_in(checksums))
    assert new_freeze_contains_absolute_paths is False
    assert checksums["schema_version"] == 3
    root = resolve_repository_root(REPO)
    files = checksums["files"]
    assert isinstance(files, list) and files
    for entry in files:
        assert "path" not in entry
        assert resolve_repo_relative(root, entry["relative_path"]).is_file()
    assert any(entry["relative_path"].startswith("experiments/configs/") for entry in files)
    # every scientific input of the final campaign lives inside the repository
    assert not checksums["missing_files"]
    FrozenExperimentConfig(name, REPO, checksums, {}, repository_root=root).validate()


@pytest.mark.parametrize("name", sorted(FINAL_CONFIGS))
@pytest.mark.parametrize("convert", [_to_crlf, _to_lf], ids=["crlf", "lf"])
def test_final_config_entry_verifies_in_another_location_and_rejects_changes(
    name: str, convert: object, tmp_path: Path
) -> None:
    config_path = FINAL_CONFIGS[name]
    original_root = resolve_repository_root(REPO)
    entry = freeze._file_entry("experiment_config", config_path, original_root)
    relative = entry["relative_path"]
    assert relative == f"experiments/configs/{config_path.name}"

    elsewhere = tmp_path / "moved" / "copy"
    target = elsewhere / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(config_path, target)
    convert(target)  # type: ignore[operator]
    _portable(entry, elsewhere).validate()

    target.write_bytes(target.read_bytes().replace(b"seed: 42", b"seed: 43", 1))
    with pytest.raises(ExperimentFreezeError, match="experiment_config"):
        _portable(entry, elsewhere).validate()
