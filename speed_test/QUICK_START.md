# Speed Test Quick Start

## Run from Repository Root

```bash
cd /home/guill_unix/repos/SpiceSeg

# Test all models
./speed_test/run_speed_test.sh ALL

# Test specific model
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

4 images of varying sizes from `data/speed_test/random_images/`:
- 512×384 (small)
- 720×960 (medium)
- 1365×1024 (medium-large)
- 1920×1080 (large)

## Results Location

```
data/speed_test/results/
├── <MODEL_NAME>/
│   ├── *.png                    # Prediction masks
│   └── log.csv                  # Timing data
└── speed_test_summary.json      # Comprehensive summary
```

## Manual Analysis

If you need to re-analyze results without re-running inference:

```bash
python3 speed_test/analyze_speed_results.py data/speed_test/results
```

## Files in speed_test/

- `run_speed_test.sh` - Main wrapper (calls Docker + analysis)
- `speed_test_foodseg.sh` - Runs inside Docker container
- `analyze_speed_results.py` - Analyzes timing logs
- `README.md` - Complete documentation
- `QUICK_START.md` - This file

## Troubleshooting

**Issue**: Script can't find repo root
**Fix**: Always run from repository root: `cd /home/guill_unix/repos/SpiceSeg`

**Issue**: Docker fails
**Fix**: Check if `foodseg103` image exists: `docker images | grep foodseg103`

**Issue**: No results generated
**Fix**: Check Docker logs and ensure paths are mounted correctly
