import sys
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation import SimulationConfig, run_simulation


class DeterminismTests(unittest.TestCase):
    def test_same_seed_produces_identical_results(self):
        config = SimulationConfig(nx=30, ny=30, nt=40, seed=2026, firefighter_count=2)
        a = run_simulation(config)
        b = run_simulation(config)

        np.testing.assert_array_equal(a["terrain"], b["terrain"])
        np.testing.assert_array_equal(a["ff_positions"], b["ff_positions"])
        for key in ("burning", "depleted", "fuel", "firefighters", "burned_total"):
            np.testing.assert_array_equal(a[key], b[key])

    def test_different_seed_can_differ(self):
        base = dict(nx=30, ny=30, nt=40, firefighter_count=2)
        a = run_simulation(SimulationConfig(seed=1, **base))
        b = run_simulation(SimulationConfig(seed=2, **base))
        # The landscape (and thus the run) should differ for different seeds.
        self.assertFalse(np.array_equal(a["terrain"], b["terrain"]))


if __name__ == "__main__":
    unittest.main()