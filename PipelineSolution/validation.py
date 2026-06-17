"""Baseline validation: compare pipeline output against the hand-run reference.

Runs the DevelopmentSolution engine with the example_run parameters and checks
that the per-turn statistics exactly match ``wildfire_counts.csv``. Because the
pipeline calls the same deterministic engine, the match is bit-for-bit exact
(integer statistics).
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import numpy as np

from DevelopmentSolution.simulation import SimulationConfig

from simulation_runner import DEFAULT_PARAMETERS, run_strategy


class BaselineValidator:
    """Validate against DevelopmentSolution/example_run/."""

    def __init__(self):
        self.baseline_dir = Path(repo_root) / "DevelopmentSolution" / "example_run"
        self.baseline_csv = self.baseline_dir / "wildfire_counts.csv"
        self.baseline = self._load_baseline_csv()
        self.config = self._baseline_config()

    def _load_baseline_csv(self) -> dict[str, np.ndarray]:
        if not self.baseline_csv.exists():
            raise FileNotFoundError(f"Baseline CSV not found: {self.baseline_csv}")
        cols = {k: [] for k in ("step", "burning", "depleted", "fuel", "firefighters", "burned_total")}
        with open(self.baseline_csv, "r") as f:
            for row in csv.DictReader(f):
                for k in cols:
                    cols[k].append(int(row[k]))
        return {k: np.array(v, dtype=np.int64) for k, v in cols.items()}

    def _baseline_config(self) -> SimulationConfig:
        # Matches example_run/INPUTS.md (defaults for the landscape; 3 ff, greedy).
        return SimulationConfig(
            nx=DEFAULT_PARAMETERS["nx"],
            ny=DEFAULT_PARAMETERS["ny"],
            nt=DEFAULT_PARAMETERS["nt"],
            seed=DEFAULT_PARAMETERS["seed"],
            mountain_fraction=DEFAULT_PARAMETERS["mountain_fraction"],
            water_fraction=DEFAULT_PARAMETERS["water_fraction"],
            high_fuel_fraction=DEFAULT_PARAMETERS["high_fuel_fraction"],
            n_blobs=DEFAULT_PARAMETERS["n_blobs"],
            blob_sigma=DEFAULT_PARAMETERS["blob_sigma"],
            p_ignite_low=DEFAULT_PARAMETERS["p_ignite_low"],
            p_ignite_high=DEFAULT_PARAMETERS["p_ignite_high"],
            p_extinguish=DEFAULT_PARAMETERS["p_extinguish"],
            firefighter_count=DEFAULT_PARAMETERS["firefighter_count"],
            strategy="greedy-closest",
        )

    def validate(self) -> tuple[bool, str]:
        results = run_strategy(self.config, strategy="greedy-closest")
        expected = self.baseline

        for key in ("burning", "depleted", "fuel", "firefighters", "burned_total"):
            got = np.asarray(results[key], dtype=np.int64)
            want = expected[key]
            if got.shape != want.shape:
                return False, f"{key}: length mismatch (got {got.shape[0]}, want {want.shape[0]})"
            if not np.array_equal(got, want):
                diff = int(np.abs(got - want).max())
                return False, f"{key}: max diff {diff} (expected exact match)"
        return True, "✓ Validation PASSED: pipeline exactly matches the hand-run baseline"

    def get_baseline_info(self) -> dict:
        b = self.baseline
        return {
            "num_steps": int(len(b["step"]) - 1),
            "final_burned": int(b["burned_total"][-1]),
            "final_fuel": int(b["fuel"][-1]),
            "peak_burning": int(b["burning"].max()),
            "firefighters": int(b["firefighters"][-1]),
        }


def validate_baseline() -> tuple[bool, str]:
    return BaselineValidator().validate()