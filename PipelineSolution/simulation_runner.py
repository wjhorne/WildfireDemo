"""Simulation runner: executes DevelopmentSolution wildfire simulations.

Thin wrapper around ``DevelopmentSolution.simulation.run_simulation`` that lets
the strategy optimizer run different firefighter motion strategies against the
SAME configuration (the engine's strategy-selection seam) and extract metrics.
"""
from __future__ import annotations

import dataclasses
import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import numpy as np

from DevelopmentSolution.simulation import SimulationConfig, run_simulation


# Default parameters mirror DevelopmentSolution/example_run/INPUTS.md.
DEFAULT_PARAMETERS = {
    "nx": 64,
    "ny": 64,
    "nt": 180,
    "seed": 12345,
    "mountain_fraction": 0.10,
    "water_fraction": 0.10,
    "high_fuel_fraction": 0.45,
    "n_blobs": 8,
    "blob_sigma": 7.0,
    "p_ignite_low": 0.12,
    "p_ignite_high": 0.35,
    "p_extinguish": 0.6,
    "firefighter_count": 3,
    "strategy": "greedy-closest",
}


def run_strategy(
    config: SimulationConfig,
    strategy: str | None = None,
    waypoints: tuple[tuple[int, int], ...] = (),
    strategy_fn=None,
) -> dict[str, np.ndarray]:
    """Run the wildfire simulation under a chosen firefighter strategy.

    The fire/landscape mechanics are never re-implemented here — this only
    selects which firefighter motion policy the engine applies.

    - ``strategy`` / ``waypoints``: select a built-in engine policy.
    - ``strategy_fn``: a pluggable callable overriding ``config.strategy``.
    """
    if strategy_fn is not None:
        return run_simulation(config, strategy_fn=strategy_fn)
    cfg = dataclasses.replace(
        config,
        strategy=strategy if strategy is not None else config.strategy,
        waypoints=tuple(waypoints),
    )
    return run_simulation(cfg)


def extract_metrics(results: dict[str, np.ndarray]) -> dict:
    """Summarize a simulation run for strategy comparison."""
    burning = results["burning"]
    return {
        "final_burned": int(results["burned_total"][-1]),
        "final_fuel": int(results["fuel"][-1]),
        "final_depleted": int(results["depleted"][-1]),
        "final_burning": int(burning[-1]),
        "peak_burning": int(burning.max()),
        "peak_step": int(burning.argmax()),
        "firefighters": int(results["firefighters"][-1]),
        "burned_trajectory": results["burned_total"],
    }


def get_default_parameters() -> dict:
    return dict(DEFAULT_PARAMETERS)