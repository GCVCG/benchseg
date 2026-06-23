"""Per-scene DoraemonGPT segmentation tool runner.
Drives GrandedSamTracker (GroundingDINO 'food' seed -> MobileSAM -> AOT/DeAOT
propagation) over each scene's frames -> binary mask <scene>_<frame>.png.
Must run with cwd = DoraemonGPT root (for ./checkpoints + ./project paths).
"""
import argparse, glob, os, re, shutil, sys
from collections import defaultdict
import numpy as np
import cv2
from PIL import Image

IMG_EXTS = (".png", ".jpg", ".jpeg")


def split_scene(base):
    if "_" not in base:
        return base, 0
    s, fr = base.rsplit("_", 1)
    m = re.search(r"\d+", fr)
    return s, (int(m.group()) if m else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--dora_root", required=True)
    ap.add_argument("--prompt", default="food")
    ap.add_argument("--tmp_root", default=None)
    ap.add_argument("--limit_scenes", type=int, default=0)
    a = ap.parse_args()

    DORA = os.path.abspath(a.dora_root)
    img_dir = os.path.abspath(a.img_dir)
    out_dir = os.path.abspath(a.out_dir)
    tmp = os.path.abspath(a.tmp_root or os.path.join("/tmp", "dora_" + out_dir.strip("/").replace("/", "_")))
    os.makedirs(out_dir, exist_ok=True)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)

    os.chdir(DORA)
    sys.path.insert(0, os.path.join(DORA, "project"))
    sys.path.insert(0, os.path.join(DORA, "project", "aot-benchmark"))
    sys.path.insert(0, os.path.join(DORA, "project", "Grounded-Segment-Anything", "EfficientSAM"))
    from GrondedSamtrack import GrandedSamTracker

    tracker = GrandedSamTracker()
    tracker.output_folder_root = tmp + "/"

    by_scene = defaultdict(list)
    for f in sorted(os.listdir(img_dir)):
        if f.lower().endswith(IMG_EXTS):
            b = os.path.splitext(f)[0]
            s, fr = split_scene(b)
            by_scene[s].append((fr, b, f))
    for s in by_scene:
        by_scene[s].sort()
    scenes = list(by_scene.items())
    if a.limit_scenes:
        scenes = scenes[: a.limit_scenes]

    def fill_empty(frames):
        for fr, b, f in frames:
            op = os.path.join(out_dir, b + ".png")
            if not os.path.exists(op):
                im = Image.open(os.path.join(img_dir, f)).size
                Image.fromarray(np.zeros((im[1], im[0]), np.uint8)).save(op)

    for scene, frames in scenes:
        # build a video from the scene frames
        first = cv2.imread(os.path.join(img_dir, frames[0][2]))
        H, W = first.shape[:2]
        vid = os.path.join(tmp, f"{scene}.mp4")
        vw = cv2.VideoWriter(vid, cv2.VideoWriter_fourcc(*"mp4v"), 15, (W, H))
        for fr, b, f in frames:
            im = cv2.imread(os.path.join(img_dir, f))
            vw.write(cv2.resize(im, (W, H)) if im.shape[:2] != (H, W) else im)
        vw.release()
        try:
            tracker.get_tracking_res(a.prompt, vid)
        except Exception as e:  # noqa: BLE001
            print(f"scene {scene}: DoraemonGPT FAILED: {repr(e)[:300]}", flush=True)
            fill_empty(frames)
            continue
        res = os.path.join(tmp, "results", scene)
        if os.path.isdir(res):
            for of in sorted(os.listdir(res)):
                m = re.search(r"\d+", of)
                if not m:
                    continue
                idx = int(m.group())
                if idx < len(frames):
                    b = frames[idx][1]
                    mask = (np.array(Image.open(os.path.join(res, of)).convert("L")) > 0).astype(np.uint8) * 255
                    Image.fromarray(mask).save(os.path.join(out_dir, b + ".png"))
        fill_empty(frames)
        print(f"scene {scene}: {len(frames)} frames done", flush=True)
    print(f"DoraemonGPT done -> {out_dir} ({len(os.listdir(out_dir))} masks)", flush=True)


if __name__ == "__main__":
    main()
