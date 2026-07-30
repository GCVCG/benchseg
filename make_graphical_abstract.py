#!/usr/bin/env python3
"""
Graphical abstract for BenchSeg (multi-panel dashboard).

Layout (wide canvas so nothing is cramped):
  Top-left   : summary card (datasets, protocol, metrics, scale, config count).
  Top-right  : the headline benchmark chart (accuracy vs flicker) with the
               dense-cluster zoom window, all per-frame baselines + key hybrids
               labelled, base->hybrid arrows, axis 'better' directions.
  Bottom     : a 2x2 grid of four diagnostic mini-panels, kept in two pairs
               row 1 : A robustness to camera-view change  B cross-partition generalization
               row 2 : C accuracy vs model size            D dense per-frame annotation scale

Rendered at 2700 x 1830 px, 300 dpi, vector PDF, Arial/Liberation Sans embedded
(Type 42). This is a portrait-leaning dashboard, taller than Elsevier's preferred
2.5:1; the online TOC down-scales it into a landscape slot.

The scatter, panel B, and panel D read from results/all_metrics.csv (the MEAN /
per-partition rows), the same source as Tables 8 and 10. Panels A and C use
values transcribed from the view-magnitude and efficiency tables. The
base->combination map matches src/compose_efficiency.py.

Usage:  python3 make_graphical_abstract.py [path/to/all_metrics.csv]
Output: graphical_abstract.pdf, graphical_abstract.png (repo root and latex/).
"""
import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (ConnectionPatch, FancyArrowPatch, FancyBboxPatch,
                                Rectangle)

from matplotlib import font_manager
_available = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Arial", "Helvetica", "Liberation Sans")
             if f in _available), "sans-serif")
matplotlib.rcParams["font.family"] = FONT
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "all_metrics.csv")

# --- palette -------------------------------------------------------------
INK = "#12232E"
MUT = "#6A757D"
HYB = "#0E7C8A"
SGL = "#DA6A34"
SGL2 = "#E8A87C"
XMEM = "#0E8A86"
SAM3C = "#2F6DB0"
SAM2C = "#9257A8"
DEVAC = "#5B6B73"
ARR = "#AEB8BF"
CARD = "#F4F7F8"
GRID = "#EAEFF1"
ACCENT = "#0E7C8A"

# --- data ----------------------------------------------------------------
part = {}
with open(CSV, encoding="utf-8") as f:
    for d in csv.DictReader(f):
        part.setdefault(d["method"], {})[d["partition"]] = d
rows = {m: p["MEAN"] for m, p in part.items() if "MEAN" in p}


def val(key):
    d = rows[key]
    return float(d["mAP"]), float(d["flicker"])


FAM = {
    "FLMM":        ("FoodLMM",   ["FLMM+X2", "FLMM+S2", "FLMM+S3"]),
    "SegMan_ADE":  ("SegMan",    ["S+X2", "Seg+S2", "Seg+S3"]),
    "SegMan_COCO": ("SegMan-C",  ["SC+X2", "SC+S2", "SC+S3"]),
    "YOLO":        ("YOLO",      ["Y+X2", "Y+S2", "Y+S3"]),
    "SegMan_FS":   ("SegMan-FT", ["SF+X2", "SF+S2", "SF+S3"]),
    "SETR_MLA":    ("SeTR-MLA",  ["FoodMem", "SeTM+S2", "SeTM+S3"]),
}
SAM2_COMBOS = {combos[1] for _, combos in FAM.values()}
TRACKER = {}
for _lab, _combos in FAM.values():
    TRACKER[_combos[0]] = "xmem2"
    TRACKER[_combos[1]] = "sam2"
    TRACKER[_combos[2]] = "sam3"
STYLE = {"base": ("^", SGL, 42), "xmem2": ("o", XMEM, 34),
         "sam3": ("D", SAM3C, 30), "sam2": ("s", SAM2C, 28),
         "deva": ("*", DEVAC, 80)}
LEGEND = [("base", "per-frame segmenter"), ("xmem2", "+ XMem2"),
          ("sam3", "+ SAM3"), ("deva", "DEVA")]


def category(name):
    if name == "DEVA":
        return "deva"
    return TRACKER.get(name, "base")


PF_DISP = {"FLMM": "FoodLMM", "SegMan_ADE": "SegMan", "SegMan_COCO": "SegMan-C",
           "YOLO": "YOLO", "SegMan_FS": "SegMan-FT", "SETR_MLA": "SeTR-MLA",
           "CCNet": "CCNet", "CCNet-Re": "CCNet-Re", "Swin-B": "Swin-B",
           "Swin-S": "Swin-S", "FSAM": "FoodSAM", "SeTN": "SeTR-N",
           "BiRefNet": "BiRefNet", "FPN-Re": "FPN-Re", "kMean++": "kMean++",
           "DoraemonGPT": "DoraGPT"}
DENSE = ["SETR_MLA", "CCNet", "Swin-B", "CCNet-Re", "SeTN", "SegMan_FS",
         "Swin-S", "FSAM"]

# =========================================================================
fig = plt.figure(figsize=(9.0, 6.10), dpi=300)   # 2700 x 1830 px
fig.patch.set_facecolor("white")


def mini_style(ax, title):
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    for s_ in ("left", "bottom"):
        ax.spines[s_].set_color("#AAB3BA")
        ax.spines[s_].set_linewidth(0.8)
    ax.tick_params(labelsize=7.6, length=2.2, colors=MUT, pad=1.5)
    ax.grid(alpha=1.0, color=GRID, linestyle="-", lw=0.6, zorder=0)
    ax.set_title(title, fontsize=9.4, weight="bold", color=INK, pad=4)


# ================================================ TOP-LEFT: summary card
fig.add_artist(FancyBboxPatch((0.010, 0.505), 0.256, 0.467,
                              boxstyle="round,pad=0.004,rounding_size=0.016",
                              facecolor=CARD, edgecolor="none",
                              transform=fig.transFigure))
fig.add_artist(plt.Line2D([0.024, 0.024], [0.535, 0.952], color=ACCENT, lw=3,
                          solid_capstyle="round"))
LX = 0.044
fig.text(LX, 0.949, "BenchSeg", fontsize=18, weight="bold", color=INK, va="center")
fig.text(LX, 0.922, "multi-view food video segmentation benchmark",
         fontsize=6.6, color=MUT, va="center")

fig.add_artist(FancyBboxPatch((0.214, 0.867), 0.046, 0.046,
                              boxstyle="round,pad=0.0,rounding_size=0.009",
                              facecolor=HYB, alpha=0.14, edgecolor="none",
                              transform=fig.transFigure))
for cx, num, lab in [(0.084, "25,284", "dense masks"), (0.168, "55", "scenes"),
                     (0.237, "35", "configs")]:
    fig.text(cx, 0.890, num, fontsize=12.5, weight="bold", color=HYB,
             ha="center", va="center")
    fig.text(cx, 0.868, lab, fontsize=6.8, color=MUT, ha="center", va="center")

fig.text(LX, 0.840, "16 per-frame segmenters, 3 memory trackers",
         fontsize=7.0, color=MUT, va="center")
fig.text(LX, 0.821, "(XMem2, SAM2, SAM3) and DEVA", fontsize=7.0, color=MUT, va="center")
fig.add_artist(plt.Line2D([LX, 0.250], [0.803, 0.803], color="#DBE2E6", lw=1.0))

fig.text(LX, 0.782, "DATASETS", fontsize=7.2, weight="bold", color=HYB, va="center")
fig.text(LX, 0.760, "Nutrition5k · Vegetables & Fruits", fontsize=7.4, color=INK, va="center")
fig.text(LX, 0.741, "MetaFood3D · FoodKit", fontsize=7.4, color=INK, va="center")
fig.text(LX, 0.722, "annotated: dense per-frame food masks", fontsize=7.4,
         color=INK, style="italic", va="center")

fig.text(LX, 0.689, "PROTOCOL", fontsize=7.2, weight="bold", color=HYB, va="center")
fig.text(LX, 0.667, "Zero-shot: train on FoodSeg103,", fontsize=7.4, color=INK, va="center")
fig.text(LX, 0.648, "evaluate on BenchSeg (no fine-tuning)", fontsize=7.4, color=INK, va="center")

fig.text(LX, 0.615, "METRICS", fontsize=7.2, weight="bold", color=HYB, va="center")
fig.text(LX, 0.593, "Spatial: mAP · IoU · recall · F1", fontsize=7.4, color=INK, va="center")
fig.text(LX, 0.574, "Temporal: continuity · flicker · drift", fontsize=7.4, color=INK, va="center")

fig.text(LX, 0.541, "amughrabi.github.io/benchseg", fontsize=7.4,
         color=HYB, style="italic", va="center")

# ================================================ TOP-RIGHT: benchmark chart
fig.text(0.610, 0.958, "Pairing a weak segmenter with temporal memory moves it "
         "to the high-accuracy, low-flicker corner",
         ha="center", va="center", fontsize=10.6, weight="bold", color=INK)

sc = fig.add_axes([0.315, 0.575, 0.505, 0.328])
sc.set_facecolor("white")
for s_ in ("top", "right"):
    sc.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    sc.spines[s_].set_color("#AAB3BA")
    sc.spines[s_].set_linewidth(0.9)
sc.set_yscale("function", functions=(lambda a: np.sqrt(np.clip(a, 0, None)),
                                     lambda a: np.asarray(a) ** 2))
XLO, XHI, YLO, YHI = 26, 100, 0, 28.5

for base, (lab, combos) in FAM.items():
    bx, by = val(base)
    for c in (combos[0], combos[2]):
        cx, cy = val(c)
        sc.add_patch(FancyArrowPatch((bx, by), (cx, cy), arrowstyle="-|>",
                                     mutation_scale=7, lw=0.8, color=ARR,
                                     alpha=0.6, shrinkA=4, shrinkB=4,
                                     connectionstyle="arc3,rad=0.06", zorder=3))
for name, d in rows.items():
    if name in SAM2_COMBOS:
        continue
    m, fl = float(d["mAP"]), float(d["flicker"])
    mk, col, sz = STYLE[category(name)]
    sc.scatter(m, fl, s=sz * 1.3, c=col, marker=mk, edgecolors="white",
               linewidths=0.6, alpha=0.95, zorder=5)

SPARSE_LAB = {"FLMM": (-2.6, -1.4, "right"), "SegMan_ADE": (-2.6, -1.6, "right"),
              "SegMan_COCO": (0.0, 4.4, "center"), "YOLO": (2.9, 0.0, "left"),
              "BiRefNet": (-2.8, -0.6, "right"), "FPN-Re": (-2.8, 1.4, "right"),
              "kMean++": (-2.6, 0.0, "right"), "DoraemonGPT": (2.7, 0.2, "left")}
for name, (dx, dy, ha) in SPARSE_LAB.items():
    m, fl = val(name)
    sc.annotate(PF_DISP[name], xy=(m, fl), xytext=(m + dx, fl + dy), ha=ha,
                va="center", fontsize=7.8, weight="bold", color=SGL, zorder=8)
HYB_LAB = {"FoodMem": (1.4, 0.4, "left", XMEM), "SeTM+S3": (1.2, 2.6, "left", SAM3C),
           "SF+X2": (-2.6, 2.2, "right", XMEM), "DEVA": (-3.0, 1.9, "right", DEVAC)}
for name, (dx, dy, ha, col) in HYB_LAB.items():
    m, fl = val(name)
    sc.annotate(name, xy=(m, fl), xytext=(m + dx, fl + dy), ha=ha, va="center",
                fontsize=7.2, weight="bold", color=col, zorder=8)

sc.set_xlim(XLO, XHI)
sc.set_ylim(YLO, YHI)
sc.set_xticks([30, 50, 70, 90])
sc.set_yticks([0, 1, 5, 20])
sc.tick_params(labelsize=8.2, length=2.6, colors=MUT, pad=2.0)
sc.set_xlabel(r"mean spatial accuracy   (mAP %) $\uparrow$", fontsize=9.6,
              color=INK, labelpad=2.0)
# the y-label is rotated 90 deg, so a left-arrow glyph renders as a visual down-arrow
sc.set_ylabel(r"flicker rate   (%) $\leftarrow$", fontsize=9.6, color=INK, labelpad=1.5)
sc.grid(alpha=1.0, color=GRID, linestyle="-", lw=0.8, zorder=0)

BX0, BX1, BY0, BY1 = 87.0, 95.6, 2.6, 9.4
sc.add_patch(Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fill=False,
                       edgecolor="#7C8790", lw=0.9, linestyle=(0, (3, 2)), zorder=9))

ins = fig.add_axes([0.852, 0.618, 0.115, 0.268])
ins.set_facecolor("#FBFCFD")
for s_ in ("top", "right", "left", "bottom"):
    ins.spines[s_].set_color("#9AA4AC")
    ins.spines[s_].set_linewidth(0.8)
for name in DENSE:
    m, fl = val(name)
    ins.scatter(m, fl, s=46, c=SGL, marker="^", edgecolors="white",
                linewidths=0.7, zorder=6)
CDISP = {"FSAM": (85.8, 8.7, "left"), "Swin-S": (89.6, 9.6, "center"),
         "CCNet": (93.8, 8.7, "left"), "Swin-B": (94.6, 7.05, "left"),
         "CCNet-Re": (94.4, 5.5, "left"), "SeTN": (86.9, 6.75, "right"),
         "SegMan_FS": (86.8, 5.5, "right"), "SETR_MLA": (95.2, 4.4, "left")}
for name, (tx, ty, ha) in CDISP.items():
    m, fl = val(name)
    ins.annotate(PF_DISP[name], xy=(m, fl), xytext=(tx, ty), ha=ha, va="center",
                 fontsize=6.6, weight="bold", color=INK, zorder=7,
                 arrowprops=dict(arrowstyle="-", color="#AFB7BD", lw=0.5,
                                 shrinkA=1, shrinkB=3))
ins.set_xlim(84.3, 100.5)
ins.set_ylim(2.2, 10.2)
ins.set_xticks([88, 94, 100])
ins.set_yticks([3, 6, 9])
ins.tick_params(labelsize=6.4, length=1.8, colors=MUT, pad=1.2)
ins.set_title("dense per-frame cluster (zoom)", fontsize=7.0, color=MUT,
              style="italic", pad=2)
ins.grid(alpha=1.0, color=GRID, linestyle="-", lw=0.6, zorder=0)
for corner_xy, ins_xy in [((BX1, BY1), (0, 1)), ((BX1, BY0), (0, 0))]:
    fig.add_artist(ConnectionPatch(xyA=corner_xy, coordsA=sc.transData,
                                   xyB=ins_xy, coordsB=ins.transAxes,
                                   color="#9AA4AC", lw=0.7, alpha=0.85, zorder=9))

handles = [plt.Line2D([0], [0], marker=STYLE[c][0], linestyle="none",
                      markerfacecolor=STYLE[c][1], markeredgecolor="white",
                      markeredgewidth=0.6, markersize=9 if c == "deva" else 8,
                      label=lab) for c, lab in LEGEND]
leg = fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.567, 0.940),
                 ncol=4, frameon=False, fontsize=8.4, handletextpad=0.3,
                 columnspacing=1.2)
for t in leg.get_texts():
    t.set_color(INK)

# ================================================ BOTTOM: 2x2 diagnostic grid
# Row 1 : (A,B) robustness / generalization.  Row 2 : (C,D) resources.
PWL, PWR, PH = 0.385, 0.445, 0.165   # right column wider than left
R1Y, R2Y = 0.300, 0.055
LXP, RXP = 0.050, 0.510

# A: robustness to camera-view change
axA = fig.add_axes([LXP, R1Y, PWL, PH])
mini_style(axA, "A  robustness to camera-view change")
vx = np.arange(3)
# Grouped bars: mean IoU of per-frame segmenters vs memory-augmented configs
# (XMem2/SAM3/DEVA; SAM2 omitted, as elsewhere) at Low/Med/High tertiles of the
# frame-to-frame view-change proxy vc = 1 - IoU(GT_t, GT_{t-1}). Memory holds/
# rises while per-frame declines, so the gap widens with view change.
pf_view = [66.8, 66.4, 64.2]     # mean over the 16 per-frame segmenters
mem_view = [68.3, 71.2, 72.3]    # mean over the 13 memory-augmented configs
wa = 0.36
axA.bar(vx - wa / 2, pf_view, wa, color=SGL, label="per-frame", zorder=3,
        edgecolor="white", linewidth=0.4)
axA.bar(vx + wa / 2, mem_view, wa, color=XMEM, label="+ memory", zorder=3,
        edgecolor="white", linewidth=0.4)
axA.annotate("memory pulls ahead", xy=(2 + wa / 2, 72.3), xytext=(1.35, 79.7),
             fontsize=6.2, color=XMEM, ha="center", va="center",
             arrowprops=dict(arrowstyle="-|>", color=XMEM, lw=0.8, shrinkB=3))
axA.set_xticks(vx)
axA.set_xticklabels(["Low", "Med", "High"])
axA.set_xlim(-0.55, 2.55)
axA.set_ylim(58, 82)
axA.set_yticks([60, 70, 80])
axA.set_ylabel(r"mean IoU (%) $\rightarrow$", fontsize=7.6, color=INK, labelpad=1.5)
axA.set_xlabel("camera-view change (tertile)", fontsize=7.6, color=INK, labelpad=1.5)
axA.legend(fontsize=6.6, frameon=False, ncol=1, loc="upper left",
           bbox_to_anchor=(0.0, 1.0), handletextpad=0.3, labelspacing=0.2)

# B: cross-partition generalization
axB = fig.add_axes([RXP, R1Y, PWR, PH])
mini_style(axB, "B  cross-partition generalization")
GG = [("BiRefNet", [95.82, 59.04, 59.77, 98.65], SGL),
      ("YOLO", [86.51, 60.49, 73.36, 59.70], SGL2),
      ("FoodMem", [94.35, 91.76, 98.34, 96.34], HYB),
      ("SeTM+S3", [94.71, 91.65, 97.97, 97.43], SAM3C)]
x = np.arange(4)
w = 0.20
for i, (name, ys, col) in enumerate(GG):
    axB.bar(x + (i - 1.5) * w, ys, w, color=col, label=name, zorder=3,
            edgecolor="white", linewidth=0.4)
axB.set_xticks(x)
axB.set_xticklabels(["N5k", "V&F", "MTF", "FKit"])
axB.set_ylim(0, 140)
axB.set_yticks([0, 50, 100])
axB.set_ylabel(r"mAP (%) $\rightarrow$", fontsize=7.6, color=INK, labelpad=1.5)
axB.set_xlabel("test partition", fontsize=7.6, color=INK, labelpad=1.5)
axB.legend(fontsize=6.2, frameon=False, ncol=4, loc="upper center",
           bbox_to_anchor=(0.5, 1.03), handletextpad=0.25, columnspacing=0.6)

# C: accuracy vs model size
axC = fig.add_axes([LXP, R2Y, PWL, PH])
mini_style(axC, "C  accuracy vs model size")
# markers match the top legend (per-frame ^, +XMem2 o, +SAM3 D, DEVA *);
# SAM2 combos omitted, as in the main chart.
COST = [("YOLO", 10.1, 70.02, "base"), ("FPN-Re", 28.5, 79.65, "base"),
        ("CCNet", 49.9, 91.77, "base"), ("CCNet-Re", 49.9, 91.20, "base"),
        ("SegMan-FT", 51.8, 90.23, "base"), ("Swin-S", 81.2, 89.37, "base"),
        ("SeTR-N", 94.8, 90.77, "base"), ("Swin-B", 121.2, 91.47, "base"),
        ("BiRefNet", 220.2, 78.32, "base"), ("SeTR-MLA", 311.5, 94.19, "base"),
        ("FoodSAM", 636.0, 88.36, "base"),
        ("Y+X2", 72.3, 87.07, "xmem2"), ("S+X2", 114.0, 60.42, "xmem2"),
        ("SC+X2", 114.0, 67.55, "xmem2"), ("SF+X2", 114.0, 94.25, "xmem2"),
        ("FoodMem", 373.7, 95.20, "xmem2"),
        ("Y+S3", 871.4, 91.44, "sam3"), ("Seg+S3", 913.0, 79.52, "sam3"),
        ("SC+S3", 913.0, 81.09, "sam3"), ("SF+S3", 913.0, 93.98, "sam3"),
        ("SeTM+S3", 1172.7, 95.44, "sam3"), ("DEVA", 241.0, 88.02, "deva")]
# label the spread-out points; the 50-120 M / 88-92 per-frame cluster stays as
# bare shaped markers (its identity is conveyed by shape + position)
CLBL = {"YOLO": (0, -9, "center", "top"), "FPN-Re": (0, -9, "center", "top"),
        "BiRefNet": (0, -9, "center", "top"), "FoodSAM": (11, -1, "left", "center"),
        "SeTR-MLA": (-11, 7, "right", "bottom"), "FoodMem": (0, 10, "center", "bottom"),
        "SeTM+S3": (3, 9, "left", "bottom"), "SF+X2": (-9, 4, "right", "center"),
        "S+X2": (-9, 0, "right", "center"), "SF+S3": (-10, 3, "right", "center"),
        "DEVA": (-8, 6, "right", "bottom"), "SeTM+S3": (0, 10, "center", "bottom")}
for name, pr, mp, cat in COST:
    mk, col, sz = STYLE[cat]
    axC.scatter(pr, mp, s=sz * 0.85, c=col, marker=mk, edgecolors="white",
                linewidths=0.5, zorder=5)
    if name in CLBL:
        dx, dy, ha, va = CLBL[name]
        axC.annotate(name, xy=(pr, mp), xytext=(dx, dy), textcoords="offset points",
                     fontsize=6.6, color=INK, ha=ha, va=va, zorder=8,
                     arrowprops=dict(arrowstyle="-", color="#9AA4AC", lw=0.5,
                                     shrinkA=1.5, shrinkB=2.5))
axC.set_xscale("log")
axC.set_xlim(7, 2100)
axC.set_ylim(55, 106)
axC.set_xticks([10, 100, 1000])
axC.set_xticklabels(["10", "100", "1000"])
axC.set_xlabel("parameters (M, log)", fontsize=7.6, color=INK, labelpad=1.5)
axC.set_ylabel(r"mean mAP (%) $\rightarrow$", fontsize=7.6, color=INK, labelpad=1.5)
legC = axC.legend(handles=[plt.Line2D([0], [0], marker=STYLE[c][0], linestyle="none",
                    markerfacecolor=STYLE[c][1], markeredgecolor="white",
                    markeredgewidth=0.5, markersize=6, label=lb)
                    for c, lb in [("base", "per-frame"), ("xmem2", "+XMem2"),
                                  ("sam3", "+SAM3"), ("deva", "DEVA")]],
           fontsize=5.8, loc="upper left", handletextpad=0.2, labelspacing=0.22,
           borderpad=0.3, frameon=True, framealpha=1.0, facecolor="white",
           edgecolor="#CCCCCC")
legC.get_frame().set_linewidth(0.6)
legC.set_zorder(20)

# D: dense per-frame annotation scale
axD = fig.add_axes([RXP, R2Y, PWR, PH])
mini_style(axD, "D  dense per-frame annotation scale")
SCALE = [("N5k", 621), ("MTF", 1749), ("V&F", 2308), ("FKit", 20606)]
names = [s[0] for s in SCALE]
counts = [s[1] for s in SCALE]
ypos = np.arange(len(SCALE))
axD.barh(ypos, counts, color=[MUT, SAM3C, XMEM, HYB], zorder=3, height=0.60)
for yp, c in zip(ypos, counts):
    axD.text(c + 450, yp, f"{c:,}", va="center", ha="left", fontsize=7.4,
             color=INK, weight="bold")
axD.set_yticks(ypos)
axD.set_yticklabels(names, fontsize=7.6)
axD.set_ylabel("dataset", fontsize=7.6, color=INK, labelpad=1.5)
axD.set_xlim(0, 25500)
axD.set_xticks([0, 10000, 20000])
axD.set_xticklabels(["0", "10k", "20k"])
axD.set_xlabel("annotated frame masks", fontsize=7.6, color=INK, labelpad=1.5)
axD.grid(False)

# Write next to this script, and also into latex/ so the manuscript picks it up.
out_dirs = [HERE]
latex_dir = os.path.join(HERE, "latex")
if os.path.isdir(latex_dir):
    out_dirs.append(latex_dir)
for d in out_dirs:
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(d, f"graphical_abstract.{ext}"), facecolor="white")
print("wrote graphical_abstract.pdf / .png (2700 x 1830 px, font=%s) to %s"
      % (FONT, ", ".join(out_dirs)))
