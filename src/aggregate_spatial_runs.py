"""Build the 5-run SPATIAL repeatability table (mean/std over runs) for the
six spatial metrics (mAP, recall, precision, f1, iou, accuracy), mirroring the
schema of results/repeatability_5runs.csv (temporal).

All methods except kMean++ are deterministic: identical predictions every run,
so their 5-run mean equals the single-run value in results/spatial_metrics.csv
and std = 0. kMean++ (k-means++ init) is genuinely re-seeded; its per-run spatial
metrics come from results/_kmspatial/run{0..4}.csv (kmeans_spatial_repeat.sbatch).

Output: results/spatial_repeatability_5runs.csv
  columns: method,partition,metric,n_runs,mean,std,min,max
"""
import csv
import glob
import os
import statistics as st

SP = "results/spatial_metrics.csv"
KM_GLOB = "results/_kmspatial/run*.csv"
OUT = "results/spatial_repeatability_5runs.csv"
METRICS = ["mAP", "recall", "precision", "f1", "iou", "accuracy"]
PARTS = ["N5K", "MTF", "VF", "FKIT"]


def main():
    # deterministic single-run values
    single = {}
    for r in csv.DictReader(open(SP)):
        single[(r["method"], r["partition"])] = r

    # kMean++ per-run values
    km = {p: {m: [] for m in METRICS} for p in PARTS}
    n_km = 0
    for f in sorted(glob.glob(KM_GLOB)):
        n_km += 1
        for r in csv.DictReader(open(f)):
            if r["method"] != "kMean++":
                continue
            for m in METRICS:
                km[r["partition"]][m].append(float(r[m]))

    rows = []
    methods = sorted({m for (m, _) in single})
    for method in methods:
        for part in PARTS:
            if (method, part) not in single and method != "kMean++":
                continue
            for metric in METRICS:
                if method == "kMean++" and km[part][metric]:
                    vals = km[part][metric]
                    mean = st.mean(vals)
                    std = st.pstdev(vals) if len(vals) > 1 else 0.0
                    rows.append([method, part, metric, len(vals),
                                 f"{mean:.4f}", f"{std:.4f}",
                                 f"{min(vals):.4f}", f"{max(vals):.4f}"])
                else:
                    r = single.get((method, part))
                    if not r:
                        continue
                    v = float(r[metric])
                    rows.append([method, part, metric, 5,
                                 f"{v:.4f}", "0.0000", f"{v:.4f}", f"{v:.4f}"])

    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["method", "partition", "metric", "n_runs", "mean", "std", "min", "max"])
        w.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} rows ({len(methods)} methods x {len(PARTS)} parts x {len(METRICS)} metrics)")
    print(f"kMean++ runs aggregated: {n_km}")
    # show kMean++ (the only nonzero-std method) summary
    mx = max((float(r[5]) for r in rows), default=0)
    print(f"max std across all cells: {mx:.4f}")
    for r in rows:
        if r[0] == "kMean++" and float(r[5]) > 0:
            print(f"  kMean++ {r[1]:4} {r[2]:9} mean={r[4]} std={r[5]}")


if __name__ == "__main__":
    main()
