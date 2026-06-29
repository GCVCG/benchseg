"""View-change-magnitude proxy (R3.8): per frame, the change in the GT foreground
mask relative to the previous frame within the same scene, vc = 1 - IoU(GT_t, GT_{t-1}).
Larger vc = larger viewpoint/appearance change between consecutive views.

Output: results/view_change_gt.csv   partition,scene,frame,vc
Joined locally with results/per_frame_iou/*/*.csv to bin method accuracy by vc.
Run on the cluster (needs GT masks).
"""
import csv
import os
import sys
from collections import defaultdict
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from per_frame_iou import split_scene_frame  # noqa: E402
from spatial_metrics import index  # noqa: E402

GT = {"N5K": "data/n5k_reordered/masks", "MTF": "data/mtf_foodMem_reordered/masks",
      "VF": "data/vf_reordered/masks", "FKIT": "data/FoodKit_dataset_reordered/masks"}


def iou(a, b):
    a = a > 0; b = b > 0
    u = (a | b).sum()
    return (a & b).sum() / u if u else 1.0


def main():
    rows = []
    for part, gt_dir in GT.items():
        if not os.path.isdir(gt_dir):
            continue
        idx = index(gt_dir)
        by_scene = defaultdict(list)
        for base in idx:
            s, f, _ = split_scene_frame(base)
            by_scene[s].append((f if f is not None else 0, base))
        for s, frames in by_scene.items():
            frames.sort(key=lambda t: t[0])
            prev = None
            for f, base in frames:
                m = np.array(Image.open(os.path.join(gt_dir, idx[base])).convert("L"))
                vc = "" if prev is None else f"{1.0 - iou(m, prev):.6f}"
                rows.append([part, s, f, vc])
                prev = m
        print(f"{part}: {len(by_scene)} scenes", flush=True)
    os.makedirs("results", exist_ok=True)
    with open("results/view_change_gt.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["partition", "scene", "frame", "vc"]); w.writerows(rows)
    print(f"wrote results/view_change_gt.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
