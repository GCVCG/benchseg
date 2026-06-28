"""Paired significance tests for the headline comparisons (R1.6 / R4.4).

For each method pair and metric, pairs scenes (same partition+scene present in
both methods) and reports: mean per-scene difference (A-B), a 95% bootstrap CI
over scenes (10,000 resamples), and a paired two-sided Wilcoxon signed-rank
p-value. A difference is 'significant' at p<0.05.

Input:  results/per_scene_metrics.csv  (from src/per_scene_metrics.py)
Output: results/significance.csv
"""
import csv
import os

import numpy as np
from scipy.stats import wilcoxon

SEED = 12345
N_BOOT = 10000
# (label, A, B); the claim is "A vs B". mAP == precision for binary masks.
PAIRS = [
    ("SeTM+S3 vs FoodMem (headline, indistinguishable?)", "SeTM+S3", "FoodMem"),
    ("FoodMem vs SeTR-MLA (XMem2 memory gain)", "FoodMem", "SETR_MLA"),
    ("SeTM+S3 vs SeTR-MLA (SAM3 memory gain)", "SeTM+S3", "SETR_MLA"),
    ("SF+X2 vs SegMan-FT (memory gain, finetuned)", "SF+X2", "SegMan_FS"),
    ("Seg+S3 vs SegMan (SAM3 memory gain)", "Seg+S3", "SegMan_ADE"),
    ("Y+S3 vs YOLO (SAM3 memory gain, weakest seed)", "Y+S3", "YOLO"),
    ("FoodMem vs BiRefNet (memory vs per-frame)", "FoodMem", "BiRefNet"),
]
METRICS = [("mAP", "precision"), ("recall", "recall"), ("iou", "iou")]


def load(path):
    d = {}
    for r in csv.DictReader(open(path)):
        d[(r["method"], r["partition"], r["scene"])] = r
    return d


def paired(d, A, B, col):
    xs, ys = [], []
    keys = {(p, s) for (m, p, s) in d if m == A} & {(p, s) for (m, p, s) in d if m == B}
    for (p, s) in sorted(keys):
        xs.append(float(d[(A, p, s)][col]))
        ys.append(float(d[(B, p, s)][col]))
    return np.array(xs), np.array(ys)


def main():
    d = load("results/per_scene_metrics.csv")
    rng = np.random.default_rng(SEED)
    rows = []
    print(f"{'pair':<48}{'metric':<7}{'n':>4}{'meanDiff':>10}{'95%CI':>20}{'Wilcoxon p':>12}{'sig':>5}")
    for label, A, B in PAIRS:
        for mname, col in METRICS:
            x, y = paired(d, A, B, col)
            if len(x) < 3:
                continue
            diff = x - y
            md = float(diff.mean())
            boot = np.array([rng.choice(diff, size=len(diff), replace=True).mean()
                             for _ in range(N_BOOT)])
            lo, hi = np.percentile(boot, [2.5, 97.5])
            try:
                p = float(wilcoxon(diff, zero_method="wilcox", alternative="two-sided").pvalue) \
                    if np.any(diff != 0) else 1.0
            except ValueError:
                p = 1.0
            sig = "*" if p < 0.05 else ""
            rows.append([label, A, B, mname, len(x), f"{md:.3f}",
                         f"{lo:.3f}", f"{hi:.3f}", f"{p:.4g}", "yes" if sig else "no"])
            print(f"{label:<48}{mname:<7}{len(x):>4}{md:>10.3f}  [{lo:>6.2f},{hi:>6.2f}]{p:>12.4g}{sig:>5}")
    with open("results/significance.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["comparison", "A", "B", "metric", "n_scenes", "mean_diff_A_minus_B",
                    "ci95_low", "ci95_high", "wilcoxon_p", "significant_p<0.05"])
        w.writerows(rows)
    print("\nwrote results/significance.csv")


if __name__ == "__main__":
    main()
