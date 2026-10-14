from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from traffic_agents.config import load_scenario_config
from traffic_agents.metrics.run_metrics import OfferedVehicle
from traffic_agents.replay import (
    DEMO_SEED,
    CameraPresetError,
    ReplayFairnessError,
    load_camera_presets,
    resolve_view,
)
from traffic_agents.replay.annotations import (
    SHOCK_MARKER_SECONDS,
    select_reference_vehicle,
    shock_marker_for,
)
from traffic_agents.replay.fairness import (
    FAIRNESS_FIELDS,
    build_replay_side,
    fairness_mismatches,
    fairness_report,
    resolve_scenario_path,
    verify_fairness,
)
from traffic_agents.replay.metadata import (
    comparison_payload,
    default_demo_id,
    frame_name,
    frame_path,
)
from traffic_agents.replay.network_geometry import intersection_junctions, load_network_geometry
from traffic_agents.replay.recorder import (
    ReplayError,
    SimulationSyncError,
    StepSynchronizer,
    validate_interval,
)
from traffic_agents.replay.visual_metrics import (
    VisualMetricsRow,
    read_visual_metrics,
    write_visual_metrics,
)

REPO = Path(__file__).resolve().parents[1]
PRESETS = REPO / "config" / "demo_camera_presets.yaml"
SCENARIO_DIR = REPO / "scenarios" / "grid_3x3"
ROUTE = ("left1A1", "A1B1", "B1C1", "C1right1")


def _geometry():
    config = load_scenario_config(SCENARIO_DIR / "scenario_s4_local_saturation_seed_42.yaml")
    geometry = load_network_geometry(SCENARIO_DIR / config.network_file)
    return config, geometry, intersection_junctions(config, geometry)


# --- camera presets ---------------------------------------------------------------------------
def test_camera_presets_parse_all_required() -> None:
    presets = load_camera_presets(PRESETS)
    assert set(presets.presets) >= {"whole_grid", "a5_center", "west_to_center", "reference_route"}
    assert presets.resolution.width % 2 == 0
    assert presets.get("reference_route").highlight_reference_route


def test_unknown_camera_rejected() -> None:
    with pytest.raises(CameraPresetError, match="unknown camera preset"):
        load_camera_presets(PRESETS).get("nope")


def test_invalid_preset_file_rejected(tmp_path: Path) -> None:
    payload = yaml.safe_load(PRESETS.read_text(encoding="utf-8"))
    payload["presets"]["a5_center"]["focus"] = {"network": True, "edges": ["A1B1"]}
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CameraPresetError, match="exactly one"):
        load_camera_presets(bad)

    del payload["presets"]["whole_grid"]
    payload["presets"]["a5_center"]["focus"] = {"network": True}
    bad.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CameraPresetError, match="missing required presets"):
        load_camera_presets(bad)


def test_odd_resolution_rejected(tmp_path: Path) -> None:
    payload = yaml.safe_load(PRESETS.read_text(encoding="utf-8"))
    payload["resolution"] = {"width": 1281, "height": 720}
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CameraPresetError, match="even"):
        load_camera_presets(bad)


def test_a5_view_contains_neighbours_and_matches_aspect() -> None:
    _, geometry, labels = _geometry()
    presets = load_camera_presets(PRESETS)
    view = resolve_view(presets.get("a5_center"), geometry, labels, width_px=1280, height_px=720)
    assert view.width_m / view.height_m == pytest.approx(1280 / 720)
    for label in ("A5", "A2", "A4", "A6", "A8"):
        x, y = geometry.junction_position(labels[label])
        assert view.min_x < x < view.max_x
        assert view.min_y < y < view.max_y
    assert labels["A5"] == "B1"
    px, py = view.world_to_pixel(*geometry.junction_position("B1"), width_px=1280, height_px=720)
    assert (px, py) == pytest.approx((640, 360))


def test_reference_route_view_spans_corridor() -> None:
    _, geometry, labels = _geometry()
    view = resolve_view(
        load_camera_presets(PRESETS).get("reference_route"),
        geometry,
        labels,
        width_px=1280,
        height_px=720,
    )
    assert view.min_x < 0 and view.max_x > 700


# --- fairness / seeds -------------------------------------------------------------------------
def _side(controller: str, seed: int = DEMO_SEED):
    path = resolve_scenario_path("S4_LOCAL_SATURATION", seed, SCENARIO_DIR)
    return build_replay_side(scenario_path=path, controller_id=controller, seed=seed)


def test_demo_seed_is_42() -> None:
    assert DEMO_SEED == 42


def test_fairness_passes_and_ignores_controller_id() -> None:
    before, after = _side("B2_LOCAL_PRESSURE"), _side("C1_COOPERATIVE_COMPACT")
    # The raw scenario hash differs by design; the neutral one must not.
    assert before.fingerprint.scenario_sha256 != after.fingerprint.scenario_sha256
    verify_fairness(before, after, requested_seed=42)
    report = fairness_report(before, after)
    assert set(FAIRNESS_FIELDS) <= set(report)


def test_same_seed_enforced() -> None:
    before = _side("B2_LOCAL_PRESSURE")
    other_seed = _side("C1_COOPERATIVE_COMPACT", seed=2027)
    with pytest.raises(ReplayFairnessError, match="seed"):
        verify_fairness(before, other_seed, requested_seed=42)
    with pytest.raises(ReplayFairnessError, match="requested seed"):
        verify_fairness(before, before, requested_seed=2027)


def test_seed_artifact_mismatch_rejected() -> None:
    path = resolve_scenario_path("S4_LOCAL_SATURATION", 42, SCENARIO_DIR)
    with pytest.raises(ReplayFairnessError, match="frozen with seed"):
        build_replay_side(scenario_path=path, controller_id="B2_LOCAL_PRESSURE", seed=7)
    with pytest.raises(ReplayFairnessError, match="no frozen scenario artifact"):
        resolve_scenario_path("S4_LOCAL_SATURATION", 7, SCENARIO_DIR)
    with pytest.raises(ReplayFairnessError, match="unknown scenario"):
        resolve_scenario_path("S9_NOPE", 42, SCENARIO_DIR)


def test_unknown_controller_rejected() -> None:
    path = resolve_scenario_path("S4_LOCAL_SATURATION", 42, SCENARIO_DIR)
    with pytest.raises(ReplayFairnessError, match="unsupported controller"):
        build_replay_side(scenario_path=path, controller_id="X9", seed=42)


@pytest.mark.parametrize(
    "field", ["network_sha256", "route_sha256", "turning_config_sha256", "scenario_neutral_sha256"]
)
def test_network_route_turning_mismatch_detected(field: str) -> None:
    before, after = _side("B2_LOCAL_PRESSURE"), _side("C1_COOPERATIVE_COMPACT")
    tampered = dict(after.fairness) | {field: "0" * 64}
    mismatches = fairness_mismatches(before.fairness, tampered)
    assert len(mismatches) == 1 and mismatches[0].startswith(field)


def test_different_scenarios_have_different_route_hash() -> None:
    s4 = _side("B2_LOCAL_PRESSURE")
    path = resolve_scenario_path("S1_BALANCED", 42, SCENARIO_DIR)
    s1 = build_replay_side(scenario_path=path, controller_id="B2_LOCAL_PRESSURE", seed=42)
    assert fairness_mismatches(s4.fairness, s1.fairness)


# --- synchronisation --------------------------------------------------------------------------
def test_step_synchronizer() -> None:
    sync = StepSynchronizer(1.0)
    sync.check(0, before_time=1.0, after_time=1.0)
    sync.check(599, before_time=600.0, after_time=600.0)
    with pytest.raises(SimulationSyncError):
        sync.check(5, before_time=6.0, after_time=7.0)
    with pytest.raises(SimulationSyncError):
        sync.check(5, before_time=7.0, after_time=7.0)


def test_interval_validation() -> None:
    validate_interval(600, 2600, 3900)
    for start, end in ((-1, 10), (10, 10), (0, 4000)):
        with pytest.raises(ReplayError):
            validate_interval(start, end, 3900)


# --- metadata / naming ------------------------------------------------------------------------
def test_file_naming(tmp_path: Path) -> None:
    assert frame_name(0) == "000000.png"
    assert frame_name(1234) == "001234.png"
    assert frame_path(tmp_path, "before", 7) == tmp_path / "frames" / "before" / "000007.png"
    with pytest.raises(ValueError, match="side"):
        frame_path(tmp_path, "middle", 0)
    assert (
        default_demo_id("S4_LOCAL_SATURATION", 42, "B2_LOCAL_PRESSURE", "C1_COOPERATIVE_COMPACT")
        == "s4_seed42_b2_vs_c1"
    )


def test_comparison_payload_fields() -> None:
    before, after = _side("B2_LOCAL_PRESSURE"), _side("C1_COOPERATIVE_COMPACT")
    payload = comparison_payload(
        scenario="S4_LOCAL_SATURATION",
        seed=42,
        official_seed=True,
        before_controller="B2_LOCAL_PRESSURE",
        after_controller="C1_COOPERATIVE_COMPACT",
        shared_inputs=fairness_report(before, after),
        start_step=600,
        end_step=2600,
        fps=30,
        camera={"preset": "a5_center"},
        sumo_version="1.27.1",
        ffmpeg_version="x",
        git_commit="abc",
        extra={},
    )
    for key in (
        "scenario",
        "seed",
        "before_controller",
        "after_controller",
        "network_sha256",
        "route_sha256",
        "turning_config_sha256",
        "start_step",
        "end_step",
        "fps",
        "camera",
        "git_sha",
        "sumo_version",
        "generated_at",
    ):
        assert key in payload
    assert payload["frames"] == 2000
    json.dumps(payload)


def test_visual_metrics_csv_roundtrip(tmp_path: Path) -> None:
    rows = [VisualMetricsRow(600, 601.0, 12, 30, 45), VisualMetricsRow(601, 602.0, 13, 31, 46)]
    path = tmp_path / "visual_metrics_before.csv"
    write_visual_metrics(path, rows)
    assert path.read_text(encoding="utf-8").splitlines()[0] == (
        "simulation_step,simulation_time_s,network_queue,arrived_count,departed_count"
    )
    assert read_visual_metrics(path) == rows


# --- reference vehicle ------------------------------------------------------------------------
def _veh(vehicle_id: str, depart: float, route: tuple[str, ...] = ROUTE) -> OfferedVehicle:
    return OfferedVehicle(vehicle_id, vehicle_id.split(".")[0], depart, route[0], route)


def test_reference_vehicle_selection_is_deterministic() -> None:
    offered = [
        _veh("a.9", 700.0),
        _veh("b.1", 650.0, ("left1A1", "A1B1", "B1C1", "C1C0")),  # not the reference route
        _veh("c.2", 650.0),
        _veh("c.1", 650.0),
        _veh("d.0", 100.0),  # before the window
    ]
    chosen = select_reference_vehicle(offered, earliest_depart_seconds=600.0)
    assert chosen is not None and chosen.vehicle_id == "c.1"
    assert (
        select_reference_vehicle(list(reversed(offered)), earliest_depart_seconds=600.0) == chosen
    )
    assert select_reference_vehicle(offered, earliest_depart_seconds=5000.0) is None


def test_reference_vehicle_exists_in_real_route_file() -> None:
    from traffic_agents.metrics.run_metrics import load_offered_vehicles

    offered = load_offered_vehicles(SCENARIO_DIR / "routes_s4_seed_42.rou.xml")
    chosen = select_reference_vehicle(offered, earliest_depart_seconds=600.0)
    assert chosen is not None and chosen.scheduled_depart >= 600.0


# --- S3 shock marker --------------------------------------------------------------------------
def test_shock_marker_reads_official_definition() -> None:
    config = load_scenario_config(SCENARIO_DIR / "scenario_s3_demand_shift_seed_42.yaml")
    marker = shock_marker_for(config)
    assert marker is not None
    assert marker.start_step == config.shock_start_step == 2100
    assert marker.end_step - marker.start_step == int(SHOCK_MARKER_SECONDS / config.step_length)
    assert not marker.is_active(2099)
    assert marker.is_active(2100)
    assert marker.is_active(marker.end_step - 1)
    assert not marker.is_active(marker.end_step)


def test_no_shock_marker_outside_s3() -> None:
    config = load_scenario_config(SCENARIO_DIR / "scenario_s4_local_saturation_seed_42.yaml")
    assert shock_marker_for(config) is None
