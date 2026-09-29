# Campaign Plan V1

Status: prepared for review, not approved for full campaign execution.

This document freezes the evaluation intent and the operational checks for the
final V1 campaign. The full campaign must not be executed until explicit
approval after the blocking pre-flight items are resolved.

## Objective

Evaluate traffic-signal controllers under the same network, route, demand,
turning-ratio, phase-plan, safety, duration, warmup, and step-length inputs for
each `scenario + seed` pair. Only the controller changes inside a comparable
pair.

The mini pilot in this plan is a pipeline check only. Its artifacts must not be
used as final scientific results.

## Controllers

The main campaign includes:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

For the main campaign, `C1_COOPERATIVE_COMPACT` and
`C2_COOPERATIVE_EXPANDED` use:

- `communication.delay_steps: 0`
- `communication.drop_probability: 0.0`
- `communication.rng_seed: null`
- `communication.max_message_age_steps: 1`

Communication degradation remains separated in S5.

## Scenarios

The main campaign includes:

- `S1_BALANCED`: `scenarios/grid_3x3/scenario.yaml`
- `S2_DIRECTIONAL_PEAK`:
  `scenarios/grid_3x3/scenario_s2_directional_peak.yaml`
- `S3_DEMAND_SHIFT`: `scenarios/grid_3x3/scenario_s3_demand_shift.yaml`
- `S4_LOCAL_SATURATION`:
  `scenarios/grid_3x3/scenario_s4_local_saturation.yaml`

`S5` remains a separate communication-robustness campaign.

## Seeds

Seed pool version: `campaign_v1_seed_pool_2026-09-29`.

Ordered seed pool:

```text
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

Rules:

- The ordered pool is fixed before final campaign results.
- Seeds must not be selected, removed, or reordered based on controller
  performance.
- The final number of seeds is `N_final`, chosen after the pilot from observed
  runtime, approximate variability, and available compute budget.
- The approved final campaign must use the first `N_final` seeds from the pool.
- Pilot runs are excluded from final results even when they use seeds from this
  pool; approved final runs must be re-executed after final freeze.

Planned main-run count:

```text
4 scenarios * 5 controllers * N_final = 20 * N_final runs
```

Pool ceiling, if all listed seeds are approved:

```text
4 scenarios * 5 controllers * 10 seeds = 200 runs
```

Mini pilot executed:

```text
1 scenario * 5 controllers * 2 seeds = 10 runs
```

## Turning Ratios

Turning ratios are scenario inputs and remain fixed across controllers:

- `S1_BALANCED`: straight `0.60`, left `0.20`, right `0.20`
- `S2_DIRECTIONAL_PEAK`: straight `0.55`, left `0.25`, right `0.20`
- `S3_DEMAND_SHIFT`: straight `0.55`, left `0.25`, right `0.20`
- `S4_LOCAL_SATURATION`: straight `0.50`, left `0.25`, right `0.25`

Turning ratios must not be altered between controllers.

## Fairness Contract

For every `scenario + seed`, all controllers must use exactly the same:

- network
- route file
- route metadata
- turning ratio
- demand profile, demand level, demand schedule, and flow rates
- duration
- warmup
- step length
- phase plan
- movement model
- safety constraints
- communication topology

Only `controller_id` changes across the five comparable runs.

The final executable campaign config must use explicit `runs` entries, not the
short `controllers + seeds` form, so each `scenario + seed` can point at its
own seed-specific scenario YAML and route file.

## Expected Files

Plan and configuration:

- `campaign_plan.md`
- final campaign config, to be created after approval:
  `experiments/configs/campaign_v1_main.yaml`
- optional resume configs:
  `experiments/configs/campaign_v1_resume_<batch>.yaml`

Prepared final scenario material, to be generated after `N_final` approval:

- `scenarios/grid_3x3/campaign_v1/network.net.xml`
- `scenarios/grid_3x3/campaign_v1/metadata.json`
- `scenarios/grid_3x3/campaign_v1/viewsettings.xml`
- `scenarios/grid_3x3/campaign_v1/scenario_s<1-4>_seed_<seed>.yaml`
- `scenarios/grid_3x3/campaign_v1/routes_s<1-4>_seed_<seed>.rou.xml`
- `scenarios/grid_3x3/campaign_v1/routes_s<1-4>_seed_<seed>.metadata.json`

Frozen artifacts:

- `artifacts/experiments/campaign_v1_main/frozen/experiment.yaml`
- `artifacts/experiments/campaign_v1_main/frozen/checksums.json`
- `artifacts/experiments/campaign_v1_main/frozen/freeze_manifest.json`

Run artifacts:

- `artifacts/experiments/campaign_v1_main/manifest.json`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/manifest.json`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/intersection_trace.csv`
- `artifacts/experiments/campaign_v1_main/runs/<batch_id>/<run_id>/performance.json`

Current code does not produce `summary.json`, `results.parquet`, or
`config.snapshot.yaml` directly during simulation.

## Runtime Estimate

Mini pilot basis:

- scenario: `S1_BALANCED`
- seeds: `42`, `2027`
- controllers: all five
- step cap: `600`
- measurement steps per run: `300`
- completed runs: `10`
- summed run wall time from manifests: about `116 s`

Observed mean wall time for 600 steps:

| Controller | Mean wall seconds | Full 3900-step estimate |
| --- | ---: | ---: |
| `B0_FIXED` | 0.846 | 5.5 s |
| `B1_LOCAL_ADAPTIVE` | 13.483 | 87.6 s |
| `B2_LOCAL_PRESSURE` | 13.745 | 89.3 s |
| `C1_COOPERATIVE_COMPACT` | 14.732 | 95.8 s |
| `C2_COOPERATIVE_EXPANDED` | 15.143 | 98.4 s |

Estimated runtime per `scenario + seed` for all five controllers:

```text
about 6.3 minutes for 3900-step scenarios
```

Estimated runtime per seed across S1-S4:

```text
about 26 minutes locally
```

The estimate treats S3 as slightly longer because its configured total duration
is longer than S1, S2, and S4. Docker runtime is not estimated because Docker
Desktop was unavailable during pre-flight.

## Disk Estimate

Mini pilot disk usage:

```text
about 70,994,982 bytes for 10 runs at 600 steps
```

Linear conservative estimate:

```text
about 44 MB per full 3900-step run
about 0.9 GB per final seed across 20 runs
about 9 GB if all 10 seed-pool entries are approved
```

Actual size can differ with telemetry volume and controller behavior.

## Mini Pilot Results

Mini pilot config:

```text
.tmp/campaign_v1_pilot/campaign_v1_mini_pilot.yaml
```

Mini pilot manifest:

```text
artifacts/experiments/campaign_v1_mini_pilot/manifest.json
```

Mini pilot non-final freeze:

```text
artifacts/experiments/campaign_v1_mini_pilot/frozen/checksums.json
```

Approximate variability in `vehicles_arrived` over the measured 300-step
window, using only two seeds:

| Controller | Mean arrived | Sample SD | CV |
| --- | ---: | ---: | ---: |
| `B0_FIXED` | 106.5 | 0.707 | 0.0066 |
| `B1_LOCAL_ADAPTIVE` | 84.0 | 2.828 | 0.0337 |
| `B2_LOCAL_PRESSURE` | 85.0 | 2.828 | 0.0333 |
| `C1_COOPERATIVE_COMPACT` | 89.5 | 3.536 | 0.0395 |
| `C2_COOPERATIVE_EXPANDED` | 87.0 | 2.828 | 0.0325 |

Interpretation limits:

- This is only a pipeline and rough variability check.
- It is not enough to rank controllers.
- Controllers must not be changed merely because of pilot ordering.
- Any methodology change after this point must be documented before final
  freeze.

## Failure Handling

Abort before starting the full campaign if any required pre-flight gate is red.

During approved execution:

- keep every run artifact, including failed runs;
- do not overwrite completed run directories;
- do not impute failed-run metrics as zero;
- record command, exit code, stderr/stdout summary, config hash, scenario hash,
  route hash, and controller id for every failure;
- investigate infrastructure failures separately from controller behavior;
- rerun only failed `scenario + seed + controller` tuples after verifying that
  the frozen checksums still match;
- document every rerun batch in the campaign manifest or companion notes.

## Resume Behavior

The current runner creates a new timestamped batch directory for each execution
and does not automatically skip completed runs.

Approved resume procedure:

1. Read `artifacts/experiments/campaign_v1_main/manifest.json` and batch run
   manifests.
2. Identify missing or failed `scenario + seed + controller` tuples.
3. Create an explicit resume config containing only those tuples.
4. Run the resume config against the same frozen inputs.
5. Verify checksums and append the resume batch to the campaign record.

Do not resume by changing seeds, routes, scenarios, controller code, or safety
constraints.

## Pre-Flight Record

Executed locally on 2026-09-29.

| Gate | Status | Evidence |
| --- | --- | --- |
| 1. Git working tree clean | Passed before writing this plan | `git status --short` was empty before `campaign_plan.md` was added. Final freeze still requires a clean tree after review/commit. |
| 2. CI green | Blocked | Local CI equivalent is not green because `ruff format --check .` reports 12 existing files would be reformatted. |
| 3. SUMO 1.27.1 | Passed | `scripts/check_sumo.py` detected `version=1.27.1`. |
| 4. Docker build green | Blocked | `docker build --tag traffic-agents-campaign-v1-preflight .` failed because Docker Desktop daemon was unavailable. |
| 5. Unit tests green | Passed | `pytest -q -m "not sumo"` passed: `259 passed, 1 deselected`. |
| 6. SUMO integration smoke green | Passed | `pytest -q -m sumo` passed: `1 passed, 259 deselected`. |
| 7. B0 smoke | Passed | S1, seed 42, 120 steps. |
| 8. B1 smoke | Passed | S1, seed 42, 120 steps. |
| 9. B2 smoke | Passed | S1, seed 42, 120 steps. |
| 10. C1 smoke | Passed | S1, seed 42, 120 steps, delay/drop zero. |
| 11. C2 smoke | Passed | S1, seed 42, 120 steps, delay/drop zero. |
| 12. S1-S4 routes valid | Passed | Scenario YAML validation passed for S1-S4; B0 SUMO route smoke passed for S1-S4. |
| 13. Phase safety tests green | Passed | `tests/test_phase_safety.py`: `9 passed`. |
| 14. Hashes consistent | Passed for pilot | Within each pilot seed, all five controllers shared identical network, route, phase, and turning hashes. Final campaign requires final freeze checksum validation. |
| 15. Freeze config prepared | Partially passed | Non-final mini-pilot freeze passed. Main final freeze is pending `N_final`, Docker availability, format gate, and clean tree. |

## Approval Gate

The campaign is not approved for full execution.

Before full execution:

1. resolve or explicitly waive the `ruff format --check` blocker;
2. start Docker Desktop and pass Docker build;
3. choose `N_final` from the ordered seed pool without using controller
   performance results;
4. generate final seed-specific scenario and route files;
5. create `experiments/configs/campaign_v1_main.yaml`;
6. run final pre-flight again;
7. run `traffic-agents experiment freeze --config experiments/configs/campaign_v1_main.yaml --final`
   on a clean Git tree;
8. obtain explicit approval to execute the full campaign.
