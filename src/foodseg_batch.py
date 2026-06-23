"""Batch foodseg (mmseg 0.x) inference: load a model ONCE, run a whole folder.

The shipped pipeline (unified_inference.sh) launches one Docker container *per
image*, reloading the model 20k+ times for FKit. This wrapper loads the model
once via init_segmentor and loops the directory, writing one class-id mask per
input frame (named to match the GT for per-frame IoU).

Output: {out_dir}/{stem}.png, single-channel class-id mask (0 = background,
>0 = food). per_frame_iou.py binarises >0 as foreground.
"""

import argparse
import glob
import os
import sys
import time

import cv2
import numpy as np

# Project root on sys.path so the vendored ``src.mmseg`` package resolves.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.mmseg.apis.inference import init_segmentor, inference_segmentor  # noqa: E402

IMG_EXTS = (".png", ".jpg", ".jpeg")


def main():
    ap = argparse.ArgumentParser(description="Batch mmseg semantic inference over a folder.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--limit", type=int, default=0, help="process only first N images (smoke test)")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    imgs = sorted(
        f for f in glob.glob(os.path.join(a.img_dir, "*"))
        if f.lower().endswith(IMG_EXTS)
    )
    if a.limit:
        imgs = imgs[: a.limit]
    print(f"loading model: {a.checkpoint}", flush=True)
    # Load config and disable backbone pretrained download (checkpoint overrides it).
    import mmcv
    cfg = mmcv.Config.fromfile(a.config)
    cfg.model.pretrained = None
    if "train_cfg" in cfg.model:
        cfg.model.train_cfg = None
    model = init_segmentor(cfg, a.checkpoint, device=a.device)
    # Single-GPU inference: convert SyncBN -> BN so no process group is required.
    try:
        from mmcv.cnn.utils import revert_sync_batchnorm
        model = revert_sync_batchnorm(model)
    except Exception as e:  # noqa: BLE001
        print(f"warn: revert_sync_batchnorm skipped ({e})", flush=True)
    print(f"running {len(imgs)} images -> {a.out_dir}", flush=True)

    t0 = time.time()
    for i, img in enumerate(imgs):
        seg = inference_segmentor(model, img)[0].astype(np.uint8)
        stem = os.path.splitext(os.path.basename(img))[0]
        cv2.imwrite(os.path.join(a.out_dir, f"{stem}.png"), seg)
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    n = max(len(imgs), 1)
    print(f"done {len(imgs)} imgs in {dt:.1f}s ({dt / n * 1000:.1f} ms/img) -> {a.out_dir}", flush=True)


if __name__ == "__main__":
    main()
