"""Experiment-freeze file verification is LF/CRLF independent and never accepts real changes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import traffic_agents.experiments.freeze as freeze
from traffic_agents.experiments import text_hashing
from traffic_agents.experiments.freeze import ExperimentFreezeError, FrozenExperimentConfig
from traffic_agents.experiments.route_artifacts import route_metadata_path
from traffic_agents.experiments.text_hashing import canonical_sha256, raw_byte_sha256

REPO = Path(__file__).resolve().parents[1]
FINAL_CONFIGS = (
    REPO / "experiments" / "configs" / "final_main.yaml",
    REPO / "experiments" / "configs" / "final_s5_packet_loss.yaml",
)
SCENARIO_DIR = REPO / "scenarios" / "grid_3x3"


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _crlf(data: bytes) -> bytes:
    return _lf(data).replace(b"\n", b"\r\n")


def _frozen(entry: dict[str, str], root: Path) -> FrozenExperimentConfig:
    """Portable (schema 3) freeze verified against ``root``."""

    return FrozenExperimentConfig(
        experiment_id="t",
        freeze_dir=root,
        checksums={"schema_version": 3, "files": [entry], "derived": []},
        manifest={},
        repository_root=root,
    )


def _frozen_legacy(entry: dict[str, str]) -> FrozenExperimentConfig:
    """Historical schema-1 record (absolute path, raw hash)."""

    return FrozenExperimentConfig(
        experiment_id="t",
        freeze_dir=Path("."),
        checksums={"files": [entry], "derived": []},
        manifest={},
    )


def _entry_for(path: Path, data: bytes, root: Path) -> dict[str, str]:
    path.write_bytes(data)
    return freeze._file_entry("experiment_config", path, root)


@pytest.mark.parametrize("config", FINAL_CONFIGS, ids=lambda p: p.name)
@pytest.mark.parametrize(("frozen_as", "checked_as"), [(_lf, _crlf), (_crlf, _lf)])
def test_final_configs_validate_across_line_endings(
    config: Path, frozen_as: object, checked_as: object, tmp_path: Path
) -> None:
    original = config.read_bytes()
    copy = tmp_path / config.name
    entry = _entry_for(copy, frozen_as(original), tmp_path)  # type: ignore[operator]
    copy.write_bytes(checked_as(original))  # type: ignore[operator]
    assert entry["raw_byte_sha256"] != raw_byte_sha256(copy.read_bytes())
    assert entry["canonical_sha256"] == canonical_sha256(copy.read_bytes())
    _frozen(entry, tmp_path).validate()


@pytest.mark.parametrize("config", FINAL_CONFIGS, ids=lambda p: p.name)
@pytest.mark.parametrize("variant", [_lf, _crlf], ids=["lf", "crlf"])
def test_final_config_yaml_change_is_rejected(
    config: Path, variant: object, tmp_path: Path
) -> None:
    original = variant(config.read_bytes())  # type: ignore[operator]
    copy = tmp_path / config.name
    entry = _entry_for(copy, original, tmp_path)
    changed = original.replace(b"seed: 42", b"seed: 43", 1)
    if changed == original:
        changed = original.replace(b"drop_probability: 0.2", b"drop_probability: 0.3", 1)
    assert changed != original
    copy.write_bytes(changed)
    with pytest.raises(ExperimentFreezeError, match="experiment_config"):
        _frozen(entry, tmp_path).validate()


def test_raw_mismatch_with_matching_canonical_hash_is_accepted(tmp_path: Path) -> None:
    copy = tmp_path / "a.yaml"
    entry = _entry_for(copy, b"a: 1\nb: 2\n", tmp_path)
    copy.write_bytes(b"a: 1\r\nb: 2\r\n")
    assert raw_byte_sha256(copy.read_bytes()) != entry["sha256"]
    _frozen(entry, tmp_path).validate()


def test_binary_file_raw_mismatch_is_rejected(tmp_path: Path) -> None:
    blob = tmp_path / "frame.bin"
    entry = _entry_for(blob, b"\x00\x01\r\n\x02", tmp_path)
    assert "canonical_sha256" not in entry
    _frozen(entry, tmp_path).validate()
    blob.write_bytes(b"\x00\x01\n\x02")  # only a line ending differs: still a different binary
    with pytest.raises(ExperimentFreezeError):
        _frozen(entry, tmp_path).validate()


def test_invalid_utf8_text_is_rejected_not_crashing(tmp_path: Path) -> None:
    copy = tmp_path / "a.yaml"
    entry = _entry_for(copy, b"a: 1\n", tmp_path)
    copy.write_bytes(b"\xff\xfe a: 1\n")
    with pytest.raises(ExperimentFreezeError):
        _frozen(entry, tmp_path).validate()


# --- legacy (schema 1, raw hash only) records -----------------------------------------------------
def _legacy_entry(path: Path, label: str = "route_file") -> dict[str, str]:
    return {"label": label, "path": str(path), "sha256": raw_byte_sha256(path.read_bytes())}


def test_legacy_record_with_matching_raw_hash_is_accepted(tmp_path: Path) -> None:
    copy = tmp_path / "final_main.yaml"
    copy.write_bytes(FINAL_CONFIGS[0].read_bytes())
    _frozen_legacy(_legacy_entry(copy)).validate()


def test_legacy_record_cross_eol_without_a_trusted_identity_is_rejected(tmp_path: Path) -> None:
    """No unconditional canonical acceptance: an unknown raw hash cannot be laundered."""

    copy = tmp_path / "final_main.yaml"
    copy.write_bytes(_lf(FINAL_CONFIGS[0].read_bytes()))
    entry = _legacy_entry(copy)
    copy.write_bytes(_crlf(FINAL_CONFIGS[0].read_bytes()))
    with pytest.raises(ExperimentFreezeError):
        _frozen_legacy(entry).validate()


@pytest.mark.parametrize("variant", [_lf, _crlf], ids=["lf", "crlf"])
def test_legacy_record_cross_eol_with_a_trusted_identity_is_accepted(
    variant: object, tmp_path: Path
) -> None:
    route = SCENARIO_DIR / "routes_s1_seed_42.rou.xml"
    recorded_raw = json.loads(route_metadata_path(route).read_text(encoding="utf-8"))["route_hash"]
    copy = tmp_path / route.name
    copy.write_bytes(variant(route.read_bytes()))  # type: ignore[operator]
    entry = {"label": "route_file", "path": str(copy), "sha256": recorded_raw}
    _frozen_legacy(entry).validate()


def test_legacy_trusted_identity_still_rejects_changed_content(tmp_path: Path) -> None:
    route = SCENARIO_DIR / "routes_s1_seed_42.rou.xml"
    recorded_raw = json.loads(route_metadata_path(route).read_text(encoding="utf-8"))["route_hash"]
    copy = tmp_path / route.name
    copy.write_bytes(_crlf(route.read_bytes()).replace(b'edges="', b'edges="X', 1))
    entry = {"label": "route_file", "path": str(copy), "sha256": recorded_raw}
    with pytest.raises(ExperimentFreezeError, match="route_file"):
        _frozen_legacy(entry).validate()


# --- one canonical standard for freeze and route validation ---------------------------------------
def test_freeze_and_route_validation_share_the_single_implementation() -> None:
    from traffic_agents.experiments import freeze_hashing, route_artifacts

    for module in (freeze, route_artifacts, freeze_hashing):
        assert module.canonical_sha256 is text_hashing.canonical_sha256  # type: ignore[attr-defined]
    source = (REPO / "src" / "traffic_agents").rglob("*.py")
    normalising = [
        path.name
        for path in source
        if 'replace("\\r\\n", "\\n")' in path.read_text(encoding="utf-8")
    ]
    assert normalising == ["text_hashing.py"]
