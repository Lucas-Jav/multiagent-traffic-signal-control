> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/pilot-assessment.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

> **SUPERSEDED STATUS (final audit, Prompt 52).** This is the original Prompt 46.8 assessment, kept unchanged below. Its gates `S3_ADAPTATION_SCENARIO_VALID = NO`, `SCIENTIFIC_PILOT_VALID = NO`, `READY_FOR_SEED_DECISION = NO` and the withheld B2-vs-C1 comparison reflect the old 360 s rule only. After the approved composite gate (Prompts 47/48) S3 is valid (5/5 seeds), the Pilot V2 was released for B2 vs C1 (Prompt 49) and the comparison was completed (Prompt 50, result MIXED). See `pilot-v2-release-decision.md`, `b2-vs-c1-final-comparison.md` and `final-scientific-conclusion.md`.

# Pilot V2 assessment

`campaign_role: PILOT` - Pilot V1 and V2 are never combined statistically. Not final results. No controller ranking or tuning.

Authoritative sources: runner `manifest.json`/`run_status.jsonl`, per-run `run_metrics.json` + canonical telemetry, `combined_metrics.parquet` (project `experiment aggregate` pipeline). Scenario validity criteria are evaluated on the `B0_FIXED` reference runs (5 seeds) and listed for all controllers as information. The analysis script is `artifacts/experiments/pilot_v2/analysis/pilot_v2_analysis.py` (reuses `scripts/calibrate_scenarios.py::analyze_run`, no source change).

## 1. Execution

- PLANNED_RUNS 100; COMPLETED_RUNS 100; FAILED_RUNS 0
- status transitions per run (run_status.jsonl): {"RUNNING->COMPLETED": 100}
- metrics_finalized=true on all runs: True; missing required metrics: 0 []
- Requested metric names vs project names: `mean_waiting_time_seconds`->`mean_waiting_time`, `mean_time_loss_seconds`->`mean_time_loss`, `mean_travel_time_seconds`->`mean_travel_time` (metrics were frozen; checked via this mapping).
- jam teleports per run (SUMO): total 17; runs with teleports 6; by scenario {'S1_BALANCED': 0, 'S2_DIRECTIONAL_PEAK': 0, 'S3_DEMAND_SHIFT': 0, 'S4_LOCAL_SATURATION': 17}

## 2. Scenario validity (B0 reference runs)

### S1_BALANCED

| seed | dep ratio | compl. departed | final-20% proj. change / mean | min junction share | turning s/l/r | checks failed |
| --- | --- | --- | --- | --- | --- | --- |
| 42 | 1.000 | 0.957 | -6.4 / 45.5 | 0.107 | 0.71/0.15/0.15 | - |
| 2027 | 1.000 | 0.960 | -2.2 / 45.7 | 0.107 | 0.70/0.15/0.16 | - |
| 3253 | 1.000 | 0.958 | -6.8 / 50.1 | 0.105 | 0.70/0.15/0.15 | - |
| 4517 | 1.000 | 0.952 | -5.4 / 47.7 | 0.106 | 0.71/0.14/0.15 | - |
| 5791 | 1.000 | 0.955 | -0.9 / 50.5 | 0.108 | 0.70/0.15/0.15 | - |

S1_STABLE_REGIME_VALID = YES

### S2_DIRECTIONAL_PEAK

| seed | offered dominant share | DBI | dep ratio | dominant dep | residual dep | left+right share | checks failed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 0.805 | 0.805 | 1.000 | 1.000 | 1.000 | 0.310 | - |
| 2027 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.297 | - |
| 3253 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.300 | - |
| 4517 | 0.806 | 0.806 | 1.000 | 1.000 | 1.000 | 0.305 | - |
| 5791 | 0.804 | 0.804 | 1.000 | 1.000 | 1.000 | 0.289 | - |

S2_DIRECTIONAL_SCENARIO_VALID = YES

### S3_DEMAND_SHIFT

| seed | pre-shock queue / S1 same window | pre-shock mean | post-shock mean (600 s) | ratio | A5 ratio | latency (s) | max insertion delay (s) | dep ratio | checks failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 1.00 | 48.1 | 65.2 | 1.36 | 2.60 | 130 | 118 | 0.997 | - |
| 2027 | 1.00 | 46.4 | 66.7 | 1.44 | 3.56 | 216 | 367 | 0.975 | - |
| 3253 | 1.00 | 46.1 | 63.1 | 1.37 | 1.79 | 131 | 94 | 0.998 | - |
| 4517 | 1.00 | 47.9 | 69.1 | 1.44 | 3.04 | 145 | 366 | 0.967 | pre_shock_stable |
| 5791 | 1.00 | 47.7 | 63.4 | 1.33 | 2.35 | 158 | 115 | 0.993 | - |

S3_ADAPTATION_SCENARIO_VALID = NO

### S4_LOCAL_SATURATION

| seed | A5 mean queue | A5 / others | neighbours / corners | min 300 s arrivals | arrivals last 1800 s / offered | dep ratio | teleports | checks failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 75.4 | 2.52 | 2.06 | 121 | 767 / 1788 | 0.491 | 2 | - |
| 2027 | 74.6 | 2.44 | 2.02 | 117 | 770 / 1784 | 0.485 | 2 | - |
| 3253 | 74.9 | 2.44 | 2.04 | 117 | 760 / 1787 | 0.485 | 4 | - |
| 4517 | 75.0 | 2.50 | 2.04 | 112 | 791 / 1787 | 0.487 | 2 | - |
| 5791 | 73.9 | 2.41 | 1.95 | 116 | 758 / 1790 | 0.474 | 4 | - |

S4_SATURATION_SCENARIO_VALID = YES

### Information: zero-arrival 300 s bins and calibration criteria per controller (all 100 runs)

| scenario | controller | runs with zero-arrival 300 s bin | runs passing all calibration criteria |
| --- | --- | --- | --- |
| S1_BALANCED | B0_FIXED | 0/5 | 5/5 |
| S1_BALANCED | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S1_BALANCED | B2_LOCAL_PRESSURE | 0/5 | 4/5 |
| S1_BALANCED | C1_COOPERATIVE_COMPACT | 0/5 | 5/5 |
| S1_BALANCED | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | B0_FIXED | 0/5 | 5/5 |
| S2_DIRECTIONAL_PEAK | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT | 0/5 | 0/5 |
| S2_DIRECTIONAL_PEAK | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S3_DEMAND_SHIFT | B0_FIXED | 0/5 | 4/5 |
| S3_DEMAND_SHIFT | B1_LOCAL_ADAPTIVE | 0/5 | 3/5 |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | 0/5 | 3/5 |
| S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | 0/5 | 4/5 |
| S3_DEMAND_SHIFT | C2_COOPERATIVE_EXPANDED | 0/5 | 0/5 |
| S4_LOCAL_SATURATION | B0_FIXED | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | B1_LOCAL_ADAPTIVE | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | 0/5 | 4/5 |
| S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT | 0/5 | 5/5 |
| S4_LOCAL_SATURATION | C2_COOPERATIVE_EXPANDED | 0/5 | 5/5 |

## 3. B0 measurement fairness

- distinct (warmup, start, end, steps, horizon_complete) tuples across all 100 runs: 1 -> ['(300.0, 300.0, 3900.0, 3900, True)']
- canonical files missing: 0; B0 lane-telemetry rows == 3900 x 36 in all B0 runs
- offered cohort identical across the 5 controllers per (scenario, seed): True
- canonical metrics present for adaptive controllers but absent for B0: []

B0_MEASUREMENT_FAIR = YES

## 4. Green-hold semantics (junction telemetry, all 100 runs)

| controller | runs | greens | greens > 20 s | max green (s) | yellow values | all-red values | non-sequential changes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0_FIXED | 20 | 28480 | 0 | 20 | [3] | [2] | 0 |
| B1_LOCAL_ADAPTIVE | 20 | 38266 | 3473 | 60 | [3] | [2] | 0 |
| B2_LOCAL_PRESSURE | 20 | 38964 | 2637 | 60 | [3] | [2] | 0 |
| C1_COOPERATIVE_COMPACT | 20 | 36174 | 3786 | 60 | [3] | [2] | 0 |
| C2_COOPERATIVE_EXPANDED | 20 | 26502 | 7012 | 60 | [3] | [2] | 0 |

max_green = 60 s (+1 step sampling tolerance). Not every controller/scenario must hold long greens.

GREEN_HOLD_SEMANTICS_OBSERVED = YES

## 5. Survivorship-safe population table (mean over 5 seeds; completed-trip metrics are conditional on completion)

| scenario | controller | offered | departed | arrived | dep ratio | compl. offered | compl. departed | waiting (s) | time loss (s) | travel (s) | stops | throughput |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1_BALANCED | B0_FIXED | 1794 | 1794 | 1716 | 1.000 | 0.956 | 0.956 | 93.7 | 113.2 | 166.3 | 2.42 | 1795 |
| S1_BALANCED | B1_LOCAL_ADAPTIVE | 1794 | 1794 | 1732 | 1.000 | 0.965 | 0.965 | 60.6 | 80.4 | 133.6 | 2.53 | 1800 |
| S1_BALANCED | B2_LOCAL_PRESSURE | 1794 | 1794 | 1741 | 1.000 | 0.970 | 0.970 | 46.8 | 66.2 | 119.3 | 2.44 | 1811 |
| S1_BALANCED | C1_COOPERATIVE_COMPACT | 1794 | 1794 | 1731 | 1.000 | 0.965 | 0.965 | 67.7 | 87.7 | 140.9 | 2.60 | 1807 |
| S1_BALANCED | C2_COOPERATIVE_EXPANDED | 1794 | 1790 | 1614 | 0.997 | 0.900 | 0.902 | 197.3 | 225.6 | 278.4 | 3.48 | 1703 |
| S2_DIRECTIONAL_PEAK | B0_FIXED | 1191 | 1191 | 1144 | 1.000 | 0.961 | 0.961 | 95.1 | 114.5 | 167.1 | 2.29 | 1195 |
| S2_DIRECTIONAL_PEAK | B1_LOCAL_ADAPTIVE | 1191 | 1191 | 1152 | 1.000 | 0.967 | 0.967 | 71.6 | 90.8 | 143.5 | 2.30 | 1199 |
| S2_DIRECTIONAL_PEAK | B2_LOCAL_PRESSURE | 1191 | 976 | 913 | 0.820 | 0.766 | 0.935 | 164.5 | 195.8 | 248.3 | 3.56 | 977 |
| S2_DIRECTIONAL_PEAK | C1_COOPERATIVE_COMPACT | 1191 | 903 | 850 | 0.758 | 0.714 | 0.942 | 143.5 | 170.2 | 222.8 | 3.09 | 917 |
| S2_DIRECTIONAL_PEAK | C2_COOPERATIVE_EXPANDED | 1191 | 824 | 773 | 0.692 | 0.649 | 0.938 | 165.5 | 192.5 | 245.0 | 3.12 | 841 |
| S3_DEMAND_SHIFT | B0_FIXED | 2019 | 1991 | 1817 | 0.986 | 0.900 | 0.913 | 114.2 | 138.3 | 192.5 | 2.83 | 1897 |
| S3_DEMAND_SHIFT | B1_LOCAL_ADAPTIVE | 2019 | 2011 | 1884 | 0.996 | 0.933 | 0.937 | 84.9 | 110.5 | 164.9 | 3.10 | 1953 |
| S3_DEMAND_SHIFT | B2_LOCAL_PRESSURE | 2019 | 1995 | 1873 | 0.988 | 0.927 | 0.938 | 76.7 | 102.6 | 157.0 | 3.07 | 1943 |
| S3_DEMAND_SHIFT | C1_COOPERATIVE_COMPACT | 2019 | 1969 | 1835 | 0.975 | 0.909 | 0.932 | 95.7 | 120.7 | 175.0 | 3.07 | 1911 |
| S3_DEMAND_SHIFT | C2_COOPERATIVE_EXPANDED | 2019 | 1832 | 1618 | 0.907 | 0.802 | 0.884 | 215.2 | 246.5 | 300.1 | 3.75 | 1707 |
| S4_LOCAL_SATURATION | B0_FIXED | 3587 | 1738 | 1317 | 0.484 | 0.367 | 0.758 | 573.1 | 680.9 | 740.2 | 11.84 | 1543 |
| S4_LOCAL_SATURATION | B1_LOCAL_ADAPTIVE | 3587 | 1532 | 1020 | 0.427 | 0.284 | 0.666 | 873.4 | 1130.6 | 1194.0 | 29.07 | 1245 |
| S4_LOCAL_SATURATION | B2_LOCAL_PRESSURE | 3587 | 1427 | 951 | 0.398 | 0.265 | 0.664 | 927.9 | 1166.2 | 1230.2 | 26.31 | 1187 |
| S4_LOCAL_SATURATION | C1_COOPERATIVE_COMPACT | 3587 | 1480 | 1096 | 0.413 | 0.306 | 0.741 | 738.2 | 894.3 | 958.1 | 16.73 | 1330 |
| S4_LOCAL_SATURATION | C2_COOPERATIVE_EXPANDED | 3587 | 1462 | 1114 | 0.408 | 0.310 | 0.762 | 609.7 | 702.5 | 765.9 | 9.33 | 1364 |

## 6. Primary pilot comparison: B2_LOCAL_PRESSURE vs C1_COOPERATIVE_COMPACT (paired scenario+seed)

WITHHELD: at least one scenario validity gate is NO (comparison only after validity passes).

## 7. Runtime, storage, variability

- sum of run wall times: 165.5 min; mean per run by controller: B0_FIXED 55 s, B1_LOCAL_ADAPTIVE 106 s, B2_LOCAL_PRESSURE 105 s, C1_COOPERATIVE_COMPACT 113 s, C2_COOPERATIVE_EXPANDED 118 s
- storage of `artifacts/experiments/pilot_v2`: 147.6 MB (1.5 MB/run)
- median across scenarios of the seed coefficient of variation (std/mean over 5 seeds):

| metric | B0_FIXED | B1_LOCAL_ADAPTIVE | B2_LOCAL_PRESSURE | C1_COOPERATIVE_COMPACT | C2_COOPERATIVE_EXPANDED |
| --- | --- | --- | --- | --- | --- |
| mean_network_queue_vehicles | 0.016 | 0.019 | 0.044 | 0.024 | 0.041 |
| throughput | 0.009 | 0.005 | 0.013 | 0.010 | 0.015 |
| mean_waiting_time | 0.018 | 0.022 | 0.053 | 0.028 | 0.051 |

## 8. Engineering differences V1 -> V2 (no statistical combination)

- Stable demand: V1 S1 was oversaturated; V2 levels come from a B0-only predeclared calibration (S1 150, S2 320, S3 base 150 + shock 150, S4 scale 2.0 veh/h per entry).
- Queue measurement: V1 queues came from controller-side traces (missing for B0, duplicated lanes); V2 uses one canonical unique-lane telemetry for every controller.
- Green-hold semantics: V1 KEEP_PHASE was effectively capped at the static green; V2 extends greens up to `max_green` with yellow/all-red still enforced.
- Turning realization: V1 declared ratios did not shape routes; V2 uses a seeded turning-ratio route walk (70/15/15) with realized proportions in metadata.
- S3 shock: V2 shock is a one-border (west) surge routed via A5 at the exact measurement midpoint (2100 s), base equals S1.
- S4 hotspot: V2 hotspot vehicles are all routed through A5 (background + hotspot entries).
- Metric finalization: V2 finalizes `run_metrics.json` automatically (`metrics_finalized=true`) and aggregates `combined_metrics.parquet` in the runner.

## 9. Methodological risks

- Only 5 seeds: paired CIs are wide and descriptive; the seed decision must use the CI widths above, not p-values.
- Scenario validity is judged on B0; controllers can change the realized regime (see per-controller information table).
- S4 scale 2.0 is the top of the calibration grid; heavy insertion-limited overload and jam teleports (count above) can distort queue physics.
- Completed-trip metrics are conditional on completion and biased when completion ratios differ across controllers.
- Pooling the 4 scenarios in one paired mean mixes regimes; per-scenario rows are the interpretable view.
- Requested metric names differ from the frozen project names (mapping listed in section 1).

## 10. Final gates

```
PLANNED_RUNS = 100
COMPLETED_RUNS = 100
FAILED_RUNS = 0
METRICS_FINALIZED_ALL_RUNS = YES
S1_STABLE_REGIME_VALID = YES
S2_DIRECTIONAL_SCENARIO_VALID = YES
S3_ADAPTATION_SCENARIO_VALID = NO
S4_SATURATION_SCENARIO_VALID = YES
B0_MEASUREMENT_FAIR = YES
GREEN_HOLD_SEMANTICS_OBSERVED = YES
SCIENTIFIC_PILOT_VALID = NO
READY_FOR_SEED_DECISION = NO
```
