> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s4-teleport-audit.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# S4 SUMO teleport audit (Prompt 46.9, part B)

No repository or scenario file changed; Pilot V2 not rerun; no controller ranking. Data: `s4-teleport-table.csv` (17 events), `artifacts/calibration/pilot_v2-diagnostic/` (`s4_analysis.json`, `s4_per_run.csv`, `diag_runs.json`, SUMO logs of the B0-only `CALIBRATION_DIAGNOSTIC` runs).

## B1. Teleport policy actually used by Pilot V2

- The project runner builds the SUMO command with only `--net-file --route-files --step-length --seed --no-step-log --quit-on-end --tripinfo-output --tripinfo-output.write-unfinished --statistic-output`. **No teleport option is set**, so every value is the SUMO 1.27.1 default: `--time-to-teleport 300` (a vehicle that has waited 300 s is teleported; non-positive disables), `--time-to-teleport.highways` default (inactive on these 13.9 m/s roads), `--time-to-teleport.disconnected` default, no `--max-num-teleports`.
- Warnings ("Teleporting vehicle ...") went to SUMO stderr and were captured only in the batch log `artifacts/pilot_v2_stderr.log`, not per run; per run only the count in `sumo/statistics.xml` (`<teleports total/jam/yield/wrongLane>`). The batch log lines were assigned to runs by execution order and the per-run counts (17 lines = 17 counted teleports, times monotonic within each run and <= 3900 s: mapping consistent).

## B2. Quantification (25 S4 runs)

- Events: 17 total (15 `jam`, 2 `yield`), in 6 of the 25 S4 runs. No teleport in S1/S2/S3 (75 runs).
- By controller: `B0_FIXED` 14 (in 5/5 seeds), `B2_LOCAL_PRESSURE` 3 (1/5 seeds, seed 5791), `B1_LOCAL_ADAPTIVE`, `C1_COOPERATIVE_COMPACT`, `C2_COOPERATIVE_EXPANDED` 0. By seed: 42 -> 2, 2027 -> 2, 3253 -> 4, 4517 -> 2, 5791 -> 7.
- By location (downstream junction, project labels): A1 11 (lane `B2A2_0` 10, `left2A2_0` 1), A3 4 (`right2C2_0`), A9 2 (`right0C0_0`, `bottom2C0_0`). **None at A5 or at A2/A4/A6/A8**: teleports are at corner approaches and border entry lanes, not at the hotspot. Groups: base 8, hotspot 9.
- Simulation time: 1012..3867 s (events in the pilot: min 1221, median 2582, max 3867).
- Extreme queues: network queue at the event is 1.08x the run mean and 0.92x the run max; correlation of the per-run teleport count with max network queue -0.0005, mean queue 0.17, departure ratio 0.47 (n = 25). Not concentrated at extreme queues.
- Conclusion: concentrated elsewhere than A5, **controller-dependent** (only B0 and one B2 run), not tied to extreme network queues.
- B0-only `CALIBRATION_DIAGNOSTIC` seeds (default policy) show the same pattern: 2, 0, 3, 3, 5 teleports, mostly lane `B2A2_0` plus entry lanes `right0C0_0`/`right2C2_0`.

## B3. Effect on the scientific metrics (from actual SUMO artifacts)

- Every teleported vehicle is present in `tripinfo.xml` (17/17); 11/17 have an `arrival` (they continue on their route after the jump and are then counted **arrived**, and count in throughput if the arrival is inside the window); 6/17 had not arrived at the end of the run (counted as unfinished). None was removed/vaporized and none reinserted.
- Travel time, waiting time and time loss are **not truncated**: the teleported vehicles carry waiting 443-2680 s and time loss 473-3210 s (run mean waiting ~580 s), so the long wait stays in the metric.
- Queue relief: the teleport removes the blocked vehicle from its lane; the lane queue fell from 7.8 (mean) to 6.1 (mean) 60 s after the event (per-event changes 0 to -6). One lane at a time, at the corner/entry approaches, not at the hotspot.
- Size: at most 4 events in a run (B0) or 3 (B2) against about 3588 offered (<= 0.11%); contribution of arrived teleported vehicles to the mean waiting time of a run <= about 0.4% (e.g. B0 seed 5791: (1717 + 993) s / ~1300 completed = 2.1 s of ~580 s); throughput effect <= 0.3%; `internal_lane_persistence_events` is computed from junction lane occupancy and is not directly altered.
- Impact classification:

| metric | impact |
| --- | --- |
| throughput | LOW |
| completion ratio | LOW |
| travel time | LOW |
| waiting time | LOW |
| time loss | LOW |
| network queue | LOW |
| internal_lane_persistence_events | NONE |

- Caveat: teleports are symptoms of a vehicle stuck at the lane front for 300 s, and only B0 and B2 seed 5791 show them. The B2 S4 seed 5791 run (3 teleports) also has the lowest departure ratio of the B2 S4 runs (0.332 vs 0.408-0.423) and the highest mean queue; the teleports cannot be proven to cause or to relieve that. This run is 1 of the 20 B2-vs-C1 pairs.

## B4. Zero-teleport counterfactual (B0 only, calibration seeds 3011, 4021, 5039, 6043, 7057, S4 at calibrated levels)

Default policy vs `--time-to-teleport -1` (added only in the diagnostic runner subclass; repository runner untouched):

| seed | teleports default / disabled | departure ratio | mean net queue | last-600 s queue | throughput | zero-arrival 300 s bins | wall time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3011 | 2 / 0 | 0.493 / 0.493 | 323 / 323 | 341 / 344 | 1559 / 1554 | 0 / 0 | 88 / 87 |
| 4021 | 0 / 0 | 0.484 / 0.484 | 316 / 316 | 330 / 330 | 1556 / 1556 | 0 / 0 | 88 / 87 |
| 5039 | 3 / 0 | 0.491 / 0.489 | 316 / 315 | 328 / 326 | 1569 / 1569 | 0 / 0 | 87 / 87 |
| 6043 | 3 / 0 | 0.486 / 0.485 | 325 / 327 | 342 / 353 | 1541 / 1526 | 0 / 0 | 87 / 79 |
| 7057 | 5 / 0 | 0.485 / 0.486 | 316 / 320 | 328 / 345 | 1554 / 1546 | 0 / 0 | 87 / 79 |

- Disabling teleports gives normal continued simulation: severe but active congestion, 3900 steps completed, every 300 s bin has arrivals (115-141), no gridlock, no unbounded backlog beyond the intended overload, same A5 hotspot and propagation, runtime unchanged (79-88 s). Metric differences are <= 1% in throughput and <= 3% in end-of-run queue.
- Limit: B0 only. The adaptive controllers were not run without teleports (forbidden in this task), so their behaviour with teleports disabled is untested.

## B5. Recommendation

**S4_TELEPORT_POLICY = ALLOW_AND_MEASURE**

- Teleports are rare (17 events, 6/25 S4 runs, <= 0.11% of a run's cohort), located away from A5, keep the waiting/time-loss in the metrics, and their removal changes aggregate metrics by <= about 1%. Disabling them changes almost nothing for B0, so disabling would not buy much and would require rerunning S4 for all controllers with an untested adaptive behaviour.
- Conditions to keep scientific integrity: report `sumo_teleports_total` (already recorded per run) next to every S4 result and run the B2-vs-C1 comparison with a sensitivity check excluding the S4 seed 5791 pair (the only pair with B2 teleports).
- If the owner prefers zero hidden relief for the FINAL experiments, `DISABLE_FOR_FINAL_EXPERIMENTS` is technically safe for B0 (B4) but must be validated for B1/B2/C1/C2 first (new runs, separate decision).

```
S4_TELEPORT_POLICY = ALLOW_AND_MEASURE
S4_TELEPORTS_AFFECT_VALIDITY = NO
S4_REQUIRES_SIMULATION_CONFIG_CHANGE = NO
S4_REQUIRES_RECALIBRATION = NO
S4_REQUIRES_PILOT_RERUN = NO
```
