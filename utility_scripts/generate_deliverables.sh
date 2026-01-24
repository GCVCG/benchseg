#!/bin/bash

# Script to generate deliverables (tar.gz files) for datasets
# Clears and regenerates the deliverables directory

set -e  # Exit on error

DELIVERABLES_DIR="/home/guill_unix/repos/SpiceSeg/deliverables"
DATA_DIR="/home/guill_unix/repos/SpiceSeg/data"

echo "=== Generating Deliverables ==="

# Ensure deliverables directory exists (do not wipe existing archives)
mkdir -p "$DELIVERABLES_DIR"

# Define datasets (excluding Deprecated and FoodSeg103_yolo_train)
DATASETS=(
    "FoodKit_dataset_reordered"
    "mtf_foodMem_reordered"
    "n5k_reordered"
    "V&F_reordered"
)

# Generate deliverables for each dataset
for dataset in "${DATASETS[@]}"; do
    echo ""
    echo "Processing dataset: $dataset"

    # Data deliverable (images, images_jpg, masks)
    data_tar="$DELIVERABLES_DIR/data_${dataset}.tar.gz"
    if [ -e "$data_tar" ]; then
        echo "  Skipping data_${dataset}.tar.gz (already exists)"
    else
        echo "  Creating data_${dataset}.tar.gz..."
        tar -czf "$data_tar" \
            -C "$DATA_DIR/$dataset" \
            images images_jpg masks
    fi

    # Metrics deliverable
    metrics_tar="$DELIVERABLES_DIR/metrics_${dataset}.tar.gz"
    if [ -e "$metrics_tar" ]; then
        echo "  Skipping metrics_${dataset}.tar.gz (already exists)"
    else
        echo "  Creating metrics_${dataset}.tar.gz..."
        tar -czf "$metrics_tar" \
            -C "$DATA_DIR/$dataset" \
            metrics
    fi

    # Results deliverable
    results_tar="$DELIVERABLES_DIR/results_${dataset}.tar.gz"
    if [ -e "$results_tar" ]; then
        echo "  Skipping results_${dataset}.tar.gz (already exists)"
    else
        echo "  Creating results_${dataset}.tar.gz..."
        tar -czf "$results_tar" \
            -C "$DATA_DIR/$dataset" \
            results
    fi
done

echo ""
echo "=== Deliverables Generated ==="
echo "Total files created:"
ls -lh "$DELIVERABLES_DIR" | grep -E "\.tar\.gz$" | wc -l
echo ""
echo "Deliverables location: $DELIVERABLES_DIR"
echo ""
ls -lh "$DELIVERABLES_DIR"
