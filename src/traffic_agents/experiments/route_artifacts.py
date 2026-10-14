from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments.legacy_artifact_hashes import (
    LEGACY_NETWORK_CANONICAL_BY_RAW,
    LEGACY_ROUTE_CANONICAL_BY_RAW,
)
from traffic_agents.experiments.run_invariants import (
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
)
from traffic_agents.experiments.text_hashing import (
    HashingError,
    canonical_sha256,
    raw_byte_sha256,
)

FLOW_RATE_TOLERANCE = 0.1


class RouteArtifactValidationError(ValueError):
    """Raised when generated route artifacts no longer match the scenario config."""


def route_metadata_path(route_path: Path) -> Path:
    if route_path.name.endswith(".rou.xml"):
        return route_path.with_name(route_path.name.replace(".rou.xml", ".metadata.json"))
    return route_path.with_suffix(".metadata.json")


def validate_route_artifacts(
    *,
    scenario_config: ScenarioConfig,
    scenario_dir: Path,
) -> None:
    network_path = scenario_dir / scenario_config.network_file
    route_path = scenario_dir / scenario_config.route_file
    metadata_path = route_metadata_path(route_path)

    _require_file(network_path, "network")
    _require_file(route_path, "route")
    _require_file(metadata_path, "route metadata")

    metadata = _read_metadata(metadata_path)
    _require_equal(metadata, "scenario_id", scenario_config.scenario_id)
    _require_equal(metadata, "seed", int(scenario_config.seed))
    _require_equal(
        metadata,
        "config_hash",
        route_generator_config_sha256(scenario_config),
    )
    _require_equal(metadata, "scenario_hash", route_artifact_scenario_sha256(scenario_config))
    _validate_text_artifact_hash(
        label="route",
        path=route_path,
        metadata=metadata,
        metadata_path=metadata_path,
        raw_field="route_hash",
        canonical_field="route_canonical_sha256",
        legacy_table=LEGACY_ROUTE_CANONICAL_BY_RAW,
        required=True,
    )
    _validate_text_artifact_hash(
        label="network",
        path=network_path,
        metadata=metadata,
        metadata_path=metadata_path,
        raw_field="network_hash",
        canonical_field="network_canonical_sha256",
        legacy_table=LEGACY_NETWORK_CANONICAL_BY_RAW,
        required=False,
    )

    _validate_route_windows(
        route_path=route_path,
        metadata=metadata,
        scenario_config=scenario_config,
    )


def _validate_text_artifact_hash(
    *,
    label: str,
    path: Path,
    metadata: Mapping[str, Any],
    metadata_path: Path,
    raw_field: str,
    canonical_field: str,
    legacy_table: Mapping[str, str],
    required: bool,
) -> None:
    """Check a text artifact against its metadata identity, independent of line endings.

    Acceptance order (this only decides whether an artifact is accepted; it never alters the
    artifact or anything the simulation reads):

    1. metadata carries ``<label>_canonical_sha256`` (``CANONICAL_TEXT_LF_V1``): the file's
       canonical hash must equal it;
    2. otherwise the historical raw hash (``route_hash`` / ``network_hash``): a raw match is
       accepted exactly as before;
    3. on a raw mismatch the file is accepted only if the recorded raw hash is a KNOWN legacy
       identity and the file's canonical hash equals the trusted canonical value stored for it
       (proof that only line endings differ). Unknown recorded hashes are rejected.
    """

    data = path.read_bytes()
    try:
        actual_canonical = canonical_sha256(data)
    except HashingError as exc:
        msg = f"route metadata {raw_field}: {label} file is not valid UTF-8 text: {path}"
        raise RouteArtifactValidationError(msg) from exc

    canonical_expected = metadata.get(canonical_field)
    if canonical_expected is not None:
        if not isinstance(canonical_expected, str) or not canonical_expected:
            msg = f"route metadata {canonical_field} must be a non-empty string: {metadata_path}"
            raise RouteArtifactValidationError(msg)
        if canonical_expected != actual_canonical:
            msg = (
                f"route metadata {canonical_field} does not match the {label} file: "
                f"expected {canonical_expected!r}, got {actual_canonical!r}"
            )
            raise RouteArtifactValidationError(msg)
        return

    recorded_raw = metadata.get(raw_field)
    if recorded_raw is None and not required:
        return
    if not isinstance(recorded_raw, str) or not recorded_raw:
        msg = f"route metadata {raw_field} must be a non-empty string: {metadata_path}"
        raise RouteArtifactValidationError(msg)
    if recorded_raw == raw_byte_sha256(data):
        return
    trusted_canonical = legacy_table.get(recorded_raw)
    if trusted_canonical is not None and trusted_canonical == actual_canonical:
        return
    msg = (
        f"route metadata {raw_field} mismatch: {label} file {path.name} matches neither the "
        f"recorded raw hash {recorded_raw!r} nor a trusted canonical identity"
    )
    raise RouteArtifactValidationError(msg)


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        msg = f"{label} file not found: {path}"
        raise FileNotFoundError(msg)
    if not path.is_file():
        msg = f"{label} path is not a file: {path}"
        raise RouteArtifactValidationError(msg)


def _read_metadata(metadata_path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"malformed route metadata JSON: {metadata_path}"
        raise RouteArtifactValidationError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"route metadata must be a JSON object: {metadata_path}"
        raise RouteArtifactValidationError(msg)
    return payload


def _require_equal(metadata: Mapping[str, Any], field: str, expected: object) -> None:
    actual = metadata.get(field)
    if actual != expected:
        msg = f"route metadata {field} mismatch: expected {expected!r}, got {actual!r}"
        raise RouteArtifactValidationError(msg)


def _validate_entry_routes(
    *,
    route_path: Path,
    metadata: Mapping[str, Any],
    scenario_config: ScenarioConfig,
) -> None:
    demand_level = scenario_config.traffic.demand_level
    expected_entries = {
        (
            entry.demand_id,
            entry.entry_edge_id,
            float(entry.begin_seconds),
            float(entry.end_seconds),
            float(entry.vehicles_per_hour[demand_level]),
        )
        for entry in scenario_config.traffic.entries
    }
    entries = metadata.get("entries")
    if not isinstance(entries, list):
        msg = "route metadata entries are missing for turning-ratio demand"
        raise RouteArtifactValidationError(msg)
    try:
        metadata_entries = {
            (
                str(entry["demand_id"]),
                str(entry["entry_edge_id"]),
                float(entry["begin_seconds"]),
                float(entry["end_seconds"]),
                float(entry["vehicles_per_hour"]),
            )
            for entry in entries
        }
    except (KeyError, TypeError, ValueError) as exc:
        msg = "route metadata entry definitions are malformed"
        raise RouteArtifactValidationError(msg) from exc
    if metadata_entries != expected_entries:
        msg = "route metadata entries do not match scenario traffic config"
        raise RouteArtifactValidationError(msg)

    offered = metadata.get("offered")
    offered_by_demand = offered.get("offered_by_demand") if isinstance(offered, dict) else None
    if not isinstance(offered_by_demand, dict):
        msg = "route metadata offered_by_demand is missing"
        raise RouteArtifactValidationError(msg)
    try:
        tree = ET.parse(route_path)
    except ET.ParseError as exc:
        msg = f"malformed route XML: {route_path}"
        raise RouteArtifactValidationError(msg) from exc
    actual_by_demand: dict[str, int] = {}
    previous_depart = -1.0
    for vehicle in tree.getroot().findall("vehicle"):
        vehicle_id = vehicle.attrib.get("id", "")
        depart = float(vehicle.attrib.get("depart", "nan"))
        if depart < previous_depart:
            msg = f"route vehicles must be sorted by departure time: {route_path}"
            raise RouteArtifactValidationError(msg)
        previous_depart = depart
        demand_id = vehicle_id.rsplit(".", 1)[0]
        actual_by_demand[demand_id] = actual_by_demand.get(demand_id, 0) + 1
        if not 0.0 <= depart <= scenario_config.total_duration_seconds:
            msg = f"route vehicle departs outside the simulation horizon: {vehicle_id}"
            raise RouteArtifactValidationError(msg)
    expected_counts = {str(key): int(value) for key, value in offered_by_demand.items()}
    if actual_by_demand != expected_counts:
        msg = f"route vehicle counts do not match route metadata offered demand: {route_path}"
        raise RouteArtifactValidationError(msg)


def _validate_route_windows(
    *,
    route_path: Path,
    metadata: Mapping[str, Any],
    scenario_config: ScenarioConfig,
) -> None:
    if scenario_config.traffic.entries:
        _validate_entry_routes(
            route_path=route_path,
            metadata=metadata,
            scenario_config=scenario_config,
        )
        return
    expected_windows = {
        (
            flow.flow_id,
            float(flow.begin_seconds),
            float(flow.end_seconds),
            float(flow.vehicles_per_hour[scenario_config.traffic.demand_level]),
        )
        for flow in scenario_config.traffic.flows
    }
    metadata_windows = _metadata_flow_windows(metadata)
    if metadata_windows and metadata_windows != expected_windows:
        msg = "route metadata flow windows do not match scenario traffic config"
        raise RouteArtifactValidationError(msg)

    route_windows = _route_flow_windows(route_path)
    if route_windows and not _flow_windows_match(route_windows, expected_windows):
        msg = f"route flow begin/end/rate windows do not match scenario config: {route_path}"
        raise RouteArtifactValidationError(msg)


def _metadata_flow_windows(metadata: Mapping[str, Any]) -> set[tuple[str, float, float, float]]:
    flows = metadata.get("flows")
    if not isinstance(flows, list):
        return set()

    windows: set[tuple[str, float, float, float]] = set()
    for flow in flows:
        if not isinstance(flow, dict):
            msg = "route metadata flows must contain JSON objects"
            raise RouteArtifactValidationError(msg)
        try:
            windows.add(
                (
                    str(flow["flow_id"]),
                    float(flow["begin_seconds"]),
                    float(flow["end_seconds"]),
                    float(flow["vehicles_per_hour"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            msg = "route metadata flow entries are malformed"
            raise RouteArtifactValidationError(msg) from exc
    return windows


def _route_flow_windows(route_path: Path) -> set[tuple[str, float, float, float]]:
    try:
        tree = ET.parse(route_path)
    except ET.ParseError as exc:
        msg = f"malformed route XML: {route_path}"
        raise RouteArtifactValidationError(msg) from exc

    windows: set[tuple[str, float, float, float]] = set()
    for flow in tree.getroot().findall("flow"):
        flow_id = flow.attrib.get("id")
        begin = flow.attrib.get("begin")
        end = flow.attrib.get("end")
        rate = flow.attrib.get("vehsPerHour", flow.attrib.get("perHour"))
        if flow_id is None or begin is None or end is None or rate is None:
            msg = f"route flow is missing id/begin/end/vehsPerHour: {route_path}"
            raise RouteArtifactValidationError(msg)
        windows.add((flow_id, float(begin), float(end), float(rate)))
    return windows


def _flow_windows_match(
    actual: set[tuple[str, float, float, float]],
    expected: set[tuple[str, float, float, float]],
) -> bool:
    actual_by_window = {(flow_id, begin, end): rate for flow_id, begin, end, rate in actual}
    expected_by_window = {(flow_id, begin, end): rate for flow_id, begin, end, rate in expected}
    if set(actual_by_window) != set(expected_by_window):
        return False
    return all(
        abs(actual_by_window[key] - expected_rate) <= FLOW_RATE_TOLERANCE
        for key, expected_rate in expected_by_window.items()
    )
