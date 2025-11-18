#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# run_sam2_speed_test.sh - Run SAM2 tracking model speed test
#
# Usage:
#   ./run_sam2_speed_test.sh [SEQUENCE_NAME]
#
# Examples:
#   ./run_sam2_speed_test.sh all               # Test all sequences
#   ./run_sam2_speed_test.sh lemon_sequence    # Test specific sequence
# ----------------------------------------------------------------------------

set -euo pipefail

SPEED_TEST_DIR="data/speed_test"
VIDEOS_DIR="$SPEED_TEST_DIR/videos_jpg"  # Use JPG versions
MASKS_DIR="$SPEED_TEST_DIR/initial_masks"
RESULTS_DIR="$SPEED_TEST_DIR/results_tracking/sam2"
SEQUENCE="${1:-all}"

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                      SAM2 Speed Test Runner                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if initial masks exist
if [[ ! -d "$MASKS_DIR" ]] || [[ -z "$(ls -A "$MASKS_DIR" 2>/dev/null)" ]]; then
    echo "⚠️  Initial masks not found!"
    echo ""
    echo "Please run the preparation script first:"
    echo "  ./speed_test/scripts/prepare_tracking_data.sh"
    echo ""
    exit 1
fi

mkdir -p "$RESULTS_DIR"

# Function to run SAM2 on a single sequence
run_sam2_sequence() {
    local seq_name="$1"
    local seq_dir="$VIDEOS_DIR/$seq_name"
    local output_dir="$RESULTS_DIR/$seq_name"
    
    if [[ ! -d "$seq_dir" ]]; then
        echo "❌ Sequence not found: $seq_name"
        return 1
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $seq_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Images: $seq_dir"
    echo "Masks:  $MASKS_DIR"
    echo "Output: $output_dir"
    echo ""
    
    # Record start time
    start_time=$(date +%s.%N)
    
    # Run SAM2 in Docker
    if docker run --rm -it --gpus all \
        -v "$(pwd)":/workspace \
        sam2-vos \
        bash -lc "
            set -euo pipefail
            
            IMAGES=\"/workspace/$seq_dir\"
            MASKS=\"/workspace/$MASKS_DIR\"
            OUT=\"/workspace/$output_dir\"
            
            /workspace/docker/sam2/batch_sam2.sh \
                --images \"\$IMAGES\" \
                --masks \"\$MASKS\" \
                --output \"\$OUT\" \
                --checkpoint /workspace/tracking_models/sam2/sam2.1_hiera_large.pt \
                --config configs/sam2.1/sam2.1_hiera_l.yaml \
                --obj-id 1 \
                --vos-optimized
        "; then
        
        # Record end time
        end_time=$(date +%s.%N)
        runtime=$(echo "$end_time - $start_time" | bc)
        
        # Count processed frames
        frame_count=$(ls "$seq_dir" | wc -l)
        output_count=$(find "$output_dir" -name "${seq_name}_*.png" 2>/dev/null | wc -l || echo 0)
        
        # Calculate FPS
        fps=$(echo "scale=2; $frame_count / $runtime" | bc)
        avg_time=$(echo "scale=3; $runtime / $frame_count" | bc)
        
        echo ""
        echo "✅ Success!"
        echo "  • Total runtime: ${runtime}s"
        echo "  • Frames processed: $output_count / $frame_count"
        echo "  • Average time per frame: ${avg_time}s"
        echo "  • FPS: $fps"
        echo ""
        
        # Save timing info
        echo "$seq_name,$frame_count,$runtime,$avg_time,$fps" >> "$RESULTS_DIR/timing_summary.csv"
        
        return 0
    else
        echo ""
        echo "❌ Failed!"
        return 1
    fi
}

# Initialize timing summary
echo "sequence,frames,total_time,avg_time_per_frame,fps" > "$RESULTS_DIR/timing_summary.csv"

# Run tests
if [[ "$SEQUENCE" == "all" ]]; then
    echo "Testing all sequences..."
    echo ""
    
    for seq_dir in "$VIDEOS_DIR"/*/ ; do
        seq_name=$(basename "$seq_dir")
        run_sam2_sequence "$seq_name" || true
        echo ""
    done
else
    run_sam2_sequence "$SEQUENCE"
fi

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                        Tests Complete!                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""

# Show summary if available
if [[ -f "$RESULTS_DIR/timing_summary.csv" ]]; then
    echo "Timing Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    column -t -s',' "$RESULTS_DIR/timing_summary.csv"
    echo ""
fi
