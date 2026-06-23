"""Emit the corrected temporal table as a drop-in LaTeX replacement for
tab:temporal_styled. Reproduces the column layout (C_t / FR / dIoU / sIoU x
{FKIT,MTF,N5K,V&F} + Global), the mean-over-std two-row format, and top-3
styling per column (bold/underline/italic). Only methods with computed data are
emitted, ordered as in the manuscript.
"""
import argparse, csv
from collections import defaultdict

PARTS = ["FKIT", "MTF", "N5K", "VF"]
PART_TEX = {"FKIT": "FKIT", "MTF": "MTF", "N5K": "N5K", "VF": "V\\&F"}
# manuscript row order (method label as it appears in our tables)
ORDER = ["FLMM", "Y+X2", "FoodMem", "S+X2", "Y+S2", "DEVA", "BiRefNet", "Seg+S2",
         "kMean++", "SegMan", "CCNet", "Swin-B", "CCNet-Re", "FSAM", "SeTN",
         "FPN-Re", "Swin-S", "YOLO"]
HIGHER_BETTER = {"continuity": True, "flicker": False, "drift": False, "sigma": False}


def load(path):
    d = defaultdict(dict)
    for r in csv.DictReader(open(path)):
        d[r["method"]][r["partition"]] = r
    return d


def style(val, rank):
    s = f"{val:.1f}"
    if rank == 0:
        return f"\\textbf{{{s}}}"
    if rank == 1:
        return f"\\underline{{{s}}}"
    if rank == 2:
        return f"\\textit{{{s}}}"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="results/table_corrected_minimal.csv")
    ap.add_argument("--out", default="results/temporal_table_corrected.tex")
    a = ap.parse_args()
    data = load(a.table)
    methods = [m for m in ORDER if m in data] + [m for m in data if m not in ORDER]

    # build value matrix: vals[metric][part] = {method: meanvalue}
    cols = []  # (metric, part)
    for metric in ("continuity", "flicker", "drift", "sigma"):
        for p in PARTS:
            cols.append((metric, p))
    # global per metric = mean across available parts
    def gmean(m, metric):
        vs = [float(data[m][p][metric]) for p in PARTS if p in data[m] and data[m][p].get(metric)]
        return sum(vs) / len(vs) if vs else None

    # rank within each column for top-3 styling
    def ranks(values):  # values: {method: val}; returns {method: rank}
        order = sorted(values.items(), key=lambda kv: kv[1], reverse=hb)
        return {m: i for i, (m, _) in enumerate(order)}

    rank_map = {}
    for metric, p in cols:
        hb = HIGHER_BETTER[metric]
        vals = {m: float(data[m][p][metric]) for m in methods if p in data[m] and data[m][p].get(metric) not in (None, "")}
        rank_map[(metric, p)] = ranks(vals)
    grank = {}
    for metric in ("continuity", "flicker", "drift", "sigma"):
        hb = HIGHER_BETTER[metric]
        vals = {m: gmean(m, metric) for m in methods if gmean(m, metric) is not None}
        grank[metric] = ranks(vals)

    lines = [
        "\\begin{table}[!htb]", "\\centering", "\\tiny", "\\setlength{\\tabcolsep}{1pt}",
        "\\caption{Temporal metrics across datasets (CORRECTED continuity $C_\\gamma$). "
        "Higher is better ($\\uparrow$) for continuity; lower ($\\downarrow$) for flicker, drift, $\\sigma$IoU. "
        "Top-3 per column styled.}",
        "\\label{tab:temporal_styled}",
        "\\begin{tabular}{l" + "c" * 20 + "}", "\\toprule",
        "\\textbf{Method} & \\multicolumn{4}{c}{$C_{\\gamma}$(\\%)$\\uparrow$} & "
        "\\multicolumn{4}{c}{$FR_{0.2}$(\\%)$\\downarrow$} & \\multicolumn{4}{c}{$\\Delta IoU$(\\%)$\\downarrow$} & "
        "\\multicolumn{4}{c}{$\\sigma IoU$(\\%)$\\downarrow$} & \\multicolumn{4}{c}{Global} \\\\",
        "\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}\\cmidrule(lr){10-13}\\cmidrule(lr){14-17}\\cmidrule(lr){18-21}",
        "mean$\\pm$std & " + " & ".join(PART_TEX[p] for _ in range(4) for p in PARTS).replace(
            ", ", " & ") + " & $C_\\gamma$ & $FR$ & $\\Delta IoU$ & $\\sigma IoU$ \\\\",
        "\\midrule",
    ]
    for m in methods:
        mean_cells, std_cells = [], []
        for metric, p in cols:
            r = data[m].get(p)
            if r and r.get(metric) not in (None, ""):
                mean_cells.append(style(float(r[metric]), rank_map[(metric, p)].get(m, 9)))
                std_cells.append(f"{float(r.get(metric + '_std', 0) or 0):.1f}")
            else:
                mean_cells.append("--"); std_cells.append("")
        for metric in ("continuity", "flicker", "drift", "sigma"):
            g = gmean(m, metric)
            mean_cells.append(style(g, grank[metric].get(m, 9)) if g is not None else "--")
            std_cells.append("")
        lines.append(f"{m} & " + " & ".join(mean_cells) + " \\\\")
        lines.append(" & " + " & ".join(std_cells) + " \\\\")
        lines.append("\\addlinespace")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]

    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {a.out} ({len(methods)} methods)")


if __name__ == "__main__":
    main()
