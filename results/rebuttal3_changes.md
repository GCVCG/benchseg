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
