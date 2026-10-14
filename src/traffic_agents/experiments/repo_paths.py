"""Repository-portable path identity for frozen scientific inputs.

Frozen files are identified by their repository-relative POSIX path (``experiments/configs/x.yaml``)
and never by an absolute location, so a freeze verifies the same after the repository is moved,
cloned elsewhere, or checked out on another operating system. The repository root is resolved with
``git rev-parse --show-toplevel`` from an anchor path, never from the current directory alone.

A serialized relative path must be: non-empty, ``/``-separated (no backslash), without drive
letter, leading slash (absolute or UNC), ``.`` / ``..`` / empty segments or NUL characters. A path
that resolves (symlinks included) outside the repository root is rejected, so a crafted record can
not make verification read arbitrary files.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class RepositoryPathError(ValueError):
    """Raised for non-portable, malformed or repository-escaping paths."""


def resolve_repository_root(anchor: Path) -> Path:
    """Git top-level directory containing ``anchor`` (a file or directory)."""

    start = anchor if anchor.is_dir() else anchor.parent
    while not start.exists() and start != start.parent:
        start = start.parent
    try:
        completed = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        msg = f"git is required to resolve the repository root: {exc}"
        raise RepositoryPathError(msg) from exc
    top_level = completed.stdout.strip()
    if completed.returncode != 0 or not top_level:
        msg = f"not inside a git repository: {anchor}"
        raise RepositoryPathError(msg)
    return Path(top_level).resolve()


def validate_relative_posix(value: object) -> PurePosixPath:
    """Return ``value`` as a safe repository-relative POSIX path or raise."""

    if not isinstance(value, str) or not value:
        msg = f"repository-relative path must be a non-empty string, got {value!r}"
        raise RepositoryPathError(msg)
    if "\\" in value:
        msg = f"repository-relative path must use '/' separators only: {value!r}"
        raise RepositoryPathError(msg)
    if "\x00" in value:
        msg = "repository-relative path contains a NUL character"
        raise RepositoryPathError(msg)
    if _DRIVE_PATTERN.match(value):
        msg = f"drive-qualified paths are not portable: {value!r}"
        raise RepositoryPathError(msg)
    if value.startswith("/"):
        msg = f"absolute or UNC paths are not portable: {value!r}"
        raise RepositoryPathError(msg)
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        msg = f"path must not contain empty, '.' or '..' segments: {value!r}"
        raise RepositoryPathError(msg)
    return PurePosixPath(value)


def resolve_repo_relative(repository_root: Path, value: object) -> Path:
    """Local file for a serialized relative path; it must stay inside ``repository_root``."""

    relative = validate_relative_posix(value)
    root = repository_root.resolve()
    resolved = (root / Path(*relative.parts)).resolve()
    if not resolved.is_relative_to(root):
        msg = f"path escapes the repository root: {value!r}"
        raise RepositoryPathError(msg)
    return resolved


def to_repo_relative_posix(path: Path, repository_root: Path) -> str:
    """Serialize ``path`` as a repository-relative POSIX path (``/`` even on Windows)."""

    root = repository_root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        msg = (
            f"scientific input outside the repository is not allowed: {path} "
            f"(repository root: {root})"
        )
        raise RepositoryPathError(msg) from exc
    serialized = relative.as_posix()
    validate_relative_posix(serialized)
    return serialized


def absolute_paths_in(value: Any, _prefix: str = "") -> list[str]:
    """Every string inside a JSON-like structure that looks like an absolute path."""

    return list(_walk_absolute(value, _prefix))


def _walk_absolute(value: Any, prefix: str) -> Iterator[str]:
    if isinstance(value, str):
        if _DRIVE_PATTERN.match(value) or value.startswith(("/", "\\")):
            yield f"{prefix}: {value}"
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_absolute(item, f"{prefix}/{key}")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            yield from _walk_absolute(item, f"{prefix}[{index}]")
