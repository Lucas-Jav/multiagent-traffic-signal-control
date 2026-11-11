"""Hashing de artefatos de TEXTO científicos independente de quebras de linha.

O Git pode obter arquivos de texto com LF ou CRLF; os bytes (e portanto o SHA-256 bruto) então
diferem enquanto o conteúdo científico não. Esta é a implementação única do hash de texto
canônico. É usada tanto pela validação de artefatos de rota (caminho de execução) quanto pelas
ferramentas de freeze, que a reexportam de ``traffic_agents.experiments.freeze_hashing``.

``CANONICAL_TEXT_LF_V1``: decodifica UTF-8 (um BOM inicial é removido), transforma todo ``CRLF``
em ``LF`` e todo ``CR`` isolado restante em ``LF``, codifica UTF-8, SHA-256. Nada mais é
normalizado: sem remoção de espaços, sem re-serialização, sem alteração de nova linha final.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

CANONICAL_TEXT_SCHEMA = "CANONICAL_TEXT_LF_V1"

# Política de texto explícita. Nomes compostos (``.net.xml``, ``.rou.xml``, ``.metadata.json``)
# são cobertos pelo sufixo final; o que não está listado é binário (apenas bytes brutos).
TEXT_SUFFIXES: tuple[str, ...] = (
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".net.xml",
    ".rou.xml",
    ".metadata.json",
    ".toml",
    ".lock",
    ".csv",
    ".md",
    ".txt",
)


class HashingError(ValueError):
    """Lançada para texto não decodificável, metadados inválidos ou um conjunto de arquivos
    científicos inconsistente.
    """


def is_text_path(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name.lower()
    return any(name.endswith(suffix) for suffix in TEXT_SUFFIXES)


def raw_byte_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text_bytes(data: bytes) -> bytes:
    """Bytes submetidos a hash por ``CANONICAL_TEXT_LF_V1`` (BOM removido, CRLF/CR -> LF, UTF-8)."""

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        msg = f"text file is not valid UTF-8: {exc}"
        raise HashingError(msg) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_sha256(data: bytes) -> str:
    return hashlib.sha256(canonical_text_bytes(data)).hexdigest()
