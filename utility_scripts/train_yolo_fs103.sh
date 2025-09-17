#!/bin/bash

YOLO_PT="yolo11s-seg"

# Retrain YOLO model with rectangular training to preserve aspect ratios
cd /workspace/data/FoodSeg103_yolo/ && yolo segment train \
    data=foodseg103.yaml \
    model="/workspace/assets/ckpts/YOLO/${YOLO_PT}.pt" \
    epochs=300 \
    patience=50 \
    imgsz=640 \
    batch=-1 \
    cache=False \
    rect=True \
    name="${YOLO_PT}_foodseg103"
