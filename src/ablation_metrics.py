"""Compute spatial (mean+/-std across scenes) AND per-frame IoU for the M-ablation
prediction dirs in ONE mask-loading pass. Used to rebuild tab:masks_ablation,
tab:masks_ablation_additional, tab:temporal_grouped_method (first vs random seeding).

Outputs (append-safe per partition):
  results/ablation_spatial.csv   method,partition,precision,recall,f1,iou,accuracy,mAP,(+_std),n_scenes
  results/ablation_per_frame_iou/<partition>/<method>.csv  partition,method,scene,frame,iou
Run per partition on ladon (CPU):
  python src/ablation_metrics.py --only_part FKIT --only_methods Y+X2_M3,Y+X2_M3_r0,...
"""
import argparse
import csv
import glob
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_metrics import frame_metrics, split_scene, index  # noqa: E402
from per_frame_iou import split_scene_frame  # noqa: E402

GT = {"N5K": "data/n5k_reordered/masks", "MTF": "data/mtf_foodMem_reordered/masks",
      "VF": "data/vf_reordered/masks", "FKIT": "data/FoodKit_dataset_reordered/masks"}
KEYS = ["precision", "recall", "f1", "iou", "accuracy"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds_root", default="data/preds")
    ap.add_argument("--only_part", required=True)
    ap.add_argument("--only_methods", default="", help="comma list of method dir names")
    ap.add_argument("--out_spatial", default="results/ablation_spatial.csv")
    ap.add_argument("--iou_root", default="results/ablation_per_frame_iou")
    a = ap.parse_args()
    part = a.only_part
    want = set(a.only_methods.split(",")) if a.only_methods else None
    gt_dir = GT[part]
    gts = index(gt_dir)
    n_gt = len(gts)

    spatial_rows = []
    for mdir in sorted(glob.glob(os.path.join(a.preds_root, part, "*"))):
        method = os.path.basename(mdir)
        if want and method not in want:
            continue
        preds = index(mdir)
        if len(preds) < n_gt:
            continue
        per_scene_metric = defaultdict(list)   # scene -> [frame metric dicts]
        iou_rows = []
        for base, gf in gts.items():
            pf = preds.get(base)
            if pf is None:
                continue
            m = frame_metrics(os.path.join(mdir, pf), os.path.join(gt_dir, gf))
            scene, frame, _ = split_scene_frame(base)
            per_scene_metric[scene].append(m)
            iou_rows.append([part, method, scene, frame if frame is not None else 0, f"{m['iou']:.6f}"])
        # per-scene mean then macro mean+/-std across scenes
        scene_means = {k: [float(np.mean([fr[k] for fr in frames])) for frames in per_scene_metric.values()]
                       for k in KEYS}
        row = {"method": method, "partition": part, "n_scenes": len(per_scene_metric)}
        for k in KEYS:
            arr = np.array(scene_means[k]) * 100
            row[k] = f"{arr.mean():.4f}"
            row[k + "_std"] = f"{arr.std(ddof=1) if len(arr) > 1 else 0.0:.4f}"
        row["mAP"] = row["precision"]
        spatial_rows.append(row)
        # write per-frame IoU
        iou_dir = os.path.join(a.iou_root, part)
        os.makedirs(iou_dir, exist_ok=True)
        with open(os.path.join(iou_dir, method + ".csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["partition", "method", "scene", "frame", "iou"])
            iou_rows.sort(key=lambda r: (str(r[2]), r[3]))
            w.writerows(iou_rows)
        print(f"{method}/{part}: {len(per_scene_metric)} scenes, mAP={row['mAP']}", flush=True)

    # append spatial rows (one file shared across partition jobs)
    hdr = ["method", "partition"] + sum([[k, k + "_std"] for k in KEYS], []) + ["mAP", "n_scenes"]
    exists = os.path.exists(a.out_spatial)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_spatial)), exist_ok=True)
    with open(a.out_spatial, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        if not exists:
            w.writeheader()
        for r in spatial_rows:
            w.writerow(r)
    print(f"appended {len(spatial_rows)} spatial rows -> {a.out_spatial}")


if __name__ == "__main__":
    main()
