#!/bin/bash

# Script to run segMAN + XMEM2 inference on all reordered datasets
# This script runs batch_xmem2.sh for each dataset using segMAN results as input masks

set -euo pipefail

echo "Running segMAN + XMEM2 inference on all reordered datasets..."

# Dataset 1: mtf_foodMem_reordered
echo "Processing mtf_foodMem_reordered..."
/home/guill_unix/repos/SpiceSeg/utility_scripts/batch_xmem2.sh \
  --images "data/mtf_foodMem_reordered/images" \
  --masks "data/mtf_foodMem_reordered/results/segMAN" \
  --output "data/mtf_foodMem_reordered/results/segMAN_XMEM2" \
  --n_masks 1

# Dataset 2: FoodKit_dataset_reordered
echo "Processing FoodKit_dataset_reordered..."
/home/guill_unix/repos/SpiceSeg/utility_scripts/batch_xmem2.sh \
  --images "data/FoodKit_dataset_reordered/images" \
  --masks "data/FoodKit_dataset_reordered/results/segMAN" \
  --output "data/FoodKit_dataset_reordered/results/segMAN_XMEM2" \
  --n_masks 1

# Dataset 3: V&F_reordered
echo "Processing V&F_reordered..."
/home/guill_unix/repos/SpiceSeg/utility_scripts/batch_xmem2.sh \
  --images "data/V&F_reordered/images" \
  --masks "data/V&F_reordered/results/segMAN" \
  --output "data/V&F_reordered/results/segMAN_XMEM2" \
  --n_masks 1

# Dataset 4: n5k_reordered
echo "Processing n5k_reordered..."
/home/guill_unix/repos/SpiceSeg/utility_scripts/batch_xmem2.sh \
  --images "data/n5k_reordered/images" \
  --masks "data/n5k_reordered/results/segMAN" \
  --output "data/n5k_reordered/results/segMAN_XMEM2" \
  --n_masks 1

echo "All segMAN + XMEM2 inference tasks completed!"
