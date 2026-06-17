# Development Plan: Wildfire Cellular-Automata Simulation (Python)

## 1. Objective
Build a deterministic, reproducible Python program in `DevelopmentSolution/` that
simulates wildfire spread on a 2D `Nx x Ny` grid for `Nt` turns using the Cellular
Automata technique with Moore neighborhoods, includes a firefighting overlay, and
animates the fire moving through a procedurally generated landscape with matplotlib.

This plan satisfies the repository requirements in the top-level `README.md`:
- Realistic, randomized, deterministic landscapes (seeded)
- Block types: mountain (impassable), water, low fuel, high fuel, fire, depleted
- CA fire spread via Moore neighborhoods with block-type-weighted ignition probabilities
- Burn durations: low fuel = 1 turn, high fuel = 2 turns; burned-out cells become depleted
- Fire never spreads to depleted / mountain / water
- Firefighter overlay with terrain-dependent movement, extinguishing, and a
  **selectable motion strategy** (the seam the analysis pipeline optimizes over)
- Deterministic results via a single seeded RNG
- A snazzy 2D animation openable from within VS Code
- Python with only `numpy` + `matplotlib` (+ `pillow` for GIF export)

## 2. Deliverables
1. `main.py` — CLI entry point: parses parameters, runs the simulation, prints
   per-turn statistics, optionally saves a CSV and/or animation.
2. `simulation.py` — core CA model: block-type codes, landscape generation,
   fire spread, burn-down, firefighter movement/extinguishing, strategy
   selection, and the deterministic time-stepping driver.
3. `visualization.py` — matplotlib animation: discrete terrain colormap with a
   firefighter marker overlay; saves GIF (VS Code-openable) or shows interactively.
4. `requirements.txt` — pinned runtime dependencies.
5. `README.md` — setup, run commands, parameter definitions, determinism notes.
6. `tests/` — determinism regression + CA state-rule checks.
7. `example_run/` — a reproducible reference run (`INPUTS.md`, `wildfire_counts.csv`,
   `wildfire.gif`).

## 3. Proposed Folder Structure
```text
DevelopmentSolution/
  PLAN.md
  README.md
  requirements.txt
  main.py
  simulation.py
  visualization.py
  tests/
    test_determinism.py
    test_state_rules.py
  example_run/
    INPUTS.md
    wildfire_counts.csv
    wildfire.gif
```

## 4. Modeling Approach
Two integer arrays describe the grid:
- `terrain[i, j]` — current cell code in {mountain, water, low_fuel, high_fuel, fire, depleted}.
- `burn_remaining[i, j]` — turns of fuel left for fire cells (1 for low fuel, 2 for high fuel).

Each turn, in fixed order:
1. **Extinguish:** each fire cell adjacent (Moore) to a firefighter is extinguished
   with probability `p_extinguish`; the cell reverts to its original fuel type
   (remaining fuel restored — *not* depleted).
2. **Move:** firefighters move toward a strategy-chosen target, terrain-costed
   (enter low/depleted = 0.5 turns, high fuel/fire = 1 turn, mountain = 2 turns,
   water impassable) with energy carryover.
3. **Spread:** fuel cells in the Moore neighborhood of a fire cell ignite with
   block-type-weighted probability (`p_ignite_low` / `p_ignite_high`); depleted,
   mountain, and water never ignite.
4. **Burn-down:** only pre-existing fires decrement `burn_remaining`; cells
   reaching 0 become depleted. (Newly ignited cells start their own timer.)

Firefighters are an overlay (`ff_positions`) that does not alter terrain. Movement
speed is determined by the terrain being entered; water is impassable; mountains
cost 2 turns per cell.

### Strategy seam (required for analysis)
`config.strategy` selects a built-in motion policy:
- `greedy-closest` (default): if no adjacent fire, move toward the nearest fire;
  if adjacent fire, stand and fight.
- `hold`: never move.
- `waypoint`: route through a configurable waypoint list.

`run_simulation(config, strategy_fn=...)` accepts a pluggable callable
`(i, ff_positions, terrain, fire_mask, rng) -> target | None`, so the
`PipelineSolution/` analysis can inject and optimize arbitrary policies without
re-implementing the fire/landscape mechanics.

## 5. Determinism Strategy
- One RNG: `rng = np.random.default_rng(config.seed)`, used for landscape blobs,
  auto-placement, extinguish rolls, and ignition rolls — in fixed order.
- Movement/pathfinding is deterministic (BFS, no randomness).
- The chosen strategy is part of the fixed input; identical inputs (incl. strategy)
  reproduce identical runs. Verified by `tests/test_determinism.py`.

## 6. CLI Parameters
Minimum required inputs: `--nx`, `--ny`, `--nt`, `--seed`, `--fire-start`,
`--firefighters` / `--firefighter-starts`, `--strategy`.

Model parameters: `--mountain-fraction`, `--water-fraction`, `--high-fuel-fraction`,
`--n-blobs`, `--blob-sigma`, `--p-ignite-low`, `--p-ignite-high`, `--p-extinguish`,
`--waypoints`.

Output controls: `--save-animation`, `--output-csv`, `--frame-stride`,
`--interval-ms`, `--no-show`.

Per-turn stdout: `step=.. burning=.. depleted=.. fuel=.. firefighters=.. burned=..`

## 7. Reproducible Environment
- Python 3.9+ (tested on 3.12); numpy 1.26 / matplotlib 3.8 require >= 3.9.
- `python3 -m venv .venv` → `source .venv/bin/activate` → `pip install -r requirements.txt`.
- One-command example run documented in `README.md` and `example_run/INPUTS.md`.

## 8. Validation and Acceptance Criteria
- Determinism: same inputs ⇒ identical `terrain`, `ff_positions`, and stats.
- CA rules: fire never enters mountain/water/depleted; burn durations correct;
  firefighters never cross water; extinguish restores fuel; invalid fire/ff
  starts raise `ValueError`. (Covered by `tests/test_state_rules.py`.)
- Animation renders/saves a VS Code-openable GIF; CSV matches stdout.

## 9. Risks and Mitigations
- BFS per firefighter per turn is O(Nx*Ny); fine for typical grids, documented.
- GIF export needs `pillow` (pinned in requirements).
- Headless environments: `--no-show` plus `--save-animation` / `--output-csv`.

## 10. Done Definition
Fresh clone + venv + `pip install -r requirements.txt` runs the documented command,
reproduces `example_run/wildfire_counts.csv` exactly for the fixed seed, renders
`wildfire.gif`, and passes all tests — satisfying every item in the top-level
README's *Final Code Program Requirements* (plus the chosen novelty, to be added).