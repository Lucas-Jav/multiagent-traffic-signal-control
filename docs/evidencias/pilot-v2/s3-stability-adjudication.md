> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s3-stability-adjudication.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

> **Status update (final audit, Prompt 52).** Historical adjudication (Prompt 46.9), kept unchanged. The statement that S3 "stays NO" refers to the frozen 360 s rule only; the gate definition was changed by the approved decision (Prompt 47) and S3 passes the composite gate 5/5 (Prompt 48).

# S3 pre-shock stability adjudication (Prompt 46.9, part A)

`campaign_role: PILOT` data (Pilot V2) plus `CALIBRATION` / `CALIBRATION_DIAGNOSTIC` B0-only data. No threshold relaxed, no repository file changed, Pilot V2 not rerun, no controller compared.
Data: `s3-stability-table.csv` (18 rows), `artifacts/calibration/pilot_v2-diagnostic/` (`s3_analysis.json`, `s3_seed4517_b0_queue_final600s.csv/.png`).

## A1. Exact failure (S3, seed 4517, B0_FIXED)

- Frozen rule: OLS line over the queue window; `projected_change = slope x window_length`; stable iff `projected_change <= 0.10 x max(mean_queue_window, 5.0)`.
- Window: final 20% of the pre-shock measurement = steps 1740..2099 (360 samples), shock at step 2100.
- Observed: slope 0.01808 veh/s, projected change **6.51 veh**, window mean 50.0, threshold **5.00** (0.10 x 50.0). Margin **-1.51 veh** (normalized slope 0.130 vs limit 0.100). FAIL.
- Window queue: mean 50.0, median 50.0, min 41, max 60.
- Pre-shock cohort (scheduled 300..2100 s): offered 900, departed 900, arrived 900 by the end of the run (86 of them still in the network at the shock instant = normal in-flight), never inserted 0, unfinished_in_network (run end) 0, departure ratio 1.000, depart delay mean ~0 s, max 1 s.
- Pre-shock mean queue 46.9 (whole 300..2100 s); the rule applied to the whole 1800 s pre-shock is normalized +0.031 (pass); to the last 720 s +0.238 (fail).

## A2. S3 seed 4517 vs S1 seed 4517 (B0)

- The S3 first half is byte-identical demand to S1 (same base vehicles, routes, departures). The pilot network-queue series of S3 and S1 are **identical for steps 0..2099 (max abs difference 0.0 vehicles)**. The same window therefore also FAILS in S1 seed 4517 (normalized +0.130); S1's own final-20% window (2940..3660 s) passes (normalized -0.114).
- Departure ratio 1.000, no insertion backlog (max insertion delay 1 s), lane saturation fraction 0.0000, max lane queue 9, arrivals in 300..2100 s 892: all equal for both.
- So the failure is not caused by S3 or the shock. The same stable traffic fails or passes depending on WHICH 360 s window is tested.

Classification of seed 4517: **LOCAL_STOCHASTIC_FLUCTUATION** (with a window-length component; see A3/A4).

## A3. All five Pilot V2 seeds (B0, S3, window 1740..2099)

| seed | projected change | threshold | margin | normalized | pass | mean pre-shock queue | departure ratio | never inserted | max lane queue | growth (last vs previous 360 s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 2.41 | 4.64 | +2.23 | 0.052 | pass | 48.0 | 1.000 | 0 | 12 | -4.09 |
| 2027 | 0.94 | 4.57 | +3.63 | 0.021 | pass | 46.7 | 1.000 | 0 | 9 | -1.62 |
| 3253 | -4.43 | 4.47 | +8.90 | -0.099 | pass | 46.5 | 1.000 | 0 | 8 | -1.60 |
| 4517 | 6.51 | 5.00 | -1.51 | 0.130 | **FAIL** | 46.9 | 1.000 | 0 | 9 | +5.82 |
| 5791 | -2.11 | 4.78 | +6.89 | -0.044 | pass | 48.6 | 1.000 | 0 | 8 | +1.27 |

4517 is **close to the threshold, not a clear outlier**: the next seeds are 0.052 (42) and -0.099/-0.044; pre-shock mean queues are 46.5-48.6 and identical in regime across seeds. No structural backlog in any seed (departure ratio 1.000, never inserted 0, saturation 0).

## A4. Calibration-only evidence (B0 only, existing rule exactly)

Existing calibration S3 runs (seeds 101, 1009, 2029, shock 150; same pre-shock regime for every shock level): 3/3 pass (normalized 0.050, -0.095, 0.024).
New `CALIBRATION_DIAGNOSTIC` S3 runs (B0, calibrated levels, seeds 3011, 4021, 5039, 6043, 7057, 8069, 9073, 10091, 11087, 12097): 7 pass / 3 fail (table below).

| seed | normalized slope | pass | projected / threshold |
| --- | --- | --- | --- |
| 3011 | -0.036 | pass | -1.62 / 4.50 |
| 4021 | 0.110 | FAIL | 5.12 / 4.63 |
| 5039 | 0.083 | pass | 3.70 / 4.44 |
| 6043 | -0.112 | pass | -5.54 / 4.94 |
| 7057 | 0.149 | FAIL | 6.95 / 4.65 |
| 8069 | 0.025 | pass | 1.15 / 4.54 |
| 9073 | -0.065 | pass | -2.87 / 4.40 |
| 10091 | 0.253 | FAIL | 12.03 / 4.75 |
| 11087 | -0.125 | pass | -5.73 / 4.57 |
| 12097 | -0.038 | pass | -1.76 / 4.63 |

All 10: departure ratio 1.000, never inserted 0.

Pooled over the 18 independent B0 pre-shock observations (5 pilot + 3 calibration + 10 diagnostic): **14 pass / 4 fail, pass rate 78%** (fails: 4517, 4021, 7057, 10091). Normalized slope over the 15 pilot+diagnostic observations: mean 0.020, sd 0.109; the limit 0.10 sits only 0.73 sd above the mean. If seeds fail independently at about 22%, the chance that all 5 seeds of a stable scenario pass is about 0.78^5 = 29%.
Sliding-window check (360 s windows, stride 30 s, all pre-shock positions, B0): 105 of 735 windows (14%) fail; over S1 B0 pilot runs (300..3900 s) 93 of 545 windows (17%) fail. So the rule flags genuinely stable, backlog-free traffic in roughly one window in six.
Window length: with the same data the rule over the last 720 s fails 1/15 and over the whole 1800 s pre-shock fails 0/15 (max normalized 0.060); the 360 s window is short against the ~98 s signal cycle and the +/-10 veh queue oscillation.

## A5. Adjudication

**S3_FAILURE_CLASS = STOCHASTIC_GATE_SENSITIVITY**

- No structural instability: every pre-shock run has departure ratio 1.000, 0 never inserted, insertion delay <= 1 s, lane saturation 0, pre-shock queue stationary (1800 s trend normalized <= 0.06 in 15/15).
- The S3 first half equals S1 exactly (series difference 0.0), so the scenario is not the cause.
- The binary 360 s slope gate has a measured false-fail rate of about 22% per seed (4/18) and about 14-17% per sliding window on stable traffic.
- Part of the sensitivity is window length (an ANALYSIS_WINDOW component), but the dominant evidence is stochastic queue fluctuation against a tight 10% limit.

```
S3_FAILURE_CLASS = STOCHASTIC_GATE_SENSITIVITY
S3_REQUIRES_SCENARIO_CHANGE = NO
S3_REQUIRES_GATE_DEFINITION_CHANGE = YES
S3_REQUIRES_NEW_SIMULATION_RUNS = NO
```

- Scenario change NO: demand is stable and identical to S1.
- Gate definition change YES: only if the owner wants S3 to be declared valid; with the frozen rule unchanged S3 stays NO (a stable regime would fail one of five seeds about 71% of the time). Nothing was implemented; any new rule must be declared before re-evaluation and judged on the 13 non-pilot observations, not tuned on seed 4517.
- New runs NO: a revised gate can be re-evaluated from the existing telemetry of Pilot V2 and the diagnostic runs.
