import sys
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation import (
    DEPLETED, FIRE, HIGH_FUEL, LOW_FUEL, MOUNTAIN, WATER,
    SimulationConfig, run_simulation,
)


def _cfg(terrain, nt, **kw):
    terrain = np.array(terrain, dtype=np.int8)
    return SimulationConfig(
        nx=terrain.shape[0], ny=terrain.shape[1], nt=nt,
        terrain_override=terrain, **kw,
    )


class FireSpreadRulesTests(unittest.TestCase):
    def test_fire_does_not_spread_to_mountain_water_or_depleted(self):
        # Center is burning low fuel; N/E/W neighbors are mountain/water/depleted
        # and must never ignite. The south neighbor is low fuel and should ignite.
        terrain = np.array([
            [LOW_FUEL, MOUNTAIN, LOW_FUEL],
            [WATER,    LOW_FUEL, DEPLETED],
            [LOW_FUEL, LOW_FUEL, LOW_FUEL],
        ])
        terrain[1, 1] = LOW_FUEL  # will be the fire start
        config = _cfg(terrain, nt=6, fire_starts=[(1, 1)], p_ignite_low=1.0, p_ignite_high=1.0,
                      p_extinguish=0.0)
        res = run_simulation(config)

        for t in range(res["terrain"].shape[0]):
            grid = res["terrain"][t]
            self.assertNotEqual(grid[0, 1], FIRE, "fire spread into mountain")
            self.assertNotEqual(grid[1, 0], FIRE, "fire spread into water")
            self.assertNotEqual(grid[1, 2], FIRE, "fire spread into depleted")

    def test_low_fuel_burns_in_one_turn_high_fuel_in_two(self):
        # Isolated 1x1 cells, no spread possible, so only burn-down matters.
        low = run_simulation(_cfg(np.array([[LOW_FUEL]]), nt=2, fire_starts=[(0, 0)],
                                  p_ignite_low=0.0, p_ignite_high=0.0))
        self.assertEqual(low["terrain"][0, 0, 0], FIRE)      # burning at step 0
        self.assertEqual(low["terrain"][1, 0, 0], DEPLETED)  # burned out after 1 turn

        high = run_simulation(_cfg(np.array([[HIGH_FUEL]]), nt=3, fire_starts=[(0, 0)],
                                   p_ignite_low=0.0, p_ignite_high=0.0))
        self.assertEqual(high["terrain"][0, 0, 0], FIRE)     # step 0
        self.assertEqual(high["terrain"][1, 0, 0], FIRE)     # still burning step 1
        self.assertEqual(high["terrain"][2, 0, 0], DEPLETED) # burned out after 2 turns


class FirefighterRulesTests(unittest.TestCase):
    def test_firefighter_never_crosses_water(self):
        # Single row: fire at left, firefighter at right, water wall between them.
        terrain = np.array([[LOW_FUEL, LOW_FUEL, WATER, LOW_FUEL, LOW_FUEL]])
        config = _cfg(terrain, nt=12, fire_starts=[(0, 0)], firefighter_starts=[(0, 4)],
                      p_ignite_low=0.0, p_ignite_high=0.0, p_extinguish=0.0,
                      strategy="greedy-closest")
        res = run_simulation(config)
        water_cell = (0, 2)
        for t in range(res["ff_positions"].shape[0]):
            for ff in res["ff_positions"][t]:
                self.assertNotEqual((int(ff[0]), int(ff[1])), water_cell,
                                    "firefighter crossed onto water")

    def test_extinguish_restores_fuel_not_depleted(self):
        # Firefighter stands adjacent to a low-fuel fire; with p_extinguish=1 it
        # is put out and the cell reverts to fuel (NOT depleted). No spread.
        terrain = np.array([[LOW_FUEL, LOW_FUEL, LOW_FUEL]])
        config = _cfg(terrain, nt=1, fire_starts=[(0, 1)], firefighter_starts=[(0, 2)],
                      p_ignite_low=0.0, p_ignite_high=0.0, p_extinguish=1.0)
        res = run_simulation(config)
        self.assertEqual(res["terrain"][1, 0, 1], LOW_FUEL)   # fuel restored
        self.assertNotEqual(res["terrain"][1, 0, 1], DEPLETED)

    def test_invalid_fire_start_raises(self):
        terrain = np.array([[WATER, MOUNTAIN, LOW_FUEL]])
        with self.assertRaises(ValueError):
            run_simulation(_cfg(terrain, nt=1, fire_starts=[(0, 0)]))  # on water
        with self.assertRaises(ValueError):
            run_simulation(_cfg(terrain, nt=1, fire_starts=[(0, 1)]))  # on mountain

    def test_firefighter_start_on_water_raises(self):
        terrain = np.array([[WATER, LOW_FUEL]])
        with self.assertRaises(ValueError):
            run_simulation(_cfg(terrain, nt=1, fire_starts=[(0, 1)],
                                firefighter_starts=[(0, 0)]))


if __name__ == "__main__":
    unittest.main()