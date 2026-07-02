# Visualization Scripts

This directory contains scripts for generating 3D camera plots, pie charts, and radar plots from CSV results.

## Files

- `plot_3d_cameras.py`: creates one 3D camera plot per method from COLMAP scene files and per-frame metrics.
- `plot_pie_charts.py`: creates one pie chart per method from per-frame metrics.
- `plot_radar_chart.py`: creates one radar/star plot from method-level summary metrics.
- `_scene_metrics.py`: shared CSV parsing and metric utilities used by the plotting scripts.
- `sample_scene_inputs/`: sample input files used by the commands below.
- `plots/`: default output folder for generated plots.

## Input Data

- The 3D and pie scripts expect a CSV table with one row per method and frame. The sample file is:

```text
Visualization/sample_scene_inputs/donut_per_frame_metrics.csv
```

Required columns:

```text
method,frame,mAP
```

Additional metric columns such as `recall`, `iou`, and `accuracy` can also be used by changing `--metric-name`.

- The 3D script also requires COLMAP text files:

```text
Visualization/sample_scene_inputs/images.txt
Visualization/sample_scene_inputs/points3D.txt
```

- The radar script expects one row per method and one or more metric columns. The sample file is:

```text
Visualization/sample_scene_inputs/efficiency_with_mean_metrics.csv
```

The radar script automatically maps common column names such as `params_M`, `speed_ms_img`, and `vram_MB` to readable labels.

## 3D Camera Plots

```bash
python Visualization/plot_3d_cameras.py \
  --metrics-root Visualization/sample_scene_inputs/donut_per_frame_metrics.csv \
  --metric-name mAP \
  --object-prefix sample \
  --images-path Visualization/sample_scene_inputs/images.txt \
  --points-path Visualization/sample_scene_inputs/points3D.txt \
  --metric-scale 0-100 \
  --view-preset sample-scene \
  --point-size 0.01 \
  --output-dir Visualization/plots/scene_3d \
  --output-format png \
  --dpi 450
```

Output files are named `3D_<method>.png` or `3D_<method>.pdf`.

## Pie Charts

```bash
python Visualization/plot_pie_charts.py \
  --metrics-root Visualization/sample_scene_inputs/donut_per_frame_metrics.csv \
  --metric-name mAP \
  --object-prefix sample \
  --metric-scale 0-100 \
  --show-percentages \
  --legend-marker-size 6 \
  --legend-font-size 8 \
  --output-dir Visualization/plots/scene_pies \
  --output-format png \
  --dpi 300
```

Output files are named `pie_<method>.png` or `pie_<method>.pdf`.

## Radar Plot

```bash
python Visualization/plot_radar_chart.py \
  --input-table Visualization/sample_scene_inputs/efficiency_with_mean_metrics.csv \
  --output-path Visualization/plots/radar/radar_plot.png \
  --output-format png \
  --dpi 300
```

## Useful Options

- `--output-format png`, `pdf`, or `both` chooses the saved file type.
- `--dpi` controls PNG resolution and rasterized content embedded in PDFs.
- `--metric-scale 0-100` or `--metric-scale 0-1` sets the input metric scale for 3D and pie plots.
- `--method-label-map labels.json` maps raw method names to display labels.
- `--method-order-file method_order.txt` controls method order.
- `--metric-key-template "{prefix}_{index:03d}"` controls how scene image names are matched to metric keys in the 3D script. That option is only needed when the names in `images.txt` do not directly match the *frame* values in the metrics CSV.
- `--output-rotation 0`, `90`, `180`, or `270` rotates saved 3D plots after rendering.

## Dependencies

- Python 3
- `numpy`
- `matplotlib`
