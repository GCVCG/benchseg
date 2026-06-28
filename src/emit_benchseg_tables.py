"""Emit BenchSeg LaTeX table bodies from the regenerated metric CSVs.

  tab:results                 -> mAP + Recall (x4 partitions) + Efficiency
  tab:results_precision_f1_IoU -> Precision/F1/IoU/Accuracy (x4)
  tab:temporal_styled          -> continuity/flicker/drift/sigma (x4) + Global

Two-row mean/std format, per-column top-3 styling (bold/underline/italic).
Sources: results/spatial_metrics.csv, results/table_corrected_minimal.csv,
results/efficiency.csv.  Run: python src/emit_benchseg_tables.py
"""
import csv
from collections import defaultdict

SP = "results/spatial_metrics.csv"
TP = "results/table_corrected_minimal.csv"
EF = "results/efficiency.csv"

# display label per all_metrics method id
DISP = {"SegMan_ADE": "SegMan", "SegMan_COCO": "SegMan-C", "SegMan_FS": "SegMan-FT",
        "S+X2": "Seg+X2", "SETR_MLA": "SeTM"}


def disp(m):
    return DISP.get(m, m)


def load(path):
    d = defaultdict(dict)
    for r in csv.DictReader(open(path)):
        d[r["method"]][r["partition"]] = r
    return d


def load_eff(path):
    d = {}
    for r in csv.DictReader(open(path)):
        d[r["method"]] = r
    return d


def fmt(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return "--"


def style_col(rows, key, higher=True, nd=2):
    """rows: list of (method, value-or-None). returns {method: styled str}."""
    vals = [(m, v) for m, v in rows if v is not None]
    order = sorted(vals, key=lambda x: x[1], reverse=higher)
    rank = {m: i for i, (m, _) in enumerate(order)}
    out = {}
    for m, v in rows:
        if v is None:
            out[m] = "--"; continue
        s = fmt(v, nd)
        r = rank.get(m, 99)
        out[m] = f"\\textbf{{{s}}}" if r == 0 else f"\\uline{{{s}}}" if r == 1 else f"\\textit{{{s}}}" if r == 2 else s
    return out


def emit_results(methods, sp, eff):
    # partition order for mAP & Recall
    PO = ["FKIT", "N5K", "VF", "MTF"]
    # mean values per method per (metric,part); mAP == precision in this pipeline
    def val(m, part, k):
        r = sp.get(m, {}).get(part)
        return float(r[k]) if r and r.get(k) not in (None, "") else None
    # build styled cells
    cells = {}
    for metric, src in (("mAP", "precision"), ("recall", "recall")):
        for part in PO:
            rows = [(m, val(m, part, src)) for m in methods]
            cells[(metric, part)] = style_col(rows, src, higher=True)
    # efficiency styled (smaller better)
    def effv(m, k):
        r = eff.get(disp_inv.get(m, m)) or eff.get(m)
        return float(r[k]) if r and r.get(k) not in (None, "") else None
    eff_cells = {}
    for k in ("params_M", "speed_ms_img", "vram_MB"):
        rows = [(m, effv(m, k)) for m in methods]
        eff_cells[k] = style_col(rows, k, higher=False, nd=1)
    # std lookups
    def std(m, part, k):
        r = sp.get(m, {}).get(part)
        return r.get(k) if r else None
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)]
                          + [cells[("mAP", p)][m] for p in PO]
                          + [cells[("recall", p)][m] for p in PO]
                          + [eff_cells["params_M"][m], eff_cells["speed_ms_img"][m], eff_cells["vram_MB"][m]])
        stds = (["", ] + [fmt(std(m, p, "precision_std")) for p in PO]
                + [fmt(std(m, p, "recall_std")) for p in PO] + ["", "", ""])
        std_row = " & ".join(stds)
        lines.append(f"{shade}{mean} \\\\\n {std_row} \\\\ \\addlinespace[2pt]")
    return "\n".join(lines)


def emit_precision(methods, sp):
    PO = ["FKIT", "MTF", "N5K", "VF"]
    METRICS = [("precision", "precision_std"), ("f1", "f1_std"),
               ("iou", "iou_std"), ("accuracy", "accuracy_std")]
    cells = {}
    for mk, _ in METRICS:
        for part in PO:
            rows = [(m, (lambda r: float(r[mk]) if r and r.get(mk) not in (None, "") else None)(sp.get(m, {}).get(part)))
                    for m in methods]
            cells[(mk, part)] = style_col(rows, mk, higher=True)
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)] + [cells[(mk, p)][m] for mk, _ in METRICS for p in PO])
        def std(p, sk):
            r = sp.get(m, {}).get(p); return fmt(r[sk]) if r and r.get(sk) else "--"
        std_row = " & ".join([""] + [std(p, sk) for _, sk in METRICS for p in PO])
        lines.append(f"{shade}{mean} \\\\\n {std_row} \\\\ \\addlinespace[3pt]")
    return "\n".join(lines)


def emit_temporal(methods, tp):
    PO = ["FKIT", "MTF", "N5K", "VF"]
    MET = [("continuity", True), ("flicker", False), ("drift", False), ("sigma", False)]
    def v(m, p, k):
        r = tp.get(m, {}).get(p); return float(r[k]) if r and r.get(k) not in (None, "") else None
    def g(m, k):  # global = mean over partitions
        xs = [v(m, p, k) for p in PO]; xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    cells = {}
    for k, hi in MET:
        for part in PO:
            cells[(k, part)] = style_col([(m, v(m, part, k)) for m in methods], k, higher=hi, nd=1)
        cells[(k, "G")] = style_col([(m, g(m, k)) for m in methods], k, higher=hi, nd=1)
    lines = []
    for i, m in enumerate(methods):
        shade = "\\rowcolor{gray!12}\n" if i % 2 else ""
        mean = " & ".join([disp(m)] + [cells[(k, p)][m] for k, _ in MET for p in PO]
                          + [cells[(k, "G")][m] for k, _ in MET])
        def std(p, k):
            r = tp.get(m, {}).get(p); return fmt(r[k + "_std"], 1) if r and r.get(k + "_std") else "--"
        std_row = " & ".join([""] + [std(p, k) for k, _ in MET for p in PO] + ["", "", "", ""])
        lines.append(f"{shade}{mean} \\\\\n {std_row} \\\\ \\addlinespace[2pt]")
    return "\n".join(lines)


disp_inv = {disp(m): m for m in DISP}

sp = load(SP)
tp = load(TP)
eff = load_eff(EF)
def fkit(m, src):
    r = src.get(m, {}).get("FKIT")
    return float(r["precision" if src is sp else "continuity"]) if r else 1e9
methods = sorted(sp.keys(), key=lambda m: fkit(m, sp))
tmethods = sorted([m for m in tp if m in sp], key=lambda m: fkit(m, tp))

b1 = emit_results(methods, sp, eff)
b2 = emit_precision(methods, sp)
b3 = emit_temporal(tmethods, tp)
open("results/tab_results_body.tex", "w").write(b1 + "\n")
open("results/tab_precision_body.tex", "w").write(b2 + "\n")
open("results/tab_temporal_body.tex", "w").write(b3 + "\n")
print(f"wrote 3 table bodies: results={len(methods)} prec={len(methods)} temporal={len(tmethods)} methods")
print("--- tab:results (first 6 lines) ---"); print("\n".join(b1.splitlines()[:6]))
print("--- tab:precision (first 4) ---"); print("\n".join(b2.splitlines()[:4]))
print("--- tab:temporal (first 4) ---"); print("\n".join(b3.splitlines()[:4]))
