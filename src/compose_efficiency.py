"""Compose a per-method efficiency table (Params M, Speed ms/img, peak VRAM MB)
for every BenchSeg method, from the measured component CSVs:
  results/efficiency_seg.csv      segmentor seeds (params, speed, vram)
  results/efficiency_track.csv    tracker per-frame speed + vram
  results/efficiency_trackers_params.csv   tracker params
  results/efficiency_baselines.csv heavy standalone baselines (speed, vram)
Hybrid = seed + tracker: params add, speed = tracker (dominant per-frame),
vram = max(seed, tracker). Heavy baselines with no clean harness (FoodMem, FSAM)
and seeds with no GPU param count here (FLMM) fall back to published values.
Writes results/efficiency.csv.
"""
import csv
import os

R = "results"


def load(path, key=0):
    d = {}
    if not os.path.exists(path):
        return d
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0] in ("method", "tracker"):
                continue
            d[row[0]] = row
    return d


seg = load(f"{R}/efficiency_seg.csv")          # tag -> [tag,params,speed,vram]
trk_sv = load(f"{R}/efficiency_track.csv")      # tag -> [tag,speed,vram,nframes]
trk_p = load(f"{R}/efficiency_trackers_params.csv")  # name -> [name,params]
base = load(f"{R}/efficiency_baselines.csv")    # method -> [method,speed,vram,nframes]

# published fallbacks (params_M, speed_ms, vram_MB) for methods we can't re-measure
PUB = {
    "FLMM": (7706.0, 5500.0, 14131.0),
    "FoodMem": (785.0, 25000.0, 6400.0),
    "FSAM": (636.0, 1353000.0, 12800.0),
    "BiRefNet": (220.18, None, None),  # params published; speed/VRAM measured (job 1478)
    "DEVA": (241.0, None, None),       # params published; speed/VRAM measured
}
TRK = {"xmem2": "XMem2", "sam2": "SAM2", "sam3": "SAM3"}


def seg_tag(t):
    return {"params": float(seg[t][1]) if seg[t][1] else None,
            "speed": float(seg[t][2]) if seg[t][2] else None,
            "vram": float(seg[t][3]) if seg[t][3] else None}


# table method -> segmentor seed tag
STD = {"YOLO": "YOLO", "SeTN": "SETR_Naive", "SETR_MLA": "SETR_MLA_L384",
       "CCNet": "CCNet", "CCNet-Re": "CCNet_ReLeM", "FPN-Re": "FPN_ReLeM",
       "Swin-S": "swin_small", "Swin-B": "swin_base",
       "SegMan_ADE": "SegMan_ADE", "SegMan_COCO": "SegMan_COCO", "SegMan_FS": "SegMan_FS"}
# table method -> (seed tag or 'FLMM', tracker key)
HYB = {"Y+X2": ("YOLO", "xmem2"), "Y+S2": ("YOLO", "sam2"), "Y+S3": ("YOLO", "sam3"),
       "S+X2": ("SegMan_ADE", "xmem2"), "Seg+S2": ("SegMan_ADE", "sam2"), "Seg+S3": ("SegMan_ADE", "sam3"),
       "SC+X2": ("SegMan_COCO", "xmem2"), "SC+S2": ("SegMan_COCO", "sam2"), "SC+S3": ("SegMan_COCO", "sam3"),
       "SeTM+S2": ("SETR_MLA_L384", "sam2"), "SeTM+S3": ("SETR_MLA_L384", "sam3"),
       "SF+X2": ("SegMan_FS", "xmem2"), "SF+S2": ("SegMan_FS", "sam2"), "SF+S3": ("SegMan_FS", "sam3"),
       "FLMM+X2": ("FLMM", "xmem2"), "FLMM+S2": ("FLMM", "sam2"), "FLMM+S3": ("FLMM", "sam3")}

methods = sorted({m for m in open(f"{R}/all_metrics.csv").read().splitlines()[1:]
                  if m for m in [m.split(",")[0]]})

rows, notes = [], []
for m in methods:
    p = s = v = None; src = ""
    if m in STD:
        d = seg_tag(STD[m]); p, s, v = d["params"], d["speed"], d["vram"]; src = "measured"
    elif m in HYB:
        seed, tk = HYB[m]
        tp = float(trk_p[TRK[tk]][1]); ts = float(trk_sv[tk][1]); tv = float(trk_sv[tk][2])
        if seed == "FLMM":
            sp, sv = PUB["FLMM"][0], PUB["FLMM"][2]
        else:
            dd = seg_tag(seed); sp, sv = dd["params"], dd["vram"]
        p = round(sp + tp, 2); s = ts; v = max(sv, tv); src = "composed(seed+tracker)"
    elif m in base:
        s = float(base[m][1]); v = float(base[m][2])
        p = PUB.get(m, (None,))[0]
        if m == "kMean++":
            p = None
        src = "measured" + ("" if m not in PUB else "+pub_params")
    elif m in PUB:
        p, s, v = PUB[m]; src = "published"
    else:
        src = "MISSING"; notes.append(m)
    rows.append([m, "" if p is None else round(p, 2),
                 "" if s is None else round(s, 1),
                 "" if v is None else int(round(v)), src])

with open(f"{R}/efficiency.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["method", "params_M", "speed_ms_img", "vram_MB", "source"])
    w.writerows(rows)
print(f"wrote {R}/efficiency.csv : {len(rows)} methods")
if notes:
    print("MISSING efficiency for:", notes)
for r in rows:
    print(f"  {r[0]:12} params={r[1]!s:>8} speed={r[2]!s:>8}ms vram={r[3]!s:>7} [{r[4]}]")
