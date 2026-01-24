#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root (parent of utility_scripts)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Model configuration
YOLO_PT="yolo11s-seg"

# Run training inside Docker container with GPU support
# Note: yolo image has entrypoint ["/bin/bash", "-l", "-c"], so we pass the command directly
docker run --gpus all --rm --ipc=host \
    -v "$(pwd)/assets:/workspace/assets" \
    -v "$(pwd)/data:/workspace/data" \
    -v "$(pwd)/src/yolo/runs:/workspace/runs" \
    -v "$(pwd)/src/:/workspace/src" \
    -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
    yolo \
    "cd /workspace/data/FoodSeg103_yolo_train/ && \
     ls -l && \
     yolo segment train \
         data=foodseg103.yaml \
         model=/workspace/assets/ckpts/YOLO/${YOLO_PT}.pt \
         seed=0 \
         epochs=300 \
         patience=50 \
         imgsz=640 \
         batch=-1 \
         cache=False \
         rect=True \
         mixup=0.15 \
         copy_paste=0.3 \
         degrees=10.0 \
         translate=0.1 \
         scale=0.5 \
         fliplr=0.5 \
         mosaic=1.0 \
         name=${YOLO_PT}_foodseg103_multiclass"