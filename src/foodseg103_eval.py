"""Multi-class FoodSeg103 evaluation: mIoU + mAcc over 104 classes.

Reproduces the standard mmseg FoodSeg103 protocol used in tab:model_comparisons:
  num_classes = 104 (0 = background, 1..103 = ingredients)
  ignore_index = 255, reduce_zero_label = False
mIoU  = mean over per-class IoU (PASCAL-VOC style).
mAcc  = mean over per-class pixel accuracy (recall), NOT global pixel accuracy.
aAcc  = global pixel accuracy.

Self-contained (histogram-based) reimplementation of mmseg's
total_intersect_and_union / eval_metrics so it does not depend on the vendored
src.mmseg package (which calls the removed np.float alias). Semantics are
identical to mmseg with reduce_zero_label=False:
    mask        = label != ignore_index
    intersect   = pred == label   (restricted to mask)
    area_*[c]   = pixel counts per class c in [0, num_classes)
    IoU[c]      = area_intersect / (area_pred + area_label - area_intersect)
    Acc[c]      = area_intersect / area_label
    mIoU/mAcc   = nanmean over classes; aAcc = sum(intersect)/sum(label)

Takes a directory of predicted class-id PNGs (foodseg_batch.py or
yolo_inference.py) and the FoodSeg103 ann_dir/test ground truth, matches by file
stem, nearest-resizing predictions to GT resolution if they differ (safety net).
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image


def load_label(path, ref_shape=None):
    a = np.array(Image.open(path))
    if a.ndim == 3:
        a = a[..., 0]
    if ref_shape is not None and a.shape != ref_shape:
        a = np.array(
            Image.fromarray(a).resize((ref_shape[1], ref_shape[0]), Image.NEAREST)
        )
    return a


def hist(arr, n):
    return np.bincount(arr.astype(np.int64), minlength=n)[:n].astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred_dir", required=True)
    ap.add_argument("--gt_dir", required=True, help="FoodSeg103 ann_dir/test")
    ap.add_argument("--num_classes", type=int, default=104)
    ap.add_argument("--ignore_index", type=int, default=255)
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    C = a.num_classes

    gts = {os.path.splitext(os.path.basename(p))[0]: p
           for p in glob.glob(os.path.join(a.gt_dir, "*.png"))}
    ti = np.zeros(C)   # intersect
    tp = np.zeros(C)   # pred area
    tl = np.zeros(C)   # label area
    n, missing = 0, 0
    for stem, gp in sorted(gts.items()):
        pp = os.path.join(a.pred_dir, stem + ".png")
        if not os.path.exists(pp):
            missing += 1
            continue
        gt = load_label(gp)
        pr = load_label(pp, ref_shape=gt.shape)
        m = gt != a.ignore_index
        gt, pr = gt[m], pr[m]
        inter = pr[pr == gt]
        ti += hist(inter, C)
        tp += hist(pr, C)
        tl += hist(gt, C)
        n += 1

    if missing:
        print(f"WARNING: {missing}/{len(gts)} GT images had no prediction", flush=True)
    if n == 0:
        print("ERROR: no matched (pred, gt) pairs", flush=True)
        sys.exit(1)

    union = tp + tl - ti
    with np.errstate(divide="ignore", invalid="ignore"):
        iou = ti / union   # NaN where union == 0 (class absent in GT and pred)
        acc = ti / tl      # NaN where class absent in GT
    miou = float(np.nanmean(iou)) * 100
    macc = float(np.nanmean(acc)) * 100
    aacc = float(ti.sum() / tl.sum()) * 100
    present = int(np.sum(tl > 0))
    label = a.name or os.path.basename(a.pred_dir.rstrip("/"))
    print(f"RESULT,{label},{n},{present},{miou:.2f},{macc:.2f},{aacc:.2f}", flush=True)
    print(f"  {label}: mIoU={miou:.2f}  mAcc={macc:.2f}  aAcc={aacc:.2f} "
          f"(n={n} imgs, {present}/{C} GT classes present)", flush=True)


if __name__ == "__main__":
    main()
