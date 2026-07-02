"""Per-frame mAP (= precision for a binary mask) for the FoodKit 'donut' scene,
per method. Backs Fig.~\\ref{fig:3d_comparasions} (pose colouring by mAP threshold)
and Fig.~\\ref{fig:dist_comparasions} (pie of frames per mAP range).

Outputs:
  results/donut_per_frame_map.csv   method,frame,mAP,recall,iou,accuracy
  results/donut_pie_bins.csv        method,n_frames,le50,r50_75,r75_95,ge95  (counts + %)
Run on the cluster (needs masks).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_metrics import frame_metrics, index  # noqa: E402

GT = "data/FoodKit_dataset_reordered/masks"
SCENE = "donut"
# all 35 canonical configurations (method column == prediction dir == all_metrics.csv name)
CONFIGS = [
    "BiRefNet", "CCNet", "CCNet-Re", "DEVA", "DoraemonGPT",
    "FLMM", "FLMM+S2", "FLMM+S3", "FLMM+X2", "FPN-Re", "FSAM", "FoodMem",
    "S+X2", "SC+S2", "SC+S3", "SC+X2", "SETR_MLA", "SF+S2", "SF+S3", "SF+X2",
    "SeTM+S2", "SeTM+S3", "SeTN", "Seg+S2", "Seg+S3",
    "SegMan_ADE", "SegMan_COCO", "SegMan_FS", "Swin-B", "Swin-S",
    "Y+S2", "Y+S3", "Y+X2", "YOLO", "kMean++",
]
METHODS = [(c, c) for c in CONFIGS]


def bin_of(m):  # m in [0,100]
    if m <= 50: return "le50"
    if m <= 75: return "r50_75"
    if m < 95:  return "r75_95"
    return "ge95"


def main():
    gts = index(GT)
    donut = sorted(b for b in gts if b.split("_")[0] == SCENE)
    print(f"donut frames in GT: {len(donut)}")
    rows, pies = [], []
    for disp, mdir_name in METHODS:
        mdir = os.path.join("data/preds/FKIT", mdir_name)
        if not os.path.isdir(mdir):
            print(f"  MISSING {disp} ({mdir_name})"); continue
        preds = index(mdir)
        bins = {"le50": 0, "r50_75": 0, "r75_95": 0, "ge95": 0}
        n = 0
        for base in donut:
            pf = preds.get(base)
            if pf is None:
                continue
            m = frame_metrics(os.path.join(mdir, pf), os.path.join(GT, gts[base]))
            mAP = m["precision"] * 100
            frame_no = int(base.split("_")[-1])
            rows.append([disp, frame_no, f"{mAP:.4f}", f"{m['recall']*100:.4f}",
                         f"{m['iou']*100:.4f}", f"{m['accuracy']*100:.4f}"])
            bins[bin_of(mAP)] += 1
            n += 1
        pies.append([disp, n] + [bins[k] for k in ("le50", "r50_75", "r75_95", "ge95")]
                    + [f"{100*bins[k]/n:.1f}" for k in ("le50", "r50_75", "r75_95", "ge95")])
        print(f"  {disp:12} n={n}  <=50:{bins['le50']:3} 50-75:{bins['r50_75']:3} "
              f"75-95:{bins['r75_95']:3} >=95:{bins['ge95']:3}")

    os.makedirs("results", exist_ok=True)
    with open("results/donut_per_frame_map.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["method", "frame", "mAP", "recall", "iou", "accuracy"]); w.writerows(rows)
    with open("results/donut_pie_bins.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "n_frames", "le50", "r50_75", "r75_95", "ge95",
                    "le50_pct", "r50_75_pct", "r75_95_pct", "ge95_pct"]); w.writerows(pies)
    print(f"wrote results/donut_per_frame_map.csv ({len(rows)} rows) + results/donut_pie_bins.csv")


if __name__ == "__main__":
    main()
