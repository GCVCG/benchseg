docker run -it --gpus all --rm --ipc=host \
    -v "$(pwd)/assets:/workspace/assets" \
    -v "$(pwd)/data:/workspace/data" \
    -v "$(pwd)/yolo/runs:/workspace/runs" \
    -v "$(pwd)/src/yolo:/workspace/src" \
    -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
    --entrypoint "" \
    yolo \
    python /workspace/src/yolo_inference.py \
    assets/ckpts/YOLO/yolo11s-seg_foodseg1032.pt \
    data/mtf_yolo/images/test/ \
    data/mtf_yolo/images/results/YOLO/


./utility_scripts/binarize.sh \
data/mtf_yolo/images/results/YOLO/ \
data/mtf_yolo/images/results/YOLO_binary/    