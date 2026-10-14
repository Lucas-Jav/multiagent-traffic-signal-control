> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s3-composite-gate-reevaluation.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# S3 composite-gate re-evaluation (Prompt 48)

`campaign_role: PILOT` (Pilot V2). Existing telemetry only: no simulation, no repository file changed, no threshold changed, no B2-vs-C1 comparison.
Gate defined in `pilot-v2-methodological-decision.md` (Prompt 47). Evaluated on the `B0_FIXED` S3 runs (5 pilot seeds), pre-shock phase (scheduled 300..2100 s; steps 300..2099). Script: `analysis/s3_composite_gate.py`; per-seed data: `s3-composite-gate-table.csv`.

## Gate

1. No structural backlog: pre-shock `departure_ratio` >= 0.98 and mean insertion delay <= 5 s.
2. No relevant never-inserted vehicles: fraction <= 0.02.
3. No structural lane saturation: fraction of lane-steps with queue >= 0.8 x lane capacity <= 0.02.
4. Aggregate 1800 s pre-shock window (steps 300..2099) passes the frozen rule: projected OLS change <= 0.10 x max(window mean, 5).
5. At least 4 of 5 seeds valid on criteria 1-4.
Retained unchanged on every seed (taken from the Prompt 46.8 S3 table, only the superseded `pre_shock_stable` 360 s check removed): base == S1, first half == S1, shock at 2100 s, west-border origin, shock through A5, visible response (ratio >= 1.25, latency <= 600 s), no multi-thousand-second insertion backlog, frozen-definition AUC.
Diagnostic only (cannot fail a seed): the 360 s rule (last 20% of the pre-shock measurement) and the 720 s rule.

## Result per seed

| seed | class | offered | departed | never inserted | max insertion delay (s) | lane saturation | 1800 s normalized (limit 0.10) | 1800 s margin (veh) | retained checks failed | 360 s diagnostic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | 0.024 | 3.67 | - | pass (0.052, margin 2.23) |
| 2027 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.042 | 6.64 | - | pass (0.021, margin 3.63) |
| 3253 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.092 | 8.95 | - | pass (-0.099, margin 8.89) |
| 4517 | **VALID_WITH_DIAGNOSTIC_WARNING** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | 0.031 | 3.22 | - | FAIL (0.130, margin -1.51) |
| 5791 | **VALID** | 900 | 900 | 0 (0.0000) | 1 | 0.00000 | -0.085 | 8.97 | - | pass (-0.044, margin 6.89) |

Criteria flags per seed (1 backlog, 2 never inserted, 3 saturation, 4 window 1800 s): 42: 1111; 2027: 1111; 3253: 1111; 4517: 1111; 5791: 1111 (1 = pass).

## Aggregate

- Valid seeds (VALID or VALID_WITH_DIAGNOSTIC_WARNING): **5/5**; rule requires >= 4/5.
- Classes: 42 VALID, 2027 VALID, 3253 VALID, 4517 VALID_WITH_DIAGNOSTIC_WARNING, 5791 VALID.
- **S3 PASSES under the composite gate.**

## Effect of seed 4517

- The 360 s diagnostic still FAILS for seed 4517 (projected change 6.51 veh vs threshold 5.00, margin -1.51, normalized 0.130 vs 0.100). This failure is reported here, not hidden, and it is not removed from `s3-stability-table.csv` or the Pilot V2 assessment.
- Under the composite gate seed 4517 is **VALID_WITH_DIAGNOSTIC_WARNING**: departure ratio 1.000, 0 never inserted, max insertion delay 1 s, lane saturation 0.00000, and the 1800 s window is stable (normalized 0.031, margin 3.22 veh).
- Seeds with a diagnostic warning: [4517]. The 720 s diagnostic for 4517 is FAIL (normalized 0.238).
- Because the aggregate rule tolerates one seed in five, the outcome would be the same even if seed 4517 were classified INVALID, as long as the other four are valid: yes, the other four seeds are valid.

## Methodological justification

- The 360 s rule had a measured false-fail rate of about 22% per seed on stable, backlog-free B0 traffic (4 of 18 independent observations) and about 14-17% per sliding window (Prompt 46.9); the S3 first half is identical to S1 for seed 4517, so the failure reflects queue fluctuation, not the scenario.
- The composite gate tests the properties that define a stable base regime (no backlog, no non-insertion, no saturation, no 1800 s trend) on the whole pre-shock phase. No threshold changed; only the decisive window of the slope rule moved from 360 s to 1800 s, as approved in Prompt 47.
- Limitation inherited from Prompt 47: the 1800 s window was chosen after observing the 46.9 diagnostics; the rule is inclusive of the original 0.10 limit and the floor of 5 veh. With 5 seeds, 4 of 5 is coarse.

## Conclusion

S3 passes the composite gate. The scenario validity gates S1, S2, S3 and S4 are then all satisfied, so the S3 block on the B2 vs C1 comparison is lifted. The comparison was NOT computed in this task.
