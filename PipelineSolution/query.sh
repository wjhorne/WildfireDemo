#!/bin/bash
# Query wrapper for PipelineSolution
# Usage: ./query.sh "<query>" [options]
#        ./query.sh "Generate a PDF report" --format pdf --output report.pdf

if [ -z "$1" ]; then
    echo "Usage: $0 <query> [options]"
    echo ""
    echo "Examples:"
    echo "  $0 'Best strategy with 3 firefighters to minimize burned area'"
    echo "  $0 '64x64 grid, 180 turns, seed 12345, 3 firefighters' --format pdf --output report.pdf"
    echo "  $0 'example configuration' --validate"
    echo ""
    echo "Options:"
    echo "  --format {text,pdf}    Output format (default: text)"
    echo "  --output FILE          Save to file instead of stdout"
    echo "  --validate             Validate the engine against the example_run baseline"
    echo ""
    exit 1
fi

if [ -n "$VIRTUAL_ENV" ]; then
    :
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run './setup.sh' first."
    exit 1
fi

QUERY="$1"
shift
python pipeline.py --query "$QUERY" "$@"