"""Stage 3 ablation orchestrator: periodic re-seeding (interval K) + fusion rule Phi.

This is a thin extension of track_pipeline.py used ONLY for the K/Phi ablation
(Reviewer 1). It never changes the default pipeline:

  * --fusion keep_propagated  (or --reseed_every <= 0) delegates verbatim to
    track_pipeline.py via subprocess, so the default output is bit-identical to
    production. That is the regression check (run once with, once without).

  * --fusion {overlap_gated,accept_fresh,union} with --reseed_every K > 0 seeds
    the tracker at frames {f0, f0+K, f0+2K, ...} instead of only at f0. The mask
    placed at each re-seed frame r>f0 is Phi(P_r, F_r), where F_r is the fresh
    per-frame segmentor mask (from --seed_preds_dir) and P_r is the propagated
    mask of the no-reset run (from --propagated_dir, i.e. the default hybrid
    preds that back the main results table). XMem2 consumes multi-frame seeds
    natively; the SAM wrappers are called with --multiseed_from_name.

The propagated masks P_r come from the already-computed default hybrid preds, so
no extra propagation pass is needed to evaluate the gate. One tracker pass per
(K, Phi) configuration is run to produce the re-seeded output.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from per_frame_iou import split_scene_frame  # noqa: E402
from fusion import fuse, reseed_frames, FUSIONS, DEFAULT_TAU  # noqa: E402

IMG_EXTS = (".png", ".jpg", ".jpeg")

# args that track_pipeline.py understands and that we pass straight through on the
# keep_propagated / no-reseed delegation path.
PASSTHROUGH = ["img_dir", "seed_preds_dir", "out_dir", "tracker", "n_seed",
               "seed_select", "seed_rng", "venv_py", "tracker_dir", "xmem_ckpt",
               "xmem_max_mid", "xmem_mem_every", "xmem_min_mid", "sam2_ckpt",
               "sam2_cfg", "tmp_root"]


def list_images(d):
    return sorted(f for f in os.listdir(d) if f.lower().endswith(IMG_EXTS))


def read_binary(path, shape=None):
    """Load a mask as bool; missing -> all-False (of `shape` if given)."""
    if path and os.path.exists(path):
        a = np.array(Image.open(path).convert("L")) > 0
        return a
    return np.zeros(shape, bool) if shape is not None else None


def build_parser():
    ap = argparse.ArgumentParser()
    # ---- identical surface to track_pipeline.py ----
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--seed_preds_dir", required=True, help="fresh per-frame segmentor masks <scene>_<frame>.png")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--tracker", required=True, choices=["xmem2", "sam2", "sam3"])
    ap.add_argument("--n_seed", type=int, default=1)
    ap.add_argument("--seed_select", choices=["first", "random"], default="first")
    ap.add_argument("--seed_rng", type=int, default=0)
    ap.add_argument("--venv_py", required=True)
    ap.add_argument("--tracker_dir", required=True)
    ap.add_argument("--xmem_ckpt", default="saves/XMem.pth")
    ap.add_argument("--xmem_max_mid", type=int, default=None)
    ap.add_argument("--xmem_mem_every", type=int, default=None)
    ap.add_argument("--xmem_min_mid", type=int, default=None)
    ap.add_argument("--sam2_ckpt", default="")
    ap.add_argument("--sam2_cfg", default="configs/sam2.1/sam2.1_hiera_l.yaml")
    ap.add_argument("--tmp_root", default="data/_track_tmp")
    # ---- new: Stage 3 ablation controls ----
    ap.add_argument("--reseed_every", type=int, default=0,
                    help="re-seed interval K in frames; <=0 means no re-seeding (default pipeline)")
    ap.add_argument("--fusion", choices=list(FUSIONS), default="keep_propagated",
                    help="fusion rule Phi at each re-seed frame (default keep_propagated == no fusion)")
    ap.add_argument("--fusion_tau", type=float, default=DEFAULT_TAU,
                    help="IoU gate threshold tau for --fusion overlap_gated")
    ap.add_argument("--propagated_dir", default="",
                    help="default (no-reset) hybrid preds <scene>_<frame>.png, used as P_r for the gate")
    return ap


def delegate_to_default(a):
    """keep_propagated / no-reseed == the untouched track_pipeline.py. Run it verbatim
    (same venv/python we were launched with) so the output is bit-identical."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "track_pipeline.py")
    cmd = [sys.executable, script]
    for k in PASSTHROUGH:
        v = getattr(a, k)
        if v is None:
            continue
        cmd += [f"--{k}", str(v)]
    print(f"[reseed] fusion={a.fusion} reseed_every={a.reseed_every} -> delegating to "
          f"track_pipeline.py (bit-identical default path)", flush=True)
    return subprocess.run(cmd).returncode


def tracker_cmd(a, fdir, sdir, odir, first_seed_idx):
    """Same command construction as track_pipeline.py, but ask the SAM wrappers to
    place each seed at the frame index encoded in its filename (multi-seed)."""
    if a.tracker == "xmem2":
        cmd = [a.venv_py, "process_video.py", "--video", os.path.abspath(fdir),
               "--masks", os.path.abspath(sdir), "--output", os.path.abspath(odir)]
        if a.xmem_max_mid is not None:
            cmd += ["--max_mid_term_frames", str(a.xmem_max_mid)]
        if a.xmem_mem_every is not None:
            cmd += ["--mem_every", str(a.xmem_mem_every)]
        if a.xmem_min_mid is not None:
            cmd += ["--min_mid_term_frames", str(a.xmem_min_mid)]
    elif a.tracker == "sam2":
        cmd = [a.venv_py, os.path.abspath(os.path.join(os.path.dirname(__file__), "sam2_track_from_mask.py")),
               "--video_path", os.path.abspath(fdir), "--mask_dir", os.path.abspath(sdir),
               "--out_dir", os.path.abspath(odir), "--checkpoint", a.sam2_ckpt, "--config", a.sam2_cfg,
               "--multiseed_from_name", "--frame_idx", str(first_seed_idx or 0)]
    else:  # sam3
        cmd = [a.venv_py, os.path.abspath(os.path.join(os.path.dirname(__file__), "sam3_track_from_mask.py")),
               "--video_path", os.path.abspath(fdir), "--mask_dir", os.path.abspath(sdir),
               "--out_dir", os.path.abspath(odir),
               "--multiseed_from_name", "--frame_idx", str(first_seed_idx or 0)]
    return cmd


def main():
    a = build_parser().parse_args()

    # default path: no fusion / no reset -> the production pipeline, verbatim.
    if a.fusion == "keep_propagated" or a.reseed_every <= 0:
        sys.exit(delegate_to_default(a))

    if not a.propagated_dir or not os.path.isdir(a.propagated_dir):
        sys.exit(f"ERROR: --fusion {a.fusion} needs --propagated_dir (default hybrid preds "
                 f"for P_r); got {a.propagated_dir!r}")

    os.makedirs(a.out_dir, exist_ok=True)
    a.tmp_root = os.path.join(a.tmp_root, a.out_dir.strip("/").replace("/", "_"))
    shutil.rmtree(a.tmp_root, ignore_errors=True)

    by_scene = defaultdict(list)
    for f in list_images(a.img_dir):
        base = os.path.splitext(f)[0]
        scene, frame, _ = split_scene_frame(base)
        by_scene[scene].append((frame if frame is not None else 0, base, f))
    for s in by_scene:
        by_scene[s].sort(key=lambda t: t[0])

    for scene, frames in by_scene.items():
        tmp = os.path.join(a.tmp_root, str(scene))
        fdir, sdir, odir = (os.path.join(tmp, x) for x in ("frames", "seeds", "out"))
        for d in (fdir, sdir, odir):
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
        idx_to_base = {}
        for i, (frame, base, f) in enumerate(frames):
            idx_to_base[i] = base
            Image.open(os.path.join(a.img_dir, f)).convert("RGB").save(os.path.join(fdir, f"{i:06d}.jpg"))

        # fresh per-frame segmentor masks F_i (only non-empty frames are candidates)
        fresh = {}   # i -> bool mask
        for i, (frame, base, f) in enumerate(frames):
            m = read_binary(os.path.join(a.seed_preds_dir, base + ".png"))
            if m is not None and m.any():
                fresh[i] = m
        if not fresh:
            print(f"scene {scene}: no non-empty seed -> all-empty masks", flush=True)
            _fill_empty(a, frames); shutil.rmtree(tmp, ignore_errors=True); continue

        order = sorted(fresh)
        f0 = order[0]
        R = reseed_frames(order, a.reseed_every, f0)

        # place a seed mask at each re-seed frame: F_f0 at f0, else Phi(P_r, F_r)
        n_written = 0
        for r in R:
            F = fresh[r]
            if r == f0:
                seedmask = (F.astype(np.uint8) * 255)
            else:
                P = read_binary(os.path.join(a.propagated_dir, idx_to_base[r] + ".png"), shape=F.shape)
                seedmask = fuse(P, F, a.fusion, a.fusion_tau)
            if seedmask.any():
                Image.fromarray(seedmask).save(os.path.join(sdir, f"{r:06d}.png"))
                n_written += 1
        first_seed_idx = f0

        if not list_images(sdir):
            print(f"scene {scene}: no usable re-seed mask -> all-empty", flush=True)
            _fill_empty(a, frames); shutil.rmtree(tmp, ignore_errors=True); continue

        cmd = tracker_cmd(a, fdir, sdir, odir, first_seed_idx)
        rr = subprocess.run(cmd, cwd=a.tracker_dir, capture_output=True, text=True)
        if rr.returncode != 0:
            print(f"scene {scene}: tracker FAILED -> all-empty\n{rr.stderr[-800:]}", flush=True)
            _fill_empty(a, frames); shutil.rmtree(tmp, ignore_errors=True); continue

        src = odir
        if os.path.isdir(os.path.join(odir, "masks")):
            src = os.path.join(odir, "masks")
        for of in list_images(src):
            m = re.search(r"\d+", of)
            if not m:
                continue
            i = int(m.group())
            base = idx_to_base.get(i)
            if base is None:
                continue
            mask = (np.array(Image.open(os.path.join(src, of)).convert("L")) > 0).astype(np.uint8) * 255
            Image.fromarray(mask).save(os.path.join(a.out_dir, base + ".png"))
        _fill_empty(a, frames)
        print(f"scene {scene}: {len(frames)} frames, re-seeded at {len(R)} frames "
              f"({n_written} masks written) [{a.fusion} K={a.reseed_every}]", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"done -> {a.out_dir} ({len(list_images(a.out_dir))} masks)", flush=True)


def _fill_empty(a, frames):
    for i, (frame, base, f) in enumerate(frames):
        op = os.path.join(a.out_dir, base + ".png")
        if not os.path.exists(op):
            sz = Image.open(os.path.join(a.img_dir, f)).size
            Image.fromarray(np.zeros((sz[1], sz[0]), np.uint8)).save(op)


if __name__ == "__main__":
    main()
