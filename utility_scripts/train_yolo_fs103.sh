#!/bin/bash

# YOLO_PT="yolo11s-seg"

# # Retrain YOLO model with rectangular training to preserve aspect ratios
# cd /workspace/data/FoodSeg103_yolo/ && yolo segment train \
#     data=foodseg103.yaml \
#     model="/workspace/assets/ckpts/YOLO/${YOLO_PT}.pt" \
#     epochs=300 \
#     patience=50 \
#     imgsz=640 \
#     batch=-1 \
#     cache=False \
#     rect=True \
#     name="${YOLO_PT}_foodseg103"

YOLO_PT="yolo11s-seg"

cd /workspace/data/FoodSeg103_yolo_train/binary/ && ls -l && yolo segment train \
    data=foodseg103.yaml \
    model="/workspace/assets/ckpts/YOLO/${YOLO_PT}.pt" \
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
    name="${YOLO_PT}_foodseg103_binary"