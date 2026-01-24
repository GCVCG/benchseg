#!/bin/bash

# Script to run eval_map.py inside Docker container
# Usage: ./run_eval_map.sh --submit_dir <dir> --truth_dir <dir> --output_dir <dir>

docker run -it --gpus all --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/assets:/workspace/assets" \
  -v "$(pwd)/data:/workspace/data" \
  -v "$(pwd)/yolo/runs:/workspace/runs" \
  -v "$(pwd)/src/:/workspace/src" \
  -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
  --entrypoint "" \
  yolo \
  python /workspace/src/eval_map.py "$@"
