"""Identidade de caminho portável entre repositórios para entradas científicas congeladas.

Arquivos congelados são identificados pelo caminho POSIX relativo ao repositório
(``experiments/configs/x.yaml``) e nunca por uma localização absoluta, de modo que um freeze é
verificado da mesma forma depois que o repositório é movido, clonado em outro lugar ou obtido em
outro sistema operacional. A raiz do repositório é resolvida com ``git rev-parse --show-toplevel``
a partir de um caminho âncora, nunca apenas a partir do diretório atual.

Um caminho relativo serializado deve ser: não vazio, separado por ``/`` (sem barra invertida), sem
letra de unidade, sem barra inicial (absoluto ou UNC), sem segmentos ``.`` / ``..`` / vazios nem
caracteres NUL. Um caminho que resolve (inclusive via symlinks) para fora da raiz do repositório é
rejeitado, para que um registro forjado não consiga fazer a verificação ler arquivos arbitrários.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class RepositoryPathError(ValueError):
    """Lançada para caminhos não portáveis, malformados ou que escapam do repositório."""


def resolve_repository_root(anchor: Path) -> Path:
    """Diretório raiz do git que contém ``anchor`` (um arquivo ou diretório)."""

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
    """Retorna ``value`` como um caminho POSIX relativo ao repositório seguro ou lança erro."""

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
    """Arquivo local para um caminho relativo serializado; deve permanecer dentro de
    ``repository_root``.
    """

    relative = validate_relative_posix(value)
    root = repository_root.resolve()
    resolved = (root / Path(*relative.parts)).resolve()
    if not resolved.is_relative_to(root):
        msg = f"path escapes the repository root: {value!r}"
        raise RepositoryPathError(msg)
    return resolved


def to_repo_relative_posix(path: Path, repository_root: Path) -> str:
    """Serializa ``path`` como caminho POSIX relativo ao repositório (``/`` mesmo no Windows)."""

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
    """Toda string dentro de uma estrutura tipo JSON que se pareça com um caminho absoluto."""

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
