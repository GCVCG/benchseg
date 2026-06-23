"""Aggregate corrected-table CSVs from N repeat runs into per-cell mean +/- std.

Reads results/runs/table_corrected_run*.csv (each a wide table from
build_temporal_table) and reports, for every (method, partition, metric), the
mean and std across runs. Deterministic methods give std=0; stochastic ones
(kMean++, possibly FoodLMM) reveal their run-to-run variance. A large std flags
a non-reproducible cell.
"""
import argparse, csv, glob, os
from collections import defaultdict
import numpy as np

METRICS = ["continuity", "flicker", "drift", "sigma"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="results/runs/table_corrected_run*.csv")
    ap.add_argument("--out", default="results/repeatability_5runs.csv")
    a = ap.parse_args()
    files = sorted(glob.glob(a.glob))
    if not files:
        print(f"no run files matching {a.glob}")
        return
    vals = defaultdict(list)  # (method,partition,metric) -> [run values]
    for fp in files:
        for r in csv.DictReader(open(fp)):
            for m in METRICS:
                if r.get(m) not in (None, ""):
                    vals[(r["method"], r["partition"], m)].append(float(r[m]))

    rows = []
    for (method, part, metric), vs in sorted(vals.items()):
        arr = np.array(vs)
        rows.append({
            "method": method, "partition": part, "metric": metric,
            "n_runs": len(vs), "mean": round(arr.mean(), 4),
            "std": round(arr.std(ddof=1) if len(vs) > 1 else 0.0, 4),
            "min": round(arr.min(), 4), "max": round(arr.max(), 4),
        })
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["method", "partition", "metric", "n_runs", "mean", "std", "min", "max"])
        w.writeheader(); w.writerows(rows)

    print(f"{len(files)} runs -> {a.out}")
    worst = sorted(rows, key=lambda r: r["std"], reverse=True)[:10]
    print("Largest run-to-run std (potential non-determinism):")
    for r in worst:
        print(f"  {r['method']:>10} {r['partition']:>5} {r['metric']:<10} mean={r['mean']:>7} std={r['std']:>6} [{r['min']}, {r['max']}]")
    print(f"max std across all cells: {max(r['std'] for r in rows):.4f}")


if __name__ == "__main__":
    main()
