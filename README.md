# WildfireDemo

# Project specification

Depending on your interest, choose whether to do the **Code Development** or the **Simulation Analysis** project described below. Setup instructions are included at the bottom of this document.

---

## Code Development Project Goal

Using agentic AI, build a small Python program that simulates **wildfire spread on a 2D grid** using the **Cellular Automata** technique with **Moore neighborhoods**, runs for `Nt` turns, and animates the fire moving through a procedurally generated landscape. The simulation must also include a **firefighting capability** as a cellular-automata overlay. Animate the result with matplotlib, and report per-turn statistics (burning cells, depleted cells, fuel remaining, firefighters active, area burned). Provide a command-line interface to specify grid size, number of turns, the random seed, initial fire locations, and firefighter placements. Keep core dependencies to `numpy` + `matplotlib`.

## Code Development Instructions

With the agentic tool of your choice, start from an empty `DevelopmentSolution/` directory and use prompts to successfully create the requisite code. Test the resulting code by hand to roughly verify results. You may introduce the requirements below as a prompt, but the **novelty must be one of your own choosing** (see *Final Code Program Requirements*).

## Final Code Program Requirements

### Landscape generation (deterministic, randomized)

- Generate realistic, randomized landscapes on a 2D `Nx × Ny` grid from a **random seed** so results are **fully deterministic** and reproducible for a fixed seed.
- The landscape generator must place the following block (cell) types with sensible, spatially coherent structure (e.g., clustered water bodies, mountain ranges, fuel patches) rather than per-cell i.i.d. noise:

| Block type | Fuel content | Fire behavior | Firefighter traversal |
| --- | --- | --- | --- |
| **Mountain** (impassable) | none | Fire **cannot** enter or spread here. | Traversable but **slow: 1 block per 2 turns** (0.5 cells/turn). |
| **Water** | none (non-fuel) | Fire **cannot** ignite or spread here. | **Cannot cross** — impassable to firefighters (must route around it). |
| **Low fuel** | low | Burnable; **burns in 1 turn**. | Firefighters traverse at the faster rate (**2 cells/turn**). |
| **High fuel** | high | Burnable; **burns in 2 turns**. | Firefighters move **1 cell/turn** (see movement rules). |
| **Fire** | actively burning | Diminishes as fuel is consumed. | Firefighters move **1 cell/turn** while standing on fire. |
| **Depleted** | zero | Fire **cannot** move/spread here. | Firefighters traverse at the faster rate (**2 cells/turn**). |

### Fire spread (Cellular Automata, Moore neighborhood)

- Use the **Moore neighborhood** (all 8 surrounding cells) for fire propagation.
- Each turn, every burning cell attempts to ignite its fuel-bearing neighbors. Each candidate neighbor gets a **per-turn probability of ignition that is weighted by its block type** (e.g., high fuel ignites more readily than low fuel).
- Fire **will not** spread to **depleted** or **impassable (mountain)** blocks, nor to non-fuel **water** blocks.
- Fire blocks **diminish as fuel is consumed**: a fire on **low fuel lasts 1 turn**; a fire on **high fuel lasts 2 turns**. When a fire finishes burning all of a cell's fuel, the cell becomes a **depleted** block (zero fuel).

### Firefighting overlay (Cellular Automata)

- Firefighters are introduced as a cellular-automata overlay. They **exist on top of existing blocks** (they do not change the underlying terrain; they sit on a cell).
- Firefighter **movement speed is determined by the terrain they traverse**:
  - In **high fuel** or **areas on fire** → move **1 cell per turn**.
  - **Impassable (mountain)** terrain → move **1 cell per 2 turns** (slow, but traversable).
  - **Water** → **cannot cross** at all (impassable to firefighters; they must route around it).
  - Otherwise (**low fuel**, **depleted**, etc.) → move **2 cells per turn**.
- Firefighters operate using cellular automata: each turn they may move and/or act on neighbors.
- Firefighters have a **chance each turn to extinguish nearby fires** (within their Moore neighborhood). Extinguishing a fire **leaves the remaining fuel where the fire once was** — i.e., the cell reverts to its fuel type (low/high fuel) with its remaining fuel, **not** depleted. (This is the key difference between *extinguished* and *burned-out* cells.)
- **Firefighter motion strategy must be selectable, not hard-coded** — this is required so the analysis path has a decision variable to optimize over. The engine's **default** policy is *greedy-closest-fire*: when no fire is adjacent, a firefighter moves toward the nearest burning cell (respecting movement speed, **water (impassable)**, and the 2-turn cost of entering mountains); when fire is adjacent, it attempts to extinguish. The engine must let an external caller override this with a different policy — e.g., a `--strategy` CLI mode (greedy-closest, hold-position, perimeter-defense, waypoint-follow, …) and/or a pluggable policy callable / per-firefighter waypoint plan. The CA fire-and-landscape mechanics stay fixed; **only the firefighter decision policy is the variable**, and this seam is what `PipelineSolution/` optimizes over. A chosen strategy + fixed seed must remain fully deterministic.
- **Inputs to the simulation:** the **number of firefighter overlay blocks** and their **starting locations** (traversable, **non-water** terrain); the **initial fire blocks** (which **must start on a low or high fuel source** — fire cannot ignite on mountain/water/depleted); and the **firefighter motion strategy** (default: greedy-closest-fire). Accept coordinates explicitly or via count + seed-based placement; accept the strategy via a CLI flag or a programmatic policy object.

### Determinism, output, and CLI

- Results must be **deterministic**: a single random seed drives landscape generation, fire-spread rolls, and firefighter rolls, and the **chosen strategy is part of the fixed input**. Identical inputs (including strategy) ⇒ identical runs.
- The input of the program must be a `grid_size (Nx, Ny)`, number of turns `Nt`, the `seed`, the **initial fire locations**, the **firefighter placement** (count + locations), and the **firefighter motion strategy**, plus any relevant model parameters (ignition probabilities per fuel type, firefighter extinguish probability, etc.).
- The output must be a **snazzy 2D animation** of the fire moving through the landscape (with firefighters visible as an overlay). The animation must be **openable from within VS Code** (e.g., an animated GIF or MP4 written to disk, plus an optional live matplotlib window). Report per-turn statistics to stdout.
- Ensure the language (Python) and dependency requirements are held: **`numpy` + `matplotlib`** for the core simulation.

### Required novelty

You must introduce **one new novelty not found in the `DevelopmentSolution/` result** for this task. Suggested options:

- **Wind:** add a wind vector field that biases fire-spread probabilities directionally (downwind neighbors ignite more readily than upwind ones), making the fire front anisotropic.
- **Cities:** add **road** and **building** blocks with appropriate fuel content as additional fuel options. The landscape generator must produce **somewhat realistic city blocks** (gridded roads, clustered buildings), and firefighters must move appropriately over them (e.g., roads at the fast rate, buildings as high fuel).
- **Fire temperature tracking:** each fire block carries a **temperature** that varies based on the **availability of fuel** and **wind conditions**; temperature in turn modulates that cell's ignition probability and/or burn duration.

## Simulation Analysis Project Goal

Using agentic AI, create an **agent-based pipeline** that wraps the wildfire simulation code located in the `DevelopmentSolution/` folder and produces an **optimized firefighting strategy**. Given an initial terrain, a fire start, and firefighter starting locations, an analyst needs to **best strategize where the firefighters should go**, respecting their motion restrictions (terrain-dependent speed, water impassability, the 2-turn mountain cost). The pipeline optimizes over the **motion strategies that `DevelopmentSolution/` exposes** — the engine already lets the strategy be chosen, so an LLM agent orchestrates running simulations under candidate strategies, evaluating outcomes (burned area, fuel saved, firefighters used), and selecting/recommending the best. The pipeline should also produce a `.pdf` report summarizing the recommended strategy, burned-area outcomes, and supporting plots.

## Simulation Analysis Instructions

Clone the WildfireDemo repo. With an agentic AI tool of your choice, enter the repo directory and use prompts to create the pipeline. You may include the requirements below as part of your prompts, but the **novelty must be of your own choice**. Test the pipeline using the same agentic tool you used for creation of the pipeline.

## Simulation Pipeline Requirements

- The pipeline must demonstrate that it **exactly matches results from a hand-run result** for at least one example set of inputs (terrain, fire start, firefighter placement).
- The pipeline must optimize over the **firefighter motion strategies exposed by `DevelopmentSolution/`** (its strategy-selection seam) — it must not re-implement the fire/landscape dynamics.
- **Plain language** must be taken as input (e.g., "Given this terrain and 3 firefighters starting in the southwest, what's the best strategy to minimize burned area?").
- Both a **`.pdf` report** and **text outputs** must be supported.
- Introduce **one new novelty** not found in `PipelineSolution`. For some examples:
  - Introduce a **goal-seeking capability** where an agent answers questions like *"What firefighter count keeps burned area under 20%?"* or *"Which starting corner minimizes total fuel lost?"*
  - Implement a **strategy search** over firefighter waypoints (greedy look-ahead, beam search, or a lightweight policy search) and report the best found strategy.
  - Produce **uncertainty bands** on burned-area outcomes via **ensemble/Monte-Carlo runs** over the stochastic fire-spread seed, then rank strategies by robustness.
  - Introduce a **multi-objective trade-off** (burned area vs. firefighter travel effort) with a Pareto frontier.

## Repo Overview

- **[`DevelopmentSolution/`](DevelopmentSolution/)** — a deterministic 2D wildfire Cellular Automata simulation (numpy + matplotlib) with a CLI for grid size, turns, seed, initial fire, firefighter placement, and a **selectable firefighter motion strategy** (default greedy-closest-fire), plus the required firefighting overlay and one chosen novelty. This is the simulation engine the pipeline wraps.
- **[`PipelineSolution/`](PipelineSolution/)** — a query-driven **strategy-optimization pipeline** that wraps `DevelopmentSolution/`. It answers plain-language questions about firefighting strategy and outcomes, **optimizes firefighter motion strategy over the engine's strategy-selection seam**, validates results against a hand-run baseline, and produces both **text** and **PDF** reports.

## Quickstart

Requires **Python 3.9+** (tested on Python 3.12). Both `DevelopmentSolution` and `PipelineSolution` need ≥3.9 (numpy 1.26 / matplotlib 3.8).

### Run the simulation — `DevelopmentSolution`

```bash
cd DevelopmentSolution
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py --nx 80 --ny 80 --nt 200 --seed 12345 \
    --fire-start "35,25" \
    --firefighters 3 --firefighter-starts "10,10 70,70 40,5" \
    --strategy greedy-closest \
    --save-animation example_run/wildfire.gif --no-show
```

This is deterministic for a fixed seed. The `--save-animation` GIF opens directly in the VS Code preview pane. See [`DevelopmentSolution/README.md`](DevelopmentSolution/README.md).

### Run the analysis pipeline — `PipelineSolution`

```bash
cd PipelineSolution
./setup.sh                                                       # one-command setup: venv, deps, tests
./query.sh "Given the example terrain and 3 firefighters, best strategy to minimize burned area?"
./query.sh "Generate a PDF report on the optimal strategy" --format pdf --output report.pdf
./query.sh "example terrain, seed 12345" --validate              # exact-match vs hand-run baseline
```

For the agentic workflow and AI-usage guide, see [`PipelineSolution/.instructions.md`](PipelineSolution/.instructions.md) and [`PipelineSolution/README.md`](PipelineSolution/README.md).

## Developing with agentic AI (devcontainers)

This repo ships **four prebuilt devcontainer configurations** under [`.devcontainer/`](.devcontainer/), each installing a different agentic AI tool. Open the repo in **VS Code** (or **GitHub Codespaces**) and run **Dev Containers: Reopen in Container…** from the Command Palette (Ctrl/Cmd+Shift+P). VS Code detects the multiple `.devcontainer/*/` configs and prompts you to pick one. The selected config builds the container, installs the agent, and drops you at the repo root.

| Choice | `.devcontainer/` folder | Agent installed | Start the agent (from the repo root) |
| --- | --- | --- | --- |
| OpenWeights | `.devcontainer/openweights/` | `pi` + `pi-ollama-cloud`, `pi-web-access`, `pi-footer` extensions | `pi` |
| Codex | `.devcontainer/codex/` | `@openai/codex` | `codex` |
| Gemini | `.devcontainer/gemini/` | `@google/gemini-cli` | `gemini` |
| Claude | `.devcontainer/claude/` | Claude Code | `claude` |

Once the container is built, start the agent binary **from the base of this repo** and begin prompting:

```bash
# OpenWeights (pi)
pi

# Codex
codex

# Gemini
gemini

# Claude
claude
```

Each agent walks you through its one-time authentication (API key or login) on first run, after which you can prompt it to build a novel wildfire simulation (see the *Code Development Project Goal* above) or a novel strategy-optimization pipeline (see the *Simulation Analysis Project Goal* above).

---