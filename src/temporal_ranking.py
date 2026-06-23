"""Rank-preservation check: OLD vs NEW orderings for continuity and flicker.

For each partition (and GLOBAL) it ranks methods by continuity (higher is better)
and by flicker (lower is better), reports the top-3 under OLD and NEW, and the
Spearman rank correlation between the two orderings over the methods present in
both tables. This is the Step-4 evidence that the bug fix does not change the
benchmark's conclusions.

NEW: wide table from build_temporal_table.py (partitions FKIT/MTF/N5K/VF).
OLD: long table from parse_old_temporal_table.py (+ GLOBAL).
"""

import argparse
import csv
from collections import defaultdict

import numpy as np

PART_MAP = {"VF": "V&F"}
PARTS = ["FKIT", "MTF", "N5K", "V&F", "GLOBAL"]
# (metric, higher_is_better)
RANKED = [("continuity", True), ("flicker", False)]


def load_new(path):
    out = {}
    bymm = defaultdict(list)
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            p = PART_MAP.get(r["partition"], r["partition"])
            for metric in ("continuity", "flicker", "drift", "sigma"):
                if r.get(metric) not in (None, ""):
                    v = float(r[metric])
                    out[(r["method"], p, metric)] = v
                    bymm[(r["method"], metric)].append(v)
    for (m, metric), vals in bymm.items():
        out[(m, "GLOBAL", metric)] = sum(vals) / len(vals)
    return out


def load_old(path):
    with open(path, newline="") as f:
        header = csv.DictReader(f).fieldnames or []
    if "old_value" not in header:  # wide table (our own old_repro)
        return load_new(path)
    out = {}
    for r in csv.DictReader(open(path, newline="")):
        if r.get("old_value") in (None, ""):
            continue
        try:
            out[(r["method"], r["partition"], r["metric"])] = float(r["old_value"])
        except (ValueError, TypeError):
            pass
    return out


def spearman(order_a, order_b):
    """Spearman rho between two rank dicts {method: rank} over shared methods."""
    common = sorted(set(order_a) & set(order_b))
    if len(common) < 2:
        return None, len(common)
    a = np.array([order_a[m] for m in common], dtype=float)
    b = np.array([order_b[m] for m in common], dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None, len(common)
    rho = float(np.corrcoef(a, b)[0, 1])
    return rho, len(common)


def ranks_from_values(values: dict, higher_is_better: bool):
    """values: {method: value} -> {method: rank} (1 = best)."""
    items = sorted(values.items(), key=lambda kv: kv[1], reverse=higher_is_better)
    return {m: i + 1 for i, (m, _) in enumerate(items)}, [m for m, _ in items]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new_csv", required=True)
    ap.add_argument("--old_csv", default="results/temporal_metrics_old.csv")
    args = ap.parse_args()
    new = load_new(args.new_csv)
    old = load_old(args.old_csv)

    print(f"{'metric':<10} {'partition':<7} {'rho':>6} {'n':>3}  top3_OLD -> top3_NEW")
    print("-" * 78)
    rhos = []
    for metric, hib in RANKED:
        for part in PARTS:
            old_vals = {m: old[(m, part, metric)] for (m, p, mt) in old
                        if p == part and mt == metric and (m, part, metric) in old}
            new_vals = {m: new[(m, part, metric)] for (m, p, mt) in new
                        if p == part and mt == metric}
            common = set(old_vals) & set(new_vals)
            if len(common) < 2:
                continue
            old_vals = {m: old_vals[m] for m in common}
            new_vals = {m: new_vals[m] for m in common}
            old_rank, old_order = ranks_from_values(old_vals, hib)
            new_rank, new_order = ranks_from_values(new_vals, hib)
            rho, n = spearman(old_rank, new_rank)
            rhos.append(rho if rho is not None else np.nan)
            top_old = ", ".join(old_order[:3])
            top_new = ", ".join(new_order[:3])
            rho_s = f"{rho:.3f}" if rho is not None else "  -  "
            print(f"{metric:<10} {part:<7} {rho_s:>6} {n:>3}  [{top_old}] -> [{top_new}]")
    valid = [r for r in rhos if r == r]
    if valid:
        print("-" * 78)
        print(f"mean Spearman rho across cells: {np.mean(valid):.3f} (min {np.min(valid):.3f})")


if __name__ == "__main__":
    main()
