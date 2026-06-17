# Development Solution: Wildfire Cellular-Automata Simulation

This folder contains a deterministic 2D wildfire cellular-automata simulation with
a firefighting overlay and a selectable firefighter motion strategy.

It is the simulation engine wrapped by [`../PipelineSolution/`](../PipelineSolution/),
which adds a plain-language strategy-optimization pipeline, baseline validation, and
text/PDF reporting.

## Requirements
- Python 3.9+ (tested on Python 3.12)
- Linux/macOS shell commands shown below (Windows PowerShell equivalents are straightforward)

## Reproducible Setup

```bash
cd DevelopmentSolution
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python main.py --nx 80 --ny 80 --nt 200 --seed 12345 --firefighters 3
```

Headless run (no interactive window):

```bash
python main.py --nx 80 --ny 80 --nt 200 --seed 12345 --firefighters 3 --no-show
```

Save a VS Code-openable animation and a per-step statistics CSV:

```bash
python main.py --nx 80 --ny 80 --nt 200 --seed 12345 --firefighters 3 \
    --save-animation outputs/wildfire.gif --output-csv outputs/wildfire_counts.csv --no-show
```

The `.gif` opens directly in the VS Code preview pane.

## Block (cell) types

| Code | Block | Fuel | Fire behavior | Firefighter traversal |
| --- | --- | --- | --- | --- |
| 0 | Mountain | none | cannot enter/spread | slow: 1 cell per 2 turns |
| 1 | Water | none | cannot ignite/spread | **cannot cross** (impassable) |
| 2 | Low fuel | low | burns in 1 turn | 2 cells/turn |
| 3 | High fuel | high | burns in 2 turns | 1 cell/turn |
| 4 | Fire | burning | diminishes as fuel is consumed | 1 cell/turn while on fire |
| 5 | Depleted | zero | cannot spread | 2 cells/turn |

Fire spreads via the **Moore neighborhood** with **block-type-weighted ignition
probabilities** (`p_ignite_low`, `p_ignite_high`). Burned-out cells become
**depleted**; extinguished cells revert to their **fuel type** (remaining fuel
restored, not depleted).

## Firefighter motion strategy (selectable)

The engine's **default** policy is `greedy-closest`: move toward the nearest fire
when none is adjacent, otherwise stand and fight. Override with `--strategy`:

- `greedy-closest` (default)
- `hold` — never move (only extinguish adjacent fires)
- `waypoint` — route through `--waypoints "R,C R,C ..."`

For programmatic control (used by the analysis pipeline), `run_simulation(config,
strategy_fn=...)` accepts a pluggable callable
`(i, ff_positions, terrain, fire_mask, rng) -> (r, c) | None`. The CA fire/landscape
mechanics stay fixed; **only the firefighter decision policy is the variable** —
this is the seam `PipelineSolution/` optimizes over.

## CLI Parameters

Minimum required inputs:
- `--nx`, `--ny`: grid dimensions
- `--nt`: number of turns
- `--seed`: deterministic RNG seed
- `--fire-start` (repeatable `R,C`, must be on low/high fuel; default auto-places 1)
- `--firefighters` (count) and/or `--firefighter-starts "R,C R,C ..."` (non-water)
- `--strategy`: `greedy-closest` | `hold` | `waypoint`

Model parameters:
- `--mountain-fraction`, `--water-fraction`, `--high-fuel-fraction`
- `--n-blobs`, `--blob-sigma` (landscape coherence)
- `--p-ignite-low`, `--p-ignite-high`, `--p-extinguish`

Output controls:
- `--save-animation`, `--output-csv`, `--frame-stride`, `--interval-ms`, `--no-show`

Program output prints per-turn statistics:

```text
step=0 burning=1 depleted=0 fuel=3978 firefighters=3 burned=1
step=1 burning=2 depleted=0 fuel=3977 firefighters=3 burned=2
...
```

## Determinism
- The simulation is deterministic for fixed arguments and a fixed `--seed`.
- The chosen `--strategy` is part of the fixed input; identical inputs (including
  strategy) produce identical trajectories.

## Run Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Example run

A reproducible reference run lives in [`example_run/`](example_run/) — see
[`example_run/INPUTS.md`](example_run/INPUTS.md) for the exact command that
reproduces `wildfire_counts.csv` and `wildfire.gif`.