#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <dataset_dir> <model_name> [num_classes] [--compute_miou]

Examples:
  $(basename "$0") "data/V&F_reordered" FoodLLM
  $(basename "$0") "data/n5k_reordered" YOLO_SAM2 2
  $(basename "$0") "data/n5k_reordered" YOLO_SAM2 2 --compute_miou

Notes:
- <dataset_dir> is the dataset root (contains 'masks' and 'results/<model_name>').
- <model_name> is the model subdirectory under results/ and metrics/ (e.g., FoodLLM, YOLO_SAM2).
- num_classes defaults to 2.
- --compute_miou: Optional flag to compute mean IoU for multiclass segmentation (num_classes > 2).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 2 ]]; then
  usage
  exit 1
fi

DATASET_DIR="${1%/}"
MODEL_NAME="${2}"
NUM_CLASSES="${3:-2}"

# Parse optional --compute_miou flag
COMPUTE_MIOU_FLAG=""
if [[ "${4:-}" == "--compute_miou" || "${3:-}" == "--compute_miou" ]]; then
  COMPUTE_MIOU_FLAG="--compute_miou"
  # If 3rd arg is the flag, use default num_classes
  if [[ "${3:-}" == "--compute_miou" ]]; then
    NUM_CLASSES="2"
  fi
fi

SUBMIT_DIR="${DATASET_DIR}/results/${MODEL_NAME}"
TRUTH_DIR="${DATASET_DIR}/masks"
OUTPUT_DIR="${DATASET_DIR}/metrics/${MODEL_NAME}"

docker run -it --gpus all --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/assets:/workspace/assets" \
  -v "$(pwd)/data:/workspace/data" \
  -v "$(pwd)/yolo/runs:/workspace/runs" \
  -v "$(pwd)/src/:/workspace/src" \
  -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
  --entrypoint "" \
  yolo \
  python /workspace/src/eval_map.py \
    --submit_dir "${SUBMIT_DIR}" \
    --truth_dir "${TRUTH_DIR}" \
    --output_dir "${OUTPUT_DIR}" \
    --num_classes "${NUM_CLASSES}" \
    --num_workers 4 \
    ${COMPUTE_MIOU_FLAG}
