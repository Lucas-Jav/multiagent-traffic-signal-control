# Experimental Scenarios V1

All V1 scenarios use the same versioned 3x3 SUMO network:
`scenarios/grid_3x3/network.net.xml`.

The scenario YAML is the source of truth for:

- simulation seed;
- route file name;
- demand profile;
- demand level;
- turning ratios;
- demand schedule;
- flow origin, destination, time window, and rate.

Controllers must not receive scenario-specific configuration. A controller may be
selected at run time with `--controller`, but the scenario files do not define
special controller parameters.

The current V1 values below are experimental design parameters chosen before the
frozen campaign. They are not scientific results.

## Shared Defaults

- `scenario_id: grid_3x3`
- `duration_seconds: 3600`
- `warmup_seconds: 300`
- `step_length: 1.0`
- `seed: 42`
- `demand_level: MEDIUM`
- `controller_id: B0_FIXED`
- `communication.delay_steps: 0`
- `communication.drop_probability: 0.0`

`controller_id` is a default only. Validation must run at least `B0_FIXED` and
`B2_LOCAL_PRESSURE` as controller overrides for smoke execution.

## S1_BALANCED

Config: `scenarios/grid_3x3/scenario.yaml`

Route: `scenarios/grid_3x3/routes_s1_seed_42.rou.xml`

Turning ratios:

- `straight: 0.60`
- `left: 0.20`
- `right: 0.20`

Schedule:

- `full_run`: 0s to 3600s, stationary balanced demand.

Purpose: baseline demand with comparable traffic across the central east-west
and north-south corridors, including turning traffic.

## S2_DIRECTIONAL_PEAK

Config: `scenarios/grid_3x3/scenario_s2_directional_peak.yaml`

Route: `scenarios/grid_3x3/routes_s2_seed_42.rou.xml`

Turning ratios:

- `straight: 0.55`
- `left: 0.25`
- `right: 0.20`

Schedule:

- `full_run`: 0s to 3600s, east-west corridor peak with background
  north-south demand.

Purpose: evaluate coordination when a dominant direction exists. The dominant
axis still includes left and right turns, so this is not a straight-only
corridor test.

## S3_DEMAND_SHIFT

Config: `scenarios/grid_3x3/scenario_s3_demand_shift.yaml`

Route: `scenarios/grid_3x3/routes_s3_seed_42.rou.xml`

Turning ratios:

- `straight: 0.55`
- `left: 0.25`
- `right: 0.20`

Schedule:

- `north_south_peak`: 0s to 1800s, north-south demand dominates.
- `east_west_peak`: 1800s to 3600s, east-west demand dominates.

Purpose: test adaptation to an exogenous demand change without changing the
controller during the simulation.

## S4_LOCAL_SATURATION

Config: `scenarios/grid_3x3/scenario_s4_local_saturation.yaml`

Route: `scenarios/grid_3x3/routes_s4_seed_42.rou.xml`

Turning ratios:

- `straight: 0.50`
- `left: 0.25`
- `right: 0.25`

Schedule:

- `full_run`: 0s to 3600s, localized high demand around project intersections
  `A1`, `A2`, `A4`, and `A5`, with lower background demand elsewhere.

Purpose: create localized congestion and observe propagation/spillback. Capacity
is not modified artificially.

## Reproducibility

For each generated route file, the adjacent `*.metadata.json` records:

- `seed`;
- `demand_profile`;
- `demand_level`;
- `turning_ratios`;
- `schedule`;
- selected `flows`;
- `config_hash`;
- `scenario_hash`;
- `route_hash`.

The same seed and same scenario config must recreate the same `route_hash`.

Current V1 generated hashes:

| Profile | Scenario hash | Route hash |
| --- | --- | --- |
| `S1_BALANCED` | `5ca7623e5f78f9953c3d744cba87236fb2550763cdaec454d912f5dbe31c7ef0` | `eae4041e7c111a62db8932ca429f6b72f786769354069dcd56e7e7b125cc0f60` |
| `S2_DIRECTIONAL_PEAK` | `c40c2d545dca4500f87d6fd9ecba042c93614b159ee8f1431a8b3be087701ae5` | `7ae57a0f7c2d10063a847b1352465981037860979740fea4dd46663d20a7a442` |
| `S3_DEMAND_SHIFT` | `6385e1139ad56c25d64a80c4dccf278b9d2bb1e53628cd3207b4d679a46cc44d` | `c32842794c04b3641cc69e2fa3d2d1cb9eb185f88719d5665fed5223baa78bee` |
| `S4_LOCAL_SATURATION` | `f9fb7d74b3b3f94881ea684c7e4b9cf3e04dfc17f2945105b78b969a816db2cc` | `195de268c4838c6d364546d25f0017c72bc7f3aca68ebe12980c169f40de6cea` |

## Validation Procedure

For every scenario file:

1. Validate the YAML config with `uv run python scripts/validate_scenario.py`.
2. Generate routes with `uv run python scripts/generate_routes.py`.
3. Confirm every generated route has at least one route/flow.
4. Confirm traffic contains straight, left, and right demand.
5. Run a smoke simulation with `B0_FIXED`.
6. Run a smoke simulation with `B2_LOCAL_PRESSURE`.
7. Confirm no SUMO errors are emitted.
8. Regenerate with the same seed and confirm `route_hash` is unchanged.

The validation smoke runs are intentionally bounded. They are not the full
scientific campaign.

## V1 Validation Record

Executed on 2026-09-07:

- YAML validation passed for `S1_BALANCED`, `S2_DIRECTIONAL_PEAK`,
  `S3_DEMAND_SHIFT`, and `S4_LOCAL_SATURATION`.
- Route generation passed for all four scenarios with `duarouter`.
- Route XML validation found routed flows for all generated flows.
- Turn validation found straight and turn flows in every scenario:
  `S1` 4 straight and 8 turn flows; `S2` 4 straight and 8 turn flows; `S3`
  8 straight and 16 turn flows; `S4` 6 straight and 12 turn flows.
- Regenerating with seed 42 preserved all four `route_hash` values.
- Smoke `B0_FIXED` passed for all four scenarios with `--max-steps 120`.
- Smoke `B2_LOCAL_PRESSURE` passed for all four scenarios with
  `--max-steps 120`.
- No SUMO errors were emitted in route generation or smoke execution.
