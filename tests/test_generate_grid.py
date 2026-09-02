from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path

import pytest

from traffic_agents.simulation import SumoEnvironmentInfo

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_generate_grid_module() -> types.ModuleType:
    module_path = REPO_ROOT / "scripts" / "generate_grid.py"
    spec = importlib.util.spec_from_file_location("generate_grid", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load generate_grid.py")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate_grid = load_generate_grid_module()


def write_network(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <junction id="J1" type="traffic_light" x="0" y="500"/>
    <junction id="J2" type="traffic_light" x="250" y="500"/>
    <junction id="J3" type="traffic_light" x="500" y="500"/>
    <junction id="J4" type="traffic_light" x="0" y="250"/>
    <junction id="J5" type="traffic_light" x="250" y="250"/>
    <junction id="J6" type="traffic_light" x="500" y="250"/>
    <junction id="J7" type="traffic_light" x="0" y="0"/>
    <junction id="J8" type="traffic_light" x="250" y="0"/>
    <junction id="J9" type="traffic_light" x="500" y="0"/>
    <tlLogic id="J1" type="static" programID="0" offset="0"/>
    <tlLogic id="J2" type="static" programID="0" offset="0"/>
    <tlLogic id="J3" type="static" programID="0" offset="0"/>
    <tlLogic id="J4" type="static" programID="0" offset="0"/>
    <tlLogic id="J5" type="static" programID="0" offset="0"/>
    <tlLogic id="J6" type="static" programID="0" offset="0"/>
    <tlLogic id="J7" type="static" programID="0" offset="0"/>
    <tlLogic id="J8" type="static" programID="0" offset="0"/>
    <tlLogic id="J9" type="static" programID="0" offset="0"/>
</net>
""",
        encoding="utf-8",
    )


def test_build_traffic_light_metadata_orders_grid_labels(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    write_network(network_path)

    traffic_light_ids = generate_grid.build_traffic_light_metadata(network_path)

    assert traffic_light_ids == {
        "A1": "J1",
        "A2": "J2",
        "A3": "J3",
        "A4": "J4",
        "A5": "J5",
        "A6": "J6",
        "A7": "J7",
        "A8": "J8",
        "A9": "J9",
    }


def test_build_traffic_light_metadata_requires_nine_tls(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text('<net><junction id="J1" type="traffic_light" x="0" y="0"/></net>')

    with pytest.raises(ValueError, match="Expected 9 traffic light junctions"):
        generate_grid.build_traffic_light_metadata(network_path)


def test_build_traffic_light_offsets_staggers_grid_labels() -> None:
    offsets = generate_grid.build_traffic_light_offsets(
        {
            "A1": "J1",
            "A2": "J2",
            "A3": "J3",
            "A4": "J4",
            "A5": "J5",
            "A6": "J6",
            "A7": "J7",
            "A8": "J8",
            "A9": "J9",
        }
    )

    assert offsets == {
        "J1": 0,
        "J2": 10,
        "J3": 20,
        "J4": 30,
        "J5": 40,
        "J6": 50,
        "J7": 60,
        "J8": 70,
        "J9": 80,
    }


def test_apply_protected_turn_phases_replaces_permissive_greens(
    tmp_path: Path,
) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <tlLogic id="J1" type="static" programID="0" offset="0">
        <phase duration="42" state="GGgrrrGGgrrr"/>
        <phase duration="3" state="yyyrrryyyrrr"/>
        <phase duration="42" state="rrrGGgrrrGGg"/>
        <phase duration="3" state="rrryyyrrryyy"/>
    </tlLogic>
</net>
""",
        encoding="utf-8",
    )

    generate_grid.apply_protected_turn_phases(network_path)

    root = ET.parse(network_path).getroot()
    traffic_light_program = root.find("tlLogic")
    assert traffic_light_program is not None
    phases = traffic_light_program.findall("phase")
    states = [phase.attrib["state"] for phase in phases]
    durations = [phase.attrib["duration"] for phase in phases]
    assert states == [
        "GGrrrrGGrrrr",
        "yyrrrryyrrrr",
        "rrGrrrrrGrrr",
        "rryrrrrryrrr",
        "rrrGGrrrrGGr",
        "rrryyrrrryyr",
        "rrrrrGrrrrrG",
        "rrrrryrrrrry",
    ]
    assert durations == ["32", "3", "10", "3", "32", "3", "10", "3"]
    assert not any("g" in state for state in states)
    assert "yyyrrryyyrrr" not in states
    assert "rrryyyrrryyy" not in states


def test_apply_traffic_light_intergreen_phases_inserts_all_red_after_yellow(
    tmp_path: Path,
) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <tlLogic id="J1" type="static" programID="0" offset="0">
        <phase duration="42" state="GGgrrrGGgrrr"/>
        <phase duration="3" state="yyyrrryyyrrr"/>
        <phase duration="42" state="rrrGGgrrrGGg"/>
        <phase duration="3" state="rrryyyrrryyy"/>
    </tlLogic>
</net>
""",
        encoding="utf-8",
    )

    generate_grid.apply_traffic_light_intergreen_phases(network_path, 2.0)

    content = network_path.read_text(encoding="utf-8")
    assert content.count('duration="2" state="rrrrrrrrrrrr"') == 2
    assert 'state="yyyrrryyyrrr"' in content
    assert 'state="rrryyyrrryyy"' in content


def test_validate_single_incoming_green_phases_accepts_one_green_approach(
    tmp_path: Path,
) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <tlLogic id="J1" type="static" programID="0" offset="0">
        <phase duration="20" state="GGGrrrrrrrrr"/>
        <phase duration="3" state="yyyrrrrrrrrr"/>
        <phase duration="2" state="rrrrrrrrrrrr"/>
        <phase duration="20" state="rrrGGGrrrrrr"/>
    </tlLogic>
</net>
""",
        encoding="utf-8",
    )

    generate_grid.validate_single_incoming_green_phases(network_path, 4)


def test_validate_single_incoming_green_phases_rejects_two_green_approaches(
    tmp_path: Path,
) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <tlLogic id="J1" type="static" programID="0" offset="0">
        <phase duration="20" state="GGGrrrGGGrrr"/>
    </tlLogic>
</net>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="opens 2 incoming approaches"):
        generate_grid.validate_single_incoming_green_phases(network_path, 4)


def test_apply_traffic_light_offsets_updates_tl_logic(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    write_network(network_path)

    generate_grid.apply_traffic_light_offsets(network_path, {"J1": 7, "J9": 23})

    content = network_path.read_text(encoding="utf-8")
    assert 'id="J1" type="static" programID="0" offset="7"' in content
    assert 'id="J9" type="static" programID="0" offset="23"' in content


def test_apply_traffic_light_stop_offsets_updates_incoming_edges(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <edge id="incoming" from="entry" to="J1">
        <lane id="incoming_0" index="0" speed="13.89" length="100"/>
    </edge>
    <edge id="outgoing" from="J1" to="exit">
        <lane id="outgoing_0" index="0" speed="13.89" length="100"/>
    </edge>
    <junction id="J1" type="traffic_light" x="0" y="0"/>
    <junction id="entry" type="dead_end" x="-100" y="0"/>
    <junction id="exit" type="dead_end" x="100" y="0"/>
</net>
""",
        encoding="utf-8",
    )

    generate_grid.apply_traffic_light_stop_offsets(network_path, 7.0)

    content = network_path.read_text(encoding="utf-8")
    assert '<stopOffset value="7" vClasses="passenger" />' in content
    assert 'id="outgoing"' in content


def test_normalize_generated_network_header_removes_timestamp(tmp_path: Path) -> None:
    network_path = tmp_path / "network.net.xml"
    network_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>

<!-- generated on 2026-09-01T21:48:09 by Eclipse SUMO netgenerate 1.27.1
<netgenerateConfiguration>
</netgenerateConfiguration>
-->
<net/>
""",
        encoding="utf-8",
    )

    generate_grid.normalize_generated_network_header(network_path)

    content = network_path.read_text(encoding="utf-8")
    assert "generated on" not in content
    assert "scripts/generate_grid.py" in content


def test_generate_grid_invokes_netgenerate_and_netcheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sumo_home = tmp_path / "sumo"
    bin_dir = sumo_home / "bin"
    net_dir = sumo_home / "tools" / "net"
    bin_dir.mkdir(parents=True)
    net_dir.mkdir(parents=True)
    netgenerate = bin_dir / "netgenerate.exe"
    netgenerate.write_text("", encoding="utf-8")
    (net_dir / "netcheck.py").write_text("", encoding="utf-8")
    network_path = tmp_path / "scenario" / "network.net.xml"
    metadata_path = tmp_path / "scenario" / "metadata.json"
    monkeypatch.setattr(generate_grid, "SCENARIO_DIR", tmp_path / "scenario")
    monkeypatch.setattr(generate_grid, "NETWORK_PATH", network_path)
    monkeypatch.setattr(generate_grid, "METADATA_PATH", metadata_path)

    calls: list[list[str]] = []

    def run(
        args: list[str],
        *,
        check: bool,
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert check is True
        assert env["SUMO_HOME"] == str(sumo_home)
        if args[0] == str(netgenerate):
            write_network(network_path)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", run)

    info = SumoEnvironmentInfo(
        sumo_home=sumo_home,
        sumo_binary=bin_dir / "sumo.exe",
        sumo_gui_binary=bin_dir / "sumo-gui.exe",
        version="1.27.1",
    )

    generated = generate_grid.generate_grid(info)

    assert generated.network_path == network_path
    assert metadata_path.exists()
    metadata = metadata_path.read_text(encoding="utf-8")
    assert '"traffic_light_offsets_seconds"' in metadata
    assert '"traffic_light_layout": "incoming"' in metadata
    assert '"phase_min_green_seconds": 10.0' in metadata
    assert '"phase_yellow_seconds": 3.0' in metadata
    assert '"phase_all_red_seconds": 2.0' in metadata
    assert '"phase_max_green_seconds": 60.0' in metadata
    assert '"traffic_light_intergreen_seconds": 2.0' in metadata
    assert '"traffic_light_stop_offset_meters": 7.0' in metadata
    assert calls[0][0] == str(netgenerate)
    assert "--grid.x-number" in calls[0]
    assert "--tls.set" in calls[0]
    assert "--tls.layout" in calls[0]
    assert "incoming" in calls[0]
    assert "--tls.yellow.time" in calls[0]
    assert "3" in calls[0]
    assert calls[1][1].endswith("netcheck.py")
