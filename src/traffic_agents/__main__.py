from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from traffic_agents.config import get_settings, load_scenario_config
from traffic_agents.experiments.runner import ExperimentRunner, load_experiment_config
from traffic_agents.simulation import TraCISimulationRunner


def main(argv: Sequence[str] = ()) -> int:
    if not argv:
        _print_application_info()
        return 0

    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


def cli() -> int:
    return main(sys.argv[1:])


def _print_application_info() -> None:
    settings = get_settings()
    print("Traffic Multi-Agent Control")
    print(f"environment={settings.app_env}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="traffic-agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulation_parser = subparsers.add_parser("simulation")
    simulation_subparsers = simulation_parser.add_subparsers(
        dest="simulation_command",
        required=True,
    )
    simulation_run_parser = simulation_subparsers.add_parser("run")
    simulation_run_parser.add_argument("--scenario", type=Path, required=True)
    simulation_run_parser.add_argument("--controller", dest="controller_id", default=None)
    simulation_run_parser.add_argument("--controller-id", dest="controller_id", default=None)
    simulation_run_parser.add_argument("--seed", type=int, default=None)
    simulation_run_parser.add_argument("--max-steps", type=int, default=None)
    simulation_run_parser.add_argument("--gui", action="store_true")
    simulation_run_parser.add_argument("--step-delay-ms", type=int, default=0)
    simulation_run_parser.add_argument("--no-manifest", action="store_true")
    simulation_run_parser.set_defaults(handler=_run_simulation)

    experiment_parser = subparsers.add_parser("experiment")
    experiment_subparsers = experiment_parser.add_subparsers(
        dest="experiment_command",
        required=True,
    )
    experiment_run_parser = experiment_subparsers.add_parser("run")
    experiment_run_parser.add_argument("--config", type=Path, required=True)
    experiment_run_parser.set_defaults(handler=_run_experiment)

    return parser


def _run_simulation(args: argparse.Namespace) -> int:
    scenario_config = load_scenario_config(args.scenario)
    updates: dict[str, object] = {}
    if args.controller_id is not None:
        updates["controller_id"] = args.controller_id
    if args.seed is not None:
        updates["simulation"] = scenario_config.simulation.model_copy(
            update={"seed": args.seed},
        )
    if updates:
        scenario_config = scenario_config.model_copy(update=updates)

    runner = TraCISimulationRunner(
        scenario_config=scenario_config,
        scenario_dir=args.scenario.parent,
        use_gui=args.gui,
        step_delay_seconds=args.step_delay_ms / 1000,
        max_steps=args.max_steps,
        controller_id=args.controller_id,
        write_manifest=not args.no_manifest,
    )

    print("simulation start")
    summary = runner.run()
    print("simulation end")
    print(f"started_at={summary.started_at}")
    print(f"ended_at={summary.ended_at}")
    print(f"controller_id={summary.controller_id}")
    print(f"controller_version={summary.controller_version}")
    print(f"demand_profile={summary.demand_profile}")
    print(f"seed={summary.seed}")
    print(f"steps_executed={summary.steps_executed}")
    print(f"measurement_steps_executed={summary.measurement_steps_executed}")
    print(f"vehicles_departed={summary.vehicles_departed}")
    print(f"vehicles_arrived={summary.vehicles_arrived}")
    print(f"total_vehicles_departed={summary.total_vehicles_departed}")
    print(f"total_vehicles_arrived={summary.total_vehicles_arrived}")
    print(f"wall_time_seconds={summary.wall_time_seconds:.3f}")
    if summary.manifest_path is not None:
        print(f"manifest={summary.manifest_path}")
    return 0


def _run_experiment(args: argparse.Namespace) -> int:
    config = load_experiment_config(args.config)
    runner = ExperimentRunner(config=config)

    print("experiment start")
    summary = runner.run()
    print("experiment end")
    print(f"experiment_id={summary.experiment_id}")
    print(f"runs_executed={len(summary.run_summaries)}")
    print(f"manifest={summary.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
