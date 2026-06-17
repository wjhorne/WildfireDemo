# Wildfire Strategy-Optimization Pipeline

A query-driven pipeline that wraps the deterministic wildfire simulation in
[`../DevelopmentSolution/`](../DevelopmentSolution/) and produces an
**optimized firefighting strategy**. Given an initial terrain, a fire start, and
firefighter starting locations, it searches over the **firefighter motion
strategies exposed by the engine** (the strategy-selection seam) and recommends
the one that minimizes burned area — without re-implementing the fire/landscape
dynamics. It answers **plain-language** requests and produces both **text** and
**PDF** reports, and it **validates exactly** against a hand-run baseline.

> The baseline searches a fixed portfolio of strategies. A **novelty**
> (richer search such as beam search, ensembles, goal-seeking, or multi-objective
> Pareto) is intentionally left for users of this repo — see the top-level
> `README.md` *Simulation Pipeline Requirements*.

## Requirements

- **Python 3.9+** (tested on Python 3.12). `numpy` 1.26 / `matplotlib` 3.8 require ≥3.9.
- Git (to clone the repo).

## Setup

### One command

```bash
cd PipelineSolution
./setup.sh
```

`setup.sh` creates `.venv`, installs [`requirements.txt`](requirements.txt)
(`numpy`, `matplotlib`), verifies imports (`test_imports.py`), and runs the unit
tests (`tests/test_core.py`).

### Manual setup

```bash
cd PipelineSolution
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python test_imports.py
python -m unittest tests.test_core -q
```

### Verify installation

```bash
python test_imports.py
```

Expected (last lines):

```
✓ Ran a strategy: shape=(31, 20, 20), final_burned=..., fuel=...
✓ Optimized: best='greedy-closest', candidates=4, best_burned=...
✓ All imports and basic operations successful!
```

## Usage

### Plain-language queries (CLI)

```bash
# Recommend a strategy to minimize burned area (text output)
python pipeline.py --query "Best strategy with 3 firefighters to minimize burned area"

# Override simulation parameters and get a PDF report
python pipeline.py --query "64x64 grid, 180 turns, seed 12345, 3 firefighters" \
    --format pdf --output report.pdf

# Specify fire + firefighter starts
python pipeline.py --query "fire at 30,30, firefighters start at 5,5 and 25,25, 2 firefighters" \
    --format text

# Validate the engine exactly matches the hand-run baseline
python pipeline.py --query "example configuration" --validate
```

Or via the wrapper (auto-activates `.venv`):

```bash
./query.sh "Best strategy with 3 firefighters to minimize burned area"
./query.sh "64x64 grid, 180 turns, seed 12345, 3 firefighters" --format pdf --output report.pdf
./query.sh "example configuration" --validate
```

### Query syntax

The parser extracts (all optional; defaults come from
[`../DevelopmentSolution/example_run/INPUTS.md`](../DevelopmentSolution/example_run/INPUTS.md)):

- **Grid**: `64x64 grid`, `nx=64`, `ny=64`
- **Turns**: `180 turns`, `180 steps`, `nt=180`
- **Seed**: `seed 12345`
- **Firefighters**: `3 firefighters`, `firefighters=3`
- **Fire start(s)**: `fire at 30,30`, `fire start 30,30`, `ignites at 30,30` (must be on low/high fuel)
- **Firefighter starts**: `firefighters start at 5,5 and 25,25` (non-water cells)
- **Dynamics**: `p_ignite_low=0.12`, `p_ignite_high=0.35`, `p_extinguish=0.6`,
  `mountain_fraction=0.10`, `water_fraction=0.10`, `high_fuel_fraction=0.45`
- **Intent**: "report/pdf/generate" → report; "validate/baseline" → validate; else optimize

Output format is selected with `--format text|pdf`; `--output FILE` saves to a file.

## Architecture

```
Query Input (plain language)
    ↓
Parse & Validate              ← query_engine.py
    ↓
Build SimulationConfig        ← config_builder.py  (defaults from example_run/INPUTS.md)
    ↓
Search strategies over the    ← strategy_optimizer.py
engine's strategy seam         (runs DevelopmentSolution/simulation.py
                                via simulation_runner.py for each candidate)
    ↓
Rank by burned area;           ← strategy_optimizer.py
pick best
    ↓
Optionally Validate           ← validation.py  (vs example_run/wildfire_counts.csv)
    ↓
Generate Report               ← report_generator.py  (text or PDF)
    ↓
Output
```

### Key components

| File | Role |
|------|------|
| `pipeline.py` | CLI entry point and orchestrator |
| `query_engine.py` | Plain-language query parser |
| `config_builder.py` | Parsed query → `SimulationConfig` |
| `simulation_runner.py` | Runs the engine under a chosen strategy + metric extraction |
| `strategy_optimizer.py` | Searches the strategy portfolio over the engine's seam; ranks by burned area |
| `report_generator.py` | Text and PDF reports (recommended strategy, comparison, plots) |
| `validation.py` | Exact-match validation against the `example_run` baseline |
| `test_imports.py` | Import smoke test |
| `tests/test_core.py` | Unit tests (parser, config, optimizer, validation) |
| `test_integration.sh` | End-to-end integration tests |
| `setup.sh` / `query.sh` | One-command setup / query wrapper |

### Strategy search (the optimization)

`strategy_optimizer.optimize(config)` evaluates a baseline portfolio by running
the **same engine** under each firefighter motion policy and ranking by final
burned area (tie-break: most fuel remaining):

1. `greedy-closest` — the engine default (move toward nearest fire; fight when adjacent)
2. `hold` — never move (only extinguish adjacent fires)
3. `waypoint: rush nearest fire start` — each firefighter beelines its nearest fire start
4. `waypoint: defensive high-fuel anchors` — position firefighters on the high-fuel
   cells nearest the primary fire start (a firebreak)

Candidates 3–4 are injected through `run_simulation(config, strategy_fn=...)` —
the engine's **pluggable strategy seam** — so the fire/landscape CA is never
duplicated. (A novelty would extend this search, e.g., beam search over
waypoints or an ensemble across seeds.)

## Validation against the hand-run baseline

`validation.py` runs the engine with the `example_run` parameters and checks the
per-turn statistics exactly match `DevelopmentSolution/example_run/wildfire_counts.csv`
(integer-exact, since the pipeline calls the same deterministic engine):

```bash
./query.sh "example configuration" --validate
# → Status: PASSED  ✓ Validation PASSED: pipeline exactly matches the hand-run baseline
```

## Tests

```bash
python -m unittest tests.test_core -v     # 12 unit tests (incl. exact-match validation)
bash test_integration.sh                    # end-to-end: imports, tests, text + PDF, validation
python test_imports.py                      # import smoke test
```

## Reproducibility

All simulations use deterministic seeds. Re-running the same query/seed
reproduces the same strategy recommendation and statistics; the configuration
used is printed in every report.

## Known limitations

- The query parser is keyword/regex based; complex natural language is reduced to
  common request patterns.
- The baseline strategy search is a fixed portfolio (4 candidates), not an
  exhaustive/learned search — that richer search is the intended novelty.
- PDF generation uses matplotlib's `PdfPages` (no external PDF library needed).