#!/usr/bin/env python3
"""
Prepare FoodSeg103 for YOLO-v8 segmentation:

• copies images into foodseg103/images/{train,test}
• converts PNG masks → YOLO polygons with Ultralytics helper
• writes foodseg103.yaml from category_id.txt
"""

import pathlib
from os import symlink
import shutil
import cv2
import numpy as np
from ultralytics.data.converter import convert_segment_masks_to_yolo_seg   # :contentReference[oaicite:0]{index=0}

# Take image and mask dirs from command line
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--image", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo_train/images")
parser.add_argument("--mask", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo_train/masks")
parser.add_argument("--dst", type=pathlib.Path, default="/workspace/data/FoodSeg103_yolo_train/multiclass")
parser.add_argument("--n_class", type=int, default=103)
args = parser.parse_args()

IMG_DIR = args.image
MASK_DIR = args.mask
DST = args.dst
N_CLASS = args.n_class

# If DST exists, remove it
if DST.exists():
    shutil.rmtree(DST)

def preprocess_binary_masks(mask_dir, n_class):
    """
    For binary segmentation (n_class = 1), convert pixel value 255 to 1.
    YOLO expects class indices 0 (background) and 1 (foreground).
    """
    if n_class != 1:
        return  # Only preprocess for binary case
    
    print(f"Preprocessing binary masks in {mask_dir} (converting 255 → 1)...")
    
    for mask_file in mask_dir.glob("**/*.png"):
        # Read mask
        mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue
            
        # Check if this is a binary mask with 255 values
        unique_vals = np.unique(mask)
        if 255 in unique_vals:
            # Convert 255 to 1 for YOLO format
            mask[mask == 255] = 1
            # Save the converted mask
            cv2.imwrite(str(mask_file), mask)

# Create label folder if it doesn't exist
(DST / "labels").mkdir(parents=True, exist_ok=True)

# Create file link to images if it doesn't exist
if not (DST / "images").exists():
    symlink(IMG_DIR, DST / "images")

# Convert all masks into yolo-format labels
splits = ["train", "test", "val"]        # use test split as validation for now
for split in splits:
    (DST / "labels" / split).mkdir(parents=True, exist_ok=True)
    
    # Preprocess masks for binary case before conversion
    split_mask_dir = MASK_DIR / split
    if split_mask_dir.exists():
        preprocess_binary_masks(split_mask_dir, N_CLASS)
    
    # Convert masks to YOLO format
    # For binary segmentation, we need classes=2 (background + 1 foreground class)
    num_classes = max(2, N_CLASS + 1) if N_CLASS == 1 else N_CLASS
    
    convert_segment_masks_to_yolo_seg(                # :contentReference[oaicite:1]{index=1}
        masks_dir=str(MASK_DIR / split),
        output_dir=str(DST / "labels" / split),
        classes=num_classes
    )
