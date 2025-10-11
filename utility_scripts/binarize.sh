#!/usr/bin/env bash
# binarize_ground_truth: Convert grayscale/pred masks to true binary (0 or 255)
# Usage: binarize_ground_truth <input_dir> <output_dir>

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <input_dir> <output_dir>" >&2
  exit 1
fi

INPUT="${1%/}"
OUTPUT="${2%/}"
mkdir -p "$OUTPUT"

# Optional: use `timeout` if available so we don't hit IM's internal time policy
TIMEOUT=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT="timeout 30s"     # kill any file that takes >30s
fi

# Speed + stability tweaks:
# - -limit time 25: keep each op under the IM policy
# - -limit memory/map: avoid excessive swapping
# - -strip: drop metadata
# - -threshold 0: any non-zero => white
# - -type bilevel: force 1-bit mask
# -define png:compression-level=9: small files, still fast
# -quiet: reduce stderr noise
shopt -s nullglob
failed=0 processed=0
for IMG in "$INPUT"/*.{png,PNG,jpg,JPG,jpeg,JPEG,bmp,BMP,tif,TIF,tiff,TIFF}; do
  [ -f "$IMG" ] || continue
  processed=$((processed+1))
  name="$(basename "$IMG")"
  out="$OUTPUT/$name"

  # Skip if already exists & newer than input (idempotent reruns)
  if [ -e "$out" ] && [ "$out" -nt "$IMG" ]; then
    continue
  fi

  if ! $TIMEOUT convert -quiet \
      -limit time 25 -limit memory 512MiB -limit map 1GiB \
      "$IMG" -threshold 0 -type bilevel -strip \
      -define png:compression-level=9 \
      "PNG:$out"; then
    echo "WARN: Failed on $IMG" >&2
    failed=$((failed+1))
  fi
done
shopt -u nullglob

echo "Binarized to: $OUTPUT (processed=$processed, failed=$failed)"
if [ "$failed" -gt 0 ]; then
  echo "Tip: re-run will retry only the failed/older files."
fi