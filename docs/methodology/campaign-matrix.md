# V1 Campaign Matrix

Status: pre-flight campaign matrix for V1 pilot and planned final campaigns.

This document describes campaign structure only. It does not report results and
does not freeze the final campaign. Pilot results must not be merged into final
frozen campaign results.

## Seed Policy

Predeclared seed pool:

```text
campaign_v1_seed_pool_2026-09-29
42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011, 16001
```

Pilot seeds fixed before pilot execution:

```text
42, 2027, 3253, 4517, 5791
```

FINAL SEED COUNT WILL ONLY BE DECIDED AFTER THE PILOT.

Seeds must not be replaced, removed, or reordered because of comparative
controller results.

## Pilot

Config:

- `experiments/configs/pilot.yaml`
- `campaign_role: PILOT`

Scenarios:

- `S1_BALANCED`
- `S2_DIRECTIONAL_PEAK`
- `S3_DEMAND_SHIFT`
- `S4_LOCAL_SATURATION`

Controllers:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Seeds:

- `42`
- `2027`
- `3253`
- `4517`
- `5791`

Planned runs:

```text
4 scenarios x 5 seeds x 5 controllers = 100 runs
```

Role:

- Validate execution stability, data completeness, storage footprint, runtime,
  route/config invariants, and variability before deciding final seed count.
- Pilot outputs are not final campaign results.

## Final Main

Config:

- `experiments/configs/final_main.yaml`
- `campaign_role: PLANNED_FINAL`
- pre-freeze planned state; do not execute as final before the final seed
  decision and freeze.

Scenarios:

- `S1_BALANCED`
- `S2_DIRECTIONAL_PEAK`
- `S3_DEMAND_SHIFT`
- `S4_LOCAL_SATURATION`

Controllers:

- `B0_FIXED`
- `B1_LOCAL_ADAPTIVE`
- `B2_LOCAL_PRESSURE`
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Seed decision:

- Pending pilot assessment.
- The current planned config uses the minimum pilot seed set as a pre-freeze
  executable template, not as a frozen final seed-count decision.

Current planned runs:

```text
4 scenarios x 5 seeds x 5 controllers = 100 planned runs
```

## S5 Packet Loss

Config:

- `experiments/configs/final_s5_packet_loss.yaml`
- `campaign_role: PLANNED_FINAL`
- pre-freeze planned state; do not execute as final before the final seed
  decision and freeze.

Base traffic scenario:

- `S2_DIRECTIONAL_PEAK`

Controllers:

- `B2_LOCAL_PRESSURE` reference
- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`

Packet-loss matrix:

- `drop_probability: 0.00`
- `drop_probability: 0.20`
- `drop_probability: 0.50`
- `drop_probability: 1.00`

Delay:

- fixed `delay_steps: 0` in the mandatory packet-loss campaign.
- delay studies remain optional and separate.

Seed decision:

- Pending pilot assessment.
- The current planned config uses the minimum pilot seed set as a pre-freeze
  executable template, not as a frozen final seed-count decision.

Current planned runs:

```text
5 seeds x (1 B2 reference + 2 cooperative controllers x 4 drop probabilities)
= 45 planned runs
```

## Optional S5B Delay

Optional only. No mandatory config is required for the V1 TCC core campaign.

If executed, keep it separate from S5 packet loss and use:

- `delay_steps: 0`
- `delay_steps: 1`
- `delay_steps: 3`
- `delay_steps: 5`

## Fairness Contract

For the same scenario and seed, compared controllers must share:

- network
- route/demand
- turning ratios
- warmup
- measurement duration
- step length
- phase plan
- safety constraints

Only controller behavior and, where designed, communication behavior may differ.
