#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# speed_test_foodseg.sh – Run FoodSeg models on the speed_test dataset
#                          and measure inference time
#
# Usage:
#   ./speed_test_foodseg.sh [MODEL_TYPE]
#
# Examples:
#   ./speed_test_foodseg.sh ALL         # Test all models
#   ./speed_test_foodseg.sh SWIN_SMALL  # Test specific model
# ----------------------------------------------------------------------------

set -euo pipefail

# --------------------------- Configuration ---------------------------
SPEED_TEST_DIR="/workspace/data/speed_test/random_images"
OUTPUT_DIR="/workspace/data/speed_test/results"
MODEL_TYPE="${1:-ALL}"

echo "========================================="
echo "FoodSeg Model Speed Test"
echo "========================================="
echo "Input: $SPEED_TEST_DIR"
echo "Output: $OUTPUT_DIR"
echo "Models: $MODEL_TYPE"
echo "========================================="
echo ""

# --------------------------- Run the batch script ---------------------------
bash /workspace/automation_scripts/foodseg_run_dir.sh \
    "$SPEED_TEST_DIR" \
    "$MODEL_TYPE" \
    "$OUTPUT_DIR"

echo ""
echo "========================================="
echo "Speed Test Complete!"
echo "========================================="
echo ""
echo "Results saved to: $OUTPUT_DIR"
echo ""

# --------------------------- Analyze timing results ---------------------------
echo "Timing Summary:"
echo "---------------"

for log_file in "$OUTPUT_DIR"/*/log.csv; do
    if [[ -f "$log_file" ]]; then
        model_name=$(basename $(dirname "$log_file"))
        echo ""
        echo "📊 $model_name:"
        
        # Check if Python is available to parse CSV
        if command -v python3 &> /dev/null; then
            python3 - <<EOF
import csv
import os
import sys

log_path = "$log_file"
if not os.path.exists(log_path):
    sys.exit(0)

times = []
with open(log_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Look for timing columns (common names)
        for key in ['inference_time', 'total_time', 'time', 'runtime']:
            if key in row:
                try:
                    times.append(float(row[key]))
                except:
                    pass

if times:
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    print(f"  • Images processed: {len(times)}")
    print(f"  • Average time: {avg_time:.3f}s")
    print(f"  • Min time: {min_time:.3f}s")
    print(f"  • Max time: {max_time:.3f}s")
    print(f"  • FPS (avg): {1/avg_time:.2f}")
else:
    print("  • No timing data found in log")
EOF
        else
            # Fallback: just show file info
            line_count=$(wc -l < "$log_file")
            echo "  • Log entries: $((line_count - 1))"
            echo "  • Log file: $log_file"
        fi
    fi
done

echo ""
echo "========================================="
echo "View detailed results:"
echo "  ls -lh $OUTPUT_DIR/*/log.csv"
echo "========================================="
