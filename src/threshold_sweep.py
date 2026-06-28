"""Threshold sensitivity sweep for the temporal metrics (R1.2 / R3.2).

The continuity threshold gamma and the flicker threshold delta are the only
tunable knobs in the temporal metrics. This script recomputes the per-method
temporal rankings over a grid of gamma in [0.4, 0.7] and delta in [0.1, 0.3]
(from the existing per-frame IoU logs, no re-inference) and reports the Spearman
rank correlation of each grid point's ranking against the default
(gamma=0.5, delta=0.2), to show the ranking is invariant to the thresholds.

Output: results/threshold_sweep.csv  + a printed summary (min rho).
Run: python src/threshold_sweep.py
"""
import csv
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import temporal_metrics as tm  # noqa: E402
from build_temporal_table import load_per_frame_iou  # noqa: E402

GAMMAS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
DELTAS = [0.10, 0.15, 0.20, 0.25, 0.30]
GAMMA0, DELTA0 = 0.50, 0.20


def macro(scene_iou, fn):
    """Macro-average a per-scene metric (fn: list[iou] -> float|None) over scenes."""
    vals = [fn(ious) for ious in scene_iou.values()]
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else None


def method_scores(data, fn):
    """Per-method score = mean over its partitions of the macro-averaged scene metric."""
    by_method = {}
    for (method, part), scene_iou in data.items():
        m = macro(scene_iou, fn)
        if m is not None:
            by_method.setdefault(method, []).append(m)
    return {mth: float(np.mean(v)) for mth, v in by_method.items() if v}


def spearman(a: dict, b: dict):
    common = sorted(set(a) & set(b))
    if len(common) < 3:
        return float("nan"), len(common)
    ra = {m: r for r, m in enumerate(sorted(common, key=lambda m: a[m]))}
    rb = {m: r for r, m in enumerate(sorted(common, key=lambda m: b[m]))}
    x = np.array([ra[m] for m in common], float)
    y = np.array([rb[m] for m in common], float)
    return float(np.corrcoef(x, y)[0, 1]), len(common)


def main():
    paths = glob.glob("results/per_frame_iou/*/*.csv")
    data = load_per_frame_iou(paths)
    print(f"loaded {len(data)} (method,partition) series from {len(paths)} CSVs")

    # default rankings
    cont0 = method_scores(data, lambda io: tm.continuity(io, GAMMA0))
    flic0 = method_scores(data, lambda io: tm.flicker(io, DELTA0, symmetric=True))

    rows, rhos = [], []
    # continuity: vary gamma (higher-is-better ranking)
    for g in GAMMAS:
        sc = method_scores(data, lambda io, g=g: tm.continuity(io, g))
        rho, n = spearman(cont0, sc)
        rows.append(["continuity", f"gamma={g:.2f}", f"delta={DELTA0:.2f}", f"{rho:.4f}", n])
        if g != GAMMA0:
            rhos.append(rho)
    # flicker: vary delta (lower-is-better, but rank correlation sign-invariant)
    for d in DELTAS:
        sc = method_scores(data, lambda io, d=d: tm.flicker(io, d, symmetric=True))
        rho, n = spearman(flic0, sc)
        rows.append(["flicker", f"gamma={GAMMA0:.2f}", f"delta={d:.2f}", f"{rho:.4f}", n])
        if d != DELTA0:
            rhos.append(rho)

    os.makedirs("results", exist_ok=True)
    with open("results/threshold_sweep.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "gamma", "delta", "spearman_rho_vs_default", "n_methods"])
        w.writerows(rows)

    print("\nmetric      gamma       delta       rho      n")
    for r in rows:
        print(f"{r[0]:<11} {r[1]:<11} {r[2]:<11} {r[3]:>7} {r[4]:>3}")
    print(f"\nmin rho over off-default grid points: {min(rhos):.4f}  (n grid points={len(rhos)})")
    print("wrote results/threshold_sweep.csv")


if __name__ == "__main__":
    main()
