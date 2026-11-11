"""Replay visual determinístico antes/depois (ferramenta de apresentação; não altera resultados)."""

from traffic_agents.replay.camera import (
    CameraPreset,
    CameraPresetError,
    CameraPresetFile,
    ViewWindow,
    load_camera_presets,
    resolve_view,
)
from traffic_agents.replay.fairness import DEMO_SEED, ReplayFairnessError

__all__ = [
    "DEMO_SEED",
    "CameraPreset",
    "CameraPresetError",
    "CameraPresetFile",
    "ReplayFairnessError",
    "ViewWindow",
    "load_camera_presets",
    "resolve_view",
]
