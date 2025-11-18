#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# prepare_tracking_data.sh - Prepare video sequences with initial masks
#                             for tracking model speed tests
#
# This script creates initial masks for each video sequence that tracking
# models (XMem2, SAM2) can use as prompts.
# ----------------------------------------------------------------------------

set -euo pipefail

SPEED_TEST_DIR="data/speed_test"
VIDEOS_DIR="$SPEED_TEST_DIR/videos"
MASKS_DIR="$SPEED_TEST_DIR/initial_masks"

echo "========================================="
echo "Preparing Tracking Model Test Data"
echo "========================================="
echo ""

# Create masks directory
mkdir -p "$MASKS_DIR"

echo "Creating initial masks for tracking..."
echo ""

# For each video sequence, we need to create an initial mask
# We'll create simple masks for the first frame of each sequence
# In a real scenario, these would come from a segmentation model or manual annotation

for seq_dir in "$VIDEOS_DIR"/*/ ; do
    seq_name=$(basename "$seq_dir")
    echo "Processing: $seq_name"
    
    # Get first frame
    first_frame=$(ls "$seq_dir" | sort | head -1)
    first_frame_path="$seq_dir/$first_frame"
    
    # Create mask with SAME filename as first frame (batch scripts expect exact match)
    mask_output="$MASKS_DIR/$first_frame"
    
    if command -v convert &> /dev/null; then
        # Get image dimensions
        dims=$(identify -format "%wx%h" "$first_frame_path")
        width=$(echo $dims | cut -d'x' -f1)
        height=$(echo $dims | cut -d'x' -f2)
        
        # Create a mask with a centered object (60% of image size)
        obj_w=$((width * 60 / 100))
        obj_h=$((height * 60 / 100))
        x_offset=$(((width - obj_w) / 2))
        y_offset=$(((height - obj_h) / 2))
        
        # Create binary mask with white rectangle on black background
        convert -size "${width}x${height}" xc:black \
            -fill white -draw "rectangle $x_offset,$y_offset $((x_offset+obj_w)),$((y_offset+obj_h))" \
            "$mask_output"
        
        echo "  ✓ Created mask: $(basename $mask_output) (${width}x${height})"
    else
        echo "  ⚠ ImageMagick not found, cannot create mask"
        echo "  Please install ImageMagick: sudo apt install imagemagick"
        exit 1
    fi
done

echo ""
echo "========================================="
echo "Initial masks created in: $MASKS_DIR"
echo "========================================="
echo ""

# Create JPG versions of masks for SAM2 (which requires JPG format)
echo "Creating JPG versions of masks for SAM2..."
for mask in "$MASKS_DIR"/*.png; do
    if [ -f "$mask" ]; then
        base_name=$(basename "$mask" .png)
        convert "$mask" "$MASKS_DIR/${base_name}.jpg"
        echo "  ✓ Created: ${base_name}.jpg"
    fi
done
echo ""

echo "Mask files:"
ls -lh "$MASKS_DIR"
echo ""
echo "✓ Ready for tracking model tests!"
echo ""
echo "Note: These are placeholder masks. For actual use, you should:"
echo "  1. Use a segmentation model to generate initial masks"
echo "  2. Or manually annotate the first frame"
echo "  3. Or copy masks from your existing datasets"
