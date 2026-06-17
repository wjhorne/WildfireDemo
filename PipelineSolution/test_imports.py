"""Import smoke test for PipelineSolution."""
import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    from query_engine import QueryParser
    from config_builder import build_config_from_query
    from simulation_runner import run_strategy, extract_metrics, DEFAULT_PARAMETERS
    from strategy_optimizer import optimize
    from report_generator import TextReportGenerator
    from validation import validate_baseline
    from DevelopmentSolution.simulation import SimulationConfig

    parsed = QueryParser().parse("20x20 grid, 30 turns, 2 firefighters")
    config = build_config_from_query(parsed)
    results = run_strategy(config, strategy="greedy-closest")
    metrics = extract_metrics(results)
    print(f"✓ Ran a strategy: shape={results['terrain'].shape}, "
          f"final_burned={metrics['final_burned']}, fuel={metrics['final_fuel']}")

    opt = optimize(SimulationConfig(nx=20, ny=20, nt=30, seed=12345, firefighter_count=2))
    print(f"✓ Optimized: best='{opt['best_name']}', "
          f"candidates={len(opt['ranking'])}, "
          f"best_burned={opt['best_metrics']['final_burned']}")

    print(f"✓ Default parameters: {DEFAULT_PARAMETERS['nx']}x{DEFAULT_PARAMETERS['nx']}, "
          f"nt={DEFAULT_PARAMETERS['nt']}, ff={DEFAULT_PARAMETERS['firefighter_count']}")
    print("\n✓ All imports and basic operations successful!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())