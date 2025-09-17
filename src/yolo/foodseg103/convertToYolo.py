#!/usr/bin/env python3
"""
Prepare FoodSeg103 for YOLO-v8 segmentation:

• copies images into foodseg103/images/{train,test}
• converts PNG masks → YOLO polygons with Ultralytics helper
• writes foodseg103.yaml from category_id.txt
"""

import pathlib, shutil, yaml
from ultralytics.data.converter import convert_segment_masks_to_yolo_seg   # :contentReference[oaicite:0]{index=0}
from tqdm import tqdm

# --------------------------------------------------------------------------------
# 1.  CONFIGURE PATHS
# --------------------------------------------------------------------------------
SRC = pathlib.Path("/workspace/data/FoodSeg103/Images")        # root that contains img_dir/ and ann_dir/
TXT = pathlib.Path("/workspace/data/FoodSeg103/category_id.txt")  # class-id ↔︎ name mapping file
DST = pathlib.Path("/workspace/data/FoodSeg103_yolo")                   # output root that YOLO will read

# --------------------------------------------------------------------------------
# 2.  COPY IMAGES AND CONVERT MASKS
# --------------------------------------------------------------------------------
splits = ["train", "test"]        # use test split as validation for now
for split in splits:
    (DST / "images" / split).mkdir(parents=True, exist_ok=True)
    (DST / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 2-A copy images ----------------------------------------------------------------
    for img_file in tqdm((SRC / "img_dir" / split).glob("*.*"),
                         desc=f"Copying {split} images"):
        shutil.copy2(img_file, DST / "images" / split / img_file.name)

    # 2-B convert masks --------------------------------------------------------------
    convert_segment_masks_to_yolo_seg(                # :contentReference[oaicite:1]{index=1}
        masks_dir=str(SRC / "ann_dir" / split),
        output_dir=str(DST / "labels" / split),
        classes=103                                   # FoodSeg103 has 103 foreground classes
    )

# --------------------------------------------------------------------------------
# 3.  BUILD THE names LIST AND WRITE YAML
# --------------------------------------------------------------------------------
names = []
with open(TXT, "r", encoding="utf-8") as f:          # Kaggle preview shows id<tab>name format :contentReference[oaicite:2]{index=2}
    for line in f:
        if line.strip():
            _id, cls = line.rstrip("\n").split("\t", 1)
            names.append(cls)

yaml_dict = {
    "path": str(DST),        # root for Ultralytics
    "train": "images/train",
    "val": "images/test",
    "test": "images/test",
    "names": names           # list form is accepted since YOLO v8.1+ :contentReference[oaicite:3]{index=3}
}

yaml_path = DST / "foodseg103.yaml"
with open(yaml_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(yaml_dict, f, sort_keys=False, allow_unicode=True)   # :contentReference[oaicite:4]{index=4}

print(f"\n✓ Dataset ready – YAML written to {yaml_path.resolve()}")
