"""Firefighter motion-strategy optimizer.

This is the wildfire pipeline's central component. Given a terrain (or seed),
a fire start, and firefighter starting locations, it searches over the
firefighter motion strategies exposed by ``DevelopmentSolution`` (the engine's
strategy-selection seam) and recommends the one that minimizes burned area.

The baseline evaluates a fixed portfolio of strategies (the engine built-ins
plus deterministic waypoint/target policies injected through the pluggable
``strategy_fn`` seam). Richer search (beam search, ensembles, goal-seeking,
multi-objective Pareto) is intentionally left as a novelty for users of this
repo — see the top-level README's *Simulation Pipeline Requirements*.
"""
from __future__ import annotations

import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import numpy as np

from DevelopmentSolution.simulation import FIRE, HIGH_FUEL, SimulationConfig

from simulation_runner import extract_metrics, run_strategy


def _initial_fire_starts(results: dict) -> list[tuple[int, int]]:
    t0 = results["terrain"][0]
    return [(int(r), int(c)) for r, c in np.argwhere(t0 == FIRE)]


def _initial_ff_starts(results: dict) -> list[tuple[int, int]]:
    pos = results["ff_positions"][0]
    return [(int(r), int(c)) for r, c in pos]


def _nearest_cells_to(target: tuple[int, int], candidates: list[tuple[int, int]], k: int) -> list[tuple[int, int]]:
    """Return the ``k`` cells from ``candidates`` nearest (Manhattan) to ``target``."""
    ranked = sorted((abs(r - target[0]) + abs(c - target[1]), (r, c)) for (r, c) in candidates)
    return [cell for _, cell in ranked[:k]]


def _make_target_strategy(targets: list[tuple[int, int]]):
    """Build a pluggable strategy_fn that sends firefighter ``i`` to ``targets[i]``."""
    def strategy(i, ff_pos, terrain, fire_mask, rng):
        return targets[i] if i < len(targets) else None
    return strategy


def _build_candidates(config: SimulationConfig, probe: dict) -> list[dict]:
    """Build the baseline strategy portfolio from a probe (greedy) run."""
    fire_starts = _initial_fire_starts(probe)
    ff_starts = _initial_ff_starts(probe)
    n_ff = len(ff_starts)

    cands: list[dict] = [
        {"name": "greedy-closest", "strategy": "greedy-closest", "waypoints": (), "strategy_fn": None},
        {"name": "hold (no movement)", "strategy": "hold", "waypoints": (), "strategy_fn": None},
    ]

    if fire_starts and n_ff > 0:
        # Each firefighter rushes its nearest fire start.
        rush = [_nearest_cells_to(ff, fire_starts, 1)[0] for ff in ff_starts]
        cands.append({
            "name": "waypoint: rush nearest fire start",
            "strategy": None, "waypoints": (), "strategy_fn": _make_target_strategy(rush),
        })

        # Defensive anchors: position firefighters on the high-fuel cells nearest
        # the primary fire start (a firebreak between the fire and dense fuel).
        t0 = probe["terrain"][0]
        high_fuel = [(int(r), int(c)) for r, c in np.argwhere(t0 == HIGH_FUEL)]
        if high_fuel:
            anchors = _nearest_cells_to(fire_starts[0], high_fuel, n_ff)
            targets = [anchors[i % len(anchors)] for i in range(n_ff)]
            cands.append({
                "name": "waypoint: defensive high-fuel anchors",
                "strategy": None, "waypoints": (), "strategy_fn": _make_target_strategy(targets),
            })
    return cands


def optimize(config: SimulationConfig, objective: str = "burned_area") -> dict:
    """Search the strategy portfolio and return the recommended strategy.

    Returns a dict with: objective, best_name, best_metrics, ranking,
    best_results, trajectories (burned area per step per candidate), config.
    """
    # Probe with the default greedy policy to discover the actual fire/ff starts
    # and initial terrain (works even when they are auto-placed from the seed).
    probe = run_strategy(config, strategy="greedy-closest")
    probe_metrics = extract_metrics(probe)

    candidates = _build_candidates(config, probe)

    evaluated: list[dict] = []
    for cand in candidates:
        is_probe = (
            cand["strategy"] == "greedy-closest"
            and cand["strategy_fn"] is None
            and cand["waypoints"] == ()
        )
        if is_probe:
            results, metrics = probe, probe_metrics
        else:
            results = run_strategy(
                config,
                strategy=cand["strategy"],
                waypoints=cand["waypoints"],
                strategy_fn=cand["strategy_fn"],
            )
            metrics = extract_metrics(results)
        evaluated.append({"name": cand["name"], **metrics, "results": results})

    # Rank: minimize final burned area; tie-break by maximizing fuel remaining.
    evaluated.sort(key=lambda e: (e["final_burned"], -e["final_fuel"]))
    best = evaluated[0]

    return {
        "objective": objective,
        "best_name": best["name"],
        "best_metrics": {
            "final_burned": best["final_burned"],
            "final_fuel": best["final_fuel"],
            "final_depleted": best["final_depleted"],
            "final_burning": best["final_burning"],
            "peak_burning": best["peak_burning"],
            "peak_step": best["peak_step"],
            "firefighters": best["firefighters"],
        },
        "ranking": [
            {
                "name": e["name"],
                "final_burned": e["final_burned"],
                "final_fuel": e["final_fuel"],
                "final_depleted": e["final_depleted"],
                "peak_burning": e["peak_burning"],
            }
            for e in evaluated
        ],
        "best_results": best["results"],
        "trajectories": {e["name"]: e["burned_trajectory"] for e in evaluated},
        "config": config,
    }