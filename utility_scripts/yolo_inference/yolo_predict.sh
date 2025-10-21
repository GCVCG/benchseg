#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <images_dir> <yolo_results_dir> [binarized_output_dir]

Examples:
  $(basename "$0") data/mtf_foodMem_reordered/images data/mtf_foodMem_reordered/results/YOLO/
  $(basename "$0") data/mtf_foodMem_reordered/images data/mtf_foodMem_reordered/results/YOLO/ data/mtf_foodMem_reordered/results/YOLO_binary

Notes:
- Paths are relative to the repo root (host), which is mounted at /workspace in the container.
- A third arg is optional; defaults to "<yolo_results_dir>_binary" (with trailing slash trimmed).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "$#" -lt 2 ]]; then
  usage
  exit 1
fi

IMAGES_DIR="${1}"
YOLO_RESULTS_DIR_RAW="${2}"

# Trim any trailing slash to keep things consistent
YOLO_RESULTS_DIR="${YOLO_RESULTS_DIR_RAW%/}"

# Optional third arg; fallback to "<results>_binary"
BINARIZED_DIR="${3:-${YOLO_RESULTS_DIR}_binary}"

# Docker image name (matches your example)
IMAGE_NAME="yolo"

# Run YOLO inference inside the container
docker run -it --gpus all --rm --ipc=host \
  -v "$(pwd)/assets:/workspace/assets" \
  -v "$(pwd)/data:/workspace/data" \
  -v "$(pwd)/yolo/runs:/workspace/runs" \
  -v "$(pwd)/src/yolo:/workspace/src" \
  -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
  --entrypoint "" \
  "${IMAGE_NAME}" \
  python /workspace/src/yolo_inference.py \
  assets/ckpts/YOLO/yolo11s-seg_foodseg1032.pt \
  "${IMAGES_DIR}" \
  "${YOLO_RESULTS_DIR}/"

# Post-process: binarize results
./utility_scripts/binarize.sh \
  "${YOLO_RESULTS_DIR}" \
  "${BINARIZED_DIR}"
