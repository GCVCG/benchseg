# Table audit — cell-to-CSV trace + changed highlights

Generator: `python scripts/build_tables.py` → `results/tables/*.tex` (drop-in bodies).
Every metric cell is read from a CSV; bold(best)/uline(2nd)/italic(3rd) are computed
programmatically per column. No metric is hand-typed.

## Per-table trace
| Table | Manuscript label | Cells trace to | Status |
|---|---|---|---|
| tab_results | tab:results | mAP/Recall = spatial_metrics.csv (precision=mAP, recall); std = `*_std`; Params/Speed/VRAM = efficiency.csv | byte-identical to manuscript ✅ |
| tab_precision | tab:results_precision_f1_IoU | precision/f1/iou/accuracy + `*_std` = spatial_metrics.csv | byte-identical ✅ |
| tab_temporal | tab:temporal_styled | continuity/flicker/drift/sigma = table_corrected_minimal.csv (+ `*_std`); Global = mean over 4 partitions | byte-identical ✅ |
| tab_model_comparisons | tab:model_comparisons | mIoU/mAcc = foodseg103_metrics.csv; Backbone/Size = fixed metadata (not metrics) | byte-identical ✅ |
| tab_temporal_module_ablation | tab:temporal_module_ablation | Seg.alone & +Module = all_metrics.csv MEAN mAP | **rebuilt** (see below) |

## Changed cells / highlights

### tab:temporal_module_ablation — rebuilt from non-traceable values
Old cells (could not be traced to any CSV metric) → new CSV-traced MEAN mAP:
| Row | OLD alone/+mod | NEW alone/+mod (MEAN mAP) |
|---|---|---|
| SeTR-MLA + SAM3 (SeTM+S3) | — | 92.31 / **93.30** |
| SeTR-MLA + XMem2 (FoodMem) | 89.40 / 93.21 | 92.31 / 92.91 |
| SegMan + SAM3 (Seg+S3) | (was SegMAN+XMem2 88.25/92.21) | 47.32 / **72.41** |
| SegMan-FT + XMem2 (SF+X2) | *(new row)* | 87.98 / **92.09** |
| YOLO + SAM3 (Y+S3) | (was YOLO+XMem2 65.67/81.49) | 66.87 / **89.44** |
Removed old rows: SegMAN+SAM2 (88.25/90.96). Module focus changed XMem2→SAM3 to match
the new headline (SeTM+S3). Bold = best +Module per segmenter group.

### tab:results / precision / temporal / model_comparisons
No change vs the current manuscript (generator reproduces them byte-identically). All
highlights are the regenerated 35-method values from the prior commits (f406163/0ab83e1).
The duplicate SeTM+X2 row was removed earlier as a FoodMem duplicate (FoodMem == SeTR-MLA+XMem2).

## Verification performed
- `\rowcolor` confirmed functional in this TeX; **0 column-count errors** across all 5 bodies
  (tab_results 12 cols, precision 17, temporal 21, model_comparisons 5, ablation 4).
- 4/5 bodies byte-identical to the committed manuscript (which compiles).
- Full `pdflatex` of the manuscript not run here: `elsarticle.cls` is not in this repo
  (the class/bib/figures live in the full manuscript project). No `\ref` targets a removed
  row (table rows are not `\label` targets; only table-level labels exist, all intact).
