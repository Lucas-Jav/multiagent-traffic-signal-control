from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
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
        env: generate_grid.Mapping[str, str],
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
    assert calls[0][0] == str(netgenerate)
    assert "--grid.x-number" in calls[0]
    assert "--tls.set" in calls[0]
    assert calls[1][1].endswith("netcheck.py")
