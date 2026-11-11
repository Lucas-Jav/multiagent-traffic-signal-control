"""Presets de câmera do replay visual e o mapeamento mundo -> pixel usado pelos overlays."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from traffic_agents.replay.network_geometry import NetworkGeometry

REQUIRED_PRESETS: tuple[str, ...] = ("whole_grid", "a5_center", "west_to_center", "reference_route")
SUPPORTED_PRESET_FILE_VERSION = 1


class CameraPresetError(ValueError):
    """Lançada para arquivos de preset malformados ou câmeras desconhecidas / não resolvíveis."""


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CameraFocus(_Model):
    network: bool = False
    intersections: tuple[str, ...] = ()
    edges: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_single_focus(self) -> Self:
        chosen = [bool(self.network), bool(self.intersections), bool(self.edges)]
        if sum(chosen) != 1:
            msg = "focus must define exactly one of network, intersections or edges"
            raise ValueError(msg)
        return self


class CameraPreset(_Model):
    description: str
    focus: CameraFocus
    margin_m: Annotated[float, Field(ge=0.0)]
    labels: tuple[str, ...] = ()
    highlight_reference_route: bool = False
    highlight_reference_vehicle: bool = False


class Resolution(_Model):
    width: PositiveInt
    height: PositiveInt

    @model_validator(mode="after")
    def validate_even(self) -> Self:
        if self.width % 2 or self.height % 2:
            msg = "resolution must be even in both dimensions (H.264 yuv420p)"
            raise ValueError(msg)
        return self


class CameraPresetFile(_Model):
    version: int
    resolution: Resolution
    presets: Mapping[str, CameraPreset]

    @model_validator(mode="after")
    def validate_required(self) -> Self:
        if self.version != SUPPORTED_PRESET_FILE_VERSION:
            msg = f"unsupported camera preset file version: {self.version}"
            raise ValueError(msg)
        missing = [name for name in REQUIRED_PRESETS if name not in self.presets]
        if missing:
            msg = f"camera preset file is missing required presets: {missing}"
            raise ValueError(msg)
        return self

    def get(self, name: str) -> CameraPreset:
        try:
            return self.presets[name]
        except KeyError:
            valid = ", ".join(sorted(self.presets))
            msg = f"unknown camera preset {name!r}; valid presets: {valid}"
            raise CameraPresetError(msg) from None


def load_camera_presets(path: Path) -> CameraPresetFile:
    try:
        with path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        msg = f"cannot read camera preset file {path}: {exc}"
        raise CameraPresetError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"camera preset file must be a YAML mapping: {path}"
        raise CameraPresetError(msg)
    try:
        return CameraPresetFile.model_validate(payload)
    except ValueError as exc:
        msg = f"invalid camera preset file {path}: {exc}"
        raise CameraPresetError(msg) from exc


@dataclass(frozen=True)
class ViewWindow:
    """Retângulo do mundo exibido por um painel; sua proporção é igual à do painel."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    @property
    def width_m(self) -> float:
        return self.max_x - self.min_x

    @property
    def height_m(self) -> float:
        return self.max_y - self.min_y

    def world_to_pixel(
        self,
        x: float,
        y: float,
        *,
        width_px: int,
        height_px: int,
    ) -> tuple[float, float]:
        """Pixel de um ponto do mundo. O y da imagem cresce para baixo; o y do mundo, para cima."""

        scale = width_px / self.width_m
        cx, cy = self.center
        return (width_px / 2 + (x - cx) * scale, height_px / 2 - (y - cy) * scale)


def focus_points(
    preset: CameraPreset,
    geometry: NetworkGeometry,
    intersection_to_junction: Mapping[str, str],
) -> list[tuple[float, float]]:
    focus = preset.focus
    if focus.network:
        return list(geometry.junctions.values())
    points: list[tuple[float, float]] = []
    if focus.intersections:
        for label in focus.intersections:
            if label not in intersection_to_junction:
                msg = f"camera focus references unknown intersection: {label}"
                raise CameraPresetError(msg)
            points.append(geometry.junction_position(intersection_to_junction[label]))
        return points
    for edge_id in focus.edges:
        if edge_id not in geometry.edges:
            msg = f"camera focus references unknown edge: {edge_id}"
            raise CameraPresetError(msg)
        for junction_id in geometry.edge_endpoints(edge_id):
            points.append(geometry.junction_position(junction_id))
    return points


def resolve_view(
    preset: CameraPreset,
    geometry: NetworkGeometry,
    intersection_to_junction: Mapping[str, str],
    *,
    width_px: int,
    height_px: int,
) -> ViewWindow:
    """Caixa delimitadora do foco mais margem, expandida à proporção do painel (nunca cortada)."""

    points = focus_points(preset, geometry, intersection_to_junction)
    min_x = min(x for x, _ in points) - preset.margin_m
    max_x = max(x for x, _ in points) + preset.margin_m
    min_y = min(y for _, y in points) - preset.margin_m
    max_y = max(y for _, y in points) + preset.margin_m
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    aspect = width_px / height_px
    if width / height < aspect:
        width = height * aspect
    else:
        height = width / aspect
    return ViewWindow(cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
