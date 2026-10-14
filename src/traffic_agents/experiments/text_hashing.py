"""Line-ending-independent hashing of scientific TEXT artifacts (``CANONICAL_TEXT_LF_V1``).

Git may check text files out with LF or CRLF; the bytes (and so the raw SHA-256) then differ while
the scientific content does not. This is the single implementation of the canonical text hash. It
is used both by the route-artifact validation (execution path) and by the freeze tooling, which
re-exports it from ``traffic_agents.experiments.freeze_hashing``.

``CANONICAL_TEXT_LF_V1``: decode UTF-8 (a leading BOM is dropped), turn every ``CRLF`` into ``LF``
and every remaining lone ``CR`` into ``LF``, encode UTF-8, SHA-256. Nothing else is normalised: no
whitespace stripping, no re-serialisation, no final-newline changes.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

CANONICAL_TEXT_SCHEMA = "CANONICAL_TEXT_LF_V1"

# Explicit text policy. Compound names (``.net.xml``, ``.rou.xml``, ``.metadata.json``) are
# covered by their final suffix; anything not listed is binary (raw bytes only).
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
    """Raised for undecodable text, invalid metadata or an inconsistent scientific file set."""


def is_text_path(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name.lower()
    return any(name.endswith(suffix) for suffix in TEXT_SUFFIXES)


def raw_byte_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text_bytes(data: bytes) -> bytes:
    """Bytes hashed by ``CANONICAL_TEXT_LF_V1`` (BOM dropped, CRLF/CR -> LF, UTF-8)."""

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        msg = f"text file is not valid UTF-8: {exc}"
        raise HashingError(msg) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_sha256(data: bytes) -> str:
    return hashlib.sha256(canonical_text_bytes(data)).hexdigest()
