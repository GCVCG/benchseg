"""Batch SegMan (mmseg 0.x, Mamba) inference.

Two output modes:
  * binary (default): map food class(es) to a 255 foreground mask. --food_classes
    is a comma-separated list of class indices, OR the literal "gt0" meaning
    "any class > 0 is food" (used for the FoodSeg103-finetuned SegMAN, whose
    class 0 is background and 1..103 are ingredients).
  * --multiclass: save the raw class-id map (0..num_classes-1), e.g. for the
    dense FoodSeg103 mIoU/mAcc table (eval with src/foodseg103_eval.py).

Output: {out_dir}/{stem}.png
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
    ap.add_argument("--food_classes", default="120",
                    help='comma-separated class indices, or "gt0" for any class > 0')
    ap.add_argument("--multiclass", action="store_true",
                    help="save raw class-id map instead of a binary food mask")
    ap.add_argument("--seg_root", default=SEG_ROOT)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    sys.path.insert(0, os.path.abspath(a.seg_root))
    import mmcv  # noqa: E402
    import torch  # noqa: F401
    import selective_scan_cuda_oflex  # noqa: F401
    from mmseg.apis import init_segmentor, inference_segmentor

    gt0 = a.food_classes.strip().lower() == "gt0"
    food = None if (gt0 or a.multiclass) else set(int(x) for x in a.food_classes.split(","))

    # Load config and disable backbone pretrained download (the checkpoint supplies
    # all weights; the config's relative encoder path would fail at inference time).
    cfg = mmcv.Config.fromfile(a.config)
    if "pretrained" in cfg.model.get("backbone", {}):
        cfg.model.backbone.pretrained = None
    if cfg.model.get("pretrained") is not None:
        cfg.model.pretrained = None

    os.makedirs(a.out_dir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(a.img_dir, "*"))
                  if f.lower().endswith((".png", ".jpg", ".jpeg")))
    if a.limit:
        imgs = imgs[: a.limit]
    print(f"loading SegMan: {a.checkpoint}", flush=True)
    model = init_segmentor(cfg, a.checkpoint, device="cuda:0")
    mode = "multiclass" if a.multiclass else ("food>0" if gt0 else f"food={sorted(food)}")
    print(f"running {len(imgs)} imgs ({mode}) -> {a.out_dir}", flush=True)
    t0 = time.time()
    for i, ip in enumerate(imgs):
        seg = inference_segmentor(model, ip)[0]
        if a.multiclass:
            out = seg.astype(np.uint8)
        elif gt0:
            out = (seg > 0).astype(np.uint8) * 255
        else:
            out = np.isin(seg, list(food)).astype(np.uint8) * 255
        stem = os.path.splitext(os.path.basename(ip))[0]
        cv2.imwrite(os.path.join(a.out_dir, f"{stem}.png"), out)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    print(f"done {len(imgs)} in {dt:.1f}s ({dt/max(len(imgs),1)*1000:.0f} ms/img) -> {a.out_dir}", flush=True)


if __name__ == "__main__":
    main()
