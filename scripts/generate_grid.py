from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from traffic_agents.simulation import SumoEnvironmentInfo, detect_sumo_environment

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO_ROOT / "scenarios" / "grid_3x3"
NETWORK_PATH = SCENARIO_DIR / "network.net.xml"
METADATA_PATH = SCENARIO_DIR / "metadata.json"
EDGE_LENGTH_METERS = 250
ATTACH_LENGTH_METERS = 100
LANE_COUNT = 1
GRID_SIZE = 3
SUMO_INTERNAL_TLS_IDS = "A0,A1,A2,B0,B1,B2,C0,C1,C2"
TLS_LAYOUT = "incoming"
TLS_APPROACH_COUNT = 4
PHASE_MIN_GREEN_SECONDS = 10.0
PHASE_YELLOW_SECONDS = 3.0
PHASE_ALL_RED_SECONDS = 2.0
PHASE_MAX_GREEN_SECONDS = 60.0
# Only used by apply_protected_turn_phases, which rewrites phases that contain permissive
# lowercase "g" signals. The incoming-layout grid from netgenerate has only protected "G"
# approach greens, so these constants are DORMANT for grid_3x3 and are not recorded in
# metadata.json. The actual green durations (18/20/20/20 s) are netgenerate defaults.
PROTECTED_THROUGH_GREEN_SECONDS = 32.0
PROTECTED_TURN_GREEN_SECONDS = 10.0
TRAFFIC_LIGHT_PROGRAM_SOURCE = "netgenerate_default_static_incoming_layout"
PROTECTED_TURN_YELLOW_SECONDS = PHASE_YELLOW_SECONDS
TRAFFIC_LIGHT_INTERGREEN_SECONDS = PHASE_ALL_RED_SECONDS
TLS_CYCLE_SECONDS = 98
TLS_OFFSET_STEP_SECONDS = 10
TRAFFIC_LIGHT_STOP_OFFSET_METERS = 7.0
GENERATED_COMMENT_PATTERN = re.compile(
    r"\n?<!-- generated on .*?</netgenerateConfiguration>\s*-->\s*",
    re.DOTALL,
)


@dataclass(frozen=True)
class GeneratedGridInfo:
    network_path: Path
    metadata_path: Path
    traffic_light_ids: dict[str, str]


def main() -> int:
    sumo_info = detect_sumo_environment()
    generated = generate_grid(sumo_info)

    print("Generated grid_3x3 network")
    print(f"network={generated.network_path}")
    print(f"metadata={generated.metadata_path}")
    return 0


def generate_grid(sumo_info: SumoEnvironmentInfo) -> GeneratedGridInfo:
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    netgenerate_binary = _sumo_tool_binary(sumo_info, "netgenerate")
    subprocess_env = _subprocess_env(sumo_info)

    subprocess.run(
        [
            str(netgenerate_binary),
            "--grid",
            "--grid.x-number",
            str(GRID_SIZE),
            "--grid.y-number",
            str(GRID_SIZE),
            "--grid.length",
            str(EDGE_LENGTH_METERS),
            "--grid.attach-length",
            str(ATTACH_LENGTH_METERS),
            "--bidi-probability",
            "1",
            "--default.lanenumber",
            str(LANE_COUNT),
            "--default.junctions.type",
            "priority",
            "--tls.set",
            SUMO_INTERNAL_TLS_IDS,
            "--tls.default-type",
            "static",
            "--tls.layout",
            TLS_LAYOUT,
            "--tls.yellow.time",
            _format_number(PHASE_YELLOW_SECONDS),
            "--no-turnarounds",
            "--seed",
            "42",
            "--output-file",
            str(NETWORK_PATH),
        ],
        check=True,
        env=subprocess_env,
    )

    normalize_generated_network_header(NETWORK_PATH)
    traffic_light_ids = build_traffic_light_metadata(NETWORK_PATH)
    apply_protected_turn_phases(NETWORK_PATH)
    apply_traffic_light_intergreen_phases(NETWORK_PATH, TRAFFIC_LIGHT_INTERGREEN_SECONDS)
    validate_single_incoming_green_phases(NETWORK_PATH, TLS_APPROACH_COUNT)
    traffic_light_offsets = build_traffic_light_offsets(traffic_light_ids)
    apply_traffic_light_offsets(NETWORK_PATH, traffic_light_offsets)
    apply_traffic_light_stop_offsets(NETWORK_PATH, TRAFFIC_LIGHT_STOP_OFFSET_METERS)
    write_metadata(
        METADATA_PATH,
        traffic_light_ids,
        traffic_light_offsets,
        TRAFFIC_LIGHT_STOP_OFFSET_METERS,
        TRAFFIC_LIGHT_INTERGREEN_SECONDS,
        read_program_timing(NETWORK_PATH),
    )
    validate_network(sumo_info, NETWORK_PATH)

    return GeneratedGridInfo(
        network_path=NETWORK_PATH,
        metadata_path=METADATA_PATH,
        traffic_light_ids=traffic_light_ids,
    )


def build_traffic_light_metadata(network_path: Path) -> dict[str, str]:
    tree = ET.parse(network_path)
    root = tree.getroot()
    junctions = []

    for junction in root.findall("junction"):
        if junction.attrib.get("type") != "traffic_light":
            continue

        junction_id = junction.attrib["id"]
        x = float(junction.attrib["x"])
        y = float(junction.attrib["y"])
        junctions.append((junction_id, x, y))

    if len(junctions) != GRID_SIZE * GRID_SIZE:
        msg = f"Expected 9 traffic light junctions, found {len(junctions)}"
        raise ValueError(msg)

    ordered = sorted(junctions, key=lambda item: (-item[2], item[1]))
    labels = [f"A{index}" for index in range(1, GRID_SIZE * GRID_SIZE + 1)]
    return dict(zip(labels, (junction_id for junction_id, _x, _y in ordered), strict=True))


def build_traffic_light_offsets(traffic_light_ids: Mapping[str, str]) -> dict[str, int]:
    return {
        traffic_light_ids[f"A{index}"]: ((index - 1) * TLS_OFFSET_STEP_SECONDS) % TLS_CYCLE_SECONDS
        for index in range(1, GRID_SIZE * GRID_SIZE + 1)
    }


def apply_protected_turn_phases(network_path: Path) -> None:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(network_path, parser=parser)
    root = tree.getroot()

    for traffic_light_program in root.findall("tlLogic"):
        phases = list(traffic_light_program.findall("phase"))
        if not phases:
            continue

        protected_phases: list[ET.Element] = []
        phase_index = 0
        while phase_index < len(phases):
            phase = phases[phase_index]
            signal_state = phase.attrib.get("state", "")
            if "g" not in signal_state:
                protected_phases.append(phase)
                phase_index += 1
                continue

            through_state = "".join("r" if signal == "g" else signal for signal in signal_state)
            turn_state = _protected_turn_state(signal_state)
            protected_phases.append(
                ET.Element(
                    "phase",
                    {
                        "duration": _format_number(PROTECTED_THROUGH_GREEN_SECONDS),
                        "state": through_state,
                    },
                )
            )
            protected_phases.append(
                ET.Element(
                    "phase",
                    {
                        "duration": _format_number(PROTECTED_TURN_YELLOW_SECONDS),
                        "state": _yellow_for_green_state(through_state),
                    },
                )
            )
            protected_phases.append(
                ET.Element(
                    "phase",
                    {
                        "duration": _format_number(PROTECTED_TURN_GREEN_SECONDS),
                        "state": turn_state,
                    },
                )
            )
            protected_phases.append(
                ET.Element(
                    "phase",
                    {
                        "duration": _format_number(PROTECTED_TURN_YELLOW_SECONDS),
                        "state": _yellow_for_green_state(turn_state),
                    },
                )
            )
            phase_index += 1
            if phase_index < len(phases) and _is_yellow_transition_phase(phases[phase_index]):
                phase_index += 1

        for phase in phases:
            traffic_light_program.remove(phase)
        for phase in protected_phases:
            traffic_light_program.append(phase)

    ET.indent(tree, space="    ")
    tree.write(network_path, encoding="utf-8", xml_declaration=True)


def apply_traffic_light_intergreen_phases(
    network_path: Path,
    intergreen_seconds: float,
) -> None:
    if intergreen_seconds <= 0:
        msg = "intergreen_seconds must be positive"
        raise ValueError(msg)

    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(network_path, parser=parser)
    root = tree.getroot()

    for traffic_light_program in root.findall("tlLogic"):
        phases = list(traffic_light_program.findall("phase"))
        if not phases:
            continue

        updated_phases: list[ET.Element] = []
        for index, phase in enumerate(phases):
            updated_phases.append(phase)
            next_phase = phases[(index + 1) % len(phases)]
            if not _needs_intergreen_after(phase, next_phase):
                continue

            intergreen = ET.Element(
                "phase",
                {
                    "duration": _format_number(intergreen_seconds),
                    "state": "r" * len(phase.attrib["state"]),
                },
            )
            updated_phases.append(intergreen)

        if updated_phases == phases:
            continue
        for phase in phases:
            traffic_light_program.remove(phase)
        for phase in updated_phases:
            traffic_light_program.append(phase)

    ET.indent(tree, space="    ")
    tree.write(network_path, encoding="utf-8", xml_declaration=True)


def validate_single_incoming_green_phases(
    network_path: Path,
    approach_count: int,
) -> None:
    if approach_count <= 0:
        msg = "approach_count must be positive"
        raise ValueError(msg)

    tree = ET.parse(network_path)
    root = tree.getroot()

    for traffic_light_program in root.findall("tlLogic"):
        traffic_light_id = traffic_light_program.attrib.get("id", "<unknown>")
        for phase in traffic_light_program.findall("phase"):
            signal_state = phase.attrib.get("state", "")
            if not _has_green(signal_state):
                continue
            if len(signal_state) % approach_count != 0:
                msg = (
                    f"traffic-light {traffic_light_id} has signal count incompatible with "
                    f"{approach_count} approaches"
                )
                raise ValueError(msg)

            signals_per_approach = len(signal_state) // approach_count
            green_approaches = 0
            for approach_index in range(approach_count):
                start_index = approach_index * signals_per_approach
                end_index = start_index + signals_per_approach
                if _has_green(signal_state[start_index:end_index]):
                    green_approaches += 1
            if green_approaches > 1:
                msg = (
                    f"traffic-light {traffic_light_id} opens {green_approaches} incoming "
                    f"approaches in phase state {signal_state}"
                )
                raise ValueError(msg)


def apply_traffic_light_offsets(
    network_path: Path,
    traffic_light_offsets: Mapping[str, int],
) -> None:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(network_path, parser=parser)
    root = tree.getroot()

    remaining_tls_ids = set(traffic_light_offsets)
    for traffic_light_program in root.findall("tlLogic"):
        traffic_light_id = traffic_light_program.attrib.get("id")
        if traffic_light_id not in traffic_light_offsets:
            continue
        traffic_light_program.set("offset", str(traffic_light_offsets[traffic_light_id]))
        remaining_tls_ids.remove(traffic_light_id)

    if remaining_tls_ids:
        msg = f"Traffic light programs not found: {tuple(sorted(remaining_tls_ids))}"
        raise ValueError(msg)

    ET.indent(tree, space="    ")
    tree.write(network_path, encoding="utf-8", xml_declaration=True)


def apply_traffic_light_stop_offsets(network_path: Path, stop_offset_meters: float) -> None:
    if stop_offset_meters <= 0:
        msg = "stop_offset_meters must be positive"
        raise ValueError(msg)

    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(network_path, parser=parser)
    root = tree.getroot()
    traffic_light_junction_ids = {
        junction.attrib["id"]
        for junction in root.findall("junction")
        if junction.attrib.get("type") == "traffic_light"
    }

    for edge in root.findall("edge"):
        if edge.attrib.get("function") == "internal":
            continue
        if edge.attrib.get("to") not in traffic_light_junction_ids:
            continue

        stop_offset = edge.find("stopOffset")
        if stop_offset is None:
            stop_offset = ET.Element("stopOffset")
            edge.insert(0, stop_offset)
        stop_offset.set("value", _format_number(stop_offset_meters))
        stop_offset.set("vClasses", "passenger")

    ET.indent(tree, space="    ")
    tree.write(network_path, encoding="utf-8", xml_declaration=True)


def normalize_generated_network_header(network_path: Path) -> None:
    content = network_path.read_text(encoding="utf-8")
    normalized = GENERATED_COMMENT_PATTERN.sub(
        "\n<!-- generated by Eclipse SUMO netgenerate 1.27.1 via scripts/generate_grid.py -->\n\n",
        content,
        count=1,
    )
    network_path.write_text(normalized, encoding="utf-8")


def read_program_timing(network_path: Path) -> dict[str, object]:
    """Describe the static fixed-time program actually stored in the generated network."""
    root = ET.parse(network_path).getroot()
    programs = root.findall("tlLogic")
    if not programs:
        return {}
    phases = programs[0].findall("phase")
    durations = [float(phase.attrib["duration"]) for phase in phases]
    greens = [
        float(phase.attrib["duration"])
        for phase in phases
        if _has_green(phase.attrib.get("state", ""))
    ]
    return {
        "traffic_light_cycle_seconds": sum(durations),
        "traffic_light_green_seconds_by_phase": greens,
    }


def write_metadata(
    metadata_path: Path,
    traffic_light_ids: dict[str, str],
    traffic_light_offsets: Mapping[str, int],
    stop_offset_meters: float,
    intergreen_seconds: float,
    program_timing: Mapping[str, object] | None = None,
) -> None:
    payload = {
        "scenario_id": "grid_3x3",
        "traffic_light_layout": TLS_LAYOUT,
        "phase_min_green_seconds": PHASE_MIN_GREEN_SECONDS,
        "phase_yellow_seconds": PHASE_YELLOW_SECONDS,
        "phase_all_red_seconds": PHASE_ALL_RED_SECONDS,
        "phase_max_green_seconds": PHASE_MAX_GREEN_SECONDS,
        "traffic_light_intergreen_seconds": intergreen_seconds,
        "traffic_light_program_source": TRAFFIC_LIGHT_PROGRAM_SOURCE,
        "traffic_light_stop_offset_meters": stop_offset_meters,
        "traffic_light_ids": traffic_light_ids,
        "traffic_light_offsets_seconds": traffic_light_offsets,
    }
    if program_timing:
        payload.update(program_timing)
    metadata_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_network(sumo_info: SumoEnvironmentInfo, network_path: Path) -> None:
    if sumo_info.sumo_home is None:
        msg = "SUMO_HOME is required to locate netcheck.py"
        raise ValueError(msg)

    netcheck_path = sumo_info.sumo_home / "tools" / "net" / "netcheck.py"
    subprocess.run(
        [sys.executable, str(netcheck_path), str(network_path)],
        check=True,
        env=_subprocess_env(sumo_info),
    )


def _subprocess_env(sumo_info: SumoEnvironmentInfo) -> Mapping[str, str]:
    env = os.environ.copy()
    if sumo_info.sumo_home is not None:
        env["SUMO_HOME"] = str(sumo_info.sumo_home)
    return env


def _sumo_tool_binary(sumo_info: SumoEnvironmentInfo, tool_name: str) -> Path:
    if sumo_info.sumo_home is None:
        msg = f"SUMO_HOME is required to locate {tool_name}"
        raise ValueError(msg)

    candidates = [
        sumo_info.sumo_home / "bin" / tool_name,
        sumo_info.sumo_home / "bin" / f"{tool_name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    msg = f"SUMO tool not found: {tool_name}"
    raise FileNotFoundError(msg)


def _format_number(value: float) -> str:
    return f"{value:g}"


def _protected_turn_state(signal_state: str) -> str:
    return "".join("G" if signal == "g" else "r" for signal in signal_state)


def _yellow_for_green_state(signal_state: str) -> str:
    return "".join("y" if signal in {"G", "g"} else "r" for signal in signal_state)


def _needs_intergreen_after(phase: ET.Element, next_phase: ET.Element) -> bool:
    state = phase.attrib.get("state", "")
    next_state = next_phase.attrib.get("state", "")
    if _is_all_red(next_state):
        return False
    return _has_yellow(state) and _has_green(next_state)


def _has_yellow(signal_state: str) -> bool:
    return any(signal in {"y", "Y"} for signal in signal_state)


def _has_green(signal_state: str) -> bool:
    return any(signal in {"g", "G"} for signal in signal_state)


def _is_all_red(signal_state: str) -> bool:
    return bool(signal_state) and all(signal in {"r", "R"} for signal in signal_state)


def _is_yellow_transition_phase(phase: ET.Element) -> bool:
    state = phase.attrib.get("state", "")
    return _has_yellow(state) and not _has_green(state)


if __name__ == "__main__":
    raise SystemExit(main())
