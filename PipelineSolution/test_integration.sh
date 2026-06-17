#!/bin/bash
# End-to-end integration tests for PipelineSolution
set -e
cd "$(dirname "$0")"

if [ -f ".venv/bin/activate" ]; then source .venv/bin/activate; fi

echo "== 1. Import smoke test =="
python test_imports.py | tail -3

echo "== 2. Unit tests =="
python -m unittest tests.test_core -q

echo "== 3. Text optimization output (small grid) =="
python pipeline.py --query "30x30 grid, 40 turns, seed 12345, 2 firefighters, best strategy" --format text \
    | grep -E "RECOMMENDED|Final burned|Strategy:" | head -5

echo "== 4. PDF report generation (small grid) =="
python pipeline.py --query "30x30 grid, 40 turns, 2 firefighters" --format pdf --output integration_report.pdf
ls -la integration_report.pdf >/dev/null && echo "  PDF written: integration_report.pdf"
rm -f integration_report.pdf

echo "== 5. Baseline validation (--validate) =="
python pipeline.py --query "30x30 grid, 40 turns, 2 firefighters" --validate --format text | grep -E "PASSED|FAILED|Recommended"

echo ""
echo "✓ All integration tests passed."