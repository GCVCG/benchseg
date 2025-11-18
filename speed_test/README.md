# FoodSeg Speed Test Guide

## Quick Start

From the SpiceSeg repository root, run the complete speed test with all models:

```bash
cd /path/to/SpiceSeg
./speed_test/run_speed_test.sh ALL
```

Or test a specific model:

```bash
./speed_test/run_speed_test.sh SWIN_SMALL
```

## Available Models

- `SWIN_SMALL` - Swin Transformer (Small)
- `SWIN_BASE` - Swin Transformer (Base)
- `FPN_RELEM` - Feature Pyramid Network with ReLeM
- `CCNET` - Criss-Cross Network
- `CCNET_RELEM` - CCNet with ReLeM
- `SETR_MLA_L384` - SETR Multi-Level Aggregation
- `SETR_NAIVE` - SETR Naive
- `ALL` - Test all models

## What Gets Tested

The speed test runs inference on 4 images of varying sizes:

1. **small_512x384.jpg** - 512×384 resolution
2. **medium_720x960.png** - 720×960 resolution
3. **medium_1365x1024.jpg** - 1365×1024 resolution
4. **large_1920x1080.png** - 1920×1080 resolution

## Output

After running the test, you'll get:

1. **Predictions** - Segmentation masks in `data/speed_test/results/<MODEL>/`
2. **Timing logs** - CSV files at `data/speed_test/results/<MODEL>/log.csv`
3. **JSON summary** - Comprehensive results at `data/speed_test/results/speed_test_summary.json`
4. **Console report** - Detailed analysis printed to terminal

## Manual Steps

If you prefer to run steps individually:

### 1. Run inference in Docker (from repo root):

```bash
docker run --gpus all -it --rm \
    -v $(pwd)/assets:/workspace/assets \
    -v $(pwd)/data:/workspace/data \
    -v $(pwd)/speed_test:/workspace/speed_test \
    -v $(pwd)/automation_scripts:/workspace/automation_scripts \
    -v $(pwd)/src:/workspace/src \
    foodseg103 \
    bash /workspace/speed_test/speed_test_foodseg.sh ALL
```

### 2. Analyze results:

```bash
python3 speed_test/analyze_speed_results.py data/speed_test/results
```

## Understanding the Results

The analysis script will show:

- **Overall Ranking** - Models ranked by average inference time
- **Performance by Image Size** - How each model performs on different resolutions
- **Speedup Comparison** - Relative performance compared to the slowest model
- **FPS (Frames Per Second)** - Real-time processing capability

### Example Output:

```
📊 Overall Model Ranking (by average inference time)
----------------------------------------

1. SWIN_SMALL
   Average time: 245.3 ms (4.08 FPS)
   Range: 180.2 - 310.5 ms
   Std dev: 45.2 ms
   Images: 4

2. FPN_RELEM
   Average time: 312.7 ms (3.20 FPS)
   ...
```

## Cleaning Up Results

To remove previous test results and start fresh:

```bash
rm -rf data/speed_test/results/
```

## Troubleshooting

**Issue**: Docker container fails to start
- **Solution**: Make sure the `foodseg103` Docker image exists. Check with `docker images | grep foodseg103`

**Issue**: No timing data in results
- **Solution**: Check that `src/FoodSAM_tools/predict_semantic_mask.py` is mounted and logs timing to CSV

**Issue**: Python3 not found for analysis
- **Solution**: The script will still run in Docker. You can analyze results manually or install Python locally

## Testing Tracking Models (XMem2 & SAM2)

The speed test dataset includes video sequences for evaluating tracking models:

### 1. Prepare Initial Masks

Tracking models require an initial mask prompt for the first frame:

```bash
./speed_test/scripts/prepare_tracking_data.sh
```

This creates initial masks in `data/speed_test/initial_masks/`.

### 2. Test XMem2

```bash
./speed_test/scripts/run_xmem2_speed_test.sh all
```

Or test a specific sequence:

```bash
./speed_test/scripts/run_xmem2_speed_test.sh food_sequence_1
```

### 3. Test SAM2

```bash
./speed_test/scripts/run_sam2_speed_test.sh all
```

Or test a specific sequence:

```bash
./speed_test/scripts/run_sam2_speed_test.sh lemon_sequence
```

### 4. Analyze Tracking Results

```bash
python3 speed_test/scripts/analyze_tracking_results.py
```

This will show:
- Per-sequence timing breakdown
- Average FPS for each model
- Model comparison (XMem2 vs SAM2)

## Next Steps

After testing, you can:

1. Test YOLO models on the random images
2. Compare results across different hardware configurations
3. Scale up to larger datasets for more comprehensive benchmarking
4. Modify `prepare_tracking_data.sh` to use real segmentation masks instead of synthetic ones

## Directory Structure

All speed test files are now organized in the `speed_test/` directory:

```
SpiceSeg/
├── speed_test/                          # Speed testing framework
│   ├── scripts/
│   │   ├── run_speed_test.sh           # Main runner for FoodSeg models
│   │   ├── speed_test_foodseg.sh       # Docker-based inference script
│   │   ├── analyze_speed_results.py    # FoodSeg results analysis
│   │   ├── prepare_tracking_data.sh    # Generate initial masks for tracking
│   │   ├── run_xmem2_speed_test.sh     # XMem2 speed test runner
│   │   ├── run_sam2_speed_test.sh      # SAM2 speed test runner
│   │   └── analyze_tracking_results.py # Tracking models analysis
│   ├── README.md                        # This file
│   └── GUIDE.md                         # Detailed user guide
├── data/
│   └── speed_test/                      # Speed test dataset & results
│       ├── random_images/               # 4 test images (varying sizes)
│       ├── videos/                      # 3 video sequences (11 frames each)
│       ├── initial_masks/               # Initial masks for tracking (generated)
│       ├── results/                     # FoodSeg results (created during test)
│       ├── tracking_results/            # Tracking model results (created during test)
│       └── README.md                    # Dataset documentation
├── assets/                              # Model checkpoints
├── src/                                 # Source code
└── automation_scripts/                  # Other automation scripts
```
