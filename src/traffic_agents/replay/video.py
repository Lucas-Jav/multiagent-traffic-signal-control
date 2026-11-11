"""Codificação H.264 local determinística com FFmpeg (um requisito externo).

O FFmpeg é procurado nesta ordem: variável de ambiente ``FFMPEG_BINARY``, ``ffmpeg`` no ``PATH``
e, por fim, o binário incluído no pacote opcional ``imageio-ffmpeg``
(``uv pip install imageio-ffmpeg``). Os frames são enviados ao FFmpeg como RGB bruto, portanto
nenhum arquivo de imagem intermediário é necessário.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from PIL import Image


class FFmpegError(RuntimeError):
    """Lançada quando o FFmpeg está ausente ou falha."""


def find_ffmpeg() -> str:
    configured = os.environ.get("FFMPEG_BINARY")
    if configured:
        if Path(configured).exists():
            return configured
        msg = f"FFMPEG_BINARY does not exist: {configured}"
        raise FFmpegError(msg)
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        bundled = importlib.import_module("imageio_ffmpeg")
        return str(bundled.get_ffmpeg_exe())
    except (ImportError, RuntimeError):
        pass
    msg = (
        "FFmpeg not found. Install FFmpeg and put it on PATH (or set FFMPEG_BINARY), or run "
        "`uv pip install imageio-ffmpeg` to use its bundled binary."
    )
    raise FFmpegError(msg)


def ffmpeg_version(ffmpeg: str) -> str:
    completed = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, check=False)
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    return first_line.strip() or "unknown"


def encode_command(ffmpeg: str, *, width: int, height: int, fps: int, output: Path) -> list[str]:
    if width % 2 or height % 2:
        msg = f"video dimensions must be even, got {width}x{height}"
        raise FFmpegError(msg)
    return [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-threads",
        "1",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-map_metadata",
        "-1",
        "-movflags",
        "+faststart",
        str(output),
    ]


def encode_frames(
    frames: Iterable[Image.Image],
    *,
    width: int,
    height: int,
    fps: int,
    output: Path,
    ffmpeg: str,
) -> int:
    """Codifica frames (todos ``width`` x ``height``) em ``output``; retorna o nº de frames."""

    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        encode_command(ffmpeg, width=width, height=height, fps=fps, output=output),
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    count = 0
    try:
        for frame in frames:
            if frame.size != (width, height):
                msg = f"frame {count} is {frame.size}, expected {(width, height)}"
                raise FFmpegError(msg)
            process.stdin.write(frame.convert("RGB").tobytes())
            count += 1
        process.stdin.close()
    except BaseException:
        process.kill()
        process.wait()
        raise
    stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
    if process.wait() != 0:
        msg = f"FFmpeg failed for {output.name}: {stderr.strip()}"
        raise FFmpegError(msg)
    if count == 0:
        msg = f"no frames were provided for {output.name}"
        raise FFmpegError(msg)
    return count
