"""Deterministic generator for the BenchSeg manuscript result tables.

Single source of truth = the result CSVs in results/. Emits one drop-in .tex
body per table into results/tables/, matching the manuscript column order and
the bold(best)/uline(2nd)/italic(3rd) highlighting, computed programmatically.
No metric is ever hand-typed; every cell traces to a CSV value.

Tables generated (CSV-derivable):
  tab_results.tex             tab:results               mAP+Recall (x4) + Efficiency
  tab_precision.tex           tab:results_precision_f1_IoU  Precision/F1/IoU/Acc (x4)
  tab_temporal.tex            tab:temporal_styled       continuity/flicker/drift/sigma + Global
  tab_model_comparisons.tex   tab:model_comparisons     FoodSeg103 mIoU/mAcc

Sources:
  results/all_metrics.csv            spatial+temporal means, partition incl MEAN
  results/spatial_metrics.csv        spatial means + *_std + n_scenes
  results/table_corrected_minimal.csv temporal means + *_std (temporal std source)
  results/efficiency.csv             params_M, speed_ms_img, vram_MB
  results/foodseg103_metrics.csv     mIoU, mAcc, aAcc (FoodSeg103 in-domain)

NOT generated here (separate experiments, not in these CSVs): tab:masks_ablation,
tab:temporal_grouped_method (M = #input-masks ablation), tab:efficiency
(GPU-utilization microbenchmark). tab:temporal_module_ablation is built in step 4.
"""
import csv
import os
from collections import defaultdict

R = "results"
OUT = "results/tables"

# CSV method id -> manuscript display label
DISP = {"SegMan_ADE": "SegMan", "SegMan_COCO": "SegMan-C", "SegMan_FS": "SegMan-FT",
        "S+X2": "Seg+X2", "SETR_MLA": "SeTM"}


def disp(m):
    return DISP.get(m, m)


def load_kv(path):
    d = defaultdict(dict)
    for r in csv.DictReader(open(path)):
        d[r["method"]][r["partition"]] = r
    return d


def load_rows(path):
    return list(csv.DictReader(open(path)))


def fnum(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return "--"


def style_col(pairs, higher=True, nd=2):
    """pairs: [(method, value|None)] -> {method: styled string} with top-3 bold/uline/italic."""
    present = [(m, v) for m, v in pairs if v is not None]
    order = sorted(present, key=lambda x: x[1], reverse=higher)
    rank = {m: i for i, (m, _) in enumerate(order)}
    out = {}
    for m, v in pairs:
        if v is None:
            out[m] = "--"; continue
        s = fnum(v, nd)
        r = rank.get(m, 99)
        out[m] = (f"\\textbf{{{s}}}" if r == 0 else f"\\uline{{{s}}}" if r == 1
                  else f"\\textit{{{s}}}" if r == 2 else s)
    return out


# ---------------------------------------------------------------- tab:results
def build_results(sp, eff):
    PO = ["FKIT", "N5K", "VF", "MTF"]
    def val(m, p, k):
        r = sp.get(m, {}).get(p)
        return float(r[k]) if r and r.get(k) not in (None, "") else None
    methods = sorted(sp.keys(), key=lambda m: (val(m, "FKIT", "precision") or 1e9))
    cells = {}
    for metric, src in (("mAP", "precision"), ("recall", "recall")):
        for p in PO:
            cells[(metric, p)] = style_col([(m, val(m, p, src)) for m in methods], higher=True)
    def effv(m, k):
        r = eff.get(m)
        return float(r[k]) if r and r.get(k) not in (None, "") else None
    ecell = {k: style_col([(m, effv(m, k)) for m in methods], higher=False, nd=1)
             for k in ("params_M", "speed_ms_img", "vram_MB")}
    def std(m, p, k):
        r = sp.get(m, {}).get(p); return fnum(r[k]) if r and r.get(k) else "--"
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)] + [cells[("mAP", p)][m] for p in PO]
                          + [cells[("recall", p)][m] for p in PO]
                          + [ecell["params_M"][m], ecell["speed_ms_img"][m], ecell["vram_MB"][m]])
        sr = " & ".join([""] + [std(m, p, "precision_std") for p in PO]
                        + [std(m, p, "recall_std") for p in PO] + ["", "", ""])
        lines.append(f"{shade}{mean} \\\\\n {sr} \\\\ \\addlinespace[2pt]")
    return "\n".join(lines), methods


# -------------------------------------------- tab:results_precision_f1_IoU
def build_precision(sp, methods):
    PO = ["FKIT", "MTF", "N5K", "VF"]
    MET = [("precision", "precision_std"), ("f1", "f1_std"),
           ("iou", "iou_std"), ("accuracy", "accuracy_std")]
    def val(m, p, k):
        r = sp.get(m, {}).get(p); return float(r[k]) if r and r.get(k) not in (None, "") else None
    cell = {}
    for mk, _ in MET:
        for p in PO:
            cell[(mk, p)] = style_col([(m, val(m, p, mk)) for m in methods], higher=True)
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)] + [cell[(mk, p)][m] for mk, _ in MET for p in PO])
        def std(p, sk):
            r = sp.get(m, {}).get(p); return fnum(r[sk]) if r and r.get(sk) else "--"
        sr = " & ".join([""] + [std(p, sk) for _, sk in MET for p in PO])
        lines.append(f"{shade}{mean} \\\\\n {sr} \\\\ \\addlinespace[3pt]")
    return "\n".join(lines)


# ------------------------------------------------------ tab:temporal_styled
def build_temporal(tp):
    PO = ["FKIT", "MTF", "N5K", "VF"]
    MET = [("continuity", True), ("flicker", False), ("drift", False), ("sigma", False)]
    def v(m, p, k):
        r = tp.get(m, {}).get(p); return float(r[k]) if r and r.get(k) not in (None, "") else None
    def g(m, k):
        xs = [v(m, p, k) for p in PO]; xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    methods = sorted([m for m in tp], key=lambda m: (v(m, "FKIT", "continuity") or 1e9))
    cell = {}
    for k, hi in MET:
        for p in PO:
            cell[(k, p)] = style_col([(m, v(m, p, k)) for m in methods], higher=hi, nd=1)
        cell[(k, "G")] = style_col([(m, g(m, k)) for m in methods], higher=hi, nd=1)
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)] + [cell[(k, p)][m] for k, _ in MET for p in PO]
                          + [cell[(k, "G")][m] for k, _ in MET])
        def std(p, k):
            r = tp.get(m, {}).get(p); return fnum(r[k + "_std"], 1) if r and r.get(k + "_std") else "--"
        sr = " & ".join([""] + [std(p, k) for k, _ in MET for p in PO] + ["", "", "", ""])
        lines.append(f"{shade}{mean} \\\\\n {sr} \\\\ \\addlinespace[2pt]")
    return "\n".join(lines)


# --------------------------------------------------- tab:model_comparisons
# FoodSeg103 in-domain. Metric cells (mIoU/mAcc) trace to foodseg103_metrics.csv;
# Backbone + Model Size are fixed metadata (not metrics). Row order ascending mIoU.
FS_ROWS = [  # (csv_method, label, backbone, size)
    ("YOLO",             "YOLO",        "YOLOv11 CNN", "\\textbf{10.1M}"),
    ("FPN",              "FPN",         "ResNet-50",   "\\textit{218M}"),
    ("FPN_ReLeM",        "ReLeM-FPN",   "Transformer", "\\textit{218M}"),
    ("CCNet",            "CCNet",       "ResNet-50",   "381M"),
    ("CCNet_ReLeM",      "ReLeM-CCNet", "Transformer", "381M"),
    ("SETR_Naive",       "SeTR",        "ViT-16/B",    "723M"),
    ("SETR_MLA_ReLeM",   "ReLeM-SeTR",  "Transformer", "723M"),
    ("SETR_Naive_ReLeM", "ReLeM-SeTR",  "LSTM",        "723M"),
    ("SegMan_FS",        "SegMAN",      "Transformer", "\\uline{51.79M}"),
]


def build_model_comparisons(fs):
    rows = [(csvm, lab, bb, sz) for (csvm, lab, bb, sz) in FS_ROWS if csvm in fs]
    miou = style_col([(csvm, float(fs[csvm]["mIoU"])) for csvm, *_ in rows], higher=True)
    macc = style_col([(csvm, float(fs[csvm]["mAcc"])) for csvm, *_ in rows], higher=True)
    out = []
    for i, (csvm, lab, bb, sz) in enumerate(rows):
        shade = "\\rowcolor{gray!12}" if i % 2 else ""
        out.append(f"{shade}{lab} & {bb} & {miou[csvm]} & {macc[csvm]} & {sz} \\\\")
    return "\n".join(out)


# ------------------------------------------------ tab:temporal_module_ablation
# Seg. alone -> seg + temporal module, MEAN mAP from all_metrics.csv. Bold = best
# +Module value within each segmenter group.
ABLATION = [  # (segmenter, module-label, csv_alone, csv_withmodule)
    ("SeTR-MLA",  "+ SAM3 (SeTM+S3)",  "SETR_MLA",   "SeTM+S3"),
    ("SeTR-MLA",  "+ XMem2 (FoodMem)", "SETR_MLA",   "FoodMem"),
    ("SegMan",    "+ SAM3 (Seg+S3)",   "SegMan_ADE", "Seg+S3"),
    ("SegMan-FT", "+ XMem2 (SF+X2)",   "SegMan_FS",  "SF+X2"),
    ("YOLO",      "+ SAM3 (Y+S3)",     "YOLO",       "Y+S3"),
]


def build_ablation(meanmap):
    # best +Module per segmenter group -> bold
    best = {}
    for seg, _, _, wm in ABLATION:
        best.setdefault(seg, []).append(meanmap[wm])
    best = {s: max(v) for s, v in best.items()}
    lines = []
    for i, (seg, lab, alone, wm) in enumerate(ABLATION):
        shade = "\\rowcolor{gray!12}" if i % 2 else ""
        a, w = meanmap[alone], meanmap[wm]
        wstr = f"\\textbf{{{w:.2f}}}" if abs(w - best[seg]) < 1e-9 else f"{w:.2f}"
        lines.append(f"{shade}{seg:9} & {lab:18} & {a:.2f} & {wstr} \\\\")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    am = load_kv(f"{R}/all_metrics.csv")
    meanmap = {m: float(am[m]["MEAN"]["mAP"]) for m in am if "MEAN" in am[m]}
    sp = load_kv(f"{R}/spatial_metrics.csv")
    tp = load_kv(f"{R}/table_corrected_minimal.csv")
    eff = {r["method"]: r for r in load_rows(f"{R}/efficiency.csv")}
    fs = {r["method"]: r for r in load_rows(f"{R}/foodseg103_metrics.csv")}

    b_res, methods = build_results(sp, eff)
    b_prec = build_precision(sp, methods)
    b_temp = build_temporal(tp)
    b_fs = build_model_comparisons(fs)

    files = {
        "tab_results.tex": b_res,
        "tab_precision.tex": b_prec,
        "tab_temporal.tex": b_temp,
        "tab_model_comparisons.tex": b_fs,
        "tab_temporal_module_ablation.tex": build_ablation(meanmap),
    }
    for fn, body in files.items():
        open(f"{OUT}/{fn}", "w").write(body + "\n")
    print(f"wrote {len(files)} table bodies to {OUT}/ ; {len(methods)} BenchSeg methods, "
          f"{len([r for r in FS_ROWS if r[0] in fs])} FoodSeg103 rows")
    for fn in files:
        print(f"  {fn}")


if __name__ == "__main__":
    main()
