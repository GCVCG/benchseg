"""Replicate deterministic methods into the 5 repeatability runs.

The repeatability runs (results/runs/run0..4) hold per-frame IoU CSVs plus a
table_corrected_run{r}.csv temporal table each. Stochastic methods (kMean++)
genuinely vary across runs; deterministic methods (segmentors and trackers,
including the +X2/+S2/+S3 hybrids) are identical across runs and were stored as
identical copies. This script adds any method present in results/per_frame_iou
but missing from run0, replicating its (deterministic) per-frame IoU and its
corrected_minimal temporal row into all 5 runs. Idempotent: methods already in
run0 are left untouched, so genuinely-stochastic runs are never overwritten.

Run AFTER run_iou_and_tables.sh has produced fresh per-frame IoU +
table_corrected_minimal.csv, then run src/aggregate_runs.py.
"""
import csv
import glob
import os
import shutil

PFI = "results/per_frame_iou"
RUNS = "results/runs"
N_RUNS = 5
TEMPORAL_SRC = "results/table_corrected_minimal.csv"


def methods_in_run0():
    return {
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(f"{RUNS}/run0/*/*.csv")
    }


def main():
    have = methods_in_run0()
    pfi_files = glob.glob(f"{PFI}/*/*.csv")
    new_methods = {
        os.path.splitext(os.path.basename(p))[0] for p in pfi_files
    } - have
    print("methods already in runs:", len(have))
    print("new methods to replicate into 5 runs:", sorted(new_methods))
    if not new_methods:
        print("nothing to do")
        return

    # 1. copy per-frame IoU into each run dir
    copied = 0
    for p in pfi_files:
        part = os.path.basename(os.path.dirname(p))
        m = os.path.splitext(os.path.basename(p))[0]
        if m not in new_methods:
            continue
        for r in range(N_RUNS):
            dst_dir = f"{RUNS}/run{r}/{part}"
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(p, f"{dst_dir}/{m}.csv")
        copied += 1
    print(f"copied per-frame IoU for {copied} (method,partition) pairs x {N_RUNS} runs")

    # 2. append new-method temporal rows (corrected_minimal) to each run table
    with open(TEMPORAL_SRC) as f:
        rd = csv.reader(f)
        header = next(rd)
        new_rows = [row for row in rd if row and row[0] in new_methods]

    for r in range(N_RUNS):
        tbl = f"{RUNS}/table_corrected_run{r}.csv"
        with open(tbl) as f:
            rd = csv.reader(f)
            next(rd)  # header
            existing = {(row[0], row[1]) for row in rd if row}
        add = [row for row in new_rows if (row[0], row[1]) not in existing]
        with open(tbl, "a", newline="") as f:
            w = csv.writer(f)
            w.writerows(add)
        print(f"run{r}: +{len(add)} temporal rows")

    print("done. now run: python src/aggregate_runs.py")


if __name__ == "__main__":
    main()
