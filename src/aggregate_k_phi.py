"""Aggregate the FULL K/Phi ablation (all 18 hybrids) into per-scene CSVs, a
coverage report, a per-config ablation table, and a cross-config robustness
summary. Uses the same metric definitions as spatial_metrics.frame_metrics
(mAP==precision, IoU) and temporal_metrics (gated continuity C_gamma at
gamma=0.5, flicker FR_0.2, IoU drift).

SAFE TO RUN AT ANY TIME and doubles as the daily-harvest tool: it skips
configs/partitions not yet complete and reports exactly what is done.

Speed: ground truth for a partition is decoded ONCE and reused across all
configs (the naive per-config re-read made this ~100x slower). Restrict work
with --parts to the finished partitions, e.g. --parts N5K,VF,MTF, so it does not
read huge not-yet-ablated anchors (FKit).

Layout:
  base (no reset / keep_propagated) : data/preds/<PART>/<method>       (main-table preds)
  injection configs                 : data/preds_kphi/<method>__<key>/<PART>
Outputs (results/ablation_k_phi/): <method>__<key>.csv (per scene) + summary.csv
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_metrics import index, split_scene, IMG_EXTS  # noqa: E402
import temporal_metrics as tm  # noqa: E402

GT = {"N5K": "data/n5k_reordered/masks", "MTF": "data/mtf_foodMem_reordered/masks",
      "VF": "data/vf_reordered/masks", "FKIT": "data/FoodKit_dataset_reordered/masks"}
PARTS = ["N5K", "MTF", "VF", "FKIT"]
SPATIAL = ["precision", "recall", "f1", "iou", "accuracy"]

HYBRIDS = ["FoodMem", "S+X2", "SC+X2", "SF+X2", "Y+X2", "FLMM+X2",
           "SeTM+S2", "Seg+S2", "SC+S2", "SF+S2", "Y+S2", "FLMM+S2",
           "SeTM+S3", "Seg+S3", "SC+S3", "SF+S3", "Y+S3", "FLMM+S3"]
KEYS = ["base", "K10", "K20", "K30", "K45", "K60", "K30_accept_fresh", "K30_union"]
KLAB = {"base": "K=inf", "K10": "K=10", "K20": "K=20", "K30": "K=30",
        "K45": "K=45", "K60": "K=60", "K30_accept_fresh": "accept_fresh", "K30_union": "union"}
K_ROWS = ["K10", "K20", "K30", "K45", "K60", "base"]
PHI_ROWS = ["K30", "base", "K30_accept_fresh", "K30_union"]


def frame_no(base):
    try:
        return int(base.rsplit("_", 1)[-1])
    except ValueError:
        return 0


def preds_dir(preds_root, kphi_root, method, key, part):
    if key == "base":
        return os.path.join(preds_root, part, method)
    return os.path.join(kphi_root, f"{method}__{key}", part)


def load_gt_cache(gt_dir):
    """{stem: bool ndarray} for one partition, decoded once."""
    cache = {}
    for f in os.listdir(gt_dir):
        if f.lower().endswith(IMG_EXTS):
            cache[os.path.splitext(f)[0]] = np.array(Image.open(os.path.join(gt_dir, f)).convert("L")) > 0
    return cache


def count_gt(gt_dir):
    """Cheap frame count (no decode) for the progress print in --workers mode."""
    return sum(1 for f in os.listdir(gt_dir) if f.lower().endswith(IMG_EXTS))


# --- process-pool worker: each worker decodes the partition GT once into a
# process-local cache, so big arrays are never pickled across processes. ---
_WGT = None


def _winit(gt_dir):
    global _WGT
    _WGT = load_gt_cache(gt_dir)


def _weval(mk_dir):
    method, key, pred_dir = mk_dir
    return method, key, eval_dir(pred_dir, _WGT)


def frame_metric(pred_path, gt):
    """Identical formula to spatial_metrics.frame_metrics, but GT is preloaded."""
    if pred_path and os.path.exists(pred_path):
        try:
            pred = np.array(Image.open(pred_path).convert("L"), dtype=np.uint8) > 0
        except Exception:
            pred = np.zeros_like(gt)
    else:
        pred = np.zeros_like(gt)
    if pred.shape != gt.shape:
        pim = Image.fromarray(pred.astype(np.uint8) * 255).resize((gt.shape[1], gt.shape[0]), Image.NEAREST)
        pred = np.array(pim, dtype=np.uint8) > 0
    tp = int(np.count_nonzero(pred & gt)); fp = int(np.count_nonzero(pred & ~gt))
    fn = int(np.count_nonzero(~pred & gt)); tn = int(np.count_nonzero(~pred & ~gt))
    prec = tp / (tp + fp) if (tp + fp) else (1.0 if fn == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / (tp + tn + fp + fn)
    return dict(precision=prec, recall=rec, f1=f1, iou=iou, accuracy=acc)


def eval_dir(pred_dir, gt_cache):
    """Per-scene spatial means (x100) + temporal metrics (x100) using cached GT.
    Returns None if the config is absent or incomplete for this partition."""
    if not os.path.isdir(pred_dir):
        return None
    preds = index(pred_dir)
    if len(preds) < len(gt_cache):
        return None
    by_scene = defaultdict(list)
    for base, gt in gt_cache.items():
        pf = preds.get(base)
        m = frame_metric(os.path.join(pred_dir, pf) if pf else None, gt)
        by_scene[split_scene(base)].append((frame_no(base), m))
    out = {}
    for scene, items in by_scene.items():
        items.sort(key=lambda t: t[0])
        sp = {k: float(np.mean([mm[k] for _, mm in items])) * 100 for k in SPATIAL}
        t = tm.scene_metrics([mm["iou"] for _, mm in items], tm.TemporalConfig(gamma=0.5, delta=0.2))
        out[scene] = {**sp,
                      "continuity": None if t["continuity"] is None else t["continuity"] * 100,
                      "flicker": None if t["flicker"] is None else t["flicker"] * 100,
                      "drift": None if t["drift"] is None else t["drift"] * 100,
                      "n_frames": t["n_frames"]}
    return out


def macro(part_scene):
    keys = SPATIAL + ["continuity", "flicker", "drift"]
    per_part = {p: {k: (float(np.mean([s[k] for s in sc.values() if s.get(k) is not None]))
                        if any(s.get(k) is not None for s in sc.values()) else None) for k in keys}
                for p, sc in part_scene.items()}
    overall = {k: (float(np.mean([per_part[p][k] for p in per_part if per_part[p].get(k) is not None]))
                   if any(per_part[p].get(k) is not None for p in per_part) else None) for k in keys}
    return overall, per_part


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds_root", default="data/preds")
    ap.add_argument("--kphi_root", default="data/preds_kphi")
    ap.add_argument("--out_dir", default="results/ablation_k_phi")
    ap.add_argument("--parts", default="", help="comma subset of N5K,MTF,VF,FKIT (default all)")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallelize config-cells across N processes (1 = sequential, bit-identical)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    parts = [p for p in a.parts.split(",") if p] or PARTS

    # partition-outer so each partition's GT is decoded exactly once
    results = defaultdict(dict)   # (method,key) -> {part: scene-metrics}
    for part in parts:
        gt_dir = GT[part]
        if not os.path.isdir(gt_dir):
            continue
        got = defaultdict(int)
        if a.workers > 1:
            print(f"# {part}: GT cached per-worker ({count_gt(gt_dir)} frames, {a.workers} workers)", flush=True)
            tasks = [(method, key, preds_dir(a.preds_root, a.kphi_root, method, key, part))
                     for method in HYBRIDS for key in KEYS]
            with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit, initargs=(gt_dir,)) as ex:
                for fut in as_completed([ex.submit(_weval, t) for t in tasks]):
                    method, key, res = fut.result()
                    if res is not None:
                        results[(method, key)][part] = res
                        got[method] += 1
            for mi, method in enumerate(HYBRIDS, 1):
                print(f"#   {part} [{mi}/18] {method}: {got[method]}/{len(KEYS)} settings complete", flush=True)
        else:
            gt_cache = load_gt_cache(gt_dir)
            print(f"# {part}: GT cached ({len(gt_cache)} frames)", flush=True)
            for mi, method in enumerate(HYBRIDS, 1):
                for key in KEYS:
                    res = eval_dir(preds_dir(a.preds_root, a.kphi_root, method, key, part), gt_cache)
                    if res is not None:
                        results[(method, key)][part] = res
                        got[method] += 1
                print(f"#   {part} [{mi}/18] {method}: {got[method]}/{len(KEYS)} settings complete", flush=True)
            gt_cache.clear()

    agg, coverage = {}, {}
    for method in HYBRIDS:
        for key in KEYS:
            ps = results.get((method, key), {})
            coverage[(method, key)] = [p for p in parts if p in ps]
            if not ps:
                continue
            rows = []
            for part in parts:
                for scene, m in sorted(ps.get(part, {}).items()):
                    rows.append([method, key, part, scene] + [f"{m[k]:.4f}" for k in SPATIAL] +
                                [("" if m[k] is None else f"{m[k]:.4f}") for k in ("continuity", "flicker", "drift")] +
                                [m["n_frames"]])
            with open(os.path.join(a.out_dir, f"{method}__{key}.csv"), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["method", "config", "partition", "scene"] + SPATIAL +
                           ["continuity", "flicker", "drift", "n_frames"])
                w.writerows(rows)
            agg[(method, key)] = macro(ps)

    def cell(m, k, metric):
        v = agg.get((m, k))
        return None if (v is None or v[0].get(metric) is None) else v[0][metric]

    def fnum(x, w=6):
        return (" " * (w - 2) + "--") if x is None else f"{x:{w}.2f}"

    ndone = sum(1 for k in coverage if coverage[k])
    print(f"\n% ==== COVERAGE ({ndone}/{len(coverage)} config-cells complete on >=1 partition) ====")
    print("% method            " + " ".join(f"{KLAB[k]:>12}" for k in KEYS))
    for method in HYBRIDS:
        print(f"% {method:16} " + " ".join(f"{(','.join(coverage.get((method,k),[])) or '-'):>12}" for k in KEYS))

    print("\n% ==== PER-CONFIG: mAP / C_gamma at each setting (macro over completed partitions) ====")
    for method in HYBRIDS:
        if not any(agg.get((method, k)) for k in KEYS):
            continue
        print(f"% {method}")
        for key in KEYS:
            mp, cg = cell(method, key, "precision"), cell(method, key, "continuity")
            if mp is None and cg is None:
                continue
            print(f"%    {KLAB[key]:14} mAP={fnum(mp)}  C={fnum(cg)}  "
                  f"flick={fnum(cell(method,key,'flicker'))}  drift={fnum(cell(method,key,'drift'))}")

    def summarize(keys_subset, title):
        print(f"\n% ---- {title}: mean over completed configs (n) + mean |delta vs base| ----")
        print("% setting        n   meanMAP   meanC   |dMAP|_vs_base  |dC|_vs_base")
        for key in keys_subset:
            maps = [cell(m, key, "precision") for m in HYBRIDS if cell(m, key, "precision") is not None]
            cs = [cell(m, key, "continuity") for m in HYBRIDS if cell(m, key, "continuity") is not None]
            dmap = [abs(cell(m, key, "precision") - cell(m, "base", "precision")) for m in HYBRIDS
                    if cell(m, key, "precision") is not None and cell(m, "base", "precision") is not None]
            dc = [abs(cell(m, key, "continuity") - cell(m, "base", "continuity")) for m in HYBRIDS
                  if cell(m, key, "continuity") is not None and cell(m, "base", "continuity") is not None]
            g = lambda v: f"{np.mean(v):.2f}" if v else "--"
            print(f"%   {KLAB[key]:12} {len(maps):>3}  {g(maps):>8} {g(cs):>7}  {g(dmap):>14}  {g(dc):>12}")

    summarize(K_ROWS, "K sweep (overlap_gated)")
    summarize(PHI_ROWS, "Phi sweep (K=30)")

    flagged = [f"{m}__{k}(mAP={agg[(m,k)][0]['precision']:.1f},flick={agg[(m,k)][0]['flicker']:.2f})"
               for (m, k) in agg if agg[(m, k)][0].get("flicker") is not None
               and agg[(m, k)][0].get("precision") is not None
               and agg[(m, k)][0]["flicker"] < 1.0 and agg[(m, k)][0]["precision"] < 70]
    print("\n% degenerate-flag (flicker<1.0 AND mAP<70): " + ("; ".join(flagged) if flagged else "none"))

    with open(os.path.join(a.out_dir, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "config", "partitions_done", "mAP", "C_gamma", "flicker", "drift"])
        for method in HYBRIDS:
            for key in KEYS:
                o = agg.get((method, key))
                w.writerow([method, key, "|".join(coverage.get((method, key), []))] +
                           ["" if (o is None or o[0].get(k) is None) else f"{o[0][k]:.4f}"
                            for k in ("precision", "continuity", "flicker", "drift")])
    print(f"\n% per-scene CSVs + summary.csv -> {a.out_dir}/")


if __name__ == "__main__":
    main()
