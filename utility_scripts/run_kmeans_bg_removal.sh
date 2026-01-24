#!/bin/bash
# Batch background removal for FoodKit dataset using k-means++

# Default parameters
INPUT_DIR="data/FoodKit_dataset_reordered/images"
OUTPUT_DIR="data/FoodKit_dataset_reordered/results/kmeans_bg_removed"
NUM_CLUSTERS=2
THRESHOLD1=93
THRESHOLD2=110
MORPH_RADIUS=3

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --clusters)
            NUM_CLUSTERS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --input DIR       Input directory (default: data/FoodKit_dataset_reordered/images)"
            echo "  --output DIR      Output directory (default: data/FoodKit_dataset_reordered/results/kmeans_bg_removed)"
            echo "  --clusters NUM    Number of clusters (default: 2)"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "K-means++ Background Removal"
echo "========================================"
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "Clusters: $NUM_CLUSTERS"
echo "========================================"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Use the virtual environment python
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

# Fallback to system python if venv doesn't exist
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python"
fi

# Run the background removal
"$PYTHON_BIN" "$SCRIPT_DIR/kmeans_background_removal.py" \
    "$INPUT_DIR" \
    --batch \
    --output_dir "$OUTPUT_DIR" \
    --num_clusters "$NUM_CLUSTERS" \
    --threshold1 "$THRESHOLD1" \
    --threshold2 "$THRESHOLD2" \
    --morph_radius "$MORPH_RADIUS" \
    --save_masks

echo ""
echo "Done! Results saved to: $OUTPUT_DIR"
