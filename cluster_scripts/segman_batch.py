"""Batch SegMan (mmseg 0.x, Mamba) inference -> binary food foreground.

SegMan is trained on ADE20k(150)/COCO-stuff(171); we map the food class(es) to
foreground. --food_classes is a comma-separated list of class indices.
Output: {out_dir}/{stem}.png binary mask (255 = food).
"""
import argparse, glob, os, sys, time
import numpy as np
import cv2

SEG_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "baselines", "SegMan", "segmentation")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--food_classes", default="120")
    ap.add_argument("--seg_root", default=SEG_ROOT)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    sys.path.insert(0, os.path.abspath(a.seg_root))
    import torch  # noqa: F401
    import selective_scan_cuda_oflex  # noqa: F401
    from mmseg.apis import init_segmentor, inference_segmentor

    food = set(int(x) for x in a.food_classes.split(","))
    os.makedirs(a.out_dir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(a.img_dir, "*"))
                  if f.lower().endswith((".png", ".jpg", ".jpeg")))
    if a.limit:
        imgs = imgs[: a.limit]
    print(f"loading SegMan: {a.checkpoint}", flush=True)
    model = init_segmentor(a.config, a.checkpoint, device="cuda:0")
    print(f"running {len(imgs)} imgs (food classes={sorted(food)}) -> {a.out_dir}", flush=True)
    t0 = time.time()
    for i, ip in enumerate(imgs):
        seg = inference_segmentor(model, ip)[0]
        mask = np.isin(seg, list(food)).astype(np.uint8) * 255
        stem = os.path.splitext(os.path.basename(ip))[0]
        cv2.imwrite(os.path.join(a.out_dir, f"{stem}.png"), mask)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    print(f"done {len(imgs)} in {dt:.1f}s ({dt/max(len(imgs),1)*1000:.0f} ms/img) -> {a.out_dir}", flush=True)


if __name__ == "__main__":
    main()
