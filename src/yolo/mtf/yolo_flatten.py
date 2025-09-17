#!/usr/bin/env python3
"""
Flatten MetaFood3D into YOLO-friendly images/ & binary-masks/
and recolour every binary mask so that the foreground pixels
carry the (grayscale) class-ID instead of plain white.

Usage:
    python yolo_flatten.py  /path/to/mtf_full   /path/to/mtf_yolo
"""
import os, sys, shutil, pathlib, cv2, numpy as np            # ▲ cv2+np
from collections import defaultdict

# ---------- CLI arguments ----------
SRC   = pathlib.Path(sys.argv[1]).resolve()
DEST  = pathlib.Path(sys.argv[2]).resolve()
(DEST/"images").mkdir(parents=True, exist_ok=True)
(DEST/"binary-masks").mkdir(parents=True, exist_ok=True)

# ---------- build a stable class-name → id map ----------
class_names = sorted([d.name for d in SRC.iterdir() if d.is_dir()])
name2id = {name: i+1 for i, name in enumerate(class_names)}   # 0=BG

# ---------- counters for a quick report ----------
stats = defaultdict(int)

IMG_EXT  = {".jpg", ".jpeg", ".png"}
MASK_EXT = {".png", ".jpg", ".jpeg"}

for cls in class_names:
    cls_dir = SRC/cls
    for ex in cls_dir.iterdir():
        img_dir, mask_dir = ex/"original", ex/"masks"
        if not (img_dir.is_dir() and mask_dir.is_dir()):
            continue                                            # incomplete

        for img_path in img_dir.iterdir():
            if img_path.suffix.lower() not in IMG_EXT:
                continue
            stem = f"{cls}_{ex.name}_{img_path.stem}"

            # ---- locate matching mask (any extension) ----
            mask_path = next((mask_dir/f"{img_path.stem}{ext}"
                              for ext in MASK_EXT
                              if (mask_dir/f"{img_path.stem}{ext}").is_file()),
                             None)
            if mask_path is None:
                stats["no_mask"] += 1
                continue

            # ---- copy RGB image unchanged ----
            dst_img = DEST/"images"/f"{stem}.jpg"
            shutil.copy(img_path, dst_img)

            # ---- recolour mask so FG → class-ID ----------  ▲
            m = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)  # 0/255
            m[m > 0] = name2id[cls]                               # set id
            dst_mask = DEST/"binary-masks"/f"{stem}.jpg"
            cv2.imwrite(str(dst_mask), m)
            stats["copied"] += 1

# ---------- final report ----------
total   = stats["copied"] + stats["no_mask"]
print(f"Flattening done – {stats['copied']} images copied,"
      f" {stats['no_mask']} skipped (no mask), {total} total.")
