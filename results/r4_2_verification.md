# R4.2 — Temporal continuity bug: verification note

**Issue (Reviewer 4.2).** FoodLMM was reported with continuity ≈ 100 % despite
per-frame IoU below the quality threshold γ = 0.5 at (essentially) every frame.

**Root cause (confirmed).** The shipped aggregator computed continuity as
`C = 1 − ΔIoU` (one minus the mean absolute frame-to-frame IoU change) instead of
the defined gated indicator
`C_γ = (1/(T−1)) Σ_t 1[IoU_{t−1} ≥ γ ∧ IoU_t ≥ γ]`.
The quality threshold γ was therefore never applied: a sequence that is *flat but
bad* (constant low or zero IoU → ΔIoU = 0) is scored as 100 % continuity.
This is verifiable directly in the published table: across **all 90 cells**
(18 methods × 5 columns), the reported continuity equals `100 − ΔIoU` exactly,
and the per-scene std of continuity equals that of drift, row for row.

**Fix.** Continuity is now the gated indicator `C_γ` (γ = 0.5), evaluated per
scene and macro-averaged across scenes (unchanged aggregation policy). It is 0
exactly when no adjacent frame pair has both IoUs ≥ γ, and is undefined
(excluded) for scenes with T < 2. Defaults γ = 0.5, δ = 0.2 are read from config.
Unit tests in `tests/test_temporal_metrics.py` pin the corrected definitions and
the bug (`continuity_buggy` reproduces the `1 − drift` behaviour); 14/14 pass.

**Validation that only the *aggregation* changed (not the data).** We recomputed
every metric from regenerated per-frame IoU and confirmed the pipeline reproduces
the *published* numbers under the buggy formula ("old_repro"): on N5k the
reproduction is exact and on MTF within ~1–4 % for the 7 directly-runnable
methods (YOLO + 6 FoodSeg segmentors). Example — SeTR-Naive: N5k 98.8/0.0/1.2/3.2
(published) vs 98.8/0.0/1.2/3.2 (reproduced). Flicker and drift columns are
recovered with the shipped variants (flicker counted symmetric |ΔIoU|>δ; σ as a
pooled std), which we additionally surface as deviations from the written
definitions.

**Effect of the fix (isolated).** Holding the per-frame IoU fixed and switching
*only* the aggregation (buggy `1-drift` -> `C_gamma`), the diff changes **exactly
the continuity column and nothing else**: in `results/temporal_metrics_diff_isolated.csv`
all 37 moved cells are continuity; flicker, drift and sigma are bit-identical.
High-IoU cells stay ~unchanged (N5k continuity ~100); low-IoU cells the bug had
inflated are correctly deflated, e.g. YOLO/FKit 86.0->52.1, FPN-ReLeM/MTF
88.5->60.7, kMean++/MTF 96.3->59.2. **Spatial metrics (mAP/Recall/Precision/IoU/
Accuracy in the other tables) are untouched** — the change is confined to the
temporal aggregation code.

**FoodLMM.** The published FoodLMM row was doubly wrong: its predictions were
degenerate (FKit drift = 0 and σ = 0 ⇒ IoU constant across every frame) *and*
the buggy aggregator turned that into 100 % continuity. The numbers are not
trustworthy; FoodLMM was re-run and now yields real (non-degenerate) masks, with
corrected continuity in the 34–48 % range across partitions.

**Ranking (conclusions unchanged).** Comparing the buggy vs corrected continuity
ordering (same per-frame IoU) over 14 regenerated methods, the mean Spearman
correlation is rho = 0.80 (min 0.52), and **FoodMem appears in every partition's
top-3 and is #1 globally**; the memory-augmented hybrids (FoodMem, Y+X2) and
high-IoU foreground methods dominate the top under both orderings. FoodMem and
the memory-augmented/foreground methods stay at ~99-100 % corrected continuity,
so the paper's headline conclusion — hybrid memory-augmented methods are the most
temporally stable — is unchanged. The mid-tier reshuffles on the harder
partitions (FKit/MTF rho ~0.3-0.5), which is precisely the correction: the bug
had inflated weak single-frame segmenters to near-100 %. (Numbers will tighten
further as the remaining XMem2/SAM2 hybrid partitions and DEVA/SegMan finish
regenerating; they are additional high-IoU methods that reinforce the top tier.)

**Reproducibility.** The corrected table was regenerated 5x. Every deterministic
method (segmentors, BiRefNet, FoodLMM greedy decoding, XMem2/SAM2 tracking) is
bit-identical across runs (std = 0). The only stochastic component, kMean++
(k-means++ init), has negligible run-to-run variance: across all cells the
maximum standard deviation is 0.29 % (continuity std <= 0.10 %), confirming the
numbers are stable. See `results/repeatability_5runs.csv`.

_Artifacts: `src/temporal_metrics.py`, `tests/test_temporal_metrics.py`,
`src/per_frame_iou.py`, `src/build_temporal_table.py`,
`results/table_corrected_minimal.csv`, `results/temporal_metrics_diff.csv`._
