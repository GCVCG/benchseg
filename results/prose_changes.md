# Prose number changes (mirror these into 03_rebuttal.tex)

All edits are wrapped in `\change{}`. Source: regenerated result CSVs.

## Headline (abstract, line ~146)
- OLD: "Our strongest configuration combines SeTR-MLA with XMem2 (FoodMem), reaching
  **92.91% mAP and 90.02% IoU** … best-in-class temporal stability."
- NEW: "Our strongest configuration pairs SeTR-MLA with the SAM3 memory module
  (**SeTM+S3**), reaching **93.30% mAP** … narrowly ahead of SeTR-MLA+XMem2
  (**FoodMem, 92.91% mAP**) which leads on Recall (95.22%), IoU (90.02%) and temporal
  stability." + finetuning: SegMAN IoU 31.95/38.72 → **82.24**, SF+X2 **89.24** mean IoU.

## Model count: 20 → 35 (5 locations)
- 146 (abstract): "20 state-of-the-art segmentation models" → "a diverse set … benchmark **35 configurations**".
- 180 (contributions item): "20 state-of-the-art models are evaluated" → "**35 configurations** … are evaluated".
- 506: "We train 20 state-of-the-art models on FoodSeg103" → "train … segmenters on FoodSeg103 and evaluate **35 configurations**".
- 2154 (conclusion): "across 20 state-of-the-art segmentation architectures" → "across **35 evaluated configurations**".
- 2350 (appendix): "discuss the 20 state-of-the-art models" → "discuss the … models … which yield **35 configurations** on BenchSeg".

## Scene count: UNCHANGED at 55 (your decision)
- Kept 55 (FKit 21, MTF 13, V&F 11, N5k 10); FKit = 38%; non-FKit = 34 scenes.
- NOTE for rebuttal: the spatial std/n_scenes in the tables aggregate the **scored** scenes
  (V&F contributes 4 scored scenes); the 55 figure is the full dataset.

## Temporal-module ablation (tab:temporal_module_ablation + surrounding text)
- Rebuilt to MEAN mAP. Sentence OLD: "largest for the weakest … (YOLO, **+15.81**)".
  NEW: "largest for the weakest … (**SegMan +25.09** with SAM3, **YOLO +22.57** with SAM3),
  while SeTR-MLA gains little (**+0.99** SAM3, **+0.60** XMem2); SegMan-FT + XMem2 adds **+4.11**."
- Footnote OLD: "ranges from **+2.71** (SegMAN+SAM2) to **+15.81** (YOLO+XMem2)".
  NEW: "ranges from **+0.60** (SeTR-MLA+XMem2) to **+25.09** (SegMan+SAM3)".

## Already updated in prior commit 380579b (for completeness)
- FKit precision: 97.09/91.99 → **96.97/91.87** (line ~798).
- Best MTF mAP: SeTM+X2 96.32 → **SF+X2 98.46** (FoodMem 98.34) (line ~1791).
- BiRefNet MTF/V&F continuity collapse → **48.8 / 36.2**.
- Stats paragraph: removed self-referential "SeTM+X2 vs FoodMem +5.56 (77.08)"; now
  memory-vs-seed gain **+2.34 Recall** (N5k 97.96→99.01), mAP **+0.60**.
- FoodMem efficiency: published 785M/25s → composed **373.7M / 542ms / 9.4GB** (= SeTR-MLA+XMem2).

## R1-minor-3 / R3.8 rebuttal note (temporal-module ablation)
Adding a training-free memory/propagation module improves four-partition MEAN mAP for
every segmenter, with the largest gains for the weakest single-frame models (SegMan +25.09,
YOLO +22.57 with SAM3) and marginal gains for the already-strong SeTR-MLA (+0.99/+0.60),
supporting the claim that temporal propagation compensates for poor per-frame predictions.
