*This project has been created as part of the 42 curriculum by odschreu.*

# Fly-in

## Description

Fly-in is a multi-agent drone routing simulator. It parses a custom map
format describing a network of zones and bidirectional connections, then
routes a fleet of drones from a single start zone to a single end zone in
as few simulation turns as possible, while respecting per-zone and
per-connection capacity limits, zone-type movement costs, and turn-based
transit rules for restricted zones.

The project is split into four stages:

1. **Parsing** — reads a `.txt` map file, validates its structure line by
   line, and builds an in-memory `Network` (zones + connections).
2. **Pathfinding** — computes the lowest-cost route from the start zone to
   the end zone using Dijkstra's algorithm, weighted by each destination
   zone's movement cost (`normal`/`priority` = 1, `restricted` = 2,
   `blocked` = unreachable).
3. **Simulation** — steps every drone through that route turn by turn,
   resolving zone/connection capacity conflicts, multi-turn transit
   through restricted zones, and arrival at the goal.
4. **Visualization** — replays the resulting turn log in an interactive
   `curses` terminal viewer.

No graph or visualization library (`networkx`, `graphlib`, etc.) is used;
the graph model, Dijkstra implementation, and terminal rendering are all
built from scratch on top of the standard library and `pydantic`.

## Instructions

### Requirements

- Python 3.10+
- `pydantic` (installed automatically, see below)
- A terminal that supports `curses` (the built-in module on Linux/macOS;
  on Windows, install `windows-curses`)

### Setup

```bash
make install   # installs project dependencies
```

### Running

Place one or more map `.txt` files in the `maps/` directory at the
project root, then run:

```bash
make run       # runs the simulation + visualizer
```

or directly:

```bash
python -m src
```

Every map found in `maps/` is parsed and simulated. Once all simulations
have finished computing, the interactive viewer opens on a menu screen.

### Debugging

```bash
make debug     # runs the main script under pdb
```

### Linting / type-checking

```bash
make lint         # flake8 + mypy (project's required flag set)
make lint-strict   # flake8 + mypy --strict
```

### Cleaning

```bash
make clean     # removes __pycache__, .mypy_cache, etc.
```

## Usage — the viewer

The viewer is keyboard-driven and moves through three screens:

- **Menu** — `↑`/`↓` to choose *start* or *quit*, `Enter` to confirm.
- **Map select** — pick which parsed map to inspect (one entry per map
  found in `maps/`).
- **Viewer** — the main split-pane screen (see *Visual Representation*
  below). `q` returns to map select, `Esc` quits.

## Algorithm choices & implementation strategy

**Parsing.** `Parser` reads a map file in two passes: a structural pass
(`_check_definition_order`) that enforces the required
`nb_drones` → zones → connections ordering and rejects malformed or
out-of-order blocks before anything is built, and a build pass
(`_read_map`) that constructs typed `Zone`/`Connection` objects. Every
failure raises a `ParseError` carrying the file, line number, offending
line, and (where relevant) the expected syntax, so the CLI can report
exactly where and why a map is invalid instead of crashing.

**Domain model.** `Zone`, `Connection`, `Drone`, `Network`, `Record`, and
`Movement` are `pydantic` models, since they are primarily typed data
holders whose validation logic (zone-type checking, metadata parsing,
name/dash rules, positive-capacity checks) benefits from `pydantic`'s
`model_validator` hooks. Behavior-heavy pieces — the resolver and the
visualizer — are plain classes instead, since their job is turn-by-turn
mutation and rendering rather than data validation.

**Pathfinding.** `PathFinder` builds an adjacency graph from the parsed
`Network` (skipping `blocked` zones entirely) and runs Dijkstra, weighted
by destination zone cost, to find the single lowest-cost route from start
to end. All drones currently follow this same shared route — the map's
capacity and turn-arbitration rules, not distinct per-drone paths, are
what spread drones out over time. Path diversification (giving drones
different routes when parallel paths exist) and a full cooperative A*
formulation (time-expanded state space with a shared reservation table)
are identified as the natural next step to push down turn counts further
on capacity-heavy maps, but are not implemented yet — the current
resolver-based arbitration was deliberately built first as a correctness
baseline.

**Turn resolution.** `TurnResolver.resolve()` runs once per simulation
turn and processes drones in three phases, in this order, so movement
this turn can never oversubscribe a zone or connection:

1. **Landing** — drones whose in-transit countdown reaches zero arrive at
   their destination zone.
2. **Continuing transit** — drones still mid-transit through a
   `restricted` connection decrement their remaining transit time; they
   cannot wait or divert once committed.
3. **Proposing** — drones currently at a zone attempt to move to the next
   zone on their path, but only if the destination zone and the
   connection both still have free capacity after the landing/transit
   phases have been accounted for.

Zone and connection occupancy are recomputed from the live drone list at
the top of every `resolve()` call rather than tracked as mutable state on
the `Zone`/`Connection` objects themselves, which avoids a whole class of
stale-state bugs when drones land, depart, and enter transit within the
same turn. A drone entering a `restricted` zone commits to
`transit_turns_left = cost - 1` turns of transit (the departure turn
itself counts as the first unit) and must arrive on schedule — it cannot
wait on the connection for space to open up at the destination.

## Visual Representation

The viewer is a `curses` terminal UI with a two-column, split-pane layout:

- **Map panel** (left) — draws every zone at a coordinate scaled from its
  `(x, y)` map position, connections as orthogonal (L-bend) routed lines
  between zone ports, and every drone's current position, stacking
  drones that share a zone so none are hidden. Zone colors from the map
  file are rendered using `curses` color pairs; a status bar in the
  bottom-right shows the current turn out of the total.
- **Connections/zone-select panel** (top right) — lists all connections
  in the map by default. Pressing `i` switches it into **zone inspection
  mode**: a scrollable list of zones (`↑`/`↓` to move the selection), and
  the map panel re-renders to highlight the selected zone together with
  every zone it's directly connected to, dimming the rest of the network
  so a specific zone's neighborhood is easy to pick out on dense maps.
- **Turn log panel** (bottom right) — a scrolling, word-wrapped log of
  every drone movement per turn (`D<id>-<destination>`), with the most
  recent turn bolded and earlier turns dimmed for context.

`←`/`→` step backward and forward through the recorded turns at any time
(including while in inspection mode), so the whole simulation — and how a
specific zone's traffic evolved turn by turn — can be replayed after the
fact rather than only observed live. This turned out to matter more than
expected for debugging capacity-arbitration logic: stepping back one turn
at a time made conflicts (e.g. two drones proposing to enter the same
zone) far easier to catch than reading the raw turn log alone.

## Resources


- Red Blob Games — pathfinding and graph-search visual explanations (redblobgames.com)
- NeetCode — algorithm walkthroughs
- `barraRRR/Fly-in` (GitHub) — a reference implementation examined for
  general approach (it uses `blessed` for terminal rendering and a
  turn-penalized A* for connection routing; this project's `curses`
  renderer and Dijkstra-based pathfinder were written independently)
- Dijkstra's Algorithm — Computerphile (Dr Mike Pound):
  https://www.youtube.com/watch?v=GazC3A4OQTE
- Dijkstra's Algorithm in 3 Minutes — Spanning Tree:
  https://www.youtube.com/watch?v=_lHSawdgXpI
- Understanding Dijkstra's Algorithm — freeCodeCamp.org (full derivation
  plus a Python implementation using an adjacency list and a min-heap
  priority queue): search "Understanding Dijkstra's Algorithm" on the
  freeCodeCamp.org YouTube channel
- Pydantic documentation — https://docs.pydantic.dev/latest/ (used for
  `Zone`, `Connection`, `Drone`, `Network`, `Record`, `Movement`, and
  their `model_validator`-based field validation)
- Python `curses` module documentation —
  https://docs.python.org/3/library/curses.html, plus the accompanying
  HOWTO tutorial — https://docs.python.org/3/howto/curses.html (used for
  windows, `color_pair`/`init_pair`, key handling, and the split-pane
  viewer layout)


**AI usage:** AI assistance (Claude) was used throughout development as a
debugging and design-review partner rather than a code generator —
working through the causes of specific bugs (e.g. an off-by-one in
transit-turn accounting, stale per-turn connection occupancy, a
`lstrip()` vs `removeprefix()` mix-up, curses color-pair handling) by
discussing the underlying logic before writing a fix, and reviewing
design decisions such as splitting data-holder classes (`pydantic`) from
behavior-heavy classes (plain typed classes), and how to structure the
zone-inspection feature's state ownership. It was also used to help
structure this README. All code in the submission was written and is
understood by the author.
