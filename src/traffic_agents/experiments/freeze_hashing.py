"""Hashing multiplataforma e fingerprint da árvore científica do freeze final (FERRAMENTAS).

Este módulo é apenas ferramenta: é excluído da árvore científica que ele fingerprinta e nunca é
importado pelo caminho de execução de simulação / experimento (garantido por um teste).

Schemas de hash
---------------
``CANONICAL_TEXT_LF_V1`` (arquivos de texto)
    Implementado uma única vez em ``traffic_agents.experiments.text_hashing`` (compartilhado com a
    validação de artefatos de rota) e reexportado aqui: decodifica UTF-8 (BOM removido), CRLF e CR
    isolado viram LF, codifica UTF-8, SHA-256. Nada mais é normalizado.

``SCIENTIFIC_METADATA_V1`` (somente JSON de metadados de rota)
    Faz o parse do JSON, remove APENAS a chave de proveniência de nível superior ``generated_at``,
    serializa com ``json.dumps(sort_keys=True, separators=(",", ":"))`` (serializador padrão,
    escapes ASCII), codifica UTF-8, SHA-256. Todo outro campo (seed, demanda, rotas, razões de
    conversão, contagens, hashes, ...) faz parte da identidade.

``SCIENTIFIC_TREE_V1`` (a impressão digital da árvore)
    Um registro por arquivo incluído, ordenado por caminho POSIX relativo ao repositório::

        <relative_path>\\t<hash_mode>\\t<authoritative_hash>\\n

    ``hash_mode`` é ``canonical`` (texto), ``semantic`` (metadados de rota) ou ``raw`` (binário ou
    extensão desconhecida). A impressão digital é o SHA-256 da concatenação UTF-8 dos registros.

Os hashes de bytes brutos são mantidos ao lado dos autoritativos como evidência forense / local;
eles dependem das quebras de linha do checkout e NÃO são usados na verificação multiplataforma.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol

from traffic_agents.experiments.text_hashing import (
    CANONICAL_TEXT_SCHEMA as CANONICAL_TEXT_SCHEMA,
)
from traffic_agents.experiments.text_hashing import (
    HashingError,
    canonical_sha256,
    is_text_path,
    raw_byte_sha256,
)
from traffic_agents.experiments.text_hashing import (
    canonical_text_bytes as canonical_text_bytes,
)

__all__ = [
    "CANONICAL_TEXT_SCHEMA",
    "canonical_sha256",
    "canonical_text_bytes",
    "is_text_path",
    "raw_byte_sha256",
]

SEMANTIC_METADATA_SCHEMA = "SCIENTIFIC_METADATA_V1"
SCIENTIFIC_TREE_SCHEMA = "SCIENTIFIC_TREE_V1"

# Campos de proveniência excluídos do hash semântico. Deliberadamente uma lista permitida de um
# elemento.
SEMANTIC_EXCLUDED_TOP_LEVEL_KEYS: tuple[str, ...] = ("generated_at",)
SEMANTIC_METADATA_SUFFIX = ".metadata.json"

MODE_CANONICAL = "canonical"
MODE_SEMANTIC = "semantic"
MODE_RAW = "raw"


FreezeHashingError = HashingError


def is_semantic_metadata_path(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name.lower()
    return name.endswith(SEMANTIC_METADATA_SUFFIX)


def semantic_metadata_object(data: bytes) -> dict[str, object]:
    """JSON de metadados sem os campos de proveniência documentados (``SCIENTIFIC_METADATA_V1``)."""

    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"metadata is not valid UTF-8 JSON: {exc}"
        raise FreezeHashingError(msg) from exc
    if not isinstance(payload, dict):
        msg = "metadata JSON must be an object"
        raise FreezeHashingError(msg)
    return {k: v for k, v in payload.items() if k not in SEMANTIC_EXCLUDED_TOP_LEVEL_KEYS}


def semantic_metadata_sha256(data: bytes) -> str:
    encoded = json.dumps(
        semantic_metadata_object(data), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FileHashes:
    """Todos os hashes de um arquivo; ``authoritative`` é o multiplataforma para o ``mode``."""

    path: str
    mode: str
    raw_byte_sha256: str
    canonical_sha256: str | None
    semantic_sha256: str | None

    @property
    def authoritative(self) -> str:
        if self.mode == MODE_SEMANTIC and self.semantic_sha256 is not None:
            return self.semantic_sha256
        if self.mode == MODE_CANONICAL and self.canonical_sha256 is not None:
            return self.canonical_sha256
        return self.raw_byte_sha256


def hash_file_bytes(path: str, data: bytes, *, semantic: bool = False) -> FileHashes:
    """Calcula o hash de um arquivo. ``semantic=True`` seleciona a identidade semântica de metadados
    (somente JSON).
    """

    posix = PurePosixPath(path.replace("\\", "/")).as_posix()
    raw = raw_byte_sha256(data)
    if not is_text_path(posix):
        if semantic:
            msg = f"semantic hashing requires a text/JSON file: {posix}"
            raise FreezeHashingError(msg)
        return FileHashes(posix, MODE_RAW, raw, None, None)
    canonical = canonical_sha256(data)
    if semantic:
        if not is_semantic_metadata_path(posix):
            msg = f"semantic hashing is only defined for *{SEMANTIC_METADATA_SUFFIX}: {posix}"
            raise FreezeHashingError(msg)
        return FileHashes(posix, MODE_SEMANTIC, raw, canonical, semantic_metadata_sha256(data))
    return FileHashes(posix, MODE_CANONICAL, raw, canonical, None)


# --- Fontes: árvore de trabalho ou um commit git
# --------------------------------------------------------
class FileSource(Protocol):
    def exists(self, path: str) -> bool: ...

    def read(self, path: str) -> bytes: ...

    def list_dir(self, directory: str) -> list[str]:
        """Caminhos POSIX relativos ao repositório de todo arquivo abaixo de ``directory``
        (recursivo).
        """
        ...


@dataclass(frozen=True)
class WorkingTreeSource:
    root: Path

    def exists(self, path: str) -> bool:
        return (self.root / path).is_file()

    def read(self, path: str) -> bytes:
        return (self.root / path).read_bytes()

    def list_dir(self, directory: str) -> list[str]:
        base = self.root / directory
        if not base.is_dir():
            return []
        return sorted(
            p.relative_to(self.root).as_posix()
            for p in base.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )


@dataclass(frozen=True)
class GitCommitSource:
    root: Path
    commit: str
    _files: frozenset[str] = field(default_factory=frozenset, compare=False)

    def __post_init__(self) -> None:
        listing = _git(self.root, "ls-tree", "-r", "--name-only", self.commit)
        object.__setattr__(self, "_files", frozenset(listing.splitlines()))

    def exists(self, path: str) -> bool:
        return path in self._files

    def read(self, path: str) -> bytes:
        completed = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{self.commit}:{path}"],
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            msg = f"cannot read {path} at {self.commit}"
            raise FreezeHashingError(msg)
        return completed.stdout

    def list_dir(self, directory: str) -> list[str]:
        prefix = directory.rstrip("/") + "/"
        return sorted(p for p in self._files if p.startswith(prefix) and "__pycache__" not in p)


# --- Conjunto de arquivos científicos
# ------------------------------------------------------------------------
@dataclass(frozen=True)
class TreeRoot:
    """Todo arquivo abaixo de ``directory`` com um dos ``suffixes``, menos prefixos/arquivos
    excluídos.
    """

    directory: str
    suffixes: tuple[str, ...]
    excluded_prefixes: tuple[str, ...] = ()
    excluded_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScientificSpec:
    """Definição explícita dos arquivos que compõem SCIENTIFIC_TREE_SHA256."""

    tree_roots: tuple[TreeRoot, ...]
    fixed_files: tuple[str, ...]
    semantic_files: tuple[str, ...] = ()
    description: Mapping[str, str] = field(default_factory=dict)

    def paths(self, source: FileSource) -> list[str]:
        selected: set[str] = set()
        for root in self.tree_roots:
            for path in source.list_dir(root.directory):
                if not path.endswith(root.suffixes):
                    continue
                if path in root.excluded_files or path.startswith(root.excluded_prefixes):
                    continue
                selected.add(path)
        for path in (*self.fixed_files, *self.semantic_files):
            if not source.exists(path):
                msg = f"required scientific file is missing: {path}"
                raise FreezeHashingError(msg)
            selected.add(path)
        return sorted(selected)


@dataclass(frozen=True)
class ScientificTree:
    entries: tuple[FileHashes, ...]
    sha256: str
    schema: str = SCIENTIFIC_TREE_SCHEMA

    def by_path(self) -> dict[str, FileHashes]:
        return {entry.path: entry for entry in self.entries}


def tree_record(entry: FileHashes) -> str:
    return f"{entry.path}\t{entry.mode}\t{entry.authoritative}\n"


def fingerprint_entries(entries: Iterable[FileHashes]) -> str:
    ordered = sorted(entries, key=lambda e: e.path)
    payload = "".join(tree_record(entry) for entry in ordered)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_scientific_tree(spec: ScientificSpec, source: FileSource) -> ScientificTree:
    semantic = set(spec.semantic_files)
    entries = tuple(
        hash_file_bytes(path, source.read(path), semantic=path in semantic)
        for path in spec.paths(source)
    )
    return ScientificTree(entries=entries, sha256=fingerprint_entries(entries))


def diff_trees(before: ScientificTree, after: ScientificTree) -> list[str]:
    """Diferenças legíveis entre duas árvores científicas (vazio = idênticas)."""

    old, new = before.by_path(), after.by_path()
    differences = [f"added: {path}" for path in sorted(new.keys() - old.keys())]
    differences += [f"removed: {path}" for path in sorted(old.keys() - new.keys())]
    for path in sorted(old.keys() & new.keys()):
        a, b = old[path], new[path]
        if (a.mode, a.authoritative) != (b.mode, b.authoritative):
            differences.append(f"changed: {path}")
    return differences


# --- Estado do git
# -----------------------------------------------------------------------------------
def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        msg = f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        raise FreezeHashingError(msg)
    return completed.stdout.strip()


def git_head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


def git_working_tree_dirty(root: Path) -> bool:
    return bool(_git(root, "status", "--porcelain"))


_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")


def git_resolve_commit(root: Path, sha: str) -> str | None:
    """SHA completo do commit para um ``sha`` hexadecimal (abreviações permitidas), ou None se não
    for um commit.
    """

    if not _COMMIT_SHA_PATTERN.match(sha):
        return None
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    resolved = completed.stdout.strip()
    return resolved if completed.returncode == 0 and resolved else None


def git_is_ancestor(root: Path, ancestor: str, descendant: str = "HEAD") -> bool:
    completed = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


@dataclass(frozen=True)
class FreezePreconditions:
    """Resultado das verificações que devem valer ANTES de inspecionar as entradas científicas."""

    head_sha: str
    scientific_source_git_sha: str
    working_tree_dirty_at_input_inspection: bool
    source_is_ancestor_of_head: bool
    source_exists: bool
    scientific_tree_sha256: str
    source_scientific_tree_sha256: str
    scientific_changes_since_source: tuple[str, ...]
    tree: ScientificTree

    @property
    def ok(self) -> bool:
        return (
            not self.working_tree_dirty_at_input_inspection
            and self.source_exists
            and self.source_is_ancestor_of_head
            and not self.scientific_changes_since_source
        )

    def failures(self) -> list[str]:
        problems: list[str] = []
        if self.working_tree_dirty_at_input_inspection:
            problems.append("working tree is not clean")
        if not self.source_exists:
            problems.append(f"scientific source {self.scientific_source_git_sha} does not exist")
        elif not self.source_is_ancestor_of_head:
            problems.append(
                f"scientific source {self.scientific_source_git_sha} is not an ancestor of HEAD"
            )
        problems.extend(
            f"scientific input changed since source commit: {change}"
            for change in self.scientific_changes_since_source
        )
        return problems


def check_freeze_preconditions(
    repo_root: Path,
    spec: ScientificSpec,
    scientific_source_git_sha: str,
) -> FreezePreconditions:
    """Inspeciona o repositório para o freeze definitivo (não grava nada).

    ``scientific_source_git_sha`` é informado pelo chamador (não pode ser conhecido antes de o
    commit-fonte existir). Deve existir, ser ancestral de ``HEAD`` (o próprio ``HEAD`` é permitido)
    e sua árvore científica deve ser igual à atual; a árvore de trabalho deve estar limpa.
    """

    dirty = git_working_tree_dirty(repo_root)
    resolved = git_resolve_commit(repo_root, scientific_source_git_sha)
    exists = resolved is not None
    ancestor = exists and git_is_ancestor(repo_root, resolved or "")
    current = compute_scientific_tree(spec, WorkingTreeSource(repo_root))
    if ancestor:
        source_tree = compute_scientific_tree(spec, GitCommitSource(repo_root, resolved or ""))
        changes = tuple(diff_trees(source_tree, current))
        source_sha = source_tree.sha256
    else:
        changes = ()
        source_sha = ""
    return FreezePreconditions(
        head_sha=git_head(repo_root),
        scientific_source_git_sha=resolved or scientific_source_git_sha,
        working_tree_dirty_at_input_inspection=dirty,
        source_is_ancestor_of_head=ancestor,
        source_exists=exists,
        scientific_tree_sha256=current.sha256,
        source_scientific_tree_sha256=source_sha,
        scientific_changes_since_source=changes,
        tree=current,
    )


def manifest_file_sha256(path: Path) -> str:
    """SHA-256 do manifesto finalizado, independente de quebras de linha (armazenado FORA do
    manifesto).
    """

    return canonical_sha256(path.read_bytes())


def write_manifest_checksum(manifest_path: Path) -> Path:
    """Grava ``<sha256>  <name>`` ao lado do manifesto (o manifesto nunca embute o próprio hash)."""

    checksum_path = manifest_path.with_suffix(".sha256")
    checksum_path.write_text(
        f"{manifest_file_sha256(manifest_path)}  {manifest_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return checksum_path


def historical_controller_labels(labels: Sequence[str], forbidden: Iterable[str]) -> list[str]:
    forbidden_set = set(forbidden)
    return [label for label in labels if label in forbidden_set]
