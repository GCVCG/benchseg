#!/bin/bash
IMG_PATH=$1
OUT_PATH=$2
SEM_MODEL_TYPE=$3

# echo "$DATASET_PATH"
# echo "$SEM_MODEL_TYPE"

# Output directory is cleaned every run
# rm -rf "$OUT_PATH"
# mkdir -p "$OUT_PATH"

declare -A CONFIG_PATHS
declare -A CHECKPOINT_PATHS

CONFIG_PATHS=(
    ["SWIN_SMALL"]="assets/ckpts/swin_small/upernet_swin_small_patch4_window7_512x1024_80k.py"
    ["SWIN_BASE"]="assets/ckpts/swin_base/upernet_swin_base_patch4_window7_512x1024_80k.py"
    ["FPN_RELEM"]="assets/ckpts/FPN_ReLeM/fpn_r50_512x1024_80k.py"
    ["CCNET"]="assets/ckpts/CCNet/ccnet_r101-d8_512x1024_80k.py"
    ["CCNET_RELEM"]="assets/ckpts/CCNet_ReLeM/ccnet_r50-d8_512x1024_80k.py"
    ["SETR_MLA_L384"]="assets/ckpts/SETR_MLA_L384/SETR_MLA_768x768_80k.py"
    ["SETR_NAIVE"]="assets/ckpts/SETR_Naive/SETR_Naive_768x768_80k_base.py"
)

CHECKPOINT_PATHS=(
    ["SWIN_SMALL"]="assets/ckpts/swin_small/iter_80000.pth"
    ["SWIN_BASE"]="assets/ckpts/swin_base/iter_80000.pth"
    ["FPN_RELEM"]="assets/ckpts/FPN_ReLeM/iter_80000.pth"
    ["CCNET"]="assets/ckpts/CCNet/iter_80000.pth"
    ["CCNET_RELEM"]="assets/ckpts/CCNet_ReLeM/iter_80000.pth"
    ["SETR_MLA_L384"]="assets/ckpts/SETR_MLA_L384/iter_80000.pth"
    ["SETR_NAIVE"]="assets/ckpts/SETR_Naive/iter_80000.pth"
)

# IMG_PATH="$DATASET_PATH/images/0001.jpg"
# OUT_PATH="$DATASET_PATH/pred_masks"

# Default case if model type not found
if [[ -n "${CONFIG_PATHS[$SEM_MODEL_TYPE]}" && -n "${CHECKPOINT_PATHS[$SEM_MODEL_TYPE]}" ]]; then
    python3 -u ./src/semantic.py \
        --img_path "$IMG_PATH" \
        --out_path "$OUT_PATH" \
        --log_path "$OUT_PATH/log.csv" \
        --semantic_config "${CONFIG_PATHS[$SEM_MODEL_TYPE]}" \
        --semantic_checkpoint "${CHECKPOINT_PATHS[$SEM_MODEL_TYPE]}"
else
    echo "Warning: Unknown SEM_MODEL_TYPE '$SEM_MODEL_TYPE'. Running default without config/checkpoint."
    python3 -u ./src/semantic.py \
        --img_path "$IMG_PATH" \
        --out_path "$OUT_PATH"
fi

# Convert mask to black and white
outfile="$OUT_PATH$(basename -- "$IMG_PATH" | sed 's/\.[^.]*$/.png/')"
convert $outfile -threshold 1% $outfile 

# Optional tracking and permissions (commented)
# cd XMem2
# python3 -u process_video.py --video "$DATASET_PATH"/images --pred_masks "$DATASET_PATH"/masks --output "$DATASET_PATH"
# chmod -R 777 "$DATASET_PATH"/pred_masks
