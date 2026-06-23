"""Spatial segmentation metrics (Precision, Recall, F1, IoU, Accuracy, mAP) per
method x partition, aggregated mean+/-std across scenes (matching the manuscript's
spatial tables tab:results / tab:results_precision_f1_IoU).

Binary foreground (pixels > 0). Per frame we compute TP/FP/FN/TN -> the metrics;
per scene we average; then macro-average across scenes (mean) with the across-scene
std as the +/- value. mAP is reported as the per-frame foreground Average Precision
(torchmetrics-free: for a binary prediction AP reduces to precision; we also emit
mIoU which some tables label mAP -- both are provided so the right one can be picked).
"""
import argparse, csv, glob, os, re
from collections import defaultdict
import numpy as np
from PIL import Image

IMG_EXTS = (".png", ".jpg", ".jpeg")


def split_scene(base):
    return base.rsplit("_", 1)[0] if "_" in base else base


def frame_metrics(pred_path, gt_path):
    gt = np.array(Image.open(gt_path).convert("L"), dtype=np.uint8) > 0
    if pred_path and os.path.exists(pred_path):
        try:
            pred = np.array(Image.open(pred_path).convert("L"), dtype=np.uint8) > 0
        except Exception:
            pred = np.zeros_like(gt)
    else:
        pred = np.zeros_like(gt)
    if pred.shape != gt.shape:
        pim = Image.fromarray(pred.astype(np.uint8) * 255).resize((gt.shape[1], gt.shape[0]), Image.NEAREST)
        pred = np.array(pim, dtype=np.uint8) > 0
    tp = int(np.count_nonzero(pred & gt)); fp = int(np.count_nonzero(pred & ~gt))
    fn = int(np.count_nonzero(~pred & gt)); tn = int(np.count_nonzero(~pred & ~gt))
    prec = tp / (tp + fp) if (tp + fp) else (1.0 if fn == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / (tp + tn + fp + fn)
    return dict(precision=prec, recall=rec, f1=f1, iou=iou, accuracy=acc)


def index(d):
    return {os.path.splitext(f)[0]: f for f in os.listdir(d) if f.lower().endswith(IMG_EXTS)}


def compute(pred_dir, gt_dir):
    gts, preds = index(gt_dir), index(pred_dir)
    per_scene = defaultdict(list)
    for base, gf in gts.items():
        pf = preds.get(base)
        m = frame_metrics(os.path.join(pred_dir, pf) if pf else None, os.path.join(gt_dir, gf))
        per_scene[split_scene(base)].append(m)
    keys = ["precision", "recall", "f1", "iou", "accuracy"]
    scene_means = {k: [] for k in keys}
    for scene, frames in per_scene.items():
        for k in keys:
            scene_means[k].append(float(np.mean([fr[k] for fr in frames])))
    out = {}
    for k in keys:
        vals = np.array(scene_means[k]) * 100
        out[k] = round(float(vals.mean()), 2)
        out[k + "_std"] = round(float(vals.std(ddof=1)) if len(vals) > 1 else 0.0, 2)
    out["mAP"] = out["precision"]      # AP of a binary mask == precision
    out["mIoU"] = out["iou"]
    out["n_scenes"] = len(per_scene)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds_root", default="data/preds")
    ap.add_argument("--out_csv", default="results/spatial_metrics.csv")
    ap.add_argument("--only_method", default=None)
    ap.add_argument("--only_part", default=None)
    a = ap.parse_args()
    GT = {"N5K": "data/n5k_reordered/masks", "MTF": "data/mtf_foodMem_reordered/masks",
          "VF": "data/vf_reordered/masks", "FKIT": "data/FoodKit_dataset_reordered/masks"}
    rows = []
    for part in (["N5K", "MTF", "VF", "FKIT"] if not a.only_part else [a.only_part]):
        gt_dir = GT[part]
        if not os.path.isdir(gt_dir):
            continue
        n_gt = len(index(gt_dir))
        for mdir in sorted(glob.glob(os.path.join(a.preds_root, part, "*"))):
            method = os.path.basename(mdir)
            if a.only_method and method != a.only_method:
                continue
            if not os.path.isdir(mdir) or len(index(mdir)) < n_gt:
                continue
            m = compute(mdir, gt_dir)
            m.update(method=method, partition=part)
            rows.append(m)
            print(f"{method}/{part}: P={m['precision']} R={m['recall']} F1={m['f1']} IoU={m['iou']} Acc={m['accuracy']} (mAP~{m['mAP']})", flush=True)
    if rows:
        cols = ["method", "partition", "mAP", "recall", "precision", "f1", "iou", "accuracy",
                "precision_std", "recall_std", "f1_std", "iou_std", "accuracy_std", "n_scenes"]
        os.makedirs(os.path.dirname(os.path.abspath(a.out_csv)), exist_ok=True)
        with open(a.out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
        print(f"-> {a.out_csv} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
