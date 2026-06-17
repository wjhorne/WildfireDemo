#!/bin/bash
# Setup script for PipelineSolution
# Run this once: ./setup.sh

set -e

echo "Setting up PipelineSolution..."

python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
echo "Python version: $python_version"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo "Error: Python 3.9+ required (numpy 1.26 / matplotlib 3.8 need >=3.9)"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null

echo "Verifying imports..."
python test_imports.py

echo "Running tests..."
python -m unittest tests.test_core -q

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next, try:"
echo "  ./query.sh 'Best strategy with 3 firefighters to minimize burned area'"
echo "  ./query.sh '64x64 grid, 180 turns' --format pdf --output report.pdf"
echo "  ./query.sh 'example configuration' --validate"
echo ""