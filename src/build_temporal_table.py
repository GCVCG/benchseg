"""Aggregate per-frame IoU logs into the temporal-stability table.

Reads per-frame IoU CSVs (from ``per_frame_iou.py``), groups frames into ordered
scenes, computes the four temporal metrics per scene, then macro-averages across
scenes within each partition -- exactly the aggregation the manuscript states:
"All temporal metrics are first averaged per-scene and then macro-averaged across
scenes within each partition." (tab:temporal_styled, sec:temporal_metrics).

Two continuity modes:
  * corrected: C_gamma = fraction of adjacent pairs with BOTH IoU >= gamma.
  * buggy:     1 - mean|dIoU|  (the shipped bug; reproduces the OLD table).

The buggy mode exists so we can demonstrate the pipeline reproduces the published
numbers, then show the corrected column is the only thing that moves.
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
from collections import defaultdict

import numpy as np

import temporal_metrics as tm


def load_per_frame_iou(csv_paths):
    """Return {(method, partition): {scene: [iou ordered by frame]}}."""
    data = defaultdict(lambda: defaultdict(list))
    raw = defaultdict(lambda: defaultdict(list))  # (m,p)->scene->[(frame, iou)]
    for path in csv_paths:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                key = (row["method"], row["partition"])
                try:
                    frame = float(row["frame"])
                except (ValueError, TypeError):
                    frame = 0.0
                raw[key][row["scene"]].append((frame, float(row["iou"])))
    for key, scenes in raw.items():
        for scene, pairs in scenes.items():
            pairs.sort(key=lambda t: t[0])
            data[key][scene] = [iou for _, iou in pairs]
    return data


# Named profiles controlling the three independent toggles.
#   continuity: "buggy" (1 - drift, shipped) | "corrected" (C_gamma)
#   flicker:    "symmetric" (shipped |dIoU|>d) | "drops" (manuscript drops-only)
#   sigma:      "pooled" (shipped std over all frames) | "per_scene" (manuscript)
PROFILES = {
    "old_repro":          {"continuity": "buggy",     "flicker": "symmetric", "sigma": "pooled"},
    "corrected_minimal":  {"continuity": "corrected", "flicker": "symmetric", "sigma": "pooled"},
    "corrected_aligned":  {"continuity": "corrected", "flicker": "drops",     "sigma": "per_scene"},
}


def aggregate(scene_iou: dict, cfg: tm.TemporalConfig, profile: dict) -> dict:
    """Per-scene metrics then macro-average for one method/partition under a profile."""
    use_buggy = profile["continuity"] == "buggy"
    symmetric = profile["flicker"] == "symmetric"
    pooled_sigma = profile["sigma"] == "pooled"

    per_scene = []
    for scene, ious in scene_iou.items():
        cont = (tm.continuity_buggy(ious, cfg.gamma) if use_buggy
                else tm.continuity(ious, cfg.gamma))
        per_scene.append({
            "continuity": cont,
            "flicker": tm.flicker(ious, cfg.delta, symmetric=symmetric),
            "drift": tm.drift(ious),
            "sigma": tm.volatility(ious),
        })
    agg = tm.macro_average(per_scene)

    if pooled_sigma:
        # Shipped behaviour: sample std over ALL frames in the partition (ddof=1).
        all_frames = [v for ious in scene_iou.values() for v in ious]
        agg["sigma"] = float(np.std(all_frames, ddof=1)) if len(all_frames) > 1 else None

    def scene_std(key):
        vals = [s[key] for s in per_scene if s.get(key) is not None]
        return float(np.std(vals)) if len(vals) > 1 else 0.0

    agg.update({k + "_std": scene_std(k) for k in ("continuity", "flicker", "drift", "sigma")})
    return agg


def build_table(csv_paths, cfg: tm.TemporalConfig, profile_name: str = "corrected_minimal"):
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile {profile_name}; choose {list(PROFILES)}")
    profile = PROFILES[profile_name]
    data = load_per_frame_iou(csv_paths)
    rows = []
    for (method, partition), scene_iou in sorted(data.items()):
        agg = aggregate(scene_iou, cfg, profile)
        rows.append(
            {
                "method": method,
                "partition": partition,
                "continuity": agg["continuity"],
                "flicker": agg["flicker"],
                "drift": agg["drift"],
                "sigma": agg["sigma"],
                "continuity_std": agg["continuity_std"],
                "flicker_std": agg["flicker_std"],
                "drift_std": agg["drift_std"],
                "sigma_std": agg["sigma_std"],
                "n_scenes": agg["n_scenes_used"],
            }
        )
    return rows


def write_table(rows, out_csv: str, as_percent: bool = True):
    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
    scale = 100.0 if as_percent else 1.0
    fields = [
        "method", "partition", "continuity", "flicker", "drift", "sigma",
        "continuity_std", "flicker_std", "drift_std", "sigma_std", "n_scenes",
    ]
    metric_cols = {"continuity", "flicker", "drift", "sigma",
                   "continuity_std", "flicker_std", "drift_std", "sigma_std"}
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = dict(r)
            for c in metric_cols:
                v = out[c]
                out[c] = "" if v is None else round(v * scale, 4)
            w.writerow(out)
    return out_csv


def main():
    ap = argparse.ArgumentParser(description="Build temporal-stability table from per-frame IoU.")
    ap.add_argument("--iou_csv", nargs="+", required=True, help="per-frame IoU CSV(s) or globs")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--gamma", type=float, default=tm.DEFAULT_GAMMA)
    ap.add_argument("--delta", type=float, default=tm.DEFAULT_DELTA)
    ap.add_argument("--profile", default="corrected_minimal", choices=list(PROFILES),
                    help="old_repro | corrected_minimal | corrected_aligned")
    ap.add_argument("--fraction", action="store_true", help="write 0-1 instead of percent")
    args = ap.parse_args()

    paths = []
    for p in args.iou_csv:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p])
    cfg = tm.TemporalConfig(gamma=args.gamma, delta=args.delta)
    rows = build_table(paths, cfg, profile_name=args.profile)
    write_table(rows, args.out_csv, as_percent=not args.fraction)
    print(f"[{args.profile}] {len(rows)} method/partition rows -> {args.out_csv}")


if __name__ == "__main__":
    main()
