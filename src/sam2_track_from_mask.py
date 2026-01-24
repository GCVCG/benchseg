#!/usr/bin/env python3
# VOS tracking from an image mask using SAM 2's add_new_mask API.

import argparse
import os
from pathlib import Path
from tracemalloc import start
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
        description="VOS mask tracking with SAM2 using initial image masks."
    )
    parser.add_argument("--video_path", required=True,
                        help="Path to a video file OR a folder of numerically named frames (e.g., 00001.jpg).")
    parser.add_argument("--mask_dir", required=True,
                        help="Path to directory containing seed mask images.")
    parser.add_argument("--n_masks", type=int, default=1,
                        help="Number of mask files to use as seed masks (uses first N files sorted by name).")
    parser.add_argument("--frame_idx", type=int, default=0,
                        help="Index of the frame where the masks apply (default: 0).")
    parser.add_argument("--checkpoint", default="checkpoints/sam2.1_hiera_large.pt")
    parser.add_argument("--config", default="configs/sam2.1/sam2.1_hiera_l.yaml")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
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

    # Build mapping from frame index to original filename (without extension)
    # This ensures that output masks have consistent names with input frames.
    frame_names_map = {}
    if os.path.isdir(args.video_path):
        # List all image files and map them by their index
        import glob
        image_files = sorted(glob.glob(os.path.join(args.video_path, "*.jpg"))) + \
                      sorted(glob.glob(os.path.join(args.video_path, "*.png"))) + \
                      sorted(glob.glob(os.path.join(args.video_path, "*.jpeg")))
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in image_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        image_files = unique_files
        
        for idx, img_path in enumerate(image_files):
            # Extract filename without extension
            filename_with_ext = os.path.basename(img_path)
            filename_without_ext = os.path.splitext(filename_with_ext)[0]
            frame_names_map[str(idx)] = filename_without_ext

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

    # Discover mask files in the mask directory
    import glob
    mask_files = sorted(glob.glob(os.path.join(args.mask_dir, "*.png"))) + \
                 sorted(glob.glob(os.path.join(args.mask_dir, "*.jpg")))
    mask_files = mask_files[:args.n_masks]  # Take only first n_masks
    
    if not mask_files:
        raise ValueError(f"No mask files found in {args.mask_dir}")

    # Add mask prompts from the first N mask files
    for mask_path in mask_files:
        raw_mask = load_mask_image(mask_path)
        _, _, _ = predictor.add_new_mask(
            inference_state=inference_state,
            frame_idx=args.frame_idx,
            obj_id=1,
            mask=raw_mask,
        )

    # Propagate through the entire video and save out masks.
    # The iterator yields (out_frame_idx, out_obj_ids, out_masks_at_video_res).
    # out_masks shape: (num_objects, H, W), float logits/scores -> threshold >0 for binary.
    for out_frame_idx, out_obj_ids, out_masks in predictor.propagate_in_video(inference_state):
        # Save one file per object.
        for k, oid in enumerate(out_obj_ids):
            # Use mapped frame name if available, otherwise use index
            if str(out_frame_idx) in frame_names_map:
                base_name = frame_names_map[str(out_frame_idx)]
            else:
                base_name = f"{out_frame_idx:05d}"
            out_name = f"{base_name}_obj{oid}.png"
            save_binary_mask(out_masks[k], os.path.join(args.out_dir, out_name))

    print(f"Done! Wrote per-frame masks to: {args.out_dir}")


if __name__ == "__main__":
    main()
