#!/usr/bin/env bash
# binarize_ground_truth: Convert grayscale ground truth masks to true binary
# Usage: binarize_ground_truth <input_dir> <output_dir>

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <input_dir> <output_dir>" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="$2"

mkdir -p "$OUTPUT"

# For ground truth masks, we want to consider any non-zero pixel as foreground
shopt -s nullglob
for IMG in "$INPUT"/*.{png,jpg,jpeg,bmp,tif,tiff}; do
  [ -f "$IMG" ] || continue
  NAME=$(basename "$IMG")
  # -threshold 0 will make any non-zero pixel white
  convert "$IMG" -threshold 0 "$OUTPUT/$NAME"
  echo "Binarized: $IMG -> $OUTPUT/$NAME"
done
shopt -u nullglob
