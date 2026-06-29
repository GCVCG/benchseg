"""View-change-magnitude analysis (R3.8): bin frames by the GT view-change proxy
(vc = 1 - IoU(GT_t, GT_{t-1})) into Low/Med/High tertiles, then report each
method's mean per-frame IoU in each bin. Shows whether memory-augmented methods
degrade less than per-frame-only methods as the viewpoint change grows.

Inputs:  results/view_change_gt.csv, results/per_frame_iou/<part>/<method>.csv
Outputs: results/view_magnitude_bins.csv + results/tables/tab_view_magnitude.tex
"""
import csv
import glob
import os
import numpy as np

# representative per-frame vs memory/hybrid methods (display name -> per_frame_iou file stem)
METHODS = [
    ("BiRefNet", "BiRefNet"), ("SeTR-MLA", "SETR_MLA"), ("YOLO", "YOLO"), ("SegMan", "SegMan_ADE"),
    ("FoodMem", "FoodMem"), ("SeTM+S3", "SeTM+S3"), ("Y+X2", "Y+X2"), ("Seg+S3", "Seg+S3"),
]
FAMILY = {"BiRefNet": "per-frame", "SeTR-MLA": "per-frame", "YOLO": "per-frame", "SegMan": "per-frame",
          "FoodMem": "memory/hybrid", "SeTM+S3": "memory/hybrid", "Y+X2": "memory/hybrid", "Seg+S3": "memory/hybrid"}


def load_vc():
    vc = {}
    for r in csv.DictReader(open("results/view_change_gt.csv")):
        if r["vc"] != "":
            vc[(r["partition"], r["scene"], str(r["frame"]))] = float(r["vc"])
    return vc


def load_method_iou(stem):
    out = {}
    for f in glob.glob(f"results/per_frame_iou/*/{stem}.csv"):
        for r in csv.DictReader(open(f)):
            out[(r["partition"], r["scene"], str(r["frame"]))] = float(r["iou"])
    return out


def main():
    vc = load_vc()
    vals = np.array(list(vc.values()))
    t1, t2 = np.percentile(vals, [33.33, 66.67])
    print(f"vc tertiles: Low<{t1:.3f}<=Med<{t2:.3f}<=High  (n={len(vals)} frame pairs)")

    def binof(v):
        return "Low" if v < t1 else ("Med" if v < t2 else "High")

    rows = []
    for disp, stem in METHODS:
        miou = load_method_iou(stem)
        bins = {"Low": [], "Med": [], "High": []}
        for k, v in vc.items():
            if k in miou:
                bins[binof(v)].append(miou[k] * 100)
        means = {b: (np.mean(bins[b]) if bins[b] else float("nan")) for b in bins}
        drop = means["Low"] - means["High"]
        rows.append([disp, FAMILY[disp]] + [f"{means[b]:.1f}" for b in ("Low", "Med", "High")] + [f"{drop:.1f}"])
        print(f"  {disp:10} ({FAMILY[disp]:12}) Low={means['Low']:.1f} Med={means['Med']:.1f} "
              f"High={means['High']:.1f}  drop(Low-High)={drop:.1f}")

    with open("results/view_magnitude_bins.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "family", "iou_low_vc", "iou_med_vc", "iou_high_vc", "drop_low_minus_high"])
        w.writerows(rows)

    # LaTeX
    L = [r"\begin{table}[htb]", r"\centering", r"\footnotesize",
         r"\caption{\change{Mean per-frame IoU (\%) by view-change magnitude (R3.8). Frames are binned "
         r"into Low/Med/High tertiles of the GT view-change proxy $vc=1-\mathrm{IoU}(\mathrm{GT}_t,\mathrm{GT}_{t-1})$. "
         r"$\Delta$ is the Low$-$High drop; smaller is more robust to viewpoint change.}}",
         r"\label{tab:view_magnitude}", r"\begin{tabular}{llcccc}", r"\toprule",
         r"\textbf{Method} & \textbf{Family} & \textbf{Low} & \textbf{Med} & \textbf{High} & \textbf{$\Delta$} \\",
         r"\midrule"]
    for r in rows:
        L.append(" & ".join(r) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    os.makedirs("results/tables", exist_ok=True)
    open("results/tables/tab_view_magnitude.tex", "w").write("\n".join(L) + "\n")
    print("wrote results/view_magnitude_bins.csv + results/tables/tab_view_magnitude.tex")


if __name__ == "__main__":
    main()
