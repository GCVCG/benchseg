#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# run_speed_test.sh – Wrapper to run FoodSeg speed tests in Docker
#
# This script runs the speed test inside the Docker container and then
# analyzes the results.
#
# Usage (from repo root):
#   cd /path/to/SpiceSeg
#   ./speed_test/run_speed_test.sh [MODEL_TYPE]
#
# Examples:
#   ./speed_test/run_speed_test.sh ALL         # Test all models
#   ./speed_test/run_speed_test.sh SWIN_SMALL  # Test specific model
# ----------------------------------------------------------------------------

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the repo root (parent of speed_test)
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

MODEL_TYPE="${1:-ALL}"

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   FoodSeg Model Speed Test Runner                     ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Model(s) to test: $MODEL_TYPE"
echo "Speed test dataset: data/speed_test/random_images/"
echo "Repo root: $REPO_ROOT"
echo ""
echo "Starting Docker container..."
echo ""

# Run the speed test in Docker
docker run --gpus all -it --rm \
    -v "$REPO_ROOT/assets:/workspace/assets" \
    -v "$REPO_ROOT/data:/workspace/data" \
    -v "$REPO_ROOT/speed_test:/workspace/speed_test" \
    -v "$REPO_ROOT/automation_scripts:/workspace/automation_scripts" \
    -v "$REPO_ROOT/src:/workspace/src" \
    foodseg103 \
    bash /workspace/speed_test/speed_test_foodseg.sh "$MODEL_TYPE"

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                     Analyzing Results...                               ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Analyze results (run locally)
if command -v python3 &> /dev/null; then
    python3 "$SCRIPT_DIR/analyze_speed_results.py" "$REPO_ROOT/data/speed_test/results"
else
    echo "Python3 not found. Skipping detailed analysis."
    echo "Run manually: python3 $SCRIPT_DIR/analyze_speed_results.py $REPO_ROOT/data/speed_test/results"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                           Test Complete!                               ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Results location:"
echo "  • Predictions: $REPO_ROOT/data/speed_test/results/"
echo "  • Timing logs: $REPO_ROOT/data/speed_test/results/*/log.csv"
echo "  • JSON summary: $REPO_ROOT/data/speed_test/results/speed_test_summary.json"
echo ""
