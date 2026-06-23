"""Per-scene DEVA (text=food) runner. For each scene, runs DEVA's
demo_with_text.py (GroundingDINO 'food' detection + SAM + DEVA propagation) over
the scene's frames and writes a binary foreground mask <scene>_<frame>.png.
"""
import argparse, glob, os, re, shutil, subprocess, sys
from collections import defaultdict
import numpy as np
from PIL import Image

IMG_EXTS = (".png", ".jpg", ".jpeg")


def split_scene_frame(base):
    if "_" not in base:
        return base, 0
    s, fr = base.rsplit("_", 1)
    m = re.search(r"\d+", fr)
    return s, (int(m.group()) if m else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--deva_dir", required=True)
    ap.add_argument("--venv_py", required=True)
    ap.add_argument("--prompt", default="food")
    ap.add_argument("--detection_every", type=int, default=5)
    ap.add_argument("--tmp_root", default="data/_deva_tmp")
    ap.add_argument("--limit_scenes", type=int, default=0)
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    a.tmp_root = os.path.join(a.tmp_root, a.out_dir.strip("/").replace("/", "_"))
    shutil.rmtree(a.tmp_root, ignore_errors=True)

    by_scene = defaultdict(list)
    for f in sorted(os.listdir(a.img_dir)):
        if f.lower().endswith(IMG_EXTS):
            base = os.path.splitext(f)[0]
            s, fr = split_scene_frame(base)
            by_scene[s].append((fr, base, f))
    for s in by_scene:
        by_scene[s].sort()

    scenes = list(by_scene.items())
    if a.limit_scenes:
        scenes = scenes[: a.limit_scenes]

    def fill_empty(frames):
        for i, (fr, base, f) in enumerate(frames):
            op = os.path.join(a.out_dir, base + ".png")
            if not os.path.exists(op):
                sz = Image.open(os.path.join(a.img_dir, f)).size
                Image.fromarray(np.zeros((sz[1], sz[0]), np.uint8)).save(op)

    for scene, frames in scenes:
        tmp = os.path.join(a.tmp_root, str(scene))
        fdir, odir = os.path.join(tmp, "frames"), os.path.join(tmp, "out")
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(fdir)
        idx_to_base = {}
        for i, (fr, base, f) in enumerate(frames):
            idx_to_base[i] = base
            Image.open(os.path.join(a.img_dir, f)).convert("RGB").save(os.path.join(fdir, f"{i:06d}.jpg"))
        cmd = [a.venv_py, "demo/demo_with_text.py",
               "--img_path", os.path.abspath(fdir),
               "--prompt", a.prompt,
               "--output", os.path.abspath(odir),
               "--temporal_setting", "semionline",
               "--detection_every", str(a.detection_every),
               "--amp", "--size", "480", "--sam_variant", "original"]
        print(f"scene {scene}: running DEVA on {len(frames)} frames ...", flush=True)
        r = subprocess.run(cmd, cwd=a.deva_dir)  # stream output to the job log
        ann = os.path.join(odir, "Annotations")
        n_ann = len(os.listdir(ann)) if os.path.isdir(ann) else 0
        print(f"scene {scene}: DEVA rc={r.returncode}, {n_ann} annotations", flush=True)
        if r.returncode != 0 or not os.path.isdir(ann):
            print(f"scene {scene}: DEVA FAILED -> empty masks", flush=True)
            fill_empty(frames)
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        for of in sorted(os.listdir(ann)):
            m = re.search(r"\d+", of)
            if not m:
                continue
            base = idx_to_base.get(int(m.group()))
            if base is None:
                continue
            mask = (np.array(Image.open(os.path.join(ann, of)).convert("L")) > 0).astype(np.uint8) * 255
            Image.fromarray(mask).save(os.path.join(a.out_dir, base + ".png"))
        fill_empty(frames)
        print(f"scene {scene}: {len(frames)} frames done", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"DEVA done -> {a.out_dir} ({len(os.listdir(a.out_dir))} masks)", flush=True)


if __name__ == "__main__":
    main()
