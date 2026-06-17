# Example Run Inputs

A reproducible reference run of the wildfire cellular-automata simulation with
three firefighters using the default `greedy-closest` strategy.

## Parameters Used
- nx: 64
- ny: 64
- nt: 180
- seed: 12345
- mountain_fraction: 0.10
- water_fraction: 0.10
- high_fuel_fraction: 0.45
- n_blobs: 8
- blob_sigma: 7.0
- p_ignite_low: 0.12
- p_ignite_high: 0.35
- p_extinguish: 0.6
- fire_starts: auto-placed (1 fire on a fuel cell, deterministic from the seed)
- firefighters: 3 (auto-placed on non-water cells, deterministic from the seed)
- strategy: greedy-closest

## Animation Settings
- frame_stride: 3
- interval_ms: 90

## Reproducible Run Command

Run this from `DevelopmentSolution/` with the virtual environment activated:

```bash
python main.py \
	--nx 64 \
	--ny 64 \
	--nt 180 \
	--seed 12345 \
	--mountain-fraction 0.10 \
	--water-fraction 0.10 \
	--high-fuel-fraction 0.45 \
	--n-blobs 8 \
	--blob-sigma 7.0 \
	--p-ignite-low 0.12 \
	--p-ignite-high 0.35 \
	--p-extinguish 0.6 \
	--firefighters 3 \
	--strategy greedy-closest \
	--frame-stride 3 \
	--interval-ms 90 \
	--save-animation example_run/wildfire.gif \
	--output-csv example_run/wildfire_counts.csv \
	--no-show
```

> **Reproducibility note:** the stdout from this command matches
> `wildfire_counts.csv` exactly (deterministic for a fixed seed). Verified on
> Python 3.12 with `numpy` 1.26.4, `matplotlib` 3.8.4, and `pillow` 10.4.0.
> `wildfire.gif` opens directly in the VS Code preview pane.

## Run Statistics
- initial fuel (step 0): 3978 cells
- peak burning: 124 cells at step 28
- final (step 180): burning=0, depleted=1742, fuel=2237, firefighters=3

The fire ignites, spreads through the fuel landscape (peaking around step 28),
and eventually burns out — leaving 1742 depleted cells and 2237 fuel cells
remaining. Firefighters (default greedy policy) engage adjacent fires throughout.

## Output Notes
- `wildfire_counts.csv` includes all steps from 0 through `nt`.
- `wildfire.gif` uses every 3rd step (61 frames) for compact rendering.
- The colormap is: gray = mountain, blue = water, light green = low fuel,
  dark green = high fuel, orange-red = fire, charred brown = depleted.
  Firefighters are shown as navy triangles with a white outline.