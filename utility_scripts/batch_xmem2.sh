#!/bin/bash

set -euo pipefail
shopt -s nullglob

usage() {
  echo "Usage: $0 --images DIR --masks DIR --output DIR --n_masks N" >&2
  exit 1
}

export MAGICK_TIME_LIMIT=3600

IMAGES_DIR=""
MASKS_DIR=""
OUTPUT_DIR=""
TEMP_DIR="temp_processing"
N_MASKS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --images)
      IMAGES_DIR="${2:-}"; shift 2 ;;
    --masks)
      MASKS_DIR="${2:-}"; shift 2 ;;
    --output)
      OUTPUT_DIR="${2:-}"; shift 2 ;;
    --n_masks)
      N_MASKS="${2:-}"; shift 2 ;;
    -h|--help)
      usage ;;
    *)
      echo "Unknown argument: $1" >&2
      usage ;;
  esac
done

if [[ -z "$IMAGES_DIR" || -z "$MASKS_DIR" || -z "$OUTPUT_DIR" ]]; then
  echo "Error: --images, --masks, and --output are required." >&2
  usage
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "${OUTPUT_DIR}/res_overlay"

# Create a temporary directory for processing
mkdir -p "$TEMP_DIR"
trap 'rm -rf "$TEMP_DIR"' EXIT

# Images and masks are named as <video_id>_<frame_id>.png
# Temp directories will be created as <video_id>_temp
for image_path in "$IMAGES_DIR"/*.png; do
  mask_path="$MASKS_DIR/$(basename "$image_path")"
  mask_filename=$(basename "$mask_path")

  image_filename=$(basename "$image_path")
  # Extract filename without extension
  filename_no_ext="${image_filename%.*}"
  
  # Extract frame digits from the end (last underscore group)
  frame_digits="${filename_no_ext##*_}"
  if [[ "$frame_digits" =~ ^[0-9]+$ ]]; then
      frame_num=$((10#$frame_digits))
      # Video ID is everything before the last underscore + frame digits
      video_id="${filename_no_ext%_${frame_digits}}"
      frame_id="${frame_digits}.${image_filename##*.}"  # frame digits + original extension
  else
      # Fallback to original logic if no numeric suffix found
      video_id="${image_filename%%_*}"
      frame_id="${image_filename#*_}"
      frame_num=0
  fi


  mkdir -p "$TEMP_DIR/${video_id}_temp/frames" 
  mkdir -p "$TEMP_DIR/${video_id}_temp/masks"

  # Make hard link to images and masks
  ln "$image_path" "$TEMP_DIR/${video_id}_temp/frames/${frame_id}"

  # Only link the first N_MASKS masks per video
  if (( frame_num < N_MASKS )); then
    ln "$mask_path" "$TEMP_DIR/${video_id}_temp/masks/${frame_id}"
  fi
done

# Process each video and mask directories in pairs with "run_docker_on_dir.sh", 
for temp_video_dir in "$TEMP_DIR"/*_temp; do
  [ -d "$temp_video_dir" ] || continue
  
  # Run inference with error handling - continue processing other videos if this one fails
  if /home/guill_unix/repos/SpiceSeg/tracking_models/XMem2/run_inference_in_docker_spice_seg.sh -v "$temp_video_dir/frames" -m "$temp_video_dir/masks" -o "$OUTPUT_DIR"; then
    # Generates masks and overlay directories inside OUTPUT_DIR
    # Now, move the files to the main output directory and rename them appropriately
    video_id=$(basename "$temp_video_dir" | sed 's/_temp$//')
    for output_file in "$OUTPUT_DIR/masks/"*.png; do
      [ -e "$output_file" ] || continue

      base="$(basename "$output_file")"   # e.g., 000.png
      stem="${base%.png}"                 # -> 000

      mv "$output_file" "$OUTPUT_DIR/${video_id}_$base"
      mv "$OUTPUT_DIR/overlay/${stem}.jpg" "$OUTPUT_DIR/res_overlay/${video_id}_${stem}.jpg"
    done
    # Clean up the mask and overlay directories created by the script
    rm -rf "$OUTPUT_DIR/masks" "$OUTPUT_DIR/overlay"
    # /home/guill_unix/repos/SpiceSeg/utility_scripts/binarize.sh "$OUTPUT_DIR" "${OUTPUT_DIR}_binary"
  else
    echo "Warning: XMem2 inference failed for video $(basename "$temp_video_dir" | sed 's/_temp$//'), skipping to next video..." >&2
  fi
done