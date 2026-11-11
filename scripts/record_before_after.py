"""Grava um vídeo de comparação ANTES/DEPOIS sincronizado do SUMO (ferramenta de apresentação).

Exemplo:

    python scripts/record_before_after.py --scenario S4_LOCAL_SATURATION --seed 42 \\
        --before-controller B2_LOCAL_PRESSURE --after-controller C1_COOPERATIVE_COMPACT \\
        --camera a5_center --start-step 600 --end-step 2600 --fps 30 \\
        --output artifacts/demos/s4_seed42_b2_vs_c1

As duas simulações rodam em lock-step por passo de simulação. O frame ``k`` é o estado ao fim do
passo ``start_step + k``; os passos ``[start_step, end_step)`` são gravados. Requer SUMO
(sumo-gui) e FFmpeg. A ferramenta nunca altera controladores, demanda, seeds ou métricas.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from traffic_agents.replay import (
    DEMO_SEED,
    CameraPresetError,
    ReplayFairnessError,
    load_camera_presets,
)
from traffic_agents.replay.fairness import KNOWN_SCENARIOS
from traffic_agents.replay.recorder import (
    DEFAULT_PRESETS_PATH,
    RecordingRequest,
    ReplayError,
    record_before_after,
)
from traffic_agents.replay.video import FFmpegError


def build_parser(camera_choices: tuple[str, ...]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("--scenario", required=True, help=f"One of: {', '.join(KNOWN_SCENARIOS)}.")
    parser.add_argument(
        "--seed",
        type=int,
        default=DEMO_SEED,
        help=(
            f"Simulation seed (default {DEMO_SEED}, the official demonstration seed). Any other "
            "seed is for debugging only and the output is marked as non-official."
        ),
    )
    parser.add_argument("--before-controller", required=True)
    parser.add_argument("--after-controller", required=True)
    parser.add_argument("--camera", required=True, choices=camera_choices)
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--end-step", type=int, required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--step-delay-ms",
        type=int,
        default=0,
        help="Wall-clock pause after each recorded step, for watching live. No effect on results.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: artifacts/demos/s4_seed42_b2_vs_c1 style id).",
    )
    parser.add_argument(
        "--reuse-existing-run",
        action="store_true",
        help=(
            "Re-encode from previously captured frames when safe (requires an earlier run with "
            "--keep-frames and identical inputs/code); otherwise capture again."
        ),
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep frames/before and frames/after (000000.png ...) for debugging or reuse.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite a non-empty output.")
    parser.add_argument(
        "--reference-vehicle",
        choices=("auto", "on", "off"),
        default="auto",
        help="Highlight the deterministic reference vehicle (auto = camera preset decides).",
    )
    parser.add_argument("--camera-presets", type=Path, default=DEFAULT_PRESETS_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    presets_path = DEFAULT_PRESETS_PATH
    if "--camera-presets" in args_list:
        presets_path = Path(args_list[args_list.index("--camera-presets") + 1])
    try:
        camera_choices = tuple(sorted(load_camera_presets(presets_path).presets))
    except CameraPresetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args = build_parser(camera_choices).parse_args(args_list)
    if args.seed != DEMO_SEED:
        print(
            f"WARNING: seed {args.seed} is not the official demonstration seed {DEMO_SEED}; "
            "the output is marked NON-OFFICIAL (debugging only).",
            file=sys.stderr,
        )
    highlight = {"auto": None, "on": True, "off": False}[args.reference_vehicle]
    request = RecordingRequest(
        scenario=args.scenario,
        seed=args.seed,
        before_controller=args.before_controller,
        after_controller=args.after_controller,
        camera=args.camera,
        start_step=args.start_step,
        end_step=args.end_step,
        fps=args.fps,
        step_delay_ms=args.step_delay_ms,
        output=args.output,
        reuse_existing_run=args.reuse_existing_run,
        keep_frames=args.keep_frames,
        overwrite=args.overwrite,
        highlight_reference_vehicle=highlight,
        presets_path=args.camera_presets,
    )
    try:
        result = record_before_after(request)
    except (ReplayError, ReplayFairnessError, CameraPresetError, FFmpegError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"frames={result.frames} reused_capture={result.reused_capture}")
    for name, path in result.videos.items():
        print(f"{name}={path}")
    print(f"comparison={result.comparison_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
