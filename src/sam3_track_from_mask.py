#!/usr/bin/env python3
# VOS tracking from an image mask using SAM3's add_new_mask API.

import argparse
import glob
import os
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import torch
from sam3.model_builder import build_sam3_video_model


def frame_index_from_name(path: str) -> int:
    """Parse the seed frame index from a mask filename. Seeds written by
    track_pipeline are named `<idx>.png` (zero-padded); prefer the integer after
    the last underscore (`<scene>_<frame>`), else the first integer in the stem."""
    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.search(r"_(\d+)$", stem)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", stem)
    if m is None:
        raise ValueError(f"cannot parse frame index from seed mask name {stem!r}")
    return int(m.group())


def load_mask_image(mask_path: str) -> np.ndarray:
    """
    Loads a mask image and returns either:
      - binary mask (H, W) bool if image has a single foreground (nonzero),
      - or labeled mask (H, W) int64 if multiple objects (labels > 0).
    """
    im = Image.open(mask_path)
    if im.mode in ("P", "L", "I;16"):
        arr = np.array(im)
    else:
        arr = np.array(im.convert("L"))

    uniq = np.unique(arr)
    if uniq.size <= 2:
        return (arr > 0).astype(bool)
    return arr.astype(np.int64)


def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


def save_binary_mask(mask, out_path):
    """
    Accepts a torch.Tensor or numpy array with shapes (H,W), (1,H,W), or (H,W,1).
    Saves an 8-bit PNG (0/255).
    """
    if isinstance(mask, torch.Tensor):
        m = mask.detach().to("cpu")
        if m.dim() == 3 and 1 in (m.shape[0], m.shape[-1]):
            m = m[0] if m.shape[0] == 1 else m[..., 0]
        if m.dtype == torch.bool:
            mask_np = m.to(torch.uint8).mul(255).numpy()
        else:
            mask_np = (m > 0).to(torch.uint8).mul(255).numpy()
    else:
        m = mask
        if m.ndim == 3 and 1 in (m.shape[0], m.shape[-1]):
            m = m[0] if m.shape[0] == 1 else m[..., 0]
        mask_np = (m > 0).astype(np.uint8) * 255

    Image.fromarray(mask_np).save(out_path)


def main():
    parser = argparse.ArgumentParser(
        description="VOS mask tracking with SAM3 using initial image masks."
    )
    parser.add_argument("--video_path", required=True,
                        help="Folder of JPEG frames.")
    parser.add_argument("--mask_dir", required=True,
                        help="Directory containing seed mask images.")
    parser.add_argument("--n_masks", type=int, default=1,
                        help="Number of seed mask files to use (first N sorted by name).")
    parser.add_argument("--frame_idx", type=int, default=0,
                        help="Frame index where the seed masks apply (default: 0).")
    parser.add_argument("--multiseed_from_name", action="store_true",
                        help="Place each seed mask at the frame index parsed from its filename "
                             "(multi-frame re-seeding), using ALL masks in --mask_dir, instead of "
                             "the first --n_masks all at --frame_idx. Default off keeps legacy behaviour.")
    parser.add_argument("--checkpoint", default=None,
                        help="Path to a SAM3 checkpoint .pt file. "
                             "If omitted, downloads sam3.pt from HuggingFace.")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--out_dir", default="vos_masks",
                        help="Where to save per-frame masks.")
    parser.add_argument("--offload_video_to_cpu", action="store_true")
    parser.add_argument("--offload_state_to_cpu", action="store_true")
    parser.add_argument("--async_loading_frames", action="store_true")

    args = parser.parse_args()
    ensure_dir(args.out_dir)

    # Collect input JPEG frames sorted by filename; build idx -> original stem map.
    raw_files = (
        glob.glob(os.path.join(args.video_path, "*.jpg")) +
        glob.glob(os.path.join(args.video_path, "*.jpeg")) +
        glob.glob(os.path.join(args.video_path, "*.JPG")) +
        glob.glob(os.path.join(args.video_path, "*.JPEG"))
    )
    image_files = sorted(set(raw_files))
    frame_names_map = {
        idx: os.path.splitext(os.path.basename(f))[0]
        for idx, f in enumerate(image_files)
    }

    # SAM3's internal loader sorts frames as int(stem), so filenames must be purely
    # numeric. Create a temp dir with numeric symlinks pointing at the originals.
    temp_dir = tempfile.mkdtemp(prefix="sam3_frames_")
    try:
        for idx, img_path in enumerate(image_files):
            ext = os.path.splitext(img_path)[1]
            os.symlink(os.path.abspath(img_path), os.path.join(temp_dir, f"{idx:05d}{ext}"))

        sam3_model = build_sam3_video_model(
            checkpoint_path=args.checkpoint,
            load_from_HF=True,
            device=args.device,
        )
        predictor = sam3_model.tracker
        predictor.backbone = sam3_model.detector.backbone

        inference_state = predictor.init_state(
            video_path=temp_dir,
            offload_video_to_cpu=args.offload_video_to_cpu,
            offload_state_to_cpu=args.offload_state_to_cpu,
            async_loading_frames=args.async_loading_frames,
        )

        mask_files = sorted(
            glob.glob(os.path.join(args.mask_dir, "*.png")) +
            glob.glob(os.path.join(args.mask_dir, "*.jpg"))
        )
        if not args.multiseed_from_name:
            mask_files = mask_files[:args.n_masks]

        if not mask_files:
            raise ValueError(f"No mask files found in {args.mask_dir}")

        for mask_path in mask_files:
            raw_mask = load_mask_image(mask_path)
            # SAM3's add_new_mask requires a 2D torch.Tensor.
            mask_tensor = torch.from_numpy(raw_mask.astype(np.float32))
            seed_idx = frame_index_from_name(mask_path) if args.multiseed_from_name else args.frame_idx
            predictor.add_new_mask(
                inference_state=inference_state,
                frame_idx=seed_idx,
                obj_id=1,
                mask=mask_tensor,
            )

        for frame_idx, obj_ids, low_res_masks, video_res_masks, obj_scores in predictor.propagate_in_video(
            inference_state,
            start_frame_idx=0,
            max_frame_num_to_track=None,
            reverse=False,
            propagate_preflight=True,
        ):
            for k, oid in enumerate(obj_ids):
                base_name = frame_names_map.get(frame_idx, f"{frame_idx:05d}")
                save_binary_mask(
                    video_res_masks[k],
                    os.path.join(args.out_dir, f"{base_name}_obj{oid}.png"),
                )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"Done! Wrote per-frame masks to: {args.out_dir}")


if __name__ == "__main__":
    main()
