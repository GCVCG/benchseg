"""Batch BiRefNet foreground segmentation over a folder.

Loads BiRefNet from HuggingFace (ZhengPeng7/BiRefNet) and, per image, predicts a
foreground probability map, thresholds at 0.5, resizes to the original size, and
saves a binary mask {stem}.png (0=bg, 255=food) for per-frame IoU.
"""
import argparse, glob, os, time
import torch
import numpy as np
from PIL import Image
from torchvision import transforms

IMG_EXTS = (".png", ".jpg", ".jpeg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--model", default="ZhengPeng7/BiRefNet")
    ap.add_argument("--reso", type=int, default=1024)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    from transformers import AutoModelForImageSegmentation
    model = AutoModelForImageSegmentation.from_pretrained(a.model, trust_remote_code=True)
    model.eval().half().cuda()
    torch.set_grad_enabled(False)

    tf = transforms.Compose([
        transforms.Resize((a.reso, a.reso)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    os.makedirs(a.out_dir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(a.img_dir, "*")) if f.lower().endswith(IMG_EXTS))
    if a.limit:
        imgs = imgs[: a.limit]
    print(f"running {len(imgs)} images -> {a.out_dir}", flush=True)
    t0 = time.time()
    for i, ip in enumerate(imgs):
        image = Image.open(ip).convert("RGB")
        W, H = image.size
        x = tf(image).unsqueeze(0).half().cuda()
        pred = model(x)[-1].sigmoid().float().cpu()[0, 0]  # (reso,reso)
        pred = transforms.functional.resize(pred.unsqueeze(0), (H, W))[0]
        mask = (pred > 0.5).numpy().astype(np.uint8) * 255
        stem = os.path.splitext(os.path.basename(ip))[0]
        Image.fromarray(mask).save(os.path.join(a.out_dir, f"{stem}.png"))
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    print(f"done {len(imgs)} imgs in {dt:.1f}s ({dt/max(len(imgs),1)*1000:.0f} ms/img)", flush=True)


if __name__ == "__main__":
    main()
