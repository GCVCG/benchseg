#!/bin/bash

# Extract and reorganize FoodSeg103 dataset into YOLO training format
# Usage: ./reorganize_foodseg103.sh <path_to_zip>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path_to_zip>"
    exit 1
fi

ZIP_FILE="$1"

if [ ! -f "$ZIP_FILE" ]; then
    echo "Error: Zip file not found: $ZIP_FILE"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
DATA_DIR="${PROJECT_ROOT}/data"
DEST_DIR="${DATA_DIR}/FoodSeg103_yolo_train"
TEMP_DIR="${DATA_DIR}/foodseg103_temp"

echo "Extracting FoodSeg103 dataset..."
mkdir -p "$TEMP_DIR"
unzip -q "$ZIP_FILE" -d "$TEMP_DIR"

echo "Reorganizing into YOLO format..."
mkdir -p "$DEST_DIR/images"
mkdir -p "$DEST_DIR/masks"

# Copy all images and masks to root directories (will be split later)
cp "$TEMP_DIR/Images/img_dir/train"/*.jpg "$DEST_DIR/images/" 2>/dev/null || true
cp "$TEMP_DIR/Images/ann_dir/train"/*.png "$DEST_DIR/masks/" 2>/dev/null || true
cp "$TEMP_DIR/Images/img_dir/test"/*.jpg "$DEST_DIR/images/" 2>/dev/null || true
cp "$TEMP_DIR/Images/ann_dir/test"/*.png "$DEST_DIR/masks/" 2>/dev/null || true

# Extract category_id.txt before cleanup
CATEGORY_FILE="$TEMP_DIR/category_id.txt"

# Copy category file to destination
cp "$CATEGORY_FILE" "$DEST_DIR/category_id.txt" 2>/dev/null || true

rm -rf "$TEMP_DIR"

echo "Splitting dataset into train/val/test (70/15/15)..."
python3 << EOF
from pathlib import Path
from sklearn.model_selection import train_test_split
import shutil

root = Path("$DEST_DIR")

imgs = sorted((root/"images").glob("*.jpg"))

print(f"Total images: {len(imgs)}")

train, tmp = train_test_split(imgs, test_size=0.3, random_state=42)
val, test = train_test_split(tmp, test_size=0.5, random_state=42)

print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

for split, files in zip(("train","val","test"), (train,val,test)):
    (root/f"images/{split}").mkdir(parents=True, exist_ok=True)
    (root/f"masks/{split}").mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {split} split with {len(files)} files...")
    
    for f in files:
        # Copy images
        img_dst = root/f"images/{split}"/f.name
        shutil.copy2(f, img_dst)
        
        # Copy corresponding masks (convert .jpg to .png extension)
        mask_name = f.stem + ".png"  # Replace .jpg with .png
        mask_src = root/"masks"/mask_name
        mask_dst = root/f"masks/{split}"/mask_name
        
        if mask_src.exists():
            shutil.copy2(mask_src, mask_dst)

# Remove original images and masks from root
import os
for f in imgs:
    f.unlink()
for mask in (root/"masks").glob("*.png"):
    mask.unlink()

print("Dataset splitting completed!")
EOF

echo "Generating foodseg103.yaml..."
python3 << EOF
import yaml
import sys
import os

# Read category_id.txt to get class names
categories = {}
category_path = "$DEST_DIR/category_id.txt"
try:
    with open(category_path, 'r') as f:
        for line in f:
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                idx, name = parts
                categories[int(idx)] = name
except FileNotFoundError:
    print("Warning: category_id.txt not found, using default class names")
    categories = {i: f"class_{i}" for i in range(104)}

# Generate YAML
yaml_data = {
    'path': '/workspace/data/FoodSeg103_yolo_train',
    'train': 'images/train',
    'val': 'images/val',
    'test': 'images/test',
    'nc': len(categories),
    'names': categories
}

yaml_path = '$DEST_DIR/foodseg103.yaml'
with open(yaml_path, 'w') as f:
    yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

print(f"✓ Generated foodseg103.yaml with {len(categories)} classes")
EOF

echo "Converting masks to YOLO format..."
python3 "$PROJECT_ROOT/src/yolo/foodseg103/convertToYolo.py" \
    --image "$DEST_DIR/images" \
    --mask "$DEST_DIR/masks" \
    --dst "$DEST_DIR" \
    --n_class 104

echo "✓ Dataset ready at: $DEST_DIR"
