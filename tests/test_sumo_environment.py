from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from traffic_agents.simulation.sumo_environment import (
    EXPECTED_SUMO_VERSION,
    SumoNotFoundError,
    UnsupportedSumoVersionError,
    detect_sumo_environment,
)


def create_fake_sumo_home(tmp_path: Path) -> Path:
    sumo_home = tmp_path / "sumo"
    bin_dir = sumo_home / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "sumo.exe").write_text("", encoding="utf-8")
    (bin_dir / "sumo-gui.exe").write_text("", encoding="utf-8")
    return sumo_home


def mock_sumo_version(monkeypatch: pytest.MonkeyPatch, output: str) -> None:
    def run(
        args: list[str],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert args[1] == "--version"
        assert capture_output is True
        assert check is False
        assert text is True
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", run)


def test_detect_sumo_environment_from_sumo_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = create_fake_sumo_home(tmp_path)
    mock_sumo_version(monkeypatch, f"Eclipse SUMO Version {EXPECTED_SUMO_VERSION}\n")

    info = detect_sumo_environment(environ={"SUMO_HOME": str(sumo_home)})

    assert info.sumo_home == sumo_home
    assert info.sumo_binary == sumo_home / "bin" / "sumo.exe"
    assert info.sumo_gui_binary == sumo_home / "bin" / "sumo-gui.exe"
    assert info.version == EXPECTED_SUMO_VERSION


def test_detect_sumo_environment_from_common_windows_install_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = create_fake_sumo_home(tmp_path / "Program Files (x86)" / "Eclipse")
    mock_sumo_version(monkeypatch, f"Eclipse SUMO Version {EXPECTED_SUMO_VERSION}\n")
    monkeypatch.setattr("shutil.which", lambda _binary_name: None)

    info = detect_sumo_environment(
        environ={"ProgramFiles(x86)": str(tmp_path / "Program Files (x86)")},
    )

    assert info.sumo_home == sumo_home
    assert info.sumo_binary == sumo_home / "bin" / "sumo.exe"


def test_detect_sumo_environment_rejects_unsupported_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = create_fake_sumo_home(tmp_path)
    mock_sumo_version(monkeypatch, "Eclipse SUMO Version 1.26.0\n")

    with pytest.raises(UnsupportedSumoVersionError, match=r"expected 1\.27\.1, found 1\.26\.0"):
        detect_sumo_environment(environ={"SUMO_HOME": str(sumo_home)})


def test_detect_sumo_environment_requires_sumo_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = tmp_path / "sumo"
    (sumo_home / "bin").mkdir(parents=True)
    (sumo_home / "bin" / "sumo-gui.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda _binary_name: None)

    with pytest.raises(SumoNotFoundError, match="sumo"):
        detect_sumo_environment(environ={"SUMO_HOME": str(sumo_home)})


def test_detect_sumo_environment_requires_sumo_gui_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = tmp_path / "sumo"
    (sumo_home / "bin").mkdir(parents=True)
    (sumo_home / "bin" / "sumo.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda _binary_name: None)

    with pytest.raises(SumoNotFoundError, match="sumo-gui"):
        detect_sumo_environment(environ={"SUMO_HOME": str(sumo_home)})


def test_detect_sumo_environment_wraps_subprocess_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = create_fake_sumo_home(tmp_path)

    def run(
        args: list[str],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(SumoNotFoundError, match="Unable to read SUMO version"):
        detect_sumo_environment(environ={"SUMO_HOME": str(sumo_home)})
