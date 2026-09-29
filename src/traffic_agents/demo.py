from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from traffic_agents.config import ScenarioConfig, get_settings, load_scenario_config
from traffic_agents.simulation import SimulationRunSummary, TraCISimulationRunner

if TYPE_CHECKING:
    from traffic_agents.metrics import StepTelemetryRecord

SCENARIO_ALIASES: Mapping[str, Path] = {
    "S1_BALANCED": Path("scenarios/grid_3x3/scenario.yaml"),
    "S2_DIRECTIONAL_PEAK": Path("scenarios/grid_3x3/scenario_s2_directional_peak.yaml"),
    "S3_DEMAND_SHIFT": Path("scenarios/grid_3x3/scenario_s3_demand_shift.yaml"),
    "S4_LOCAL_SATURATION": Path("scenarios/grid_3x3/scenario_s4_local_saturation.yaml"),
}
DEFAULT_DEMO_SPEED_FACTOR = 25.0
DEFAULT_CONSOLE_INTERVAL_STEPS = 10


class DemoConfigurationError(ValueError):
    """Raised when a SUMO-GUI demo request is invalid."""


@dataclass(frozen=True)
class DemoConfig:
    scenario: str
    controller_id: str
    seed: int
    focus_agent: str | None = None
    speed_factor: float = DEFAULT_DEMO_SPEED_FACTOR
    max_steps: int | None = None
    write_artifact: bool = False
    console_interval_steps: int = DEFAULT_CONSOLE_INTERVAL_STEPS


@dataclass(frozen=True)
class DemoRunResult:
    summary: SimulationRunSummary
    scenario_path: Path


@dataclass
class FocusAgentConsole:
    focus_agent: str
    controller_provider: Callable[[], object | None]
    interval_steps: int = DEFAULT_CONSOLE_INTERVAL_STEPS
    _latest_printed_step: int | None = field(default=None, init=False)

    def consume(self, records: tuple[StepTelemetryRecord, ...]) -> None:
        focus_records = [record for record in records if record.intersection_id == self.focus_agent]
        if not focus_records:
            return
        step_index = focus_records[0].step_index
        if step_index % self.interval_steps != 0:
            return
        if self._latest_printed_step == step_index:
            return
        self._latest_printed_step = step_index
        print(_focus_agent_line(focus_records, self.controller_provider()))


def run_demo(config: DemoConfig) -> DemoRunResult:
    scenario_path = resolve_demo_scenario_path(config.scenario)
    scenario_config = load_scenario_config(scenario_path)
    scenario_config = _apply_demo_overrides(
        scenario_config,
        controller_id=config.controller_id,
        seed=config.seed,
    )

    if config.speed_factor <= 0:
        msg = "speed_factor must be positive"
        raise DemoConfigurationError(msg)
    if config.console_interval_steps <= 0:
        msg = "console_interval_steps must be positive"
        raise DemoConfigurationError(msg)

    runner: TraCISimulationRunner | None = None
    console = (
        FocusAgentConsole(
            focus_agent=config.focus_agent,
            controller_provider=lambda: runner.controller if runner is not None else None,
            interval_steps=config.console_interval_steps,
        )
        if config.focus_agent is not None
        else None
    )
    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=scenario_path.parent,
        use_gui=True,
        step_delay_seconds=scenario_config.step_length / config.speed_factor,
        max_steps=config.max_steps,
        controller_id=config.controller_id,
        artifacts_dir=get_settings().artifacts_dir / "demos" if config.write_artifact else None,
        write_manifest=config.write_artifact,
        run_mode="DEMO",
        step_telemetry_consumer=console.consume if console is not None else None,
    )
    summary = runner.run()
    return DemoRunResult(summary=summary, scenario_path=scenario_path)


def resolve_demo_scenario_path(scenario: str) -> Path:
    alias = scenario.upper()
    if alias in SCENARIO_ALIASES:
        return SCENARIO_ALIASES[alias]
    path = Path(scenario)
    if path.exists():
        return path
    supported = ", ".join(sorted(SCENARIO_ALIASES))
    msg = f"unknown demo scenario {scenario!r}; use one of {supported} or a scenario YAML path"
    raise DemoConfigurationError(msg)


def _apply_demo_overrides(
    scenario_config: ScenarioConfig,
    *,
    controller_id: str,
    seed: int,
) -> ScenarioConfig:
    return scenario_config.model_copy(
        update={
            "controller_id": controller_id,
            "simulation": scenario_config.simulation.model_copy(update={"seed": seed}),
        }
    )


def _focus_agent_line(records: Sequence[StepTelemetryRecord], controller: object | None) -> str:
    first = records[0]
    queue_total = sum(record.queue for record in records)
    queue_max = max(record.queue for record in records)
    safety_status = "override" if any(record.safety_override for record in records) else "ok"
    parts = [
        f"step={first.step_index}",
        f"controller={_controller_id(controller)}",
        f"agent={first.intersection_id}",
        f"phase={first.current_phase}",
        f"phase_elapsed={first.phase_elapsed:g}",
        f"queue_total={queue_total}",
        f"queue_max={queue_max}",
        f"requested_phase={first.requested_phase}",
        f"actual_phase={first.actual_phase}",
        f"safety={safety_status}",
        f"neighbors_used={_neighbors_used(controller, first.intersection_id)}",
    ]
    parts.extend(_cooperative_console_parts(controller))
    return "demo " + " ".join(parts)


def _controller_id(controller: object) -> str:
    value = getattr(controller, "controller_id", None)
    return str(value) if value is not None else "unknown"


def _cooperative_console_parts(controller: object) -> list[str]:
    parts: list[str] = []
    bus = getattr(controller, "_message_bus", None)
    metrics = getattr(bus, "metrics", None)
    if metrics is not None:
        parts.extend(
            [
                f"messages_received={getattr(metrics, 'messages_delivered', 0)}",
                f"messages_sent={getattr(metrics, 'messages_sent', 0)}",
                f"messages_dropped={getattr(metrics, 'messages_dropped', 0)}",
            ]
        )
    adjustment = getattr(controller, "last_adjustment_result", None)
    if adjustment is not None:
        parts.extend(
            [
                f"messages_fresh={getattr(adjustment, 'messages_fresh', 0)}",
                f"messages_stale={getattr(adjustment, 'messages_stale', 0)}",
                f"avg_message_age={getattr(adjustment, 'average_message_age', 0.0):g}",
                f"max_message_age={getattr(adjustment, 'max_observed_message_age', 0)}",
            ]
        )
    return parts


def _neighbors_used(controller: object | None, focus_agent: str) -> str:
    runtime_by_intersection = getattr(controller, "_runtime_by_intersection", None)
    if not isinstance(runtime_by_intersection, Mapping):
        return "-"
    runtime = runtime_by_intersection.get(focus_agent)
    adjustment = getattr(runtime, "adjustment", None)
    neighbor_ids = getattr(adjustment, "neighbor_ids", ())
    if not neighbor_ids:
        return "-"
    return ",".join(str(neighbor_id) for neighbor_id in neighbor_ids)
