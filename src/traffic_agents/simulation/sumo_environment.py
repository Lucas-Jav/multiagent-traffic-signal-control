from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

EXPECTED_SUMO_VERSION = "1.27.1"
_VERSION_PATTERN = re.compile(
    r"\b(?:Version|sumo)\s+([0-9]+(?:\.[0-9]+){1,2})\b",
    re.IGNORECASE,
)


class SumoNotFoundError(RuntimeError):
    """Lançada quando os binários do SUMO não podem ser encontrados ou executados."""


class UnsupportedSumoVersionError(RuntimeError):
    """Lançada quando a versão instalada do SUMO não é a esperada."""


@dataclass(frozen=True)
class SumoEnvironmentInfo:
    sumo_home: Path | None
    sumo_binary: Path
    sumo_gui_binary: Path
    version: str


def detect_sumo_environment(
    *,
    expected_version: str = EXPECTED_SUMO_VERSION,
    environ: Mapping[str, str] | None = None,
) -> SumoEnvironmentInfo:
    env = environ if environ is not None else os.environ
    sumo_home = _find_sumo_home(env)
    sumo_binary = _find_binary("sumo", sumo_home)
    sumo_gui_binary = _find_binary("sumo-gui", sumo_home)
    version = _read_sumo_version(sumo_binary)

    if version != expected_version:
        msg = f"Unsupported SUMO version: expected {expected_version}, found {version}"
        raise UnsupportedSumoVersionError(msg)

    return SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=sumo_binary,
        sumo_gui_binary=sumo_gui_binary,
        version=version,
    )


def _find_sumo_home(environ: Mapping[str, str]) -> Path | None:
    raw_sumo_home = environ.get("SUMO_HOME")
    if raw_sumo_home:
        sumo_home = Path(raw_sumo_home).expanduser()
        if not sumo_home.exists():
            msg = f"SUMO_HOME does not exist: {sumo_home}"
            raise SumoNotFoundError(msg)
        return sumo_home

    sumo_path = shutil.which("sumo")
    if sumo_path is None:
        for candidate in _candidate_sumo_homes(environ):
            if candidate.exists():
                return candidate.resolve()
        return None

    binary_path = Path(sumo_path).resolve()
    if binary_path.parent.name.lower() == "bin":
        return binary_path.parent.parent

    for candidate in _candidate_sumo_homes(environ):
        if candidate.exists():
            return candidate.resolve()

    return None


def _candidate_sumo_homes(environ: Mapping[str, str]) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for variable_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        raw_base_path = environ.get(variable_name)
        if raw_base_path:
            base_path = Path(raw_base_path)
            candidates.extend(
                [
                    base_path / "Eclipse" / "Sumo",
                    base_path / "Sumo",
                ]
            )
    return tuple(candidates)


def _find_binary(binary_name: str, sumo_home: Path | None) -> Path:
    candidates = []
    if sumo_home is not None:
        candidates.extend(
            [
                sumo_home / "bin" / binary_name,
                sumo_home / "bin" / f"{binary_name}.exe",
            ]
        )

    found = shutil.which(binary_name)
    if found is not None:
        candidates.append(Path(found))

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    msg = f"SUMO binary not found: {binary_name}"
    raise SumoNotFoundError(msg)


def _read_sumo_version(sumo_binary: Path) -> str:
    try:
        completed = subprocess.run(
            [str(sumo_binary), "--version"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        msg = f"Unable to execute SUMO binary: {sumo_binary}"
        raise SumoNotFoundError(msg) from error

    output = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0:
        msg = f"Unable to read SUMO version from {sumo_binary}: {output.strip()}"
        raise SumoNotFoundError(msg)

    match = _VERSION_PATTERN.search(output)
    if match is None:
        msg = f"Unable to parse SUMO version from {sumo_binary}: {output.strip()}"
        raise SumoNotFoundError(msg)

    return match.group(1)
