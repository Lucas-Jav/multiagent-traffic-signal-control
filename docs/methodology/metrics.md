# Scenario-Specific Metrics

Status: V1 final metric definitions (revised in Prompt 46.6 after the Pilot V1 forensic
diagnosis). These definitions must be frozen before Pilot V2 or the final campaign is executed.
Pilot V1 numbers computed with the previous definitions are superseded (see
`artifacts/experiments/pilot_v1/pilot-assessment-erratum.md`).

The final campaign must not use hand-calculated metrics. Every completed run is finalized by
the canonical pipeline (`run_metrics.json`, `metrics_finalized: true` in the run manifest) and
the experiment runner aggregates all finalized runs into `combined_metrics.parquet`
(`traffic-agents experiment aggregate <folder>` does the same for an existing experiment).
Report generation and paired analysis read that file. A run whose finalization fails is a
FAILED run: it is never exported as zeros and never marked complete.

## Measurement and population policy

All scenarios share one timing: `warmup_seconds = 300`, `measurement_duration_seconds = 3600`,
`step_length = 1.0` (total 3900 s; step `i` runs simulation time `i` to `i + 1`). Measurement
steps are `300 <= i < 3900`. Scenario S3 places its shock at 50% of the MEASUREMENT window:
`shock_start_seconds = 300 + 3600 / 2 = 2100` (`shock_start_step = 2100`).

* **Measurement cohort**: the offered vehicles (route file) whose SCHEDULED departure lies in
  `[warmup, warmup + measurement_duration)`. Population counts and all completed-trip metrics
  use the cohort, so warmup demand never contaminates measurement populations.
* **Full-run** counts (`full_run_*`) cover every offered vehicle of the whole run.
* **Populations** are persisted as `offered`, `departed` (inserted), `arrived` (completed),
  `never_inserted` (offered - departed) and `unfinished_in_network` (departed - arrived), both
  for the cohort (`offered_vehicle_count`, ... and the equivalent `measurement_*` names) and for
  the whole run (`full_run_*`). Derived ratios: `departure_ratio = departed / offered`,
  `completion_ratio_offered = arrived / offered`, `completion_ratio_departed = arrived / departed`
  (0.0 when the denominator is 0).
* **`throughput`** is a flow count: vehicles that ARRIVE inside the measurement window (it also
  counts vehicles scheduled during warmup that arrive in the window).
* **Completed-trip metrics** (`mean_travel_time`, `mean_waiting_time`, `mean_time_loss`,
  `mean_stops`, `mean_time_in_system_seconds`, `corridor_*`, `post_shock_time_loss`) are
  CONDITIONAL on completion: they average only cohort vehicles that arrived before the run ended.
  SUMO `duration` starts at insertion, so travel time, waiting time and time loss exclude the
  insertion delay and every never-inserted vehicle. A controller that completes fewer trips can
  therefore show lower completed-trip delay without being better. Final analysis must always pair
  these metrics with `throughput`, `completion_ratio_offered`/`departure_ratio` and the queue
  metrics (`COMPANION_METRICS` in `metric_definitions.py`) and must not read a lower
  completed-trip delay as better when completion ratios differ.
* **Insertion delay**: `mean_depart_delay_seconds` and `total_depart_delay_seconds` come from
  SUMO `departDelay` of cohort vehicles that actually departed. Never-inserted vehicles are
  reported separately (`never_inserted_vehicle_count`) and a documented LOWER BOUND of their
  backlog delay (`never_inserted_backlog_delay_lower_bound_seconds`: run end minus scheduled
  departure) is provided; it is never merged into completed-trip means.

## Queue metrics

Queue telemetry is produced by the simulation runner for every controller (including
`B0_FIXED`) after each simulation step. It stores one row per UNIQUE incoming lane and step
(`lane_telemetry.parquet`) and one row per intersection and step (`junction_telemetry.parquet`).
The former per-movement trace repeated one lane queue once per movement using the lane; sums
over that trace overcounted queues threefold and are no longer used.

* `lane_queue`: SUMO halting-vehicle count of one incoming lane and step.
* `intersection_total_queue`: sum of the unique incoming-lane queues of one intersection.
* `network_total_queue`: sum of the unique incoming-lane queues of all intersections.

Final queue metrics: `mean_network_queue_vehicles`, `max_network_queue_vehicles`,
`mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`,
`max_lane_queue_vehicles` (plus the diagnostic `mean_lane_queue_vehicles`). There is no
unscoped `max_queue`/`mean_queue`.

**Physical capacity note.** `max_lane_queue_vehicles` may saturate at the physical storage of a
lane: a 235.6 m single-lane edge holds about 30 halted vehicles (vehicle length 5 m plus
minimum gap 2.5 m, stop offset 7 m), a 92.8 m border edge about 12. About 30 is therefore a
physical limit, not a software cap. In overloaded scenarios `max_lane_queue_vehicles` loses
discriminatory power (every run reaches the same maximum); the network and intersection
aggregates remain available for that reason and must be reported alongside it.

## Post-shock queue AUC (S3, frozen definition)

`post_shock_queue_auc_vehicle_seconds` is the integral of the canonical `network_total_queue`
over the post-shock measurement interval, with trapezoidal integration over simulation time:

```text
auc = sum((Q_i + Q_{i+1}) / 2 * (t_{i+1} - t_i))     [vehicle-seconds]
```

* `Q_i` = `network_total_queue` = sum over UNIQUE incoming lanes of the halting count sampled
  after step `i` (never movement-level rows, so no lane is counted twice);
* `t_i` = telemetry timestamp of step `i` (`(i + 1) * step_length`);
* samples are steps `shock_start_step <= i < measurement_end_step` where
  `shock_start_step = shock_start_seconds / step_length` and `shock_start_seconds` is the
  scenario's frozen `traffic.shock_start_seconds` (2100 s for S3 = 50% of the measurement
  window);
* fewer than two samples -> 0. The related `post_shock_mean_network_queue_vehicles` and
  `post_shock_max_network_queue_vehicles` use the same samples.

`post_shock_time_loss` uses completed trips of cohort vehicles SCHEDULED at or after the shock
start (not vehicles inserted after it), so a pre-shock entry backlog cannot masquerade as
post-shock demand.

## Corridor Definition

Corridor definition version: `west-east-middle-corridor-v2`

Operational path:

```text
West -> A4 -> A5 -> A6 -> East
```

SUMO identifiers:

- entry edge: `left1A1`
- controlled junction path: `A1 -> B1 -> C1`
- through edges: `A1B1`, `B1C1`
- exit edge: `C1right1`

Corridor membership: the vehicle route traverses edge `A1B1` immediately followed by edge
`B1C1`. Corridor metrics are computed for those vehicles only; the corridor target is
directional demand, not a claim that every vehicle travels straight through the whole network.

## Entry accounting

`run_metrics.json` also stores, per entry edge and per demand group (`base`, `dominant`,
`residual`, `shock`, `hotspot`), the cohort `offered`, `departed`, `arrived` and
`entry_departure_ratio` (`by_entry`, `by_group`), plus `min_entry_departure_ratio`. They let a
run validate that the intended demand pattern (for example the 80% West dominant share of S2)
still reaches the network and is not hidden by insertion starvation.

## Scenario Metric Sets

| Scenario | Metrics |
|---|---|
| `S1_BALANCED` | `throughput`, `mean_travel_time`, `mean_waiting_time`, `mean_time_loss`, `mean_stops`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S2_DIRECTIONAL_PEAK` | `throughput`, `mean_stops`, `mean_time_loss`, `corridor_throughput`, `corridor_mean_travel_time`, `corridor_mean_stops`, `min_entry_departure_ratio`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S3_DEMAND_SHIFT` | `post_shock_mean_network_queue_vehicles`, `post_shock_max_network_queue_vehicles`, `post_shock_time_loss`, `post_shock_queue_auc_vehicle_seconds`, `throughput`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S4_LOCAL_SATURATION` | `throughput`, `mean_time_loss`, `mean_travel_time`, `internal_lane_persistence_events`, `mean_network_queue_vehicles`, `max_network_queue_vehicles`, `mean_intersection_queue_vehicles`, `max_intersection_queue_vehicles`, `max_lane_queue_vehicles`, `offered_vehicle_count`, `departed_vehicle_count`, `arrived_vehicle_count`, `never_inserted_vehicle_count`, `unfinished_in_network_count`, `departure_ratio`, `completion_ratio_offered`, `completion_ratio_departed`, `mean_depart_delay_seconds` |
| `S5_COMMUNICATION_DEGRADATION` | `throughput`, `mean_waiting_time`, `mean_time_loss`, `mean_network_queue_vehicles`, `messages_sent`, `messages_delivered`, `messages_dropped`, `messages_stale`, `bytes_sent`, `bytes_delivered`, `mean_message_age_steps`, `max_message_age_steps`, `throughput_change_vs_zero_loss`, `completion_ratio_offered` |

`recovery_time_seconds` is not implemented for V1 because no fixed, pre-result threshold rule
has been frozen. S3 uses post-shock queue/time-loss metrics instead.

Downstream occupancy is available to controller logic, but it is not aggregated as a final
campaign metric from run artifacts. It must not be reported as a final S4 metric until an
artifact-level aggregation is implemented and frozen.

## Metric Definitions

| Name | Unit | Source | Population / denominator | Measurement window | Aggregation | Edge cases | Completed trips only |
|---|---|---|---|---|---|---|---|
| `offered_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Count of offered vehicles in the measurement cohort (alias of measurement_offered_vehicle_count). | Counts are 0 when the population is empty. | no |
| `departed_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles that were inserted into the network before the run ended. | Counts are 0 when the population is empty. | no |
| `arrived_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles that arrived before the run ended. | Counts are 0 when the population is empty. | no |
| `never_inserted_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles that never entered the network (offered - departed). | Counts are 0 when the population is empty. | no |
| `unfinished_in_network_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles inserted but not arrived at the end of the run (departed - arrived). | Counts are 0 when the population is empty. | no |
| `full_run_offered_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Every offered vehicle. | Whole run, including warmup (offered/departed/arrived over every vehicle). | All vehicles offered by the route file over the whole run. | Counts are 0 when the population is empty. | no |
| `full_run_departed_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Every offered vehicle. | Whole run, including warmup (offered/departed/arrived over every vehicle). | All vehicles inserted into the network over the whole run. | Counts are 0 when the population is empty. | no |
| `full_run_arrived_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Every offered vehicle. | Whole run, including warmup (offered/departed/arrived over every vehicle). | All vehicles that arrived over the whole run. | Counts are 0 when the population is empty. | no |
| `full_run_never_inserted_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Every offered vehicle. | Whole run, including warmup (offered/departed/arrived over every vehicle). | Offered vehicles that never entered the network over the whole run. | Counts are 0 when the population is empty. | no |
| `full_run_unfinished_in_network_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Every offered vehicle. | Whole run, including warmup (offered/departed/arrived over every vehicle). | Vehicles inserted but not arrived at the end of the run. | Counts are 0 when the population is empty. | no |
| `measurement_offered_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Offered vehicles scheduled inside the measurement window. | Counts are 0 when the population is empty. | no |
| `measurement_departed_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles inserted before the run ended. | Counts are 0 when the population is empty. | no |
| `measurement_arrived_vehicle_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles that arrived before the run ended. | Counts are 0 when the population is empty. | no |
| `departure_ratio` | ratio | Population counts from route file and SUMO tripinfo. | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | departed_vehicle_count / offered_vehicle_count. | Reported as 0.0 when the denominator is 0. | no |
| `completion_ratio_offered` | ratio | Population counts from route file and SUMO tripinfo. | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | arrived_vehicle_count / offered_vehicle_count. | Reported as 0.0 when the denominator is 0. | no |
| `completion_ratio_departed` | ratio | Population counts from route file and SUMO tripinfo. | Measurement cohort. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | arrived_vehicle_count / departed_vehicle_count. | Reported as 0.0 when the denominator is 0. | no |
| `throughput` | vehicles | SUMO tripinfo arrival times (equals SUMO arrived counts per step). | Flow count: every vehicle arriving in the window, including vehicles scheduled during warmup. | Warmup excluded; measurement interval from scenario config. | Count of vehicles that arrive during the measurement window. | If no vehicles arrive, report 0. | no |
| `completed_trip_count` | vehicles | Route file (scheduled departures) joined with SUMO tripinfo (departed/arrived). | Measurement cohort, completed trips. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Cohort vehicles used for completed-trip metrics (arrived before the run ended). | Counts are 0 when the population is empty. | no |
| `mean_depart_delay_seconds` | seconds/vehicle | SUMO tripinfo departDelay (insertion time - scheduled departure). | Cohort vehicles that actually departed (never-inserted vehicles excluded). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over cohort vehicles that were inserted. | Omitted if no cohort vehicle was inserted. | no |
| `total_depart_delay_seconds` | seconds | SUMO tripinfo departDelay. | Cohort vehicles that actually departed. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Sum over cohort vehicles that were inserted. | 0 when no cohort vehicle was inserted. | no |
| `never_inserted_backlog_delay_lower_bound_seconds` | seconds | Route file scheduled departure and the simulated run end. | Cohort vehicles that never entered the network. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Sum over never-inserted cohort vehicles of (run end - scheduled departure); a LOWER BOUND of their backlog delay, never merged into completed-trip means. | 0 when every cohort vehicle was inserted. | no |
| `mean_travel_time` | seconds/vehicle | SUMO tripinfo duration (arrival - insertion; excludes insertion delay). | Completed trips of the measurement cohort (conditional on completion). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `mean_waiting_time` | seconds/vehicle | SUMO tripinfo waitingTime for completed trips. | Completed trips of the measurement cohort (conditional on completion). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `mean_time_loss` | seconds/vehicle | SUMO tripinfo timeLoss for completed trips. | Completed trips of the measurement cohort (conditional on completion). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `mean_stops` | stops/vehicle | SUMO tripinfo waitingCount for completed trips. | Completed trips of the measurement cohort (conditional on completion). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `mean_time_in_system_seconds` | seconds/vehicle | SUMO tripinfo duration + departDelay for completed trips. | Completed trips of the measurement cohort (conditional on completion). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean of (travel time + insertion delay) over completed trips. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `corridor_throughput` | vehicles | Route file corridor membership (west-east-middle-corridor-v2) and tripinfo. | Flow count of vehicles whose route traverses the middle-row corridor. | Warmup excluded; measurement interval from scenario config. | Count of corridor vehicles that arrive during the measurement window. | If no corridor vehicles arrive, report 0. | no |
| `corridor_mean_travel_time` | seconds/vehicle | SUMO tripinfo duration filtered to west-east-middle-corridor-v2. | Completed corridor trips of the measurement cohort (conditional). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `corridor_mean_stops` | stops/vehicle | SUMO tripinfo waitingCount filtered to west-east-middle-corridor-v2. | Completed corridor trips of the measurement cohort (conditional). | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `post_shock_time_loss` | seconds/vehicle | SUMO tripinfo timeLoss of completed trips scheduled at or after the shock time. | Completed trips of cohort vehicles SCHEDULED at or after the shock start (conditional on completion; population defined by scheduled, not insertion, time). | Post-shock subset of the measurement window. | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `pre_shock_time_loss` | seconds/vehicle | SUMO tripinfo timeLoss of completed trips scheduled before the shock time. | Completed trips of cohort vehicles scheduled before the shock start (conditional on completion). | Pre-shock subset of the measurement window. | Arithmetic mean over completed trips of the cohort. | If no cohort vehicle completes its trip, omit the metric for that run. | yes |
| `mean_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Mean over measurement steps of network_total_queue (sum of unique incoming-lane halting counts). | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `max_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Maximum over measurement steps of network_total_queue. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `mean_intersection_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Mean over measurement steps and intersections of intersection_total_queue (sum of the unique incoming-lane halting counts of one intersection). | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `max_intersection_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Maximum over measurement steps and intersections of intersection_total_queue. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `mean_lane_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Mean over measurement steps and lanes of lane_queue (diluted by idle lanes; diagnostic only). | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `max_lane_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Maximum lane_queue over measurement steps and lanes. May saturate at the physical storage capacity of a lane (about 30 vehicles on a 235.6 m edge) in overloaded scenarios and then loses discriminatory power; use the network/intersection aggregates alongside it. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `post_shock_mean_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Post-shock subset of the measurement window (step >= shock start step). | Mean network_total_queue over post-shock measurement steps. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `post_shock_max_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Post-shock subset of the measurement window (step >= shock start step). | Maximum network_total_queue over post-shock measurement steps. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `pre_shock_mean_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Pre-shock subset of the measurement window. | Mean network_total_queue over pre-shock measurement steps. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `pre_shock_max_network_queue_vehicles` | vehicles | Canonical lane_telemetry.parquet / junction_telemetry.parquet (SUMO halting vehicle count per UNIQUE incoming lane, sampled by the simulation runner for every controller). | All vehicles halting on incoming lanes; each physical lane counted once. | Pre-shock subset of the measurement window. | Maximum network_total_queue over pre-shock measurement steps. | Omitted only if no telemetry samples exist in the window (run fails). | no |
| `post_shock_queue_auc_vehicle_seconds` | vehicle-seconds | Canonical lane_telemetry.parquet (unique-lane halting counts). | network_total_queue = sum over unique incoming lanes; never movement rows. | Post-shock subset of the measurement window. | Trapezoidal integral of network_total_queue over simulation time from the shock start step to the last measurement step: sum((Q_i + Q_{i+1}) / 2 * (t_{i+1} - t_i)) with t_i the telemetry timestamp of step i. | 0 if fewer than two post-shock samples exist. | no |
| `internal_lane_persistence_events` | events | Canonical junction_telemetry.parquet: vehicles present on the internal lanes of an intersection in two consecutive steps. | Vehicles on junction internal lanes. | Measurement-window steps only (warmup excluded); one sample per simulation step. | Sum over measurement steps and intersections (one row per intersection and step). Proxy of internal-junction occupancy, not a spillback or gridlock measurement. | Report 0 when no persistence events are observed. | no |
| `offered_by_entry` | vehicles | Route file entry edges (scheduled departures). | Measurement cohort grouped by entry edge. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Exported per entry edge as `offered_by_entry__<entry_edge>`: cohort vehicles offered at that border entry. | 0 for an entry without offered vehicles. | no |
| `departed_by_entry` | vehicles | Route file entry edges joined with SUMO tripinfo. | Measurement cohort grouped by entry edge. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Exported per entry edge as `departed_by_entry__<entry_edge>`: cohort vehicles of that entry that were inserted. | 0 for an entry without departures. | no |
| `arrived_by_entry` | vehicles | Route file entry edges joined with SUMO tripinfo. | Measurement cohort grouped by entry edge. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Exported per entry edge as `arrived_by_entry__<entry_edge>`: cohort vehicles of that entry that arrived before the run ended. | 0 for an entry without arrivals. | no |
| `entry_departure_ratio` | ratio | Route file entry edges joined with SUMO tripinfo. | Measurement cohort grouped by entry edge. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Exported per entry edge as `entry_departure_ratio__<entry_edge>`: departed / offered at that entry; shows whether the intended demand pattern reaches the network or is hidden by insertion starvation. | Reported as 0.0 when the entry offered no vehicles. | no |
| `min_entry_departure_ratio` | ratio | Route file entry edges joined with SUMO tripinfo. | Measurement cohort grouped by entry edge. | Measurement window; cohort = vehicles scheduled to depart inside [warmup, warmup + measurement_duration). | Minimum over entry edges of departed / offered (cohort). | 0.0 for an entry with no departures. | no |
| `messages_sent` | messages | MessageBus communication metrics. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total messages published by cooperative controllers. | For non-communicating controllers, report 0 or omit from communication tables. | no |
| `messages_delivered` | messages | MessageBus communication metrics. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total messages delivered to destination inboxes. | For non-communicating controllers, report 0 or omit from communication tables. | no |
| `messages_dropped` | messages | MessageBus communication metrics. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total messages dropped by the configured loss process. | Report 0 when no drops are observed. | no |
| `messages_stale` | messages | Cooperative controller message freshness accounting. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total received messages rejected as stale. | Report 0 when no stale messages are observed. | no |
| `bytes_sent` | bytes | MessageBus serialized message accounting. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total serialized bytes published. | Report 0 when no messages are sent. | no |
| `bytes_delivered` | bytes | MessageBus serialized message accounting. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Total serialized bytes delivered. | Report 0 when no messages are delivered. | no |
| `mean_message_age_steps` | simulation steps/message | Cooperative controller message freshness accounting. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Arithmetic mean age of observed messages. | Report 0 when no messages are observed. | no |
| `max_message_age_steps` | simulation steps | Cooperative controller message freshness accounting. | Not population dependent. | Full simulated run, including warmup, unless report labels otherwise. | Maximum observed message age. | Report 0 when no messages are observed. | no |
| `throughput_change_vs_zero_loss` | vehicles | Derived from throughput rows grouped by scenario, controller, and seed. | Not population dependent. | Same measurement window as throughput. | throughput(drop_probability=x) - throughput(drop_probability=0). | Only exported when a same-scenario/controller/seed zero-loss baseline exists. | no |

## S4 Internal-Lane Proxy Policy

`internal_lane_persistence_events` is a proxy for persistent internal-junction occupancy. It is
the number of vehicles present on the internal lanes of an intersection in two consecutive
steps, summed over intersections and measurement steps (one value per intersection and step; it
is not replicated per movement). It is not spillback duration, gridlock duration, or a universal
direct measurement of blocked junctions.

## S5 Derived Metric Policy

`throughput_change_vs_zero_loss` is a descriptive within-controller comparison against the
zero-loss condition for the same scenario and seed. Do not describe the value as degradation
caused by communication without the full experimental context and controls.
