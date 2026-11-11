from __future__ import annotations

import copy
import importlib.util
import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from traffic_agents.controllers import (
    FIXED_TIME_CONTROLLER_ID,
    FIXED_TIME_PLAN_CONTROLLER_ID,
    FixedTimeController,
    FixedTimePlan,
    FixedTimePlanController,
    FixedTimePlanError,
    TrafficLightTiming,
    build_controller,
    load_plan,
    plan_from_payload,
)
from traffic_agents.controllers.fixed_time_plan import (
    DEFAULT_FIXED_TIME_PLAN_PATH,
    cycle_start_state,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
NETWORK_PATH = REPO_ROOT / "scenarios" / "grid_3x3" / "network.net.xml"
STATES = (
    "GGGrrrrrrrrr",
    "yyyrrrrrrrrr",
    "rrrrrrrrrrrr",
    "rrrGGGrrrrrr",
    "rrryyyrrrrrr",
    "rrrrrrrrrrrr",
    "rrrrrrGGGrrr",
    "rrrrrryyyrrr",
    "rrrrrrrrrrrr",
    "rrrrrrrrrGGG",
    "rrrrrrrrryyy",
    "rrrrrrrrrrrr",
)


def _plan(
    cycle: int = 100, greens: tuple[int, ...] = (20, 20, 20, 20), offset: int = 0
) -> FixedTimePlan:
    return FixedTimePlan(
        plan_id="test_plan",
        cycle_seconds=cycle,
        traffic_lights={
            "A0": TrafficLightTiming(greens, offset),
            "B1": TrafficLightTiming(greens, (offset + 30) % cycle),
        },
    )


@dataclass
class FakePhase:
    duration: float
    state: str
    minDur: float  # noqa: N815 - mirrors the TraCI attribute
    maxDur: float  # noqa: N815


@dataclass
class FakeLogic:
    phases: tuple[FakePhase, ...]
    currentPhaseIndex: int = 0  # noqa: N815


@dataclass
class FakeTrafficLight:
    calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    def getAllProgramLogics(self, tls_id: str) -> list[FakeLogic]:  # noqa: N802
        phases = tuple(FakePhase(18.0, state, 18.0, 18.0) for state in STATES)
        return [FakeLogic(phases=phases)]

    def setProgramLogic(self, tls_id: str, logic: FakeLogic) -> None:  # noqa: N802
        self.calls.append(("setProgramLogic", (tls_id, copy.deepcopy(logic))))

    def setPhase(self, tls_id: str, index: int) -> None:  # noqa: N802
        self.calls.append(("setPhase", (tls_id, index)))

    def setPhaseDuration(self, tls_id: str, duration: float) -> None:  # noqa: N802
        self.calls.append(("setPhaseDuration", (tls_id, duration)))


@dataclass
class FakeConnection:
    trafficlight: FakeTrafficLight = field(default_factory=FakeTrafficLight)


class ExplodingConnection:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"traffic-responsive access: {name}")


def test_valid_plan_cycle_is_consistent_with_phase_durations() -> None:
    plan = _plan(cycle=116, greens=(24, 24, 24, 24))

    for tls_id in plan.traffic_lights:
        durations = plan.phase_durations(tls_id)
        assert sum(durations) == plan.cycle_seconds
        assert durations[1::3] == (3, 3, 3, 3)  # amarelo preservado
        assert durations[2::3] == (2, 2, 2, 2)  # vermelho total preservado
        assert durations[0::3] == plan.traffic_lights[tls_id].green_seconds


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"cycle": 99}, "cycle"),
        ({"greens": (9, 20, 20, 20), "cycle": 89}, "outside"),
        ({"greens": (61, 20, 20, 20), "cycle": 141}, "outside"),
        ({"greens": (20, 20, 20), "cycle": 80}, "expected 4 greens"),
        ({"offset": 100}, "offset"),
    ],
)
def test_invalid_plans_are_rejected(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(FixedTimePlanError, match=message):
        _plan(**kwargs)


def test_safety_timings_cannot_be_changed() -> None:
    with pytest.raises(FixedTimePlanError, match="safety timings"):
        FixedTimePlan(
            plan_id="bad",
            cycle_seconds=96,
            yellow_seconds=4,
            traffic_lights={"A0": TrafficLightTiming((20, 20, 20, 20), 0)},
        )


def test_start_state_matches_sumo_native_offsets_of_the_historical_plan() -> None:
    durations = (18, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2)

    # Verificado contra os offsets nativos do tlLogic via TraCI no instante de simulação 0.
    assert cycle_start_state(durations, 0) == (0, 18)
    assert cycle_start_state(durations, 60) == (3, 5)  # A0
    assert cycle_start_state(durations, 30) == (7, 3)  # A1


def test_install_preserves_states_yellow_all_red_and_sets_offset() -> None:
    controller = FixedTimePlanController(_plan(offset=0))
    connection = FakeConnection()

    controller.before_simulation_step(connection)

    installed = {
        tls: logic
        for name, (tls, logic) in connection.trafficlight.calls
        if name == "setProgramLogic"
    }
    assert set(installed) == {"A0", "B1"}
    for logic in installed.values():
        assert [phase.state for phase in logic.phases] == list(STATES)
        assert [phase.duration for phase in logic.phases] == [
            20.0,
            3.0,
            2.0,
            20.0,
            3.0,
            2.0,
            20.0,
            3.0,
            2.0,
            20.0,
            3.0,
            2.0,
        ]
        assert all(phase.minDur == phase.maxDur == phase.duration for phase in logic.phases)
    # offset 0 começa na primeira fase com o verde inteiro restante; offset 30 está no meio do ciclo
    assert ("setPhase", ("A0", 0)) in connection.trafficlight.calls
    assert ("setPhaseDuration", ("A0", 20.0)) in connection.trafficlight.calls
    index_b1, remaining_b1 = cycle_start_state(_plan().phase_durations("B1"), 30)
    assert ("setPhase", ("B1", index_b1)) in connection.trafficlight.calls
    assert ("setPhaseDuration", ("B1", float(remaining_b1))) in connection.trafficlight.calls


def test_controller_is_not_traffic_responsive() -> None:
    controller = FixedTimePlanController(_plan())
    connection = FakeConnection()
    controller.before_simulation_step(connection)
    calls_after_install = len(connection.trafficlight.calls)

    # Após a instalação única, nenhum acesso à conexão ocorre.
    exploding = ExplodingConnection()
    for _ in range(50):
        controller.before_simulation_step(exploding)
        controller.after_simulation_step(exploding)

    assert controller.installed
    assert len(connection.trafficlight.calls) == calls_after_install
    assert not hasattr(controller, "pop_step_telemetry_records")
    assert controller.manifest_metadata()["traffic_responsive"] is False
    assert controller.manifest_metadata()["adaptive_adjustments_enabled"] is False


def test_plan_payload_round_trip_and_hash_are_reproducible(tmp_path: Path) -> None:
    plan = _plan(offset=10)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan.to_payload()), encoding="utf-8")

    loaded = load_plan(path)

    assert loaded.to_payload() == plan.to_payload()
    assert loaded.sha256() == plan.sha256()
    assert plan_from_payload(plan.to_payload()).sha256() == plan.sha256()
    assert _plan(offset=11).sha256() != plan.sha256()
    # a proveniência não afeta o hash de identidade
    with_provenance = FixedTimePlan(
        plan_id=plan.plan_id,
        cycle_seconds=plan.cycle_seconds,
        traffic_lights=plan.traffic_lights,
        provenance={"note": "x"},
    )
    assert with_provenance.sha256() == plan.sha256()


def test_baseline_identity_in_manifests(tmp_path: Path) -> None:
    historical = build_controller(FIXED_TIME_CONTROLLER_ID)
    assert isinstance(historical, FixedTimeController)
    assert historical.manifest_metadata() == {
        "controller_id": "B0_FIXED",
        "controller_version": "0.1.0",
        "adaptive_adjustments_enabled": False,
    }

    plan = _plan()
    metadata = FixedTimePlanController(plan).manifest_metadata()
    assert metadata["controller_id"] == FIXED_TIME_PLAN_CONTROLLER_ID == "B0_FIXED_CALIBRATED"
    assert metadata["fixed_time_plan_id"] == "test_plan"
    assert metadata["fixed_time_plan_sha256"] == plan.sha256()
    assert metadata["fixed_time_cycle_seconds"] == 100
    assert metadata["baseline_family"] == "FIXED_TIME_CALIBRATED"


def test_final_calibrated_plan_file_is_valid_and_loadable() -> None:
    plan = load_plan(DEFAULT_FIXED_TIME_PLAN_PATH)

    assert plan.method == "EMPIRICAL_FIXED_TIME"
    assert (plan.yellow_seconds, plan.all_red_seconds) == (3, 2)
    assert len(plan.traffic_lights) == 9
    build = build_controller(FIXED_TIME_PLAN_CONTROLLER_ID)
    assert isinstance(build, FixedTimePlanController)
    assert build.plan.sha256() == plan.sha256()
    for tls_id in plan.traffic_lights:
        assert sum(plan.phase_durations(tls_id)) == plan.cycle_seconds


def _load_calibration_script() -> types.ModuleType:
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "calibrate_fixed_time", REPO_ROOT / "scripts" / "calibrate_fixed_time.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_calibration_split_allocation_is_deterministic_and_bounded() -> None:
    module = _load_calibration_script()

    greens = module.allocate_greens([0.1, 0.2, 0.3, 0.4], 80)

    assert greens == module.allocate_greens([0.1, 0.2, 0.3, 0.4], 80)
    assert sum(greens) == 80
    assert all(module.MIN_GREEN <= green <= module.MAX_GREEN for green in greens)
    assert greens == sorted(greens)  # proporcional à ordem de participação
    assert module.allocate_greens([0.25] * 4, 80) == [20, 20, 20, 20]


def test_calibration_candidates_cover_the_predeclared_grid_and_are_valid() -> None:
    module = _load_calibration_script()
    shares = {f"{col}{row}": [0.25, 0.25, 0.25, 0.25] for col in "ABC" for row in range(3)}
    logical_index = {tls: index + 1 for index, tls in enumerate(sorted(shares))}

    plans = [
        module.build_plan(cycle, split, offset, shares, logical_index)
        for cycle in module.CYCLES
        for split in module.SPLITS
        for offset in module.OFFSETS
    ]

    assert len(plans) == len(module.CYCLES) * len(module.SPLITS) * len(module.OFFSETS)
    assert len({plan.plan_id for plan in plans}) == len(plans)
    for plan in plans:  # FixedTimePlan valida ciclo/verdes/offsets/segurança na construção
        assert plan.yellow_seconds == 3
        assert plan.all_red_seconds == 2
    assert module.predeclaration()["method"].startswith("EMPIRICAL_FIXED_TIME")


def test_calibration_objective_ranks_reference_at_one_and_applies_guards() -> None:
    module = _load_calibration_script()
    rows = []
    for plan_id, completion, queue, loss in (
        (module.REFERENCE_ID, 0.80, 100.0, 50.0),
        ("better", 0.90, 80.0, 40.0),
        ("collapsed", 0.50, 70.0, 30.0),
    ):
        for scenario in module.SCENARIOS:
            rows.append(
                {
                    "plan_id": plan_id,
                    "scenario": scenario,
                    "seed": 1,
                    "completion_ratio_offered": completion,
                    "departure_ratio": completion,
                    "mean_network_queue_vehicles": queue,
                    "mean_time_loss": loss,
                }
            )

    evaluations = {
        e["plan_id"]: e for e in module.evaluate(rows, [module.REFERENCE_ID, "better", "collapsed"])
    }

    assert evaluations[module.REFERENCE_ID]["J"] == pytest.approx(1.0)
    assert evaluations["better"]["J"] < 1.0
    assert evaluations["better"]["guards_ok"]
    assert not evaluations["collapsed"]["guards_ok"]  # o colapso de conclusão é rejeitado
    picked = module.pick(
        list(evaluations.values()), {"better": 100, "collapsed": 100, module.REFERENCE_ID: 98}
    )
    assert picked is not None
    assert picked["plan_id"] == "better"
