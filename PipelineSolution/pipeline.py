#!/usr/bin/env python3
"""Wildfire strategy-optimization pipeline: main entry point.

Orchestrates: query parsing -> config building -> strategy optimization ->
(baseline validation) -> text/PDF reporting.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from config_builder import build_config_from_query
from query_engine import QueryParser
from report_generator import PDFReportGenerator, TextReportGenerator
from strategy_optimizer import optimize
from validation import validate_baseline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optimize a wildfire firefighting strategy from a plain-language query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py --query "Best strategy with 3 firefighters to minimize burned area"
  python pipeline.py --query "64x64 grid, 180 turns, seed 12345, 3 firefighters" --format pdf --output report.pdf
  python pipeline.py --query "example configuration" --validate
        """,
    )
    parser.add_argument("--query", type=str, required=True,
                        help="Plain-language strategy/parameter request")
    parser.add_argument("--format", choices=["text", "pdf"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file (default: stdout for text, auto-named for PDF)")
    parser.add_argument("--validate", action="store_true",
                        help="Also validate the engine against the example_run baseline")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        print(f"[Pipeline] Parsing query: {args.query[:60]}...")
        parsed = QueryParser().parse(args.query)

        print("[Pipeline] Building configuration...")
        config = build_config_from_query(parsed)

        validation_result = None
        if args.validate or parsed.get("validate"):
            print("[Pipeline] Validating engine against hand-run baseline...")
            validation_result = validate_baseline()
            print(f"  {validation_result[1]}")

        print("[Pipeline] Optimizing firefighter strategy...")
        optimization = optimize(config, objective=parsed.get("objective", "burned_area"))
        print(f"[Pipeline] Recommended strategy: {optimization['best_name']} "
              f"(burned={optimization['best_metrics']['final_burned']}, "
              f"fuel={optimization['best_metrics']['final_fuel']})")

        print(f"[Pipeline] Generating {args.format} output...")
        if args.format == "text":
            text = TextReportGenerator.generate_text(optimization, validation_result)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(text)
                print(f"✓ Text report saved to: {args.output}")
            else:
                print(text)
        else:
            if not args.output:
                args.output = f"strategy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            PDFReportGenerator.generate_pdf(optimization, args.output)
            print(f"✓ PDF report saved to: {args.output}")

        print("[Pipeline] ✓ Completed successfully!")
        return 0

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())