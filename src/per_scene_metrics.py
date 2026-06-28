"""Dump per-scene spatial metrics (precision/recall/f1/iou/accuracy, x100) per
method x partition, for the significance tests (R1.6 / R4.4). mAP == precision
for a binary mask. Reuses spatial_metrics.frame_metrics / split_scene.

Output: results/per_scene_metrics.csv  (method,partition,scene,precision,recall,f1,iou,accuracy)
Run on the cluster (needs the prediction + GT masks):
  python src/per_scene_metrics.py --only_methods SeTM+S3,FoodMem,SETR_MLA,...
"""
import argparse
import csv
import glob
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_metrics import frame_metrics, split_scene, index, IMG_EXTS  # noqa: E402

GT = {"N5K": "data/n5k_reordered/masks", "MTF": "data/mtf_foodMem_reordered/masks",
      "VF": "data/vf_reordered/masks", "FKIT": "data/FoodKit_dataset_reordered/masks"}
KEYS = ["precision", "recall", "f1", "iou", "accuracy"]


def per_scene(pred_dir, gt_dir):
    gts, preds = index(gt_dir), index(pred_dir)
    by_scene = defaultdict(list)
    for base, gf in gts.items():
        pf = preds.get(base)
        if pf is None:
            continue
        by_scene[split_scene(base)].append(frame_metrics(os.path.join(pred_dir, pf),
                                                         os.path.join(gt_dir, gf)))
    out = {}
    for scene, frames in by_scene.items():
        out[scene] = {k: float(np.mean([fr[k] for fr in frames])) * 100 for k in KEYS}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds_root", default="data/preds")
    ap.add_argument("--only_methods", default="")
    ap.add_argument("--out_csv", default="results/per_scene_metrics.csv")
    a = ap.parse_args()
    want = set(a.only_methods.split(",")) if a.only_methods else None

    rows = []
    for part in ["N5K", "MTF", "VF", "FKIT"]:
        gt_dir = GT[part]
        if not os.path.isdir(gt_dir):
            continue
        n_gt = len(index(gt_dir))
        for mdir in sorted(glob.glob(os.path.join(a.preds_root, part, "*"))):
            method = os.path.basename(mdir)
            if want and method not in want:
                continue
            if not os.path.isdir(mdir) or len(index(mdir)) < n_gt:
                continue
            for scene, m in per_scene(mdir, gt_dir).items():
                rows.append([method, part, scene] + [f"{m[k]:.4f}" for k in KEYS])
            print(f"{method}/{part}: {len(per_scene(mdir, gt_dir))} scenes", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_csv)), exist_ok=True)
    with open(a.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "partition", "scene"] + KEYS)
        w.writerows(rows)
    print(f"wrote {a.out_csv}: {len(rows)} rows")


if __name__ == "__main__":
    main()
