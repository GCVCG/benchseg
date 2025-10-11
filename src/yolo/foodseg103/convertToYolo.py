#!/usr/bin/env python3
"""
Prepare FoodSeg103 for YOLO-v8 segmentation:

• copies images into foodseg103/images/{train,test}
• converts PNG masks → YOLO polygons with Ultralytics helper
• writes foodseg103.yaml from category_id.txt
"""

import pathlib, shutil, yaml
from os import symlink
from ultralytics.data.converter import convert_segment_masks_to_yolo_seg   # :contentReference[oaicite:0]{index=0}
from tqdm import tqdm

# Take image and mask dirs from command line
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--image", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo_train/images")
parser.add_argument("--mask", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo_train/masks")
parser.add_argument("--dst", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo/multiclass")
parser.add_argument("--n_class", type=int, default=104)
args = parser.parse_args()

IMG_DIR = args.image
MASK_DIR = args.mask
DST = args.dst
N_CLASS = args.n_class

# Create label folder if it doesn't exist
(DST / "labels").mkdir(parents=True, exist_ok=True)

# Create file link to images if it doesn't exist
if not (DST / "images").exists():
    symlink(IMG_DIR, DST / "images")

# Convert all masks into yolo-format labels
splits = ["train", "test", "val"]        # use test split as validation for now
for split in splits:
    (DST / "labels" / split).mkdir(parents=True, exist_ok=True)
    convert_segment_masks_to_yolo_seg(                # :contentReference[oaicite:1]{index=1}
        masks_dir=str(MASK_DIR / split),
        output_dir=str(DST / "labels" / split),
        classes=2            # FoodSeg103 has 104 classes (103 foreground + 1 background)
    )
