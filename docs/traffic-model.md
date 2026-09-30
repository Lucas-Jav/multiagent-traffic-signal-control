# Traffic Model

This document defines the physical traffic model used by `scenarios/grid_3x3`
before adding new scientific controllers.

## Scope

The 3x3 scenario contains nine controlled intersections exposed to controllers
as `A1` through `A9`. The SUMO network keeps its generated junction IDs
(`A0`, `B1`, `C2`, etc.); `scenarios/grid_3x3/metadata.json` maps controller
intersection IDs to SUMO traffic-light IDs.

Visual styling for vehicles, colors, road legibility, and GUI debug settings is
kept in route/view files and simulation setup. It is not part of the control
policy.

## Movements

Each intersection models movements by approach direction and exit direction:

- `north_to_south`
- `north_to_east`
- `north_to_west`
- `south_to_north`
- `south_to_east`
- `south_to_west`
- `east_to_west`
- `east_to_north`
- `east_to_south`
- `west_to_east`
- `west_to_north`
- `west_to_south`

U-turns are excluded. In the current 3x3 topology all nine intersections have
the twelve non-U-turn movements above.

Code represents these as `MovementId` values using:

```text
<intersection_id>:<from_direction>_to_<to_direction>
```

Example:

```text
A5:north_to_south
A5:west_to_north
```

The movement model is built from:

- ordered incoming lanes in `scenario.yaml`: north, east, south, west;
- ordered outgoing lanes in `scenario.yaml`: north, east, south, west;
- SUMO `<connection>` elements and their `linkIndex`;
- SUMO junction `<request>` conflict information.

## Conflicts

Conflicts are represented explicitly per intersection as a movement conflict
matrix. The matrix is derived from SUMO's junction request data and attached to
the `IntersectionTrafficModel`.

A movement pair is considered conflicting when SUMO marks the corresponding
link indexes as foes or response conflicts. Movements from the same incoming
lane are treated as compatible at signal-control level because only one vehicle
stream can discharge from that lane at a time.

Controllers must not encode conflict rules with local `if` statements. They use
controller intents, and phase safety validates movements against the matrix.

## Phase Plan

The scenario uses SUMO `--tls.layout incoming`. Each green phase currently opens
one incoming approach and all valid non-U-turn movements from that approach:

```text
PHASE_NORTH_APPROACH: GGGrrrrrrrrr
PHASE_EAST_APPROACH:  rrrGGGrrrrrr
PHASE_SOUTH_APPROACH: rrrrrrGGGrrr
PHASE_WEST_APPROACH:  rrrrrrrrrGGG
```

This is conservative but valid. The model does not require only one approach per
phase forever. Future phase plans may share compatible movements from multiple
approaches if the explicit conflict matrix allows it.

Each green phase has a derived movement list. A phase is safe only when no two
listed movements conflict.

## Yellow And All-Red

Every transition between green phases must follow:

```text
green -> yellow -> all-red clearance -> next green
```

Current development timing:

- `min_green_seconds`: `10.0`
- `yellow_seconds`: `3.0`
- `all_red_seconds`: `2.0`
- `max_green_seconds`: `60.0`

Controllers cannot skip yellow or all-red phases. They can only return intents
such as `KEEP_PHASE`, `REQUEST_NEXT_PHASE`, or an allowed phase target. The
`PhaseSafetyManager` converts those intents into legal SUMO phase indexes.

## Stop Line And Clearance

Incoming edges have SUMO `stopOffset` for passenger vehicles, currently `7.0m`.
This moves the visual stop position upstream so queued vehicles do not appear to
stand on the signal line.

Vehicles that already entered a junction legally may finish crossing. The safety
requirement is not to teleport or reposition vehicles. The requirement is:

- do not admit new vehicles after their movement closes;
- keep yellow and all-red clearance before a conflicting green opens;
- keep internal-lane clearance checks for adaptive controllers.

If a vehicle appears inside the junction, inspect:

- whether it entered during its legal green/yellow interval;
- incoming lane shape and stop offset;
- internal lane occupancy;
- yellow and all-red timing;
- whether the next phase opened while an internal lane was still blocked.

## Turning Routes

The route configuration contains straight, left-turn, and right-turn demand.
The turning ratios are configured in the scenario YAML and drive route generation
(`src/traffic_agents/simulation/route_walk.py`): at every signalized junction a vehicle picks
straight/left/right with these probabilities, using only legal movements of the network:

```yaml
turning_ratios:
  straight: 0.70
  left: 0.15
  right: 0.15
```

These are the approved V1 protocol values. Route generation remains deterministic by seed; the
realized movement counts and proportions are reported in the route metadata.

## Safe Phase

A safe phase is a green phase that:

- lists the movements it permits;
- contains no conflicting movement pair;
- is reachable through the configured SUMO yellow and all-red sequence;
- respects minimum and maximum green constraints;
- never requires a controller to emit a raw signal-state string.
