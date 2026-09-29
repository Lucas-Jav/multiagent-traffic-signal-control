# V1 Final Experimental Protocol

Status: approved methodological source of truth for the V1 final experiments.

This protocol defines the scientific comparisons, scenarios, metrics, fairness
contract, and seed policy for the final campaign. It supersedes older planning
notes when there is a conflict. The final campaign must not be executed until
the implementation mismatches listed at the end of this document are resolved
and frozen.

This document does not report experimental results. It must not describe any
controller as superior before final campaign results exist.

Operational metric definitions live in `docs/methodology/metrics.md`. If a
metric name appears in this protocol, its unit, source, aggregation, measurement
window, and edge-case policy are defined there.

## Research Question

In a simulated urban traffic network, does local information exchange between
decentralized traffic signal controllers improve network performance compared
with a local adaptive controller without cooperation and with fixed-time
control, under different traffic demand conditions?

The expected answer is not hardcoded. All conclusions must be derived from the
final frozen artifacts and statistical analysis.

## Controllers and Experimental Roles

The final V1 campaign uses five controllers:

| Controller | Experimental role |
|---|---|
| `B0_FIXED` | Traditional fixed-time baseline |
| `B1_LOCAL_ADAPTIVE` | Secondary local adaptive controller |
| `B2_LOCAL_PRESSURE` | Primary non-cooperative adaptive baseline |
| `C1_COOPERATIVE_COMPACT` | Main cooperative method |
| `C2_COOPERATIVE_EXPANDED` | Communication-rich ablation/comparison |

The final fixed-time baseline is `B0_FIXED`.

`B0_FIXED` must be described only as a traditional/static fixed-time baseline.
It is not Webster-optimized. No `B0_WEBSTER_FIXED` baseline is implemented for
V1, and V1 reports must not use "Webster" as a synonym for `B0_FIXED`.

Primary scientific comparison:

```text
B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT
```

Reason: `B2_LOCAL_PRESSURE` and `C1_COOPERATIVE_COMPACT` share the local
pressure core. The major experimental difference is the use of cooperative
neighbor information by `C1_COOPERATIVE_COMPACT`.

Secondary comparisons:

- `B0_FIXED` vs `B2_LOCAL_PRESSURE`
- `B0_FIXED` vs `C1_COOPERATIVE_COMPACT`
- `B2_LOCAL_PRESSURE` vs `C2_COOPERATIVE_EXPANDED`
- `C1_COOPERATIVE_COMPACT` vs `C2_COOPERATIVE_EXPANDED`

## Common Fairness Contract

For the same scenario and seed, all compared controllers must share:

- network
- routes
- traffic demand
- turning ratios
- warmup
- measurement duration
- step length
- phase plan
- movement model
- safety constraints

Only controller behavior and, where designed, communication behavior may differ.

Scientific fairness must be checked using independently recorded invariants:

- `network_sha256`
- `route_sha256`
- `phase_plan_sha256`
- `movement_model_sha256`
- `turning_config_sha256`

`scenario_sha256` may include controller or communication fields in the current
implementation and is therefore not the primary fairness source of truth.

## Seeds

Minimum pilot: 5 distinct seeds.

Seed selection must happen before examining comparative controller results. Do
not replace, remove, or reorder seeds because a run produces an unfavorable
result.

Use the existing planned seed pool:

```text
campaign_v1_seed_pool_2026-09-29
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

The minimum pilot uses the first five seeds:

```text
42, 2027, 3253, 4517, 5791
```

If a larger final campaign is approved, it must use the next seeds in the fixed
order above.

## Scenario S1 - Balanced Traffic

Definition:

- Scenario id: `S1_BALANCED`
- Demand: balanced demand from all borders
- Final turning distribution:
  - straight: `0.70`
  - left: `0.15`
  - right: `0.15`
- Goal: evaluate controller behavior under stable and predictable demand.

Do not define success as "`C1_COOPERATIVE_COMPACT` must outperform fixed-time."

Metrics:

- throughput
- mean travel time
- mean waiting time
- mean time loss
- mean queue
- max queue
- mean stops

## Scenario S2 - Directional Peak

Definition:

- Scenario id: `S2_DIRECTIONAL_PEAK`
- Demand: strong West to East demand bias
- Target: approximately 80% of injected demand associated with the dominant
  corridor/direction
- Turning behavior must be preserved. The target does not mean that 80% of
  vehicles must travel only straight through the entire network.
- The scenario must contain straight, left, and right movements.
- Goal: evaluate whether local and cooperative controllers handle a dominant
  directional traffic stream and platoon-like demand.

Do not claim that a green wave exists unless it is observed in the final
artifacts using an explicit definition.

Metrics:

- mean stops
- time loss
- corridor travel time
- corridor throughput
- network throughput
- queues

## Scenario S3 - Abrupt Demand Shift

Definition:

- Scenario id: `S3_DEMAND_SHIFT`
- Use two explicit demand windows.
- First 50%: balanced traffic.
- Second 50%: strong directional/localized demand shock.
- The exact shock start time must be frozen before the campaign.
- Goal: evaluate controller response after a demand regime change.

Selected recovery metric policy:

The current implemented data products do not yet define a scientifically
defensible threshold for `recovery_time_seconds` without arbitrary tuning.
Therefore the final V1 protocol must not invent a threshold-based recovery time
metric until such a rule is implemented and frozen.

Use these post-shock metrics instead:

- post-shock mean queue
- post-shock max queue
- area under queue curve after shock
- post-shock time loss

## Scenario S4 - Localized Saturation

Definition:

- Scenario id: `S4_LOCAL_SATURATION`
- Demand: strong demand focused toward the A5 region
- The scenario may intentionally approach or exceed local capacity.
- Goal: evaluate whether cooperation mitigates propagation of localized
  congestion compared with local-only control.

Do not claim that any controller must solve overload.

Metrics:

- mean queue
- max queue
- throughput
- time loss
- travel time
- downstream occupancy where available
- `internal_lane_persistence_events`

`internal_lane_persistence_events` is a proxy for persistent internal-junction
occupancy. It is not a direct universal measurement of spillback, gridlock, or
physical blockage.

Do not use "gridlock duration" unless an explicit operational definition is
implemented and frozen before the final campaign.

## Scenario S5 - Communication Degradation

Definition:

- Scenario id: `S5_COMMUNICATION_DEGRADATION`
- Use an existing traffic demand profile, preferably `S2_DIRECTIONAL_PEAK`.
- Packet-loss experiment over `drop_probability`:
  - `0.00`
  - `0.20`
  - `0.50`
  - `1.00`
- Primary controllers:
  - `C1_COOPERATIVE_COMPACT`
  - `C2_COOPERATIVE_EXPANDED`
- Reference controller:
  - `B2_LOCAL_PRESSURE`

At 100% packet loss, `C1_COOPERATIVE_COMPACT` and
`C2_COOPERATIVE_EXPANDED` should rely on local fallback behavior. Do not assume
their final metrics will exactly equal `B2_LOCAL_PRESSURE` unless implementation
semantics guarantee exact equivalence.

Metrics:

- throughput
- waiting time
- time loss
- queue
- communication messages sent
- communication messages delivered
- communication messages dropped
- bytes
- message age

## Optional Secondary Delay Study

`S5B_DELAY` is secondary and optional. It is not mandatory for the TCC core
campaign.

If executed, use:

- `delay_steps: 0`
- `delay_steps: 1`
- `delay_steps: 3`
- `delay_steps: 5`

The delay study must not be mixed with the mandatory packet-loss comparison
unless the analysis labels it separately.

## Final Metric List by Scenario

| Scenario | Final metrics |
|---|---|
| `S1_BALANCED` | throughput; mean travel time; mean waiting time; mean time loss; mean queue; max queue; mean stops |
| `S2_DIRECTIONAL_PEAK` | mean stops; time loss; corridor travel time; corridor throughput; network throughput; queues |
| `S3_DEMAND_SHIFT` | post-shock mean queue; post-shock max queue; area under queue curve after shock; post-shock time loss |
| `S4_LOCAL_SATURATION` | mean queue; max queue; throughput; time loss; travel time; downstream occupancy where available; `internal_lane_persistence_events` |
| `S5_COMMUNICATION_DEGRADATION` | throughput; waiting time; time loss; queue; messages sent; messages delivered; messages dropped; bytes; message age |
| `S5B_DELAY` | same as S5, reported separately as optional/secondary |

## Exact Scenario Definitions to Freeze

The final executable artifacts must encode these definitions before campaign
execution:

| Scenario | Demand and communication definition |
|---|---|
| `S1_BALANCED` | Balanced demand from all borders; turning ratios straight `0.70`, left `0.15`, right `0.15`; no special communication degradation in main campaign |
| `S2_DIRECTIONAL_PEAK` | Strong West to East demand bias; approximately 80% of injected demand associated with the dominant corridor/direction while preserving straight, left, and right movements |
| `S3_DEMAND_SHIFT` | Two explicit windows; first 50% balanced; second 50% strong directional/localized demand shock; shock start frozen before campaign |
| `S4_LOCAL_SATURATION` | Strong demand focused toward A5; may approach or exceed local capacity |
| `S5_COMMUNICATION_DEGRADATION` | Existing base demand, preferably S2; C1/C2 packet-loss matrix at drop probabilities `0.00`, `0.20`, `0.50`, `1.00`; B2 reference |
| `S5B_DELAY` | Optional delay matrix over `delay_steps` `0`, `1`, `3`, `5`; reported separately |

## Current Implementation Mismatches

These mismatches must be resolved before the final campaign is frozen or run:

1. `S1_BALANCED` currently uses turning ratios straight `0.60`, left `0.20`,
   right `0.20` in `scenarios/grid_3x3/scenario.yaml`; this protocol requires
   straight `0.70`, left `0.15`, right `0.15`.
2. Existing S1-S4 route artifacts are generated for seed `42` only. The final
   minimum pilot requires five distinct seeds: `42`, `2027`, `3253`, `4517`,
   and `5791`.
3. Existing S5 configs use `drop_probability` values `0.00`, `0.05`, `0.10`,
   and `0.25`, and combine them with delay values. The core S5 protocol
   requires packet-loss values `0.00`, `0.20`, `0.50`, and `1.00`; delay is a
   separate optional `S5B_DELAY` study.
4. `S3_DEMAND_SHIFT` implementation must be checked or updated so its first 50%
   is balanced and its second 50% is the frozen directional/localized shock
   specified by this protocol.
5. Corridor-specific metrics for S2 and post-shock metrics for S3 must be
   available in the final analysis outputs before final reporting.

## Implementation Work Still Required

Before running the final campaign:

1. Update or generate final scenario artifacts to match this protocol.
2. Generate seed-specific scenarios, routes, and route metadata for the approved
   seed set without using comparative controller results.
3. Regenerate S5 packet-loss configs to use `0.00`, `0.20`, `0.50`, and `1.00`
   as the mandatory core matrix.
4. Keep delay experiments under the optional `S5B_DELAY` label if they are run.
5. Ensure final analysis includes scenario-specific metrics listed in this
   protocol, especially S2 corridor metrics and S3 post-shock metrics.
6. Freeze all final inputs and verify route/config/hash invariants before
   campaign execution.

## Prohibited Actions

- Do not tune controllers based on observed performance.
- Do not select, remove, or reorder seeds based on observed performance.
- Do not change controller logic unless explicitly required by this protocol.
- Do not describe any controller as superior before final results exist.
- Do not run the final campaign before final scenario artifacts and frozen
  inputs match this protocol.
