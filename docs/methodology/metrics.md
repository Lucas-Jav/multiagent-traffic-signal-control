# Scenario-Specific Metrics

Status: V1 final metric definitions. These definitions must be frozen before
the pilot or final campaign is executed.

The final campaign must not use hand-calculated metrics. Metrics are exported
from run artifacts into `combined_metrics.parquet`; report generation reads that
file and writes `metric_definitions.json` for the observed metric names.

Warmup is excluded from traffic metrics unless a metric explicitly states
otherwise. Communication counters describe the configured communication process
over the simulated run and must be interpreted with the scenario communication
settings.

## Corridor Definition

Corridor definition version: `west-east-middle-corridor-v1`

Operational path:

```text
West -> A4 -> A5 -> A6 -> East
```

SUMO identifiers:

- entry edge: `left1A1`
- controlled junction path: `A1 -> B1 -> C1`
- through edges: `A1B1`, `B1C1`
- exit edge: `C1right1`

Corridor metrics are computed only for vehicles assigned to this corridor by
route or flow identifiers. The corridor target is directional demand, not a
claim that every vehicle travels straight through the whole network.

## Scenario Metric Sets

| Scenario | Metrics |
|---|---|
| `S1_BALANCED` | `throughput`, `mean_travel_time`, `mean_waiting_time`, `mean_time_loss`, `mean_queue`, `max_queue`, `mean_stops` |
| `S2_DIRECTIONAL_PEAK` | `network_throughput`, `mean_stops`, `mean_time_loss`, `mean_queue`, `corridor_throughput`, `corridor_travel_time`, `corridor_stops` |
| `S3_DEMAND_SHIFT` | `post_shock_mean_queue`, `post_shock_max_queue`, `post_shock_time_loss`, `post_shock_queue_auc` |
| `S4_LOCAL_SATURATION` | `mean_queue`, `max_queue`, `throughput`, `mean_time_loss`, `mean_travel_time`, `internal_lane_persistence_events` |
| `S5_COMMUNICATION_DEGRADATION` | `throughput`, `mean_waiting_time`, `mean_time_loss`, `mean_queue`, `messages_sent`, `messages_delivered`, `messages_dropped`, `messages_stale`, `bytes_sent`, `bytes_delivered`, `mean_message_age_steps`, `max_message_age_steps`, `throughput_change_vs_zero_loss` |

`recovery_time_seconds` is not implemented for V1 because no fixed,
pre-result threshold rule has been frozen. S3 uses post-shock queue/time-loss
metrics instead.

Downstream occupancy is available to controller logic, but it is not currently
aggregated as a final campaign metric from run artifacts. It must not be
reported as a final S4 metric until an artifact-level aggregation is implemented
and frozen.

## Metric Definitions

| Name | Unit | Source | Aggregation | Measurement window | Edge-case policy |
|---|---|---|---|---|---|
| `throughput` | vehicles | SUMO arrived counts | Count of vehicles that arrive | Measurement window, warmup excluded | If no vehicles arrive, report 0 |
| `network_throughput` | vehicles | SUMO arrived counts | Alias of `throughput` for whole-network scope | Measurement window, warmup excluded | If no vehicles arrive, report 0 |
| `mean_travel_time` | seconds/vehicle | SUMO tripinfo `duration` | Arithmetic mean over arrived vehicles | Measurement window, warmup excluded | If no vehicles arrive, omit metric |
| `mean_waiting_time` | seconds/vehicle | SUMO tripinfo `waitingTime` | Arithmetic mean over arrived vehicles | Measurement window, warmup excluded | If no vehicles arrive, omit metric |
| `mean_time_loss` | seconds/vehicle | SUMO tripinfo `timeLoss` | Arithmetic mean over arrived vehicles | Measurement window, warmup excluded | If no vehicles arrive, omit metric |
| `mean_queue` | vehicles | `intersection_trace.csv` movement queue rows | Arithmetic mean over post-warmup movement queue samples | Measurement window, warmup excluded | If no trace rows exist, omit metric |
| `max_queue` | vehicles | `intersection_trace.csv` movement queue rows | Maximum post-warmup movement queue sample | Measurement window, warmup excluded | If no trace rows exist, omit metric |
| `mean_stops` | stops/vehicle | SUMO tripinfo `waitingCount` | Arithmetic mean over arrived vehicles | Measurement window, warmup excluded | If no vehicles arrive, omit metric |
| `corridor_throughput` | vehicles | SUMO tripinfo joined to route/flow IDs for `west-east-middle-corridor-v1` | Count of arrived corridor vehicles | Measurement window, warmup excluded | If no corridor vehicles arrive, report 0 |
| `corridor_travel_time` | seconds/vehicle | SUMO tripinfo `duration` filtered to `west-east-middle-corridor-v1` | Arithmetic mean over arrived corridor vehicles | Measurement window, warmup excluded | If no corridor vehicles arrive, omit metric |
| `corridor_stops` | stops/vehicle | SUMO tripinfo `waitingCount` filtered to `west-east-middle-corridor-v1` | Arithmetic mean over arrived corridor vehicles | Measurement window, warmup excluded | If no corridor vehicles arrive, omit metric |
| `post_shock_mean_queue` | vehicles | `intersection_trace.csv` queue rows after frozen shock time | Arithmetic mean over post-shock queue samples | Post-shock subset of measurement window | If no post-shock trace rows exist, omit metric |
| `post_shock_max_queue` | vehicles | `intersection_trace.csv` queue rows after frozen shock time | Maximum post-shock queue sample | Post-shock subset of measurement window | If no post-shock trace rows exist, omit metric |
| `post_shock_time_loss` | seconds/vehicle | SUMO tripinfo `timeLoss` for vehicles departing at or after the shock time | Arithmetic mean over post-shock arrived vehicles | Post-shock subset of measurement window | If no post-shock vehicles arrive, omit metric |
| `post_shock_queue_auc` | vehicle-seconds | `intersection_trace.csv` queue rows after frozen shock time | Trapezoidal integration of the post-shock queue time series | Post-shock subset of measurement window | If fewer than two post-shock queue samples exist, report 0 |
| `internal_lane_persistence_events` | events | Internal-lane vehicle persistence tracker in `intersection_trace.csv` | Sum of post-warmup persistence events | Measurement window, warmup excluded | Report 0 when no persistence events are observed |
| `messages_sent` | messages | MessageBus metrics | Total messages published | Full simulated run unless report labels otherwise | Non-communicating controllers report 0 or are omitted from communication tables |
| `messages_delivered` | messages | MessageBus metrics | Total messages delivered to inboxes | Full simulated run unless report labels otherwise | Non-communicating controllers report 0 or are omitted |
| `messages_dropped` | messages | MessageBus metrics | Total messages dropped by the configured loss process | Full simulated run unless report labels otherwise | Report 0 when no drops are observed |
| `messages_stale` | messages | Cooperative controller freshness accounting | Total received messages rejected as stale | Full simulated run unless report labels otherwise | Report 0 when no stale messages are observed |
| `bytes_sent` | bytes | MessageBus serialized message accounting | Total serialized bytes published | Full simulated run unless report labels otherwise | Report 0 when no messages are sent |
| `bytes_delivered` | bytes | MessageBus serialized message accounting | Total serialized bytes delivered | Full simulated run unless report labels otherwise | Report 0 when no messages are delivered |
| `mean_message_age_steps` | simulation steps/message | Cooperative controller freshness accounting | Arithmetic mean age of observed messages | Full simulated run unless report labels otherwise | Report 0 when no messages are observed |
| `max_message_age_steps` | simulation steps | Cooperative controller freshness accounting | Maximum observed message age | Full simulated run unless report labels otherwise | Report 0 when no messages are observed |
| `throughput_change_vs_zero_loss` | vehicles | Derived from throughput rows grouped by scenario, controller, and seed | `throughput(drop_probability=x) - throughput(drop_probability=0)` | Same as `throughput` | Export only when a same-scenario/controller/seed zero-loss baseline exists |

## S3 Queue AUC Method

`post_shock_queue_auc` uses trapezoidal integration:

```text
auc = sum((q_i + q_{i+1}) / 2 * (t_{i+1} - t_i))
```

The time series starts at the frozen shock time and ends at the measurement
window end. Queue samples use the same movement-level queue signal as
`mean_queue`. The method is fixed before results are inspected.

## S4 Internal-Lane Proxy Policy

`internal_lane_persistence_events` is a proxy for persistent internal-junction
occupancy. It is not spillback duration, gridlock duration, or a universal
direct measurement of blocked junctions.

## S5 Derived Metric Policy

`throughput_change_vs_zero_loss` is a descriptive within-controller comparison
against the zero-loss condition for the same scenario and seed. Do not describe
the value as degradation caused by communication without the full experimental
context and controls.
