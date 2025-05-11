#!/bin/bash
DATASET_PATH=$1
SEM_MODEL_TYPE=$2

echo $DATASET_PATH
echo $SEM_MODEL_TYPE

# Output directory is cleaned every run
if [ -d "$DATASET_PATH/masks/" ]; then
    rm -rf "$DATASET_PATH"/masks
fi
mkdir -p "$DATASET_PATH"/masks

case $SEM_MODEL_TYPE in
    "SWIN")
        python3 -u ./src/semantic.py --img_path "$DATASET_PATH"/images/0001.jpg \
            --out_path "$DATASET_PATH"/masks/ \
            --semantic_config "configs/upernet_swin_small_provisional.py" \
            --semantic_checkpoint "ckpts/swin_small/iter_80000.pth"
        ;;
    *)
        SEM_MODEL_TYPE="SeTr"
        python3 -u ./src/semantic.py --img_path "$DATASET_PATH"/images/0001.jpg \
            --out_path "$DATASET_PATH"/masks/
        ;;
esac

# colors are assigned from semantic segmentation by default. Since we support a single object per scene, we need to
# convert the mask into black and white
convert "$DATASET_PATH"/masks/0001.png -threshold 1% "$DATASET_PATH"/masks/0001.png
# # track them
# cd XMem2
# python3 -u process_video.py --video "$DATASET_PATH"/images --masks "$DATASET_PATH"/masks --output "$DATASET_PATH"
# # changing the permission
# chmod -R 777 "$DATASET_PATH"/masks