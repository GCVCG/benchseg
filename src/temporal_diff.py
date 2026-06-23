"""Diff a recomputed temporal table (NEW) against the published table (OLD).

Produces a long-format CSV with one row per (method, partition, metric):
    method, partition, metric, old, new, delta, abs_delta
sorted by abs_delta descending, so the largest changes surface first.

NEW comes from build_temporal_table.py (wide: continuity/flicker/drift/sigma
columns, partitions FKIT/MTF/N5K/VF). OLD comes from parse_old_temporal_table.py
(long: metric column, partitions FKIT/MTF/N5K/V&F + GLOBAL). The partition label
``VF`` in NEW maps to ``V&F`` in OLD. A GLOBAL row per method/metric is computed
for NEW as the mean across the four partitions (matching the manuscript's Global
columns).
"""

import argparse
import csv
import os
from collections import defaultdict

METRICS = ["continuity", "flicker", "drift", "sigma"]
PART_MAP = {"VF": "V&F"}  # NEW label -> OLD label


def load_new(path):
    """Return {(method, partition_old, metric): value} from the wide NEW table."""
    out = {}
    by_method_metric = defaultdict(list)
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            m = r["method"]
            p = PART_MAP.get(r["partition"], r["partition"])
            for metric in METRICS:
                if r.get(metric) not in (None, ""):
                    v = float(r[metric])
                    out[(m, p, metric)] = v
                    by_method_metric[(m, metric)].append(v)
    # GLOBAL = mean across available partitions
    for (m, metric), vals in by_method_metric.items():
        if vals:
            out[(m, "GLOBAL", metric)] = sum(vals) / len(vals)
    return out


def load_old(path):
    """Baseline values. Auto-detects long (published: method,partition,metric,old_value)
    vs wide (our own table: continuity/flicker/drift/sigma columns)."""
    with open(path, newline="") as f:
        header = csv.DictReader(f).fieldnames or []
    if "old_value" in header:  # long published table
        out = {}
        for r in csv.DictReader(open(path, newline="")):
            if r.get("old_value") in (None, ""):
                continue
            try:
                out[(r["method"], r["partition"], r["metric"])] = float(r["old_value"])
            except (ValueError, TypeError):
                pass
        return out
    # wide table (e.g. our old_repro): reuse load_new layout
    return load_new(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new_csv", required=True, help="recomputed table (wide, one profile)")
    ap.add_argument("--old_csv", default="results/temporal_metrics_old.csv")
    ap.add_argument("--out_csv", default="results/temporal_metrics_diff.csv")
    ap.add_argument("--include_global", action="store_true")
    args = ap.parse_args()

    new = load_new(args.new_csv)
    old = load_old(args.old_csv)

    rows = []
    keys = set(new) | set(old)
    for (method, part, metric) in keys:
        if part == "GLOBAL" and not args.include_global:
            continue
        o = old.get((method, part, metric))
        n = new.get((method, part, metric))
        if o is None or n is None:
            delta = abs_delta = None
        else:
            delta = round(n - o, 4)
            abs_delta = round(abs(n - o), 4)
        rows.append({
            "method": method, "partition": part, "metric": metric,
            "old": o, "new": (round(n, 4) if n is not None else None),
            "delta": delta, "abs_delta": abs_delta,
        })

    rows.sort(key=lambda r: (r["abs_delta"] is not None, r["abs_delta"] or 0), reverse=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)
    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["method", "partition", "metric", "old", "new", "delta", "abs_delta"])
        w.writeheader()
        w.writerows(rows)

    # Console summary: biggest movers + spatial-metric sanity (none should exist here).
    paired = [r for r in rows if r["abs_delta"] is not None]
    print(f"{len(rows)} cells -> {args.out_csv} ({len(paired)} comparable)")
    print("Top 10 movers:")
    for r in paired[:10]:
        print(f"  {r['method']:>10} {r['partition']:>5} {r['metric']:<10} "
              f"old={r['old']:>6} new={r['new']:>7} Δ={r['delta']:>7}")
    moved = defaultdict(int)
    for r in paired:
        if r["abs_delta"] and r["abs_delta"] > 0.5:
            moved[r["metric"]] += 1
    print("Cells changed >0.5 by metric:", dict(moved))


if __name__ == "__main__":
    main()
