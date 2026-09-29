from __future__ import annotations

import importlib.util
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from traffic_agents.experiments.runner import load_experiment_config


def load_generator() -> Any:
    script_path = Path("scripts/generate_s5_matrix.py")
    spec = importlib.util.spec_from_file_location("generate_s5_matrix", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_s5_matrix_writes_deterministic_c1_and_c2_configs(tmp_path: Path) -> None:
    generator = load_generator()
    output_dir = tmp_path / "configs"

    first = generator.generate_s5_configs(
        output_dir=output_dir,
        base_scenario=Path("scenarios/grid_3x3/scenario_s2_directional_peak.yaml"),
    )
    first_payloads = {path.name: path.read_text(encoding="utf-8") for path in first}
    second = generator.generate_s5_configs(
        output_dir=output_dir,
        base_scenario=Path("scenarios/grid_3x3/scenario_s2_directional_peak.yaml"),
    )
    second_payloads = {path.name: path.read_text(encoding="utf-8") for path in second}

    assert first_payloads == second_payloads
    assert {path.name for path in first} == {
        "s5_communication_degradation_c1.yaml",
        "s5_communication_degradation_c2.yaml",
    }


def test_generated_s5_c1_config_has_reference_and_full_matrix(tmp_path: Path) -> None:
    generator = load_generator()
    output_dir = tmp_path / "configs"
    generator.generate_s5_configs(
        output_dir=output_dir,
        base_scenario=Path("scenarios/grid_3x3/scenario_s2_directional_peak.yaml"),
    )
    config_path = output_dir / "s5_communication_degradation_c1.yaml"

    config = load_experiment_config(config_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config.experiment_id == "s5_communication_degradation_c1"
    assert config.matrix is not None
    assert tuple(config.matrix.delay_steps) == (0, 1, 3, 5)
    assert tuple(config.matrix.drop_probability) == (0.0, 0.05, 0.10, 0.25)
    assert len(config.runs) == 17
    assert len({run.run_id for run in config.runs}) == 17

    reference_runs = [run for run in config.runs if run.controller_id == "B2_LOCAL_PRESSURE"]
    c1_runs = [run for run in config.runs if run.controller_id == "C1_COOPERATIVE_COMPACT"]
    assert [run.run_id for run in reference_runs] == ["s5_b2_reference"]
    assert len(c1_runs) == 16

    combos = {
        (
            int(run.communication.delay_steps),
            float(run.communication.drop_probability),
        )
        for run in c1_runs
    }
    assert combos == set(product((0, 1, 3, 5), (0.0, 0.05, 0.10, 0.25)))
    assert all(run.scenario_base == "S2_DIRECTIONAL_PEAK" for run in config.runs)
    assert all(
        run.communication_seed_policy == "derived_from_simulation_seed_delay_drop"
        for run in config.runs
    )
    assert all(run.communication.rng_seed is None for run in config.runs)
    assert all(run.communication.max_message_age_steps == 1 for run in config.runs)
    assert "s5_c1_delay3_drop010" in {run["run_id"] for run in payload["runs"]}
