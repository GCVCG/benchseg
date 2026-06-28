# Derived numbers — every prose claim tied to a CSV cell

Source of truth: `results/all_metrics.csv` (MEAN = four-partition mean), `results/spatial_metrics.csv`.
Regenerate the tables with `python scripts/build_tables.py`. This file lists each
number quoted in prose, its CSV-traced value, and the manuscript location, so prose
and tables cannot drift. **Items marked ⚠ need an author decision.**

## 1. Headline / best-model claims (MEAN over 4 partitions)

| Config | = | mAP | Recall | IoU |
|---|---|---|---|---|
| **SeTM+S3** | SeTR-MLA + SAM3 | **93.30** (best mAP) | 94.58 | 89.40 |
| **FoodMem** | SeTR-MLA + XMem2 | 92.91 | **95.22** (best Recall) | **90.02** (best IoU) |
| SF+X2 | SegMan-FT + XMem2 | 92.09 | 94.69 | 89.24 |
| SETR_MLA (SeTM) | single-frame | 92.31 | 92.88 | 86.85 |
| SegMan-FT | single-frame finetuned | 87.98 | 90.46 | 82.24 |

- **SeTM+S3 − FoodMem mAP gap = 0.39** (93.30 − 92.91). ✅ matches manuscript.
- ⚠ **Abstract (line 146) currently headlines `FoodMem` (92.91 mAP).** Per the agreed framing,
  the top-mAP model is **SeTM+S3 = SeTR-MLA+SAM3 (93.30)**; FoodMem leads Recall/IoU/temporal.
  Proposed: feature SeTM+S3 as best mAP, FoodMem as best IoU/Recall + best-in-class stability.
- Finetuning story (keep): SegMAN standalone IoU 31.95 (ADE) / 38.72 (COCO) → **82.24** (SegMan-FT);
  SF+X2 = 89.24 mean IoU. (lines 146, 836.)

## 2. Best-per-partition mAP (for any prose that names a per-partition leader)
- FKit: BiRefNet 98.65, DEVA 97.61, SeTM+S3 97.43
- N5k: BiRefNet 95.82, CCNet-Re 95.30, SeTN 95.17
- V&F: SF+S3 83.39, SeTM+S3 83.09, SF+X2 83.04
- MTF: **SF+X2 98.46**, FoodMem 98.34, SF+S3 98.24   (line 1791 — already updated)
- MEAN: SeTM+S3 93.30, FoodMem 92.91, SETR_MLA 92.31

## 3. Temporal-module ablation deltas (Step 4; MEAN mAP, seed → seed+module)
- SETR_MLA 92.31 → **SeTM+S3 93.30 = +0.99**   (SAM3 module)
- SETR_MLA 92.31 → FoodMem 92.91 = +0.60         (XMem2 module)
- SegMan 47.32 → Seg+S3 72.41 = +25.09
- SegMan-FT 87.98 → SF+X2 92.09 = +4.11
- YOLO 66.87 → Y+S3 89.44 = +22.57 ;  YOLO → Y+X2 84.86 = +17.99

## 4. ⚠ COUNT DISCREPANCY 1 — scenes: CSV says 48, manuscript says 55
`spatial_metrics.csv` n_scenes: FKit **21**, MTF **13**, N5k **10**, **V&F 4** → **48 total**.
Manuscript says 55 (FKit 21, MTF 13, V&F **11**, N5k 10). The entire discrepancy is **V&F: 4 evaluated vs 11 claimed.**
Manuscript locations and the CSV-consistent values (FKit = 43.8% of 48; non-FKit = 27 scenes):
- **line 146** (abstract): "55 dish scenes"
- **line 385** (table row): "25,284 images, 55 dishes"
- **line 605**: "25,284 images across 55 scenes"
- **line 638**: "$21$ (FKit), $13$ (MTF), $11$ (V\&F), $10$ (N5k) $=55$ scenes, i.e. FKit is $38\%$ of scenes … non-FKit partitions ($34$ scenes, $4{,}678$ frames)"
  - CSV-consistent: V&F 4 → **48 scenes**, FKit **43.8%**, non-FKit **27 scenes**.
- **DECISION NEEDED:** is the benchmark 48 (scenes actually scored) or 55 (full dataset; V&F has 11 scenes but only 4 scored)? If 55 is the intended dataset size, why does V&F score only 4 scenes? (Not changed — your call.)

## 5. ⚠ COUNT DISCREPANCY 2 — models: text says 20, CSVs have 35
The CSVs contain **35 configurations**. The text "20 models" likely means **20 base segmentation
models**, which become 35 once combined with the {XMem2, SAM2, SAM3} memory modules.
Locations: **146** (abstract), **180** (contributions), **506**, **2154** (conclusion), **2350** (appendix).
- **PROPOSAL (your call):** either (a) keep "20 base models" and add "yielding 35 configurations with
  memory modules", or (b) change to "35 configurations". Not changed — your decision.

## 6. Generator / table sync
`scripts/build_tables.py` reproduces `tab:results`, `tab:results_precision_f1_IoU`,
`tab:temporal_styled`, `tab:model_comparisons` **byte-identical** to the manuscript (verified).
Not CSV-derivable (separate experiments): `tab:masks_ablation`, `tab:temporal_grouped_method`
(M = #input-masks), `tab:efficiency` (GPU-utilization microbenchmark).
