"""Regenerate the per-partition metric bar charts:
  Fig.~\\ref{fig:metrics_comparasions}          (main, all methods)
  Fig.~\\ref{fig:metrics_comparasions_ablation}  (mask-count ablation)

Each panel is one partition; grouped bars per method give Precision, Accuracy,
F1 and IoU (image/scene-wise mean), with error bars = standard deviation.

Sources (already carry the corrected complete-V&F numbers):
  results/spatial_metrics.csv            main  (precision/f1/iou/accuracy + *_std)
  results/ablation_spatial_<PART>.csv    ablation (same columns, first-M variants)

Outputs -> results/figures/
  main:     FKit_all_metrics.png  MTF_all_metrics.png  N5k_all_metrics.png  vnf_all_metrics.png
  ablation: FKit_all_metrics_ablation.png  MTF_..  N5k_..  V&F_all_metrics_ablation.png
"""
import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results/figures"
# metric key -> (legend label, std key, colour)
METRICS = [
    ("precision", "Precision", "precision_std", "#4C72B0"),
    ("accuracy",  "Accuracy",  "accuracy_std",  "#DD8452"),
    ("f1",        "F1 score",  "f1_std",        "#55A868"),
    ("iou",       "IoU",       "iou_std",       "#C44E52"),
]
# CSV partition key -> (panel title, main filename stem, ablation filename stem)
PARTS = {
    "FKIT": ("FKit", "FKit", "FKit"),
    "MTF":  ("MTF",  "MTF",  "MTF"),
    "N5K":  ("N5k",  "N5k",  "N5k"),
    "VF":   ("V&F", "vnf", "V&F"),
}
ABLATION_COMBOS = ["Y+X2", "S+X2", "SF+X2"]
ABLATION_M = [1, 3, 6, 9]


def load(path):
    return list(csv.DictReader(open(path)))


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def draw(title, methods, get_row, fname):
    """methods: list of (label, row-dict). get_row unused (rows embedded)."""
    n = len(methods)
    x = np.arange(n)
    w = 0.2
    fig, ax = plt.subplots(figsize=(max(7, 0.42 * n + 2), 4.6))
    for i, (key, label, skey, colour) in enumerate(METRICS):
        vals = [fnum(r.get(key)) for _, r in methods]
        errs = [fnum(r.get(skey)) for _, r in methods]
        ax.bar(x + (i - 1.5) * w, vals, w, yerr=errs, capsize=2,
               label=label, color=colour, error_kw=dict(lw=0.6, alpha=0.6))
    ax.set_xticks(x)
    ax.set_xticklabels([m for m, _ in methods], rotation=90, fontsize=7)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Score (\\%)".replace("\\", ""))
    ax.set_title(title, loc="left", fontweight="bold")
    ax.legend(ncol=4, fontsize=8, loc="lower center",
              bbox_to_anchor=(0.5, 1.02), frameon=False)
    ax.grid(axis="y", ls=":", alpha=0.4)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, fname)
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {p}  ({n} methods)")


def main_figs():
    rows = load("results/spatial_metrics.csv")
    for part, (title, stem, _) in PARTS.items():
        sub = [r for r in rows if r["partition"] == part]
        # stable order: descending precision within the panel
        sub.sort(key=lambda r: fnum(r["precision"]), reverse=True)
        methods = [(r["method"], r) for r in sub]
        draw(title, methods, None, f"{stem}_all_metrics.png")


def ablation_figs():
    for part, (title, _, stem) in PARTS.items():
        rows = {r["method"]: r for r in load(f"results/ablation_spatial_{part}.csv")}
        methods = []
        for c in ABLATION_COMBOS:
            for m in ABLATION_M:
                name = c if m == 1 else f"{c}_M{m}"
                if name in rows:
                    methods.append((f"{c} M{m}", rows[name]))
        draw(title, methods, None, f"{stem}_all_metrics_ablation.png")


if __name__ == "__main__":
    main_figs()
    ablation_figs()
