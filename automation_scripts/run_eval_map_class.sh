#!/bin/bash

# This script is meant to be run inside the Docker container
# Directory containing the results
RESULTS_DIR="/workspace/data/FoodSeg103_yolo/images/results"
GROUND_TRUTH_DIR="/workspace/data/FoodSeg103_yolo/ann_dir/test"
OUTPUT_DIR="/workspace/data/FoodSeg103_yolo/metrics"
NUM_CLASSES=104  # Adjust based on your dataset

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Run eval_map_class.py for each model's results
for MODEL_DIR in $RESULTS_DIR/*; do
    if [ -d "$MODEL_DIR" ]; then
        MODEL_NAME=$(basename $MODEL_DIR)
        echo "Evaluating $MODEL_NAME..."
        python /workspace/src/eval_map_class.py \
            --submit_dir $MODEL_DIR \
            --truth_dir $GROUND_TRUTH_DIR \
            --output_dir $OUTPUT_DIR/$MODEL_NAME \
            --num_classes $NUM_CLASSES
    fi
done

echo "Evaluation completed for all models."
