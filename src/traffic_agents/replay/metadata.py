"""Naming helpers, code fingerprint and ``comparison.json`` payload for replay outputs."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from traffic_agents.experiments.run_invariants import file_sha256

COMPARISON_FILE = "comparison.json"
CAPTURE_STATE_FILE = "capture_state.json"
THUMBNAIL_FILE = "thumbnail.png"
BEFORE_VIDEO = "before.mp4"
AFTER_VIDEO = "after.mp4"
SIDE_BY_SIDE_VIDEO = "side_by_side.mp4"
VISUAL_METRICS_BEFORE = "visual_metrics_before.csv"
VISUAL_METRICS_AFTER = "visual_metrics_after.csv"
FRAMES_DIR = "frames"
FRAME_SUFFIX = ".png"

_CODE_FINGERPRINT_EXCLUDED_PARTS = frozenset({"replay", "__pycache__"})


def frame_name(frame_index: int) -> str:
    """Deterministic frame file name (``000000.png``); same index for BEFORE and AFTER."""

    if frame_index < 0:
        msg = "frame_index must be non-negative"
        raise ValueError(msg)
    return f"{frame_index:06d}{FRAME_SUFFIX}"


def frame_path(output_dir: Path, side: str, frame_index: int) -> Path:
    if side not in {"before", "after"}:
        msg = f"side must be 'before' or 'after', got {side!r}"
        raise ValueError(msg)
    return output_dir / FRAMES_DIR / side / frame_name(frame_index)


def default_demo_id(scenario: str, seed: int, before_controller: str, after_controller: str) -> str:
    """``S4_LOCAL_SATURATION`` + ``B2_LOCAL_PRESSURE`` + ``C1_...`` -> ``s4_seed42_b2_vs_c1``."""

    scenario_short = scenario.split("_", maxsplit=1)[0].lower()
    before_short = before_controller.split("_", maxsplit=1)[0].lower()
    after_short = after_controller.split("_", maxsplit=1)[0].lower()
    return f"{scenario_short}_seed{seed}_{before_short}_vs_{after_short}"


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def git_sha(repo_dir: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    sha = completed.stdout.strip()
    return sha if completed.returncode == 0 and sha else None


def simulation_code_fingerprint(package_dir: Path) -> str:
    """Hash of every simulation/controller source file (the replay package itself excluded).

    Used to decide whether previously captured frames are still valid for reuse.
    """

    digest = hashlib.sha256()
    for path in sorted(package_dir.rglob("*.py")):
        relative = path.relative_to(package_dir)
        if _CODE_FINGERPRINT_EXCLUDED_PARTS.intersection(relative.parts):
            continue
        digest.update(relative.as_posix().encode())
        digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def comparison_payload(
    *,
    scenario: str,
    seed: int,
    official_seed: bool,
    before_controller: str,
    after_controller: str,
    shared_inputs: Mapping[str, object],
    start_step: int,
    end_step: int,
    fps: int,
    camera: Mapping[str, object],
    sumo_version: str,
    ffmpeg_version: str,
    git_commit: str | None,
    extra: Mapping[str, object],
) -> dict[str, object]:
    """Contents of ``comparison.json``."""

    payload: dict[str, object] = {
        "scenario": scenario,
        "seed": seed,
        "official_demo_seed": official_seed,
        "before_controller": before_controller,
        "after_controller": after_controller,
        "network_sha256": shared_inputs["network_sha256"],
        "route_sha256": shared_inputs["route_sha256"],
        "turning_config_sha256": shared_inputs["turning_config_sha256"],
        "start_step": start_step,
        "end_step": end_step,
        "frames": end_step - start_step,
        "fps": fps,
        "camera": dict(camera),
        "git_sha": git_commit,
        "sumo_version": sumo_version,
        "ffmpeg_version": ffmpeg_version,
        "generated_at": utc_timestamp(),
        "verified_shared_inputs": dict(shared_inputs),
    }
    payload.update(dict(extra))
    return payload
