"""Orquestração determinística da gravação ANTES/DEPOIS.

Duas instâncias do SUMO GUI são inicializadas a partir de entradas congeladas idênticas e
avançadas em lock-step, por passo de simulação (nunca por relógio de parede). O frame ``k`` de
ambos os lados é o estado ao fim do passo de simulação ``start_step + k``. O pipeline é:

    captura (screenshots do SUMO GUI, ambos os lados, mesmo passo) -> compor overlays -> FFmpeg
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from traffic_agents.experiments.reference_route import REFERENCE_ROUTE_EDGES
from traffic_agents.experiments.run_invariants import json_sha256
from traffic_agents.metrics.run_metrics import OfferedVehicle, load_offered_vehicles
from traffic_agents.replay import overlay
from traffic_agents.replay.annotations import (
    REFERENCE_VEHICLE_RULE,
    SHOCK_LABEL,
    SHOCK_MARKER_SECONDS,
    ShockMarker,
    select_reference_vehicle,
    shock_marker_for,
)
from traffic_agents.replay.camera import (
    CameraPreset,
    CameraPresetFile,
    ViewWindow,
    load_camera_presets,
    resolve_view,
)
from traffic_agents.replay.fairness import (
    DEMO_SEED,
    ReplaySide,
    build_replay_side,
    fairness_report,
    resolve_scenario_path,
    verify_fairness,
)
from traffic_agents.replay.metadata import (
    AFTER_VIDEO,
    BEFORE_VIDEO,
    CAPTURE_STATE_FILE,
    COMPARISON_FILE,
    FRAMES_DIR,
    SIDE_BY_SIDE_VIDEO,
    THUMBNAIL_FILE,
    VISUAL_METRICS_AFTER,
    VISUAL_METRICS_BEFORE,
    comparison_payload,
    default_demo_id,
    frame_path,
    git_sha,
    simulation_code_fingerprint,
)
from traffic_agents.replay.network_geometry import (
    NetworkGeometry,
    intersection_junctions,
    load_network_geometry,
)
from traffic_agents.replay.sumo_session import ReplayRunner
from traffic_agents.replay.video import encode_frames, ffmpeg_version, find_ffmpeg
from traffic_agents.replay.visual_metrics import (
    VisualMetricsCollector,
    VisualMetricsRow,
    read_visual_metrics,
    write_visual_metrics,
)
from traffic_agents.simulation import detect_sumo_environment

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS_PATH = REPO_ROOT / "config" / "demo_camera_presets.yaml"
DEFAULT_VIEWSETTINGS_PATH = REPO_ROOT / "config" / "demo_viewsettings.xml"
DEFAULT_SCENARIO_DIR = REPO_ROOT / "scenarios" / "grid_3x3"
DEFAULT_DEMOS_DIR = REPO_ROOT / "artifacts" / "demos"
REFERENCE_VEHICLE_COLOR = (255, 0, 200, 255)
VIDEO_VARIANTS: tuple[str, ...] = ("before", "after", "side_by_side")


class ReplayError(RuntimeError):
    """Lançada para solicitações de gravação inválidas ou uma gravação que falhou."""


class SimulationSyncError(ReplayError):
    """Lançada quando ANTES e DEPOIS não estão no mesmo passo/tempo de simulação."""


@dataclass(frozen=True)
class RecordingRequest:
    scenario: str
    seed: int
    before_controller: str
    after_controller: str
    camera: str
    start_step: int
    end_step: int
    fps: int = 30
    step_delay_ms: int = 0
    output: Path | None = None
    reuse_existing_run: bool = False
    keep_frames: bool = False
    overwrite: bool = False
    highlight_reference_vehicle: bool | None = None
    presets_path: Path = DEFAULT_PRESETS_PATH
    viewsettings_path: Path | None = DEFAULT_VIEWSETTINGS_PATH
    scenario_dir: Path = DEFAULT_SCENARIO_DIR


@dataclass(frozen=True)
class RecordingResult:
    output_dir: Path
    comparison_path: Path
    frames: int
    reused_capture: bool
    videos: Mapping[str, Path] = field(default_factory=dict)


def validate_interval(start_step: int, end_step: int, total_steps: int) -> None:
    """Os frames cobrem os passos ``[start_step, end_step)`` dos ``total_steps`` do cenário."""

    if start_step < 0:
        msg = f"start_step must be non-negative, got {start_step}"
        raise ReplayError(msg)
    if end_step <= start_step:
        msg = f"end_step ({end_step}) must be greater than start_step ({start_step})"
        raise ReplayError(msg)
    if end_step > total_steps:
        msg = f"end_step ({end_step}) exceeds the scenario length ({total_steps} steps)"
        raise ReplayError(msg)


class StepSynchronizer:
    """Garante que ANTES e DEPOIS estão no mesmo passo de simulação (sincronizados apenas por
    passo).
    """

    def __init__(self, step_length: float) -> None:
        self._step_length = step_length

    def check(self, step_index: int, *, before_time: float, after_time: float) -> None:
        expected = (step_index + 1) * self._step_length
        if abs(before_time - after_time) > 1e-9 or abs(before_time - expected) > 1e-6:
            msg = (
                f"simulations out of sync at step {step_index}: before t={before_time}, "
                f"after t={after_time}, expected t={expected}"
            )
            raise SimulationSyncError(msg)


def frame_indices(start_step: int, end_step: int) -> range:
    return range(end_step - start_step)


def capture_fingerprint(
    *,
    request: RecordingRequest,
    shared_inputs: Mapping[str, object],
    preset: CameraPreset,
    view: ViewWindow,
    resolution: tuple[int, int],
    reference_vehicle_id: str | None,
) -> str:
    """Tudo que determina os pixels capturados; o reuso só é seguro se isso não tiver mudado."""

    return json_sha256(
        {
            "scenario": request.scenario.upper(),
            "seed": request.seed,
            "before_controller": request.before_controller,
            "after_controller": request.after_controller,
            "start_step": request.start_step,
            "end_step": request.end_step,
            "shared_inputs": dict(shared_inputs),
            "preset": preset.model_dump(mode="json"),
            "view": [view.min_x, view.min_y, view.max_x, view.max_y],
            "resolution": list(resolution),
            "reference_vehicle_id": reference_vehicle_id,
            "code": simulation_code_fingerprint(PACKAGE_DIR),
            "viewsettings": (
                json_sha256(request.viewsettings_path.read_text(encoding="utf-8"))
                if request.viewsettings_path is not None and request.viewsettings_path.exists()
                else None
            ),
        }
    )


@dataclass
class _CaptureSide:
    runner: ReplayRunner
    collector: VisualMetricsCollector
    rows: list[VisualMetricsRow] = field(default_factory=list)
    highlighted: bool = False


def capture_frames(
    *,
    sides: Mapping[str, ReplaySide],
    view: ViewWindow,
    resolution: tuple[int, int],
    request: RecordingRequest,
    output_dir: Path,
    geometry: NetworkGeometry,
    reference_vehicle_id: str | None,
) -> dict[str, list[VisualMetricsRow]]:
    """Avança as duas simulações em lock-step e captura a tela a cada passo do intervalo."""

    width, height = resolution
    before_side = sides["before"]
    step_length = before_side.config.step_length
    synchronizer = StepSynchronizer(step_length)
    capture: dict[str, _CaptureSide] = {}
    edge_ids = geometry.edge_ids
    started: list[ReplayRunner] = []
    try:
        for name, side in sides.items():
            runner = ReplayRunner(
                scenario_config=side.config,
                scenario_dir=side.scenario_dir,
                controller_id=side.controller_id,
                gui_settings_path=request.viewsettings_path,
                window_size=resolution,
                label=f"replay-{name}-{time.time_ns()}",
            )
            runner.start()
            started.append(runner)
            runner.frame_for_view(view, width=width, height=height)
            capture[name] = _CaptureSide(runner, VisualMetricsCollector(edge_ids))
        for step_index in range(request.end_step):
            capturing = step_index >= request.start_step
            frame_index = step_index - request.start_step
            if capturing:
                for name, state in capture.items():
                    state.runner.request_screenshot(frame_path(output_dir, name, frame_index))
            for state in capture.values():
                state.runner.step()
                state.collector.update_counts(state.runner.traci_connection)
            times = {
                name: float(state.runner.traci_connection.simulation.getTime())
                for name, state in capture.items()
            }
            synchronizer.check(step_index, before_time=times["before"], after_time=times["after"])
            if not capturing:
                continue
            for state in capture.values():
                connection = state.runner.traci_connection
                state.rows.append(state.collector.sample(connection, step_index=step_index))
                _highlight_reference_vehicle(state, connection, reference_vehicle_id)
            if request.step_delay_ms > 0:
                time.sleep(request.step_delay_ms / 1000)
    finally:
        for runner in started:
            runner.stop()
    return {name: state.rows for name, state in capture.items()}


def _highlight_reference_vehicle(
    state: _CaptureSide,
    connection: Any,
    reference_vehicle_id: str | None,
) -> None:
    """Halo visual em torno do veículo pré-selecionado (somente GUI; sem efeito na simulação)."""

    if reference_vehicle_id is None or state.highlighted:
        return
    if reference_vehicle_id in connection.vehicle.getIDList():
        connection.vehicle.highlight(reference_vehicle_id, REFERENCE_VEHICLE_COLOR, 14.0)
        state.highlighted = True


def _pane_context(
    *,
    title: str,
    side: ReplaySide,
    view: ViewWindow,
    resolution: tuple[int, int],
    label_points: Mapping[str, tuple[float, float]],
    route_polyline: Sequence[tuple[float, float]],
) -> overlay.PaneContext:
    return overlay.PaneContext(
        title=title,
        controller_id=side.controller_id,
        view=view,
        width=resolution[0],
        height=resolution[1],
        label_points=label_points,
        route_polyline=route_polyline,
    )


def _frame_state(row: VisualMetricsRow, *, shock_active: bool) -> overlay.FrameState:
    return overlay.FrameState(
        simulation_time_s=row.simulation_time_s,
        network_queue=row.network_queue,
        arrived_count=row.arrived_count,
        shock_active=shock_active,
    )


def compose_frames(
    *,
    output_dir: Path,
    rows: Mapping[str, Sequence[VisualMetricsRow]],
    contexts: Mapping[str, overlay.PaneContext],
    footer: overlay.FooterInfo,
    start_step: int,
    shock: ShockMarker | None,
    variant: str,
) -> Iterator[Image.Image]:
    """Produz um frame composto por índice para ``before``, ``after`` ou ``side_by_side``."""

    if variant not in VIDEO_VARIANTS:
        msg = f"unknown video variant {variant!r}"
        raise ValueError(msg)
    sides = ("before", "after") if variant == "side_by_side" else (variant,)
    for frame_index, (row_b, row_a) in enumerate(zip(rows["before"], rows["after"], strict=True)):
        step_index = start_step + frame_index
        if row_b.simulation_step != step_index or row_a.simulation_step != step_index:
            msg = (
                f"visual metrics out of step at frame {frame_index}: "
                f"before={row_b.simulation_step}, after={row_a.simulation_step}, "
                f"expected={step_index}"
            )
            raise SimulationSyncError(msg)
        shock_active = shock is not None and shock.is_active(step_index)
        panes = {}
        for name in sides:
            row = row_b if name == "before" else row_a
            with Image.open(frame_path(output_dir, name, frame_index)) as raw:
                panes[name] = overlay.compose_pane(
                    raw,
                    contexts[name],
                    _frame_state(row, shock_active=shock_active),
                    shock_text=SHOCK_LABEL,
                )
        shared = overlay.FrameState(simulation_time_s=row_b.simulation_time_s)
        if variant == "side_by_side":
            yield overlay.side_by_side(panes["before"], panes["after"], shared, footer)
        else:
            yield overlay.stack_with_footer(panes[variant], shared, footer)


def _read_capture_state(output_dir: Path) -> dict[str, Any] | None:
    path = output_dir / CAPTURE_STATE_FILE
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _frames_complete(output_dir: Path, frames: int) -> bool:
    return all(
        frame_path(output_dir, side, index).exists()
        for side in ("before", "after")
        for index in range(frames)
    )


def record_before_after(request: RecordingRequest) -> RecordingResult:
    presets: CameraPresetFile = load_camera_presets(request.presets_path)
    preset = presets.get(request.camera)
    resolution = (presets.resolution.width, presets.resolution.height)

    scenario_path = resolve_scenario_path(request.scenario, request.seed, request.scenario_dir)
    before = build_replay_side(
        scenario_path=scenario_path, controller_id=request.before_controller, seed=request.seed
    )
    after = build_replay_side(
        scenario_path=scenario_path, controller_id=request.after_controller, seed=request.seed
    )
    verify_fairness(before, after, requested_seed=request.seed)
    shared_inputs = fairness_report(before, after)
    config = before.config
    validate_interval(request.start_step, request.end_step, config.total_simulation_steps)

    geometry = load_network_geometry(before.scenario_dir / config.network_file)
    label_to_junction = intersection_junctions(config, geometry)
    for label in preset.labels:
        if label not in label_to_junction:
            msg = f"camera {request.camera!r} labels unknown intersection {label!r}"
            raise ReplayError(msg)
    view = resolve_view(
        preset, geometry, label_to_junction, width_px=resolution[0], height_px=resolution[1]
    )
    label_points = {
        label: geometry.junction_position(label_to_junction[label]) for label in preset.labels
    }
    route_polyline: list[tuple[float, float]] = []
    if preset.highlight_reference_route:
        route_polyline = _reference_route_polyline(geometry)

    shock = shock_marker_for(config)
    want_vehicle = (
        preset.highlight_reference_vehicle
        if request.highlight_reference_vehicle is None
        else request.highlight_reference_vehicle
    )
    reference_vehicle = _select_reference_vehicle(before, request, offered=want_vehicle)

    official_seed = request.seed == DEMO_SEED
    demo_id = default_demo_id(
        request.scenario, request.seed, request.before_controller, request.after_controller
    )
    output_dir = request.output or (DEFAULT_DEMOS_DIR / demo_id)
    fingerprint = capture_fingerprint(
        request=request,
        shared_inputs=shared_inputs,
        preset=preset,
        view=view,
        resolution=resolution,
        reference_vehicle_id=reference_vehicle.vehicle_id if reference_vehicle else None,
    )
    frames = request.end_step - request.start_step

    state = _read_capture_state(output_dir)
    reuse = bool(
        request.reuse_existing_run
        and state is not None
        and state.get("capture_fingerprint") == fingerprint
        and state.get("complete") is True
        and (output_dir / VISUAL_METRICS_BEFORE).exists()
        and (output_dir / VISUAL_METRICS_AFTER).exists()
        and _frames_complete(output_dir, frames)
    )
    if request.reuse_existing_run and not reuse:
        print(
            "reuse-existing-run: no safe capture to reuse (missing/changed frames or inputs); "
            "capturing again"
        )

    if not reuse:
        if output_dir.exists() and any(output_dir.iterdir()) and not request.overwrite:
            msg = f"output directory is not empty (use --overwrite): {output_dir}"
            raise ReplayError(msg)
        if (output_dir / FRAMES_DIR).exists():
            shutil.rmtree(output_dir / FRAMES_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / CAPTURE_STATE_FILE).unlink(missing_ok=True)
        rows = capture_frames(
            sides={"before": before, "after": after},
            view=view,
            resolution=resolution,
            request=request,
            output_dir=output_dir,
            geometry=geometry,
            reference_vehicle_id=reference_vehicle.vehicle_id if reference_vehicle else None,
        )
        write_visual_metrics(output_dir / VISUAL_METRICS_BEFORE, rows["before"])
        write_visual_metrics(output_dir / VISUAL_METRICS_AFTER, rows["after"])
        (output_dir / CAPTURE_STATE_FILE).write_text(
            json.dumps({"capture_fingerprint": fingerprint, "frames": frames, "complete": True})
            + "\n",
            encoding="utf-8",
        )
    else:
        rows = {
            "before": read_visual_metrics(output_dir / VISUAL_METRICS_BEFORE),
            "after": read_visual_metrics(output_dir / VISUAL_METRICS_AFTER),
        }

    contexts = {
        "before": _pane_context(
            title=overlay.BEFORE_TITLE,
            side=before,
            view=view,
            resolution=resolution,
            label_points=label_points,
            route_polyline=route_polyline,
        ),
        "after": _pane_context(
            title=overlay.AFTER_TITLE,
            side=after,
            view=view,
            resolution=resolution,
            label_points=label_points,
            route_polyline=route_polyline,
        ),
    }
    footer = overlay.FooterInfo(
        scenario_id=config.traffic.demand_profile, seed=request.seed, official=official_seed
    )
    ffmpeg = find_ffmpeg()
    pane_w = resolution[0]
    pane_h = resolution[1] + overlay.HEADER_HEIGHT + overlay.FOOTER_HEIGHT
    sbs_w = pane_w * 2 + overlay.DIVIDER_WIDTH
    videos = {
        "before": output_dir / BEFORE_VIDEO,
        "after": output_dir / AFTER_VIDEO,
        "side_by_side": output_dir / SIDE_BY_SIDE_VIDEO,
    }
    thumbnail_index = (frames - 1) // 2
    sizes = {
        "before": (pane_w, pane_h),
        "after": (pane_w, pane_h),
        "side_by_side": (sbs_w, pane_h),
    }
    for variant in VIDEO_VARIANTS:
        composed = compose_frames(
            output_dir=output_dir,
            rows=rows,
            contexts=contexts,
            footer=footer,
            start_step=request.start_step,
            shock=shock,
            variant=variant,
        )
        encoded = encode_frames(
            _with_thumbnail(
                composed,
                save_at=thumbnail_index,
                path=output_dir / THUMBNAIL_FILE,
                enabled=variant == "side_by_side",
            ),
            width=sizes[variant][0],
            height=sizes[variant][1],
            fps=request.fps,
            output=videos[variant],
            ffmpeg=ffmpeg,
        )
        if encoded != frames:
            msg = f"{videos[variant].name}: encoded {encoded} frames, expected {frames}"
            raise ReplayError(msg)

    sumo_version = detect_sumo_environment().version
    payload = comparison_payload(
        scenario=config.traffic.demand_profile,
        seed=request.seed,
        official_seed=official_seed,
        before_controller=request.before_controller,
        after_controller=request.after_controller,
        shared_inputs=shared_inputs,
        start_step=request.start_step,
        end_step=request.end_step,
        fps=request.fps,
        camera={
            "preset": request.camera,
            "description": preset.description,
            "view_world_m": [view.min_x, view.min_y, view.max_x, view.max_y],
            "resolution_px": list(resolution),
            "labels": list(preset.labels),
            "preset_file": _relative(request.presets_path),
        },
        sumo_version=sumo_version,
        ffmpeg_version=ffmpeg_version(ffmpeg),
        git_commit=git_sha(REPO_ROOT),
        extra={
            "demo_id": output_dir.name,
            "step_semantics": (
                "frame k shows the state at the end of simulation step start_step + k "
                "(simulation time = (step + 1) * step_length); steps [start_step, end_step)"
            ),
            "synchronisation": "lock-step by simulation step; asserted every step",
            "capture_fingerprint": fingerprint,
            "reused_capture": reuse,
            "shock_marker": (
                None
                if shock is None
                else {
                    "label": SHOCK_LABEL,
                    "source": "traffic.shock_start_seconds",
                    "start_step": shock.start_step,
                    "end_step": shock.end_step,
                    "duration_seconds": SHOCK_MARKER_SECONDS,
                    "visible_in_interval": shock.start_step < request.end_step
                    and shock.end_step > request.start_step,
                }
            ),
            "reference_vehicle": _reference_vehicle_payload(
                reference_vehicle, want_vehicle, request, before
            ),
            "reference_route": list(REFERENCE_ROUTE_EDGES)
            if preset.highlight_reference_route
            else None,
            "disclaimer": overlay.DISCLAIMER,
            "visual_metrics_note": (
                "network_queue (halting vehicles) and arrived_count are overlay annotations only; "
                "they are not scientific metrics"
            ),
            "outputs": {key: path.name for key, path in videos.items()}
            | {"thumbnail": THUMBNAIL_FILE}
            | {
                "visual_metrics_before": VISUAL_METRICS_BEFORE,
                "visual_metrics_after": VISUAL_METRICS_AFTER,
            },
        },
    )
    comparison_path = output_dir / COMPARISON_FILE
    comparison_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not request.keep_frames:
        shutil.rmtree(output_dir / FRAMES_DIR, ignore_errors=True)
        (output_dir / CAPTURE_STATE_FILE).unlink(missing_ok=True)
    return RecordingResult(
        output_dir=output_dir,
        comparison_path=comparison_path,
        frames=frames,
        reused_capture=reuse,
        videos=videos,
    )


def _with_thumbnail(
    frames: Iterator[Image.Image],
    *,
    save_at: int,
    path: Path,
    enabled: bool,
) -> Iterator[Image.Image]:
    for index, frame in enumerate(frames):
        if enabled and index == save_at:
            frame.save(path)
        yield frame


def _reference_route_polyline(geometry: NetworkGeometry) -> list[tuple[float, float]]:
    nodes = [geometry.edge_endpoints(REFERENCE_ROUTE_EDGES[0])[0]]
    for edge_id in REFERENCE_ROUTE_EDGES:
        nodes.append(geometry.edge_endpoints(edge_id)[1])
    return [geometry.junction_position(node) for node in nodes]


def _select_reference_vehicle(
    side: ReplaySide,
    request: RecordingRequest,
    *,
    offered: bool,
) -> OfferedVehicle | None:
    if not offered:
        return None
    route_path = side.scenario_dir / side.config.route_file
    config = side.config
    earliest = max(
        config.measurement_start_step * config.step_length,
        request.start_step * config.step_length,
    )
    return select_reference_vehicle(
        load_offered_vehicles(route_path), earliest_depart_seconds=earliest
    )


def _reference_vehicle_payload(
    vehicle: OfferedVehicle | None,
    requested: bool,
    request: RecordingRequest,
    side: ReplaySide,
) -> dict[str, object] | None:
    if not requested:
        return None
    config = side.config
    return {
        "rule": REFERENCE_VEHICLE_RULE,
        "vehicle_id": vehicle.vehicle_id if vehicle else None,
        "scheduled_depart_seconds": vehicle.scheduled_depart if vehicle else None,
        "earliest_depart_seconds": max(
            config.measurement_start_step * config.step_length,
            request.start_step * config.step_length,
        ),
    }


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
