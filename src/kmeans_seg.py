"""k-means++ background-removal segmentation (kMean++ baseline), CPU-only.

Faithful reimplementation of utility_scripts/kmeans_background_removal.py using
OpenCV's built-in kmeans (avoids faiss/skimage deps): HSV-saturation preprocess
-> k-means++ (k=2) -> smallest cluster = foreground -> morphological opening.
Saves a binary mask {stem}.png (0=bg, 255=food) per input frame.
"""
import argparse, glob, os, time
import cv2
import numpy as np

IMG_EXTS = (".png", ".jpg", ".jpeg")


def preprocess(img, t1=93, t2=110):
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    _, th1 = cv2.threshold(hsv[:, :, 1], t1, 255, cv2.THRESH_BINARY)
    _, th2 = cv2.threshold(th1, t2, 255, cv2.THRESH_BINARY)
    final = cv2.bitwise_and(img, img, mask=th2)
    return cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)


def kmeans_mask(gray, k=2, niter=200):
    Z = gray.reshape(-1, 1).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, niter, 0.2)
    _, labels, _ = cv2.kmeans(Z, k, None, criteria, 1, cv2.KMEANS_PP_CENTERS)
    labels = labels.reshape(gray.shape)
    uniq, cnt = np.unique(labels, return_counts=True)
    smallest = uniq[np.argmin(cnt)]
    return np.where(labels == smallest, 255, 0).astype(np.uint8)


def morph(mask, r=3):
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(cv2.erode(mask, se), se)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--clusters", type=int, default=2)
    ap.add_argument("--t1", type=int, default=93)
    ap.add_argument("--t2", type=int, default=110)
    ap.add_argument("--morph_radius", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for k-means++ init (vary across repeat runs)")
    a = ap.parse_args()
    cv2.setRNGSeed(a.seed)
    os.makedirs(a.out_dir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(a.img_dir, "*")) if f.lower().endswith(IMG_EXTS))
    if a.limit:
        imgs = imgs[: a.limit]
    t0 = time.time()
    for i, ip in enumerate(imgs):
        img = cv2.imread(ip)
        if img is None:
            continue
        m = morph(kmeans_mask(preprocess(img, a.t1, a.t2), a.clusters), a.morph_radius)
        stem = os.path.splitext(os.path.basename(ip))[0]
        cv2.imwrite(os.path.join(a.out_dir, f"{stem}.png"), m)
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    print(f"done {len(imgs)} imgs in {dt:.1f}s -> {a.out_dir}", flush=True)


if __name__ == "__main__":
    main()
