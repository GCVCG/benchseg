"""Join spatial + temporal metric tables into one comprehensive all-metrics table.
Output: results/all_metrics.csv with method x partition (N5K/MTF/VF/FKIT + MEAN)
and all 10 headline metrics (6 spatial + 4 temporal)."""
import argparse, csv, os
from collections import defaultdict

SPATIAL = ["mAP", "recall", "precision", "f1", "iou", "accuracy"]
TEMPORAL = ["continuity", "flicker", "drift", "sigma"]
ALL = SPATIAL + TEMPORAL
PARTS = ["N5K", "MTF", "VF", "FKIT"]


def load(path):
    d = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            d[(r["method"], r["partition"])] = r
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spatial", default="results/spatial_metrics.csv")
    ap.add_argument("--temporal", default="results/table_corrected_minimal.csv")
    ap.add_argument("--out", default="results/all_metrics.csv")
    a = ap.parse_args()

    sp, tp = load(a.spatial), load(a.temporal)
    keys = sorted(set(sp) | set(tp))
    methods = sorted({m for m, _ in keys})
    perm = defaultdict(dict)
    rows = []
    for (m, p) in keys:
        s, t = sp.get((m, p), {}), tp.get((m, p), {})
        row = {"method": m, "partition": p}
        for k in SPATIAL:
            row[k] = s.get(k, "")
        for k in TEMPORAL:
            row[k] = t.get(k, "")
        rows.append(row)
        perm[m][p] = row

    # four-partition mean per method (only over partitions present)
    for m in methods:
        mean = {"method": m, "partition": "MEAN"}
        for k in ALL:
            vals = [float(perm[m][p][k]) for p in PARTS
                    if p in perm[m] and perm[m][p].get(k) not in ("", None)]
            mean[k] = round(sum(vals) / len(vals), 2) if vals else ""
        rows.append(mean)

    order = {p: i for i, p in enumerate(PARTS + ["MEAN"])}
    rows.sort(key=lambda r: (r["method"], order.get(r["partition"], 9)))
    cols = ["method", "partition"] + ALL
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"wrote {a.out}: {len(rows)} rows, {len(methods)} methods")
    # report any method missing either family
    for m in methods:
        for p in perm[m]:
            r = perm[m][p]
            miss = [k for k in ALL if r.get(k) in ("", None)]
            if miss:
                print(f"  incomplete {m}/{p}: missing {miss}")


if __name__ == "__main__":
    main()
