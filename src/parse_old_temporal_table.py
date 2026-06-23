"""Parse the OLD (published) temporal table tab:temporal_styled from the manuscript.

Extracts the per-method mean (and std) values for the four metrics across the
four partitions plus the four Global columns, into a tidy CSV. These are the
BASELINE numbers used for the Step-3 diff and Step-4 ranking, and to verify that
our buggy-mode recomputation reproduces the published values.

Column layout in the .tex (per the header rows):
  Method | C_t(%) x4 | FR_0.2(%) x4 | dIoU(%) x4 | sIoU(%) x4 | Global x4
partition order within each group: FKIT, MTF, N5K, V&F
Global order: C_t, FR, dIoU, sIoU
Each method has a mean row followed by a std row.
"""

from __future__ import annotations

import argparse
import csv
import os
import re

PARTITIONS = ["FKIT", "MTF", "N5K", "V&F"]
GROUPS = ["continuity", "flicker", "drift", "sigma"]


def _clean(cell: str) -> str:
    """Strip LaTeX styling from a table cell, leaving the bare token."""
    s = cell
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\underline\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\uline\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\rowcolor\{[^}]*\}", "", s)
    s = re.sub(r"\\cmidrule(\([^)]*\))?\{[^}]*\}", "", s)
    s = re.sub(r"\\(midrule|toprule|bottomrule|centering|addlinespace|tiny|small)\b", "", s)
    s = s.replace("\\blacktriangle", "").replace("\\triangle", "")
    s = s.replace("$", "").replace("\\%", "").replace("\\,", "")
    return s.strip()


def _num(cell: str):
    c = _clean(cell)
    m = re.search(r"-?\d+\.?\d*", c)
    return float(m.group()) if m else None


def _extract_table_block(tex: str) -> str:
    i = tex.find("\\label{tab:temporal_styled}")
    if i < 0:
        raise ValueError("tab:temporal_styled not found")
    start = tex.find("\\midrule", i)
    end = tex.find("\\bottomrule", start)
    return tex[start:end]


def parse(tex_path: str):
    with open(tex_path) as f:
        tex = f.read()
    block = _extract_table_block(tex)

    # Split into LaTeX rows on '\\', drop separators.
    raw_rows = []
    for line in block.split("\\\\"):
        line = line.strip()
        if not line or line.startswith("\\midrule") or "\\addlinespace" in line and "&" not in line:
            # keep lines that contain data cells
            pass
        if "&" in line:
            raw_rows.append(line)

    rows = []
    # Data rows come in (mean, std) pairs; the mean row starts with a method label.
    i = 0
    records = []
    for line in raw_rows:
        line = re.sub(r"\\addlinespace", "", line).strip()
        cells = [c for c in line.split("&")]
        if len(cells) < 21:
            continue
        records.append(cells)

    # Pair up: a "mean" row has a non-empty first cell (method name); the
    # following row (empty first cell) is its std.
    out = []
    k = 0
    while k < len(records):
        cells = records[k]
        label = _clean(cells[0])
        if label == "":
            k += 1
            continue
        mean_cells = cells[1:21]
        std_cells = None
        if k + 1 < len(records) and _clean(records[k + 1][0]) == "":
            std_cells = records[k + 1][1:21]
        means = [_num(c) for c in mean_cells]
        stds = [_num(c) for c in std_cells] if std_cells else [None] * 20
        # 4 groups x 4 partitions = first 16; last 4 = global
        for gi, group in enumerate(GROUPS):
            for pi, part in enumerate(PARTITIONS):
                idx = gi * 4 + pi
                out.append({
                    "method": label,
                    "partition": part,
                    "metric": group,
                    "old_value": means[idx],
                    "old_std": stds[idx],
                })
        # Global columns (partition = GLOBAL)
        for gi, group in enumerate(GROUPS):
            out.append({
                "method": label,
                "partition": "GLOBAL",
                "metric": group,
                "old_value": means[16 + gi],
                "old_std": stds[16 + gi],
            })
        k += 2 if std_cells else 1
    return out


def write_csv(records, out_csv):
    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["method", "partition", "metric", "old_value", "old_std"])
        w.writeheader()
        w.writerows(records)
    return out_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default="elsarticle-template-num.tex")
    ap.add_argument("--out_csv", default="results/temporal_metrics_old.csv")
    args = ap.parse_args()
    recs = parse(args.tex)
    write_csv(recs, args.out_csv)
    methods = sorted({r["method"] for r in recs})
    print(f"Parsed {len(methods)} methods, {len(recs)} cells -> {args.out_csv}")
    print("Methods:", ", ".join(methods))


if __name__ == "__main__":
    main()
