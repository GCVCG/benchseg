# Rebuttal 3 — required corrections (verified against current CSVs)

All NEW values traced to `results/all_metrics.csv` / `efficiency.csv`. Reviewer
*quotes* (`\itshape` cmtbox) are left untouched; only **Response/Change** text changes.

## A. SAM2 → SAM3 naming error (systematic — the labels are swapped)
The repo/CSV convention is `+S2 = SAM2`, `+S3 = SAM3`. The headline `SeTM+S3` and
`FLMM+S3` are **SAM3**, not SAM2. Their numbers are right; only the word "SAM2" is wrong.
1. **R1.6 minor 2 (Response):** "the headline method (SeTR-MLA combined with **SAM2**) is distinct"
   → "(SeTR-MLA combined with **SAM3**)".
2. **R2.1 (Response):** "to $83.09$ when coupled with **SAM2** (SeTM+S3)"
   → "coupled with **SAM3** (SeTM+S3)".
3. **R1.4 (Response):** "**FoodLMM+SAM2** reaches mean mAP $75.72$ and continuity $70.31$"
   → "**FoodLMM+SAM3** reaches mean mAP $75.72$ and continuity $70.31$"
   (75.72/70.31 = FLMM+S3 = SAM3; FLMM+S2/SAM2 is only 44.07/17.51).

## B. Stale numbers
4. **R1.3 (Response):** FKit precision "namely **97.09 and 91.99** respectively"
   → "namely **96.97 and 91.87** respectively". (CSV: SeTR-MLA 96.97, CCNet 91.87.)
5. **R1.6 minor 1 (Response):** "the weak BenchSeg mAP obtained by YOLO, namely **56.91** on FKit"
   → "**59.70** on FKit". (CSV: YOLO FKit mAP = 59.70.)
   Also reconcile the 71.5 framing: the manuscript now reports YOLO under the **same dense
   104-class mIoU** as all methods (**22.61**), so reword to: "We now evaluate YOLO under the
   identical dense 104-class semantic mIoU protocol (22.61), replacing the previously-listed
   Ultralytics instance-mask score (71.5); the two are not directly comparable."
6. **R1 minor 3 (Response):** "ranges from **$+2.71$ to $+15.81$** and is largest for the
   weakest segmenter, **YOLO**" → "ranges from **$+0.60$ to $+25.09$** and is largest for the
   weakest segmenters (**SegMan $+25.09$, YOLO $+22.57$** with SAM3)".
7. **R3.8 (Change):** "a gain in mean mAP from **$+2.71$ to $+15.81$**, which is largest for the
   weakest segmenter" → "from **$+0.60$ to $+25.09$**, largest for the weakest segmenters".
8. **R2.4 (Response):** "YOLO requires 10.1M parameters at **2.9 ms** per image, whereas FoodMem
   requires **785M** parameters at **25 s** per image."
   → "YOLO requires 10.1M parameters at **56.6 ms** per image, whereas FoodMem (the SeTR-MLA+XMem2
   pipeline) requires **373.7M** parameters at **542 ms** per image."
   (CSV efficiency: YOLO 10.12/56.6; FoodMem 373.72/541.5; FoodMem == SeTR-MLA+XMem2.)

## C. Model count 20 → 35 (Responses only; keep reviewer quotes verbatim)
9. **Cover letter:** "a single zero-shot protocol over **20 models**" → "over **35 configurations**".
10. **R4.1 (Response):** "the **20-model** comparison" → "the **35-configuration** comparison".
- KEEP as-is (reviewer quotes): R3.3 "Although 20 models have been evaluated…", R1.5/R4.1 "55 scenes".

## D. Already correct in rebuttal 3 (no change)
SeTM+S3 93.30 / FoodMem 92.91 / gap 0.39; R2.1 SeTR-MLA 80.01 → 83.09; FLMM 49.21/43.90/35.42;
DoraemonGPT 32.27/26.12; 5-run std 0.29%; the continuity (R4.2) correction narrative; 55 scenes.

## E. Run-to-run stability surfaced in manuscript (post-V&F, last change)
Reason: rebuttal R1.4 and R4.4 claimed a "regenerated the full table five times" stability
check, but it appeared nowhere in the manuscript — a reviewer cross-checking would not find it.
Backing data: results/repeatability_5runs.csv, results/spatial_repeatability_5runs.csv,
results/foodseg103_repeatability_5runs.csv (5 runs each).

Manuscript (docs_work/elsarticle-template-num.tex, Reproducibility section):
- Added \subsection{Run-to-run stability} (\label{sec:repeatability}): 34/35 configs
  bit-identical across 5 runs (per-cell std = 0); only kMean++ stochastic (k-means++ init),
  max per-cell std 0.29% across all metrics/partitions; FoodSeg103 table also bit-identical.
- Added summary table \label{tab:repeatability} (worst-case per-metric std):
  kMean++ max sigma  -> mAP 0.04, Recall 0.10, IoU 0.04, C_t 0.10, FR 0.29, dIoU 0.06
  Other 34 methods   -> 0.00 on every metric.
  Numbers verified against results/repeatability_5runs.csv:
  continuity max std 0.1011 (kMean++/MTF), flicker 0.2927 (kMean++/N5K), drift 0.0634,
  sigma 0.0148; spatial mAP 0.0383, recall 0.0974, iou 0.0354 (all kMean++).

Rebuttal (docs_work/rebuttal.tex):
- R1.4 and R4.4: appended a pointer to the new "Run-to-run stability" subsection/table so the
  five-times claim is now verifiable in the manuscript; noted per-run CSVs are in the release.

Verified: table floats balanced 29/29; active tabulars 25/25 (35/34 raw counts commented-out
template blocks). No new experiments required — all reviewer-requested experiments already run.

## F. Ablation tables verified current (no change needed)
Checked whether the mask-count (M=1,3,6,9, first vs random) and memory-size ablation tables in
the manuscript reflect the complete-V&F data. Regenerated both via src/build_ablation_tables.py
and diffed row-by-row against docs_work/elsarticle-template-num.tex.

- tab:masks_ablation (\label): 12/12 data rows MATCH the freshly-built table (Y+X2, S+X2, SF+X2
  x M in {1,3,6,9}). The "random" column IS present — last column, mean+/-std over 3 draws.
- tab:memory_ablation (\label): 4/4 rows MATCH (working memory 4/10/20/40).

Where the random draws live:
- In the paper: the "random" column of tab:masks_ablation (first-M vs random-M folded into one
  table, per earlier decision — not two separate tables).
- Raw data: results/ablation_spatial_{FKIT,MTF,N5K,VF}.csv, rows named <combo>_M<M>_r{0,1,2}
  (e.g. Y+X2_M3_r0/r1/r2); build_ablation_tables.py averages r0/r1/r2 into mean+/-std cells.

Outcome: no edit required — both ablation tables already regenerated on complete V&F; random
results present. (Open option: split random draws into a standalone table if desired.)

## G. Donut per-frame mAP extended to all 35 configs (for Fig 7/8 3D plots)
The old results/donut_per_frame_map.csv covered only 16 methods (the original figure set);
the other 25 configs were missing (user-flagged). Root cause: local data/preds/FKIT held only
14 dirs; all 35 donut prediction dirs (780 masks each) live on the cluster.

- src/donut_per_frame.py: METHODS replaced with the full 35 canonical configs (method column
  == prediction dir == all_metrics.csv name).
- Ran on cluster (login node), regenerated on complete predictions, synced back:
  results/donut_per_frame_map.csv  = 27,300 rows (35 x 780), cols method,frame,mAP,recall,iou,accuracy
  results/donut_pie_bins.csv       = 35 rows, bins <=50 / 50-75 / 75-95 / >=95 (counts + %)
- Verified: methods == all_metrics.csv set exactly (0 missing, 0 extra); 780 frames per method.

NAMING CHANGE: method column now uses canonical names (FLMM, SETR_MLA, SeTM+S3, SegMan_ADE,
Y+X2, ...) instead of the old figure display aliases (FoodLMM, SeTR-MLA, SegMan, YOLO+XMem2).
Fig 7/8 plotting code keyed on the old 16 display names must remap those aliases.

3D RENDER STILL PENDING (not blocking data): the actual Fig-7 camera-location plots need each
donut frame's 3D camera position (SfM/COLMAP), which is NOT in the repo or data drives. Per user
decision, we deliver the CSVs only; plotting to be done in the user's existing pipeline.
