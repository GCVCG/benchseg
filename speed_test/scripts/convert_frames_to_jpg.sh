#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# convert_frames_to_jpg.sh - Convert PNG video frames to JPG for SAM2
# ----------------------------------------------------------------------------

set -uo pipefail

VIDEOS_DIR="data/speed_test/videos"
JPG_DIR="data/speed_test/videos_jpg"

echo "========================================="
echo "Converting Video Frames to JPG"
echo "========================================="
echo ""

# Create JPG directory
mkdir -p "$JPG_DIR"

# Convert each video sequence
for seq_dir in "$VIDEOS_DIR"/*/ ; do
    seq_name=$(basename "$seq_dir")
    echo "Converting: $seq_name"
    
    # Create output directory
    output_dir="$JPG_DIR/$seq_name"
    mkdir -p "$output_dir"
    
    # Convert all PNG frames to JPG
    frame_count=0
    for png_file in "$seq_dir"/*.png; do
        if [ -f "$png_file" ]; then
            base_name=$(basename "$png_file" .png)
            jpg_file="$output_dir/${base_name}.jpg"
            
            convert "$png_file" -quality 95 "$jpg_file"
            ((frame_count++))
        fi
    done
    
    echo "  ✓ Converted $frame_count frames"
done

echo ""
echo "========================================="
echo "JPG frames created in: $JPG_DIR"
echo "========================================="
echo ""
echo "✓ Ready for SAM2 tests!"
