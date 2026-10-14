"""Route/network artifact validation must not depend on checkout line endings (LF vs CRLF)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from traffic_agents.config import load_scenario_config
from traffic_agents.experiments import final_freeze as ff
from traffic_agents.experiments.freeze_hashing import semantic_metadata_sha256
from traffic_agents.experiments.legacy_artifact_hashes import (
    LEGACY_NETWORK_CANONICAL_BY_RAW,
    LEGACY_ROUTE_CANONICAL_BY_RAW,
)
from traffic_agents.experiments.route_artifacts import (
    RouteArtifactValidationError,
    route_metadata_path,
    validate_route_artifacts,
)
from traffic_agents.experiments.text_hashing import canonical_sha256, raw_byte_sha256

REPO = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO / "scenarios" / "grid_3x3"
PILOT_SEEDS = ff.PILOT_V2_SEEDS
EXTENSION_SEEDS = ff.EXTENSION_SEEDS
NEW_METADATA_KEYS = (
    "route_raw_sha256",
    "route_canonical_sha256",
    "network_raw_sha256",
    "network_canonical_sha256",
)


def _crlf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _stage(tmp_path: Path, scenario: str, seed: int, convert: object) -> Path:
    """Copy one scenario's artifacts into ``tmp_path`` with every text file converted."""

    target = tmp_path / f"{scenario}_{seed}"
    target.mkdir()
    scenario_path = SCENARIO_DIR / ff.scenario_file_name(scenario, seed)
    config = load_scenario_config(scenario_path)
    route = SCENARIO_DIR / config.route_file
    for source in (
        scenario_path,
        SCENARIO_DIR / config.network_file,
        route,
        route_metadata_path(route),
    ):
        (target / source.name).write_bytes(convert(source.read_bytes()))  # type: ignore[operator]
    return target / scenario_path.name


def _validate(scenario_yaml: Path) -> None:
    config = load_scenario_config(scenario_yaml)
    validate_route_artifacts(scenario_config=config, scenario_dir=scenario_yaml.parent)


# --- LF <-> CRLF equivalence --------------------------------------------------------------------
@pytest.mark.parametrize("seed", [*PILOT_SEEDS, *EXTENSION_SEEDS])
@pytest.mark.parametrize("scenario", ff.MAIN_SCENARIOS)
@pytest.mark.parametrize("variant", ["lf", "crlf"])
def test_line_ending_variants_are_accepted(
    tmp_path: Path, scenario: str, seed: int, variant: str
) -> None:
    convert = _lf if variant == "lf" else _crlf
    scenario_yaml = _stage(tmp_path, scenario, seed, convert)
    _validate(scenario_yaml)


def test_raw_hashes_differ_but_canonical_hashes_match(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    lf_yaml = _stage(tmp_path / "a", "S4_LOCAL_SATURATION", 42, _lf)
    crlf_yaml = _stage(tmp_path / "b", "S4_LOCAL_SATURATION", 42, _crlf)
    for name in ("network.net.xml", "routes_s4_seed_42.rou.xml"):
        lf_bytes = (lf_yaml.parent / name).read_bytes()
        crlf_bytes = (crlf_yaml.parent / name).read_bytes()
        assert raw_byte_sha256(lf_bytes) != raw_byte_sha256(crlf_bytes)
        assert canonical_sha256(lf_bytes) == canonical_sha256(crlf_bytes)
    _validate(lf_yaml)
    _validate(crlf_yaml)


def test_validation_has_no_side_effects(tmp_path: Path) -> None:
    scenario_yaml = _stage(tmp_path, "S1_BALANCED", 42, _lf)
    before = {p.name: p.read_bytes() for p in scenario_yaml.parent.iterdir()}
    _validate(scenario_yaml)
    assert {p.name: p.read_bytes() for p in scenario_yaml.parent.iterdir()} == before


# --- real scientific changes are still rejected -------------------------------------------------
@pytest.mark.parametrize("variant", [_lf, _crlf], ids=["lf", "crlf"])
def test_changed_route_edge_is_rejected(tmp_path: Path, variant: object) -> None:
    scenario_yaml = _stage(tmp_path, "S4_LOCAL_SATURATION", 42, variant)
    route = scenario_yaml.parent / "routes_s4_seed_42.rou.xml"
    text = route.read_bytes().decode("utf-8")
    assert 'edges="left1A1 A1B1' in text or "edges=" in text
    changed = text.replace('edges="', 'edges="X', 1)
    assert changed != text
    route.write_bytes(changed.encode("utf-8"))
    with pytest.raises(RouteArtifactValidationError, match="route_hash"):
        _validate(scenario_yaml)


@pytest.mark.parametrize("variant", [_lf, _crlf], ids=["lf", "crlf"])
def test_single_digit_change_in_route_is_rejected(tmp_path: Path, variant: object) -> None:
    scenario_yaml = _stage(tmp_path, "S2_DIRECTIONAL_PEAK", 6841, variant)
    route = scenario_yaml.parent / "routes_s2_seed_6841.rou.xml"
    text = route.read_bytes().decode("utf-8")
    index = text.index('depart="') + len('depart="')
    flipped = "9" if text[index] != "9" else "8"
    route.write_bytes((text[:index] + flipped + text[index + 1 :]).encode("utf-8"))
    with pytest.raises(RouteArtifactValidationError):
        _validate(scenario_yaml)


@pytest.mark.parametrize("variant", [_lf, _crlf], ids=["lf", "crlf"])
def test_changed_network_is_rejected(tmp_path: Path, variant: object) -> None:
    scenario_yaml = _stage(tmp_path, "S1_BALANCED", 8089, variant)
    network = scenario_yaml.parent / "network.net.xml"
    text = network.read_bytes().decode("utf-8")
    network.write_bytes(text.replace('speed="13.89"', 'speed="13.88"', 1).encode("utf-8"))
    with pytest.raises(RouteArtifactValidationError, match="network_hash"):
        _validate(scenario_yaml)


def test_added_trailing_whitespace_is_a_content_change(tmp_path: Path) -> None:
    scenario_yaml = _stage(tmp_path, "S3_DEMAND_SHIFT", 10007, _crlf)
    route = scenario_yaml.parent / "routes_s3_seed_10007.rou.xml"
    route.write_bytes(route.read_bytes() + b" ")
    with pytest.raises(RouteArtifactValidationError):
        _validate(scenario_yaml)


def test_unknown_recorded_raw_hash_cannot_be_laundered(tmp_path: Path) -> None:
    """A raw mismatch is never accepted just because the file is 'valid': the recorded hash
    must be a known legacy identity whose canonical hash equals the file's."""

    scenario_yaml = _stage(tmp_path, "S1_BALANCED", 42, _crlf)
    metadata_path = scenario_yaml.parent / "routes_s1_seed_42.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["route_hash"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(RouteArtifactValidationError, match="route_hash"):
        _validate(scenario_yaml)


def test_route_file_swapped_for_another_seed_is_rejected(tmp_path: Path) -> None:
    scenario_yaml = _stage(tmp_path, "S1_BALANCED", 42, _crlf)
    other = SCENARIO_DIR / "routes_s1_seed_2027.rou.xml"
    (scenario_yaml.parent / "routes_s1_seed_42.rou.xml").write_bytes(_crlf(other.read_bytes()))
    with pytest.raises(RouteArtifactValidationError):
        _validate(scenario_yaml)


@pytest.mark.parametrize(
    ("field", "value"),
    [("seed", 7), ("scenario_id", "other"), ("config_hash", "stale"), ("scenario_hash", "stale")],
)
def test_scientific_metadata_field_changes_fail_validation(
    tmp_path: Path, field: str, value: object
) -> None:
    scenario_yaml = _stage(tmp_path, "S2_DIRECTIONAL_PEAK", 12011, _crlf)
    metadata_path = scenario_yaml.parent / "routes_s2_seed_12011.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(RouteArtifactValidationError, match=field):
        _validate(scenario_yaml)


def test_generated_at_only_change_keeps_validation_and_semantic_identity(tmp_path: Path) -> None:
    scenario_yaml = _stage(tmp_path, "S3_DEMAND_SHIFT", 16001, _lf)
    metadata_path = scenario_yaml.parent / "routes_s3_seed_16001.metadata.json"
    original = metadata_path.read_bytes()
    metadata = json.loads(original)
    metadata["generated_at"] = "1999-12-31T23:59:59Z"
    changed = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode()
    assert semantic_metadata_sha256(original) == semantic_metadata_sha256(changed)
    metadata_path.write_bytes(changed)
    _validate(scenario_yaml)


@pytest.mark.parametrize("field", ["turning_ratios", "offered", "entries", "shock_start_seconds"])
def test_other_scientific_metadata_fields_change_semantic_identity(field: str) -> None:
    metadata = json.loads((SCENARIO_DIR / "routes_s3_seed_6841.metadata.json").read_bytes())
    original = semantic_metadata_sha256(json.dumps(metadata).encode())
    metadata[field] = (
        [*metadata[field], "extra"]
        if isinstance(metadata[field], list)
        else {"changed": metadata[field]}
    )
    assert semantic_metadata_sha256(json.dumps(metadata).encode()) != original


# --- new metadata (canonical fields) ------------------------------------------------------------
def _with_canonical_fields(scenario_yaml: Path, scenario: str, seed: int) -> None:
    short = scenario.split("_", maxsplit=1)[0].lower()
    metadata_path = scenario_yaml.parent / f"routes_{short}_seed_{seed}.metadata.json"
    route = scenario_yaml.parent / f"routes_{short}_seed_{seed}.rou.xml"
    network = scenario_yaml.parent / "network.net.xml"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["route_canonical_sha256"] = canonical_sha256(route.read_bytes())
    metadata["network_canonical_sha256"] = canonical_sha256(network.read_bytes())
    # a raw hash that matches no checkout: only the canonical field can authorise the files
    metadata["route_hash"] = "f" * 64
    metadata["network_hash"] = "e" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


@pytest.mark.parametrize("convert", [_lf, _crlf], ids=["lf", "crlf"])
def test_canonical_metadata_fields_authorise_either_line_ending(
    tmp_path: Path, convert: object
) -> None:
    scenario_yaml = _stage(tmp_path, "S4_LOCAL_SATURATION", 42, convert)
    _with_canonical_fields(scenario_yaml, "S4_LOCAL_SATURATION", 42)
    _validate(scenario_yaml)


def test_canonical_metadata_fields_still_reject_changed_files(tmp_path: Path) -> None:
    scenario_yaml = _stage(tmp_path, "S4_LOCAL_SATURATION", 42, _crlf)
    _with_canonical_fields(scenario_yaml, "S4_LOCAL_SATURATION", 42)
    route = scenario_yaml.parent / "routes_s4_seed_42.rou.xml"
    route.write_bytes(route.read_bytes().replace(b'edges="', b'edges="X', 1))
    with pytest.raises(RouteArtifactValidationError, match="route_canonical_sha256"):
        _validate(scenario_yaml)


def test_generator_emits_raw_and_canonical_fields_without_changing_routes(
    tmp_path: Path,
) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import generate_scenarios  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    for name in ("scenario.yaml", "network.net.xml", "metadata.json"):
        shutil.copy(SCENARIO_DIR / name, tmp_path / name)
    generate_scenarios.generate(tmp_path, seeds=(6841,), write_base_files=False)
    for scenario in ff.MAIN_SCENARIOS:
        name = ff.route_metadata_file_name(scenario, 6841)
        regenerated = json.loads((tmp_path / name).read_bytes())
        committed = json.loads((SCENARIO_DIR / name).read_bytes())
        route = tmp_path / ff.route_file_name(scenario, 6841)
        network = tmp_path / "network.net.xml"
        assert regenerated["route_hash"] == regenerated["route_raw_sha256"]
        assert regenerated["route_raw_sha256"] == raw_byte_sha256(route.read_bytes())
        assert regenerated["route_canonical_sha256"] == canonical_sha256(route.read_bytes())
        assert regenerated["network_canonical_sha256"] == canonical_sha256(network.read_bytes())
        # route content is the committed content (only line endings may differ)
        assert canonical_sha256(route.read_bytes()) == canonical_sha256(
            (SCENARIO_DIR / ff.route_file_name(scenario, 6841)).read_bytes()
        )
        # apart from the new fields and provenance, the metadata is the committed metadata
        scientific_regenerated = {
            k: v
            for k, v in regenerated.items()
            if k not in {*NEW_METADATA_KEYS, "generated_at", "route_hash", "network_hash"}
        }
        scientific_committed = {
            k: v
            for k, v in committed.items()
            if k not in {"generated_at", "route_hash", "network_hash"}
        }
        assert scientific_regenerated == scientific_committed
        # and the regenerated artifacts validate (also with CRLF copies)
        scenario_yaml = tmp_path / ff.scenario_file_name(scenario, 6841)
        _validate(scenario_yaml)
        for path in (route, network):
            path.write_bytes(_crlf(path.read_bytes()))
        _validate(scenario_yaml)
        for path in (route, network):
            path.write_bytes(_lf(path.read_bytes()))


# --- historical (Pilot V2 / existing) artifacts --------------------------------------------
@pytest.mark.parametrize("seed", PILOT_SEEDS)
@pytest.mark.parametrize("scenario", ff.MAIN_SCENARIOS)
def test_pilot_v2_artifacts_validate_in_place(scenario: str, seed: int) -> None:
    _validate(SCENARIO_DIR / ff.scenario_file_name(scenario, seed))


@pytest.mark.parametrize("seed", EXTENSION_SEEDS)
@pytest.mark.parametrize("scenario", ff.MAIN_SCENARIOS)
def test_final_extension_artifacts_validate_in_place(scenario: str, seed: int) -> None:
    _validate(SCENARIO_DIR / ff.scenario_file_name(scenario, seed))


def test_legacy_tables_cover_every_committed_artifact_and_only_those() -> None:
    expected_routes: dict[str, str] = {}
    expected_networks: dict[str, str] = {}
    for route in sorted(SCENARIO_DIR.glob("routes_*.rou.xml")):
        metadata = json.loads(route_metadata_path(route).read_text(encoding="utf-8"))
        expected_routes[metadata["route_hash"]] = canonical_sha256(route.read_bytes())
        expected_networks[metadata["network_hash"]] = canonical_sha256(
            (SCENARIO_DIR / "network.net.xml").read_bytes()
        )
    assert dict(LEGACY_ROUTE_CANONICAL_BY_RAW) == expected_routes
    assert dict(LEGACY_NETWORK_CANONICAL_BY_RAW) == expected_networks
    assert len(expected_routes) == 40


# --- scientific semantics -----------------------------------------------------------------------
def test_validation_module_only_decides_acceptance() -> None:
    """The route validation imports hashing/config helpers only: it cannot reach simulation code."""

    import ast

    source = (REPO / "src/traffic_agents/experiments/route_artifacts.py").read_text(
        encoding="utf-8"
    )
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden = ("simulation", "controllers", "metrics", "communication", "agents")
    segments = {segment for module in imported for segment in module.split(".")}
    assert segments.isdisjoint(forbidden), imported
    assert not any("freeze_hashing" in module or "final_freeze" in module for module in imported)
