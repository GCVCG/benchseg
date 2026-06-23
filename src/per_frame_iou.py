"""Recompute per-frame foreground IoU from predicted vs GT masks.

Produces the *raw per-frame IoU logs* that the temporal-stability table is built
from. IoU is the binary foreground IoU (pixels > 0 are foreground), matching the
definition used by the repo's spatial evaluator ``src/eval_map.py`` so the
temporal recomputation is consistent with the published spatial metrics.

Scene/frame convention (matches unified_inference.sh's ``video_id="${name%_*}"``):
    filename  "chocolate_cake_282.png"  ->  scene "chocolate_cake", frame 282
    filename  "1_038.png"               ->  scene "1",              frame 38
i.e. scene = everything before the LAST underscore; frame = the numeric suffix.

Output CSV columns: partition, method, scene, frame, filename, iou
Rows are ordered by (scene, frame) so each scene is a temporally ordered IoU
sequence ready for the temporal metrics.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from typing import Optional

import numpy as np
from PIL import Image

IMG_EXTS = (".png", ".jpg", ".jpeg")


def _base(name: str) -> str:
    return os.path.splitext(name)[0]


def _index(directory: str) -> dict:
    out = {}
    for f in sorted(os.listdir(directory)):
        if f.lower().endswith(IMG_EXTS):
            out[_base(f)] = f
    return out


def split_scene_frame(base_filename: str):
    """Return (scene, frame_int, frame_raw) splitting on the LAST underscore."""
    if "_" not in base_filename:
        return base_filename, None, ""
    scene, frame_raw = base_filename.rsplit("_", 1)
    m = re.search(r"\d+", frame_raw)
    frame_int = int(m.group()) if m else None
    return scene, frame_int, frame_raw


def binary_iou(pred_path: Optional[str], gt_path: str) -> float:
    """Binary foreground IoU. Empty union -> 0.0 (matches eval_map.py)."""
    gt = np.array(Image.open(gt_path).convert("L"), dtype=np.uint8) > 0
    if pred_path is None:
        pred = np.zeros_like(gt)
    else:
        try:
            pred = np.array(Image.open(pred_path).convert("L"), dtype=np.uint8) > 0
        except (OSError, IOError, Image.UnidentifiedImageError):
            pred = np.zeros_like(gt)
    if pred.shape != gt.shape:
        # resize pred to gt with nearest-neighbour to be robust to size drift
        pred_img = Image.fromarray(pred.astype(np.uint8) * 255).resize(
            (gt.shape[1], gt.shape[0]), Image.NEAREST
        )
        pred = np.array(pred_img, dtype=np.uint8) > 0
    inter = int(np.count_nonzero(pred & gt))
    union = int(np.count_nonzero(pred | gt))
    return inter / union if union > 0 else 0.0


def compute_per_frame_iou(pred_dir: str, gt_dir: str, partition: str, method: str):
    """Return a list of row dicts (scene-frame ordered) of per-frame IoU."""
    preds = _index(pred_dir)
    gts = _index(gt_dir)
    rows = []
    for base, gt_file in gts.items():
        pred_file = preds.get(base)
        pred_path = os.path.join(pred_dir, pred_file) if pred_file else None
        iou = binary_iou(pred_path, os.path.join(gt_dir, gt_file))
        scene, frame_int, frame_raw = split_scene_frame(base)
        rows.append(
            {
                "partition": partition,
                "method": method,
                "scene": scene,
                "frame": frame_int if frame_int is not None else frame_raw,
                "frame_sort": frame_int if frame_int is not None else 0,
                "filename": gt_file,
                "iou": iou,
            }
        )
    rows.sort(key=lambda r: (str(r["scene"]), r["frame_sort"]))
    for r in rows:
        del r["frame_sort"]
    return rows


def write_csv(rows, out_csv: str):
    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
    fields = ["partition", "method", "scene", "frame", "filename", "iou"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out_csv


def main():
    ap = argparse.ArgumentParser(description="Recompute per-frame foreground IoU.")
    ap.add_argument("--pred_dir", required=True)
    ap.add_argument("--gt_dir", required=True)
    ap.add_argument("--partition", required=True)
    ap.add_argument("--method", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()
    rows = compute_per_frame_iou(args.pred_dir, args.gt_dir, args.partition, args.method)
    write_csv(rows, args.out_csv)
    n_scenes = len({r["scene"] for r in rows})
    print(f"{args.method}/{args.partition}: {len(rows)} frames, {n_scenes} scenes -> {args.out_csv}")


if __name__ == "__main__":
    main()
