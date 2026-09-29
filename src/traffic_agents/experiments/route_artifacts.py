from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from traffic_agents.config import ScenarioConfig
from traffic_agents.experiments.run_invariants import (
    file_sha256,
    route_artifact_scenario_sha256,
    route_generator_config_sha256,
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
    _require_equal(metadata, "route_hash", file_sha256(route_path))

    network_hash = metadata.get("network_hash")
    if network_hash is not None:
        if not isinstance(network_hash, str) or not network_hash:
            msg = f"route metadata network_hash must be a non-empty string: {metadata_path}"
            raise RouteArtifactValidationError(msg)
        if network_hash != file_sha256(network_path):
            msg = f"route metadata network_hash does not match network file: {metadata_path}"
            raise RouteArtifactValidationError(msg)

    _validate_route_windows(
        route_path=route_path,
        metadata=metadata,
        scenario_config=scenario_config,
    )


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


def _validate_route_windows(
    *,
    route_path: Path,
    metadata: Mapping[str, Any],
    scenario_config: ScenarioConfig,
) -> None:
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
