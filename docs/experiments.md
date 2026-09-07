# Experiments

## S5 Communication Degradation

Objective: measure robustness of cooperative controllers under message delay and
message loss.

S5 does not define a new traffic demand scenario. It uses the fixed base demand
`S2_DIRECTIONAL_PEAK` from
`scenarios/grid_3x3/scenario_s2_directional_peak.yaml` and varies only the
communication channel for cooperative controllers.

Reference controller:

- `B2_LOCAL_PRESSURE`

Cooperative controllers:

- `C1_COOPERATIVE_COMPACT`
- `C2_COOPERATIVE_EXPANDED`, generated separately as an optional config

Matrix:

- `delay_steps`: `0`, `1`, `3`, `5`
- `drop_probability`: `0.00`, `0.05`, `0.10`, `0.25`

The matrix produces 16 cooperative combinations per cooperative controller.
Each generated experiment file also includes one `B2_LOCAL_PRESSURE` reference
run.

Generated configs:

- `experiments/configs/s5_communication_degradation_c1.yaml`
- `experiments/configs/s5_communication_degradation_c2.yaml`

Example generated run IDs:

- `s5_c1_delay0_drop0`
- `s5_c1_delay3_drop010`
- `s5_c1_delay5_drop025`

Reproducibility fields in every run config:

- `scenario_base`
- `scenario`
- `controller_id`
- `seed`
- `communication_seed_policy`
- `communication.delay_steps`
- `communication.drop_probability`
- `communication.rng_seed`
- `communication.max_message_age_steps`

`communication_seed_policy: derived_from_simulation_seed_delay_drop` means the
effective message-channel RNG seed is derived deterministically from the
simulation seed, `delay_steps`, and `drop_probability`.

`max_message_age_steps` remains fixed at `1` across the matrix. It is not
increased automatically when delay increases, so runs with `delay_steps > 1` can
produce stale cooperative messages.

Regenerate the S5 configs deterministically:

```powershell
python scripts\generate_s5_matrix.py
```

Do not run S5 as part of smoke validation. S5 is a campaign config and should be
executed only when the communication-degradation campaign is intentionally
started.
