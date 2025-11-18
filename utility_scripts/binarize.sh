#!/usr/bin/env bash
# binarize_ground_truth: Convert grayscale/pred masks to true binary (0 or 255)
# Usage: binarize_ground_truth <input_dir> <output_dir> [max_jobs]

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <input_dir> <output_dir> [max_jobs]" >&2
  echo "  max_jobs: Number of parallel jobs (default: number of CPU cores)" >&2
  exit 1
fi

INPUT="${1%/}"
OUTPUT="${2%/}"
MAX_JOBS="${3:-$(nproc)}"  # Default to number of CPU cores
mkdir -p "$OUTPUT"

TIMEOUT=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT="timeout 30s"     # kill any file that takes >30s
fi

# Function to process a single image
process_image() {
  local IMG="$1"
  local name="$(basename "$IMG")"
  local out="$OUTPUT/$name"

  # Skip if already exists & newer than input (idempotent reruns)
  if [ -e "$out" ] && [ "$out" -nt "$IMG" ]; then
    return 0
  fi

  if $TIMEOUT convert -quiet \
      -limit time 25 -limit memory 512MiB -limit map 1GiB \
      "$IMG" -threshold 0 -type bilevel -strip \
      -define png:compression-level=9 \
      "PNG:$out"; then
    return 0
  else
    echo "WARN: Failed on $IMG" >&2
    return 1
  fi
}

# Export function for xargs
export -f process_image
export OUTPUT TIMEOUT

# Find all image files and process them in parallel using xargs
shopt -s nullglob
images=("$INPUT"/*.{png,PNG,jpg,JPG,jpeg,JPEG,bmp,BMP,tif,TIF,tiff,TIFF})
shopt -u nullglob

if [ ${#images[@]} -eq 0 ]; then
  echo "No images found in $INPUT"
  exit 0
fi

echo "Processing ${#images[@]} images with $MAX_JOBS parallel jobs..."

# Use printf to list files and xargs to process them in parallel
failed=0
processed=${#images[@]}
if printf '%s\n' "${images[@]}" | xargs -n 1 -P "$MAX_JOBS" -I {} bash -c 'process_image "$@"' _ {}; then
  echo "All jobs completed successfully"
else
  # Count actual failures by checking output files
  for img in "${images[@]}"; do
    name="$(basename "$img")"
    out="$OUTPUT/$name"
    if [ ! -e "$out" ] || [ "$img" -nt "$out" ]; then
      failed=$((failed + 1))
    fi
  done
fi

echo "Binarized to: $OUTPUT (processed=$processed, failed=$failed)"
if [ "$failed" -gt 0 ]; then
  echo "Tip: re-run will retry only the failed/older files."
fi