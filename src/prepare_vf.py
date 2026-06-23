"""Flatten the nested V&F dataset into the standard <scene>_<frame> layout.

Source layout:
    V&F/<class>/<capture>/imgs/<n>.jpg        (input frames)
                          gt_masks/<n>.png     (binary GT, subset of frames)
                          masks_*/...          (IGNORED per instruction)

Output (drop-in like the other partitions):
    out/images/<scene>_<n>.jpg
    out/masks/<scene>_<n>.png

Scene = class name (one capture per class here). Only frames with a GT mask are
emitted, so images and masks align and the temporal metrics run over adjacent
*annotated* frames (matching the manuscript's evaluation-on-annotated-frames).
"""

import argparse
import os
import shutil
import glob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vf_root", required=True, help="path to the V&F directory")
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    img_out = os.path.join(args.out_dir, "images")
    mask_out = os.path.join(args.out_dir, "masks")
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(mask_out, exist_ok=True)

    classes = sorted(d for d in os.listdir(args.vf_root)
                     if os.path.isdir(os.path.join(args.vf_root, d)))
    total_frames = 0
    summary = []
    for cls in classes:
        cls_dir = os.path.join(args.vf_root, cls)
        captures = sorted(d for d in os.listdir(cls_dir)
                          if os.path.isdir(os.path.join(cls_dir, d)))
        cls_frames = 0
        for cap in captures:
            cap_dir = os.path.join(cls_dir, cap)
            gt_dir = os.path.join(cap_dir, "gt_masks")
            img_dir = os.path.join(cap_dir, "imgs")
            if not (os.path.isdir(gt_dir) and os.path.isdir(img_dir)):
                continue
            # scene name: class, or class_capture if a class has >1 capture
            scene = cls if len(captures) == 1 else f"{cls}-{cap}"
            for gt_path in sorted(glob.glob(os.path.join(gt_dir, "*.png"))):
                n = os.path.splitext(os.path.basename(gt_path))[0]
                # find the matching input frame (try common extensions)
                img_src = None
                for ext in (".jpg", ".jpeg", ".png"):
                    cand = os.path.join(img_dir, n + ext)
                    if os.path.exists(cand):
                        img_src = cand
                        break
                if img_src is None:
                    continue
                img_ext = os.path.splitext(img_src)[1]
                shutil.copy2(img_src, os.path.join(img_out, f"{scene}_{n}{img_ext}"))
                shutil.copy2(gt_path, os.path.join(mask_out, f"{scene}_{n}.png"))
                cls_frames += 1
        total_frames += cls_frames
        summary.append((cls, cls_frames))

    print(f"V&F flattened -> {args.out_dir}")
    for cls, n in summary:
        print(f"  {cls}: {n} annotated frames")
    print(f"  TOTAL: {total_frames} frames across {len(classes)} scenes")


if __name__ == "__main__":
    main()
