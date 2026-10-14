"""Frame composition: pane header, intersection labels, corridor highlight, footer, banners.

Overlays are drawn with Pillow on top of the raw SUMO screenshots. The SUMO network and its
geometry are never modified. The fonts shipped with matplotlib (DejaVu) are used so the output
does not depend on the fonts installed on the machine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

from traffic_agents.replay.camera import ViewWindow

DISCLAIMER = "Visualização ilustrativa — resultados científicos utilizam múltiplas seeds."
BEFORE_TITLE = "ANTES"
AFTER_TITLE = "DEPOIS"
HEADER_HEIGHT = 56
FOOTER_HEIGHT = 64
DIVIDER_WIDTH = 4

_HEADER_COLORS = {BEFORE_TITLE: (55, 71, 79), AFTER_TITLE: (0, 105, 92)}
_FOOTER_COLOR = (33, 33, 33)
_DIVIDER_COLOR = (255, 255, 255)
_ROUTE_BAND_RGBA = (255, 193, 7, 80)
_LABEL_BOX_RGBA = (255, 255, 255, 215)
_SHOCK_RGBA = (198, 40, 40, 235)
_WHITE = (255, 255, 255)


@cache
def _font(size: int, *, bold: bool) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / name
    return ImageFont.truetype(str(path), size)


def format_clock(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass(frozen=True)
class PaneContext:
    """Static (per recording) information every pane needs."""

    title: str
    controller_id: str
    view: ViewWindow
    width: int
    height: int
    label_points: Mapping[str, tuple[float, float]]
    route_polyline: Sequence[tuple[float, float]] = ()


@dataclass(frozen=True)
class FrameState:
    """Dynamic (per frame) information: all of it is annotation-only."""

    simulation_time_s: float
    network_queue: int | None = None
    arrived_count: int | None = None
    shock_active: bool = False


@dataclass(frozen=True)
class FooterInfo:
    scenario_id: str
    seed: int
    official: bool


def _draw_route_band(image: Image.Image, context: PaneContext) -> Image.Image:
    if not context.route_polyline:
        return image
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    points = [
        context.view.world_to_pixel(x, y, width_px=context.width, height_px=context.height)
        for x, y in context.route_polyline
    ]
    scale = context.width / context.view.width_m
    draw.line(points, fill=_ROUTE_BAND_RGBA, width=max(6, round(9 * scale)), joint="curve")
    return Image.alpha_composite(image, layer)


def _draw_labels(image: Image.Image, context: PaneContext) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(20, bold=True)
    for label, (x, y) in context.label_points.items():
        px, py = context.view.world_to_pixel(x, y, width_px=context.width, height_px=context.height)
        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        text_w, text_h = right - left, bottom - top
        # Offset up-right of the junction so the label does not cover the stop lines.
        x0, y0 = px + 14, py - 14 - text_h - 8
        draw.rounded_rectangle(
            (x0, y0, x0 + text_w + 12, y0 + text_h + 8), radius=5, fill=_LABEL_BOX_RGBA
        )
        draw.text((x0 + 6 - left, y0 + 4 - top), label, font=font, fill=(20, 20, 20, 255))
    return Image.alpha_composite(image, layer)


def _draw_shock_banner(image: Image.Image, text: str) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(44, bold=True)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = right - left, bottom - top
    x0 = (image.width - text_w) / 2 - 24
    y0 = 24
    draw.rounded_rectangle(
        (x0, y0, x0 + text_w + 48, y0 + text_h + 28), radius=10, fill=_SHOCK_RGBA
    )
    draw.text((x0 + 24 - left, y0 + 14 - top), text, font=font, fill=(*_WHITE, 255))
    return Image.alpha_composite(image, layer)


def compose_pane(
    raw: Image.Image,
    context: PaneContext,
    state: FrameState,
    *,
    shock_text: str,
) -> Image.Image:
    """Raw SUMO frame + labels/corridor/shock banner + header strip. Size: W x (H + header)."""

    if raw.size != (context.width, context.height):
        msg = f"raw frame is {raw.size}, expected {(context.width, context.height)}"
        raise ValueError(msg)
    canvas = raw.convert("RGBA")
    canvas = _draw_route_band(canvas, context)
    canvas = _draw_labels(canvas, context)
    if state.shock_active:
        canvas = _draw_shock_banner(canvas, shock_text)

    pane = Image.new("RGB", (context.width, context.height + HEADER_HEIGHT), _FOOTER_COLOR)
    draw = ImageDraw.Draw(pane)
    draw.rectangle(
        (0, 0, context.width, HEADER_HEIGHT), fill=_HEADER_COLORS.get(context.title, _FOOTER_COLOR)
    )
    title_font = _font(30, bold=True)
    body_font = _font(22, bold=False)
    draw.text((16, 9), context.title, font=title_font, fill=_WHITE)
    title_w = draw.textlength(context.title, font=title_font)
    draw.text((16 + title_w + 18, 15), context.controller_id, font=body_font, fill=_WHITE)
    metrics = []
    if state.network_queue is not None:
        metrics.append(f"Fila: {state.network_queue} veíc. parados")
    if state.arrived_count is not None:
        metrics.append(f"Chegaram: {state.arrived_count}")
    if metrics:
        text = "   |   ".join(metrics)
        draw.text(
            (context.width - 16 - draw.textlength(text, font=body_font), 15),
            text,
            font=body_font,
            fill=_WHITE,
        )
    pane.paste(canvas.convert("RGB"), (0, HEADER_HEIGHT))
    return pane


def _footer(width: int, state: FrameState, info: FooterInfo) -> Image.Image:
    footer = Image.new("RGB", (width, FOOTER_HEIGHT), _FOOTER_COLOR)
    draw = ImageDraw.Draw(footer)
    seed_text = f"Seed: {info.seed}" if info.official else f"Seed: {info.seed} (NÃO OFICIAL)"
    clock = format_clock(state.simulation_time_s)
    line = (
        f"Cenário: {info.scenario_id}   |   {seed_text}   |   "
        f"Tempo da simulação: {clock} (t = {state.simulation_time_s:.0f} s)"
    )
    draw.text((16, 7), line, font=_font(22, bold=True), fill=_WHITE)
    draw.text((16, 37), DISCLAIMER, font=_font(18, bold=False), fill=(200, 200, 200))
    return footer


def stack_with_footer(pane: Image.Image, state: FrameState, info: FooterInfo) -> Image.Image:
    footer = _footer(pane.width, state, info)
    frame = Image.new("RGB", (pane.width, pane.height + FOOTER_HEIGHT))
    frame.paste(pane, (0, 0))
    frame.paste(footer, (0, pane.height))
    return frame


def side_by_side(
    before_pane: Image.Image,
    after_pane: Image.Image,
    state: FrameState,
    info: FooterInfo,
) -> Image.Image:
    if before_pane.size != after_pane.size:
        msg = "BEFORE and AFTER panes must have the same size"
        raise ValueError(msg)
    width = before_pane.width * 2 + DIVIDER_WIDTH
    frame = Image.new("RGB", (width, before_pane.height + FOOTER_HEIGHT), _DIVIDER_COLOR)
    frame.paste(before_pane, (0, 0))
    frame.paste(after_pane, (before_pane.width + DIVIDER_WIDTH, 0))
    frame.paste(_footer(width, state, info), (0, before_pane.height))
    return frame
