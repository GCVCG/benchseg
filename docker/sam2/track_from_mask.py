#!/usr/bin/env python3
# VOS tracking from an image mask using SAM 2's add_new_mask API.

import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

import torch
from sam2.build_sam import build_sam2_video_predictor


def load_mask_image(mask_path: str) -> np.ndarray:
    """
    Loads a mask image and returns either:
      - binary mask (H, W) bool if image has a single foreground (nonzero),
      - or labeled mask (H, W) int64 if multiple objects (labels > 0).
    Accepted inputs:
      - single-channel grayscale (uint8/bool) where >0 is foreground
      - palette PNGs where values are class ids
      - RGB will be treated as a single binary mask via luminance (>0)
    """
    im = Image.open(mask_path)
    # If palette or L mode -> single channel array of ids/intensity
    if im.mode in ("P", "L", "I;16"):
        arr = np.array(im)
    else:
        # e.g., RGB: collapse to grayscale magnitude
        arr = np.array(im.convert("L"))

    # If there are only 0/1-like values, return boolean.
    uniq = np.unique(arr)
    if uniq.size <= 2:
        return (arr > 0).astype(bool)

    # Otherwise treat as labeled mask: labels>0 are objects. Cast to int64 for safety.
    return arr.astype(np.int64)


def labeled_to_instances(label_mask: np.ndarray) -> Dict[int, np.ndarray]:
    """
    Splits a labeled mask into {obj_id: binary_mask}. Skips 0 (background).
    obj_id uses the label value by default.
    """
    instances = {}
    labels = np.unique(label_mask)
    labels = labels[labels > 0]
    for lab in labels:
        instances[int(lab)] = (label_mask == lab)
    return instances


def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)



def save_binary_mask(mask, out_path):
    """
    Accepts a torch.Tensor or numpy array with shapes (H,W), (1,H,W), or (H,W,1).
    Saves an 8-bit PNG (0/255).
    """
    if isinstance(mask, torch.Tensor):
        m = mask.detach().to("cpu")
        # squeeze singleton channel anywhere it appears
        if m.dim() == 3 and 1 in (m.shape[0], m.shape[-1]):
            if m.shape[0] == 1:  # (1,H,W) -> (H,W)
                m = m[0]
            elif m.shape[-1] == 1:  # (H,W,1) -> (H,W)
                m = m[..., 0]
        # binarize at 0 (logits>0 ~= prob>0.5)
        mask_np = (m > 0).to(torch.uint8).mul(255).numpy()
    else:
        m = mask
        if m.ndim == 3 and 1 in (m.shape[0], m.shape[-1]):
            if m.shape[0] == 1:
                m = m[0]
            elif m.shape[-1] == 1:
                m = m[..., 0]
        mask_np = ((m > 0).astype(np.uint8) * 255)

    Image.fromarray(mask_np).save(out_path)


def main():
    parser = argparse.ArgumentParser(
        description="VOS mask tracking with SAM2 using an initial image mask."
    )
    parser.add_argument("--video_path", required=True,
                        help="Path to a video file OR a folder of numerically named frames (e.g., 00001.jpg).")
    parser.add_argument("--mask_path", required=True,
                        help="Path to a binary or labeled mask image for the selected frame.")
    parser.add_argument("--frame_idx", type=int, default=0,
                        help="Index of the frame where the mask applies (default: 0).")
    parser.add_argument("--checkpoint", default="checkpoints/sam2.1_hiera_large.pt")
    parser.add_argument("--config", default="configs/sam2.1/sam2.1_hiera_l.yaml")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--obj_id", type=int, default=None,
                        help="Optional object id to use when mask is binary. Ignored for labeled masks.")
    parser.add_argument("--out_dir", default="vos_masks",
                        help="Where to save per-frame masks.")
    parser.add_argument("--vos_optimized", action="store_true",
                        help="Enable model compilation / VOS optimizations when supported.")
    parser.add_argument("--offload_video_to_cpu", action="store_true",
                        help="Lower VRAM by keeping frames on CPU (slight speed hit).")
    parser.add_argument("--offload_state_to_cpu", action="store_true",
                        help="Lower VRAM by keeping state on CPU (slower).")
    parser.add_argument("--async_loading_frames", action="store_true")

    args = parser.parse_args()
    ensure_dir(args.out_dir)

    # Build predictor just like in the notebook.
    predictor = build_sam2_video_predictor(
        args.config,
        args.checkpoint,
        device=args.device,
        vos_optimized=args.vos_optimized,  # safe to leave False if your stack isn't up to date
    )

    # Initialize video state (folder-of-frames OR video file path both work with SAM2's loader).
    inference_state = predictor.init_state(
        video_path=args.video_path,
        offload_video_to_cpu=args.offload_video_to_cpu,
        offload_state_to_cpu=args.offload_state_to_cpu,
        async_loading_frames=args.async_loading_frames,
    )

    # Load mask image.
    raw_mask = load_mask_image(args.mask_path)

    # Add mask prompt(s).
    if raw_mask.dtype == bool:
        # Single binary mask
        obj_id = args.obj_id if args.obj_id is not None else 1
        _, _, _ = predictor.add_new_mask(
            inference_state=inference_state,
            frame_idx=args.frame_idx,
            obj_id=obj_id,
            mask=raw_mask,
        )
        obj_ids = [obj_id]
    else:
        # Labeled mask -> one object per label (>0)
        insts = labeled_to_instances(raw_mask)
        obj_ids = sorted(list(insts.keys()))
        if len(obj_ids) == 0:
            raise ValueError("No objects found in labeled mask (>0 labels).")
        for oid in obj_ids:
            _, _, _ = predictor.add_new_mask(
                inference_state=inference_state,
                frame_idx=args.frame_idx,
                obj_id=int(oid),
                mask=insts[oid],
            )

    # Propagate through the entire video and save out masks.
    # The iterator yields (out_frame_idx, out_obj_ids, out_masks_at_video_res).
    # out_masks shape: (num_objects, H, W), float logits/scores -> threshold >0 for binary.
    for out_frame_idx, out_obj_ids, out_masks in predictor.propagate_in_video(inference_state):
        # Save one file per object.
        for k, oid in enumerate(out_obj_ids):
            out_name = f"{out_frame_idx:05d}_obj{oid}.png"
            save_binary_mask(out_masks[k], os.path.join(args.out_dir, out_name))

    print(f"Done! Wrote per-frame masks to: {args.out_dir}")


if __name__ == "__main__":
    main()
