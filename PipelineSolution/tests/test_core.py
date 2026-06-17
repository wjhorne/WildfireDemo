"""Tests for the query parser, config builder, optimizer, and validation."""
import os
import sys
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query_engine import QueryParser
from config_builder import ConfigBuilder, build_config_from_query
from simulation_runner import run_strategy, extract_metrics
from strategy_optimizer import optimize
from validation import BaselineValidator, validate_baseline
from DevelopmentSolution.simulation import SimulationConfig


class TestQueryParser(unittest.TestCase):
    def setUp(self):
        self.parser = QueryParser()

    def test_parse_grid_and_turns(self):
        r = self.parser.parse("64x64 grid, 180 turns, 3 firefighters")
        self.assertEqual(r["params"]["nx"], 64)
        self.assertEqual(r["params"]["ny"], 64)
        self.assertEqual(r["params"]["nt"], 180)
        self.assertEqual(r["params"]["firefighter_count"], 3)

    def test_parse_seed(self):
        r = self.parser.parse("with seed 999, 2 firefighters")
        self.assertEqual(r["params"]["seed"], 999)
        self.assertEqual(r["params"]["firefighter_count"], 2)

    def test_parse_fire_and_firefighter_starts(self):
        r = self.parser.parse("fire at 30,30, firefighters start at 5,5 and 25,25")
        self.assertEqual(r["params"]["fire_starts"], ((30, 30),))
        self.assertEqual(r["params"]["firefighter_starts"], ((5, 5), (25, 25)))

    def test_intent_report_and_validate(self):
        self.assertEqual(self.parser.parse("generate a PDF report")["intent"], "report")
        self.assertEqual(self.parser.parse("validate against baseline")["intent"], "validate")
        self.assertEqual(self.parser.parse("best strategy to minimize burned area")["intent"], "optimize")


class TestConfigBuilder(unittest.TestCase):
    def test_defaults(self):
        c = ConfigBuilder.build_config({})
        self.assertEqual(c.nx, 64)
        self.assertEqual(c.nt, 180)
        self.assertEqual(c.firefighter_count, 3)

    def test_overrides(self):
        c = ConfigBuilder.build_config({"nx": 40, "ny": 40, "firefighter_count": 2})
        self.assertEqual(c.nx, 40)
        self.assertEqual(c.firefighter_count, 2)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            ConfigBuilder.build_config({"nx": -1})

    def test_from_query(self):
        parsed = QueryParser().parse("40x40 grid, 100 turns, seed 7, 2 firefighters")
        c = build_config_from_query(parsed)
        self.assertEqual(c.nx, 40)
        self.assertEqual(c.nt, 100)
        self.assertEqual(c.seed, 7)


class TestOptimizer(unittest.TestCase):
    def test_optimize_returns_ranking_and_best(self):
        config = SimulationConfig(nx=20, ny=20, nt=30, seed=12345, firefighter_count=2)
        opt = optimize(config)
        self.assertGreater(len(opt["ranking"]), 1)
        self.assertIn(opt["best_name"], [r["name"] for r in opt["ranking"]])
        # Best is the minimum burned area among candidates.
        min_burned = min(r["final_burned"] for r in opt["ranking"])
        self.assertEqual(opt["best_metrics"]["final_burned"], min_burned)
        # Trajectories present for every candidate.
        self.assertEqual(len(opt["trajectories"]), len(opt["ranking"]))

    def test_optimize_uses_engine_seam_not_reimplemented(self):
        # The optimizer must not re-implement dynamics: running the same strategy
        # directly via the engine matches the optimizer's results for that candidate.
        config = SimulationConfig(nx=20, ny=20, nt=30, seed=12345, firefighter_count=2)
        opt = optimize(config)
        direct = run_strategy(config, strategy="greedy-closest")
        self.assertEqual(int(direct["burned_total"][-1]),
                         int(opt["best_results"]["burned_total"][-1])
                         if opt["best_name"] == "greedy-closest"
                         else int(opt["trajectories"]["greedy-closest"][-1]))


class TestValidation(unittest.TestCase):
    def setUp(self):
        try:
            self.validator = BaselineValidator()
        except FileNotFoundError as e:
            self.skipTest(f"Baseline files not found: {e}")

    def test_baseline_loaded(self):
        self.assertGreater(len(self.validator.baseline["burned_total"]), 0)

    def test_validate_exact_match(self):
        passed, message = validate_baseline()
        self.assertTrue(passed, message)


if __name__ == "__main__":
    unittest.main()