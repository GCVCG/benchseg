#!/usr/bin/env python3
"""
Comprehensive model comparison for all models used in SpiceSeg speed tests
"""

def format_size(mb):
    if mb >= 1000:
        return f"{mb/1000:.2f} GB"
    return f"{mb:.2f} MB"

def format_params(m):
    if m >= 1000:
        return f"{m/1000:.2f}B"
    return f"{m:.2f}M"

print("="*80)
print("MODEL COMPARISON: All Models Used in SpiceSeg Speed Tests")
print("="*80)
print()

# Model data
models = [
    # Tracking Models
    {
        'category': 'Video Tracking',
        'name': 'XMem2',
        'size_mb': 237.49,
        'params_m': 62.22,
        'fps': '~2-4',  # From speed test results
        'notes': 'Memory-based video object segmentation'
    },
    {
        'category': 'Video Tracking',
        'name': 'SAM2.1 (Hiera Large)',
        'size_mb': 856.48,
        'params_m': 224.45,
        'fps': '0.12',
        'notes': 'Segment Anything Model 2 (used in tests)'
    },
    {
        'category': 'Video Tracking',
        'name': 'SAM2.1 (Hiera Tiny)',
        'size_mb': 148.78,
        'params_m': 38.96,
        'fps': 'N/A',
        'notes': 'Available variant (not tested)'
    },
    {
        'category': 'Video Tracking',
        'name': 'SAM2.1 (Hiera Small)',
        'size_mb': 175.87,
        'params_m': 46.06,
        'fps': 'N/A',
        'notes': 'Available variant (not tested)'
    },
    {
        'category': 'Video Tracking',
        'name': 'SAM2.1 (Hiera Base+)',
        'size_mb': 308.62,
        'params_m': 80.85,
        'fps': 'N/A',
        'notes': 'Available variant (not tested)'
    },
    # Instance Segmentation
    {
        'category': 'Instance Segmentation',
        'name': 'YOLO11s-seg',
        'size_mb': 19.66,
        'params_m': 10.12,
        'fps': 'N/A',
        'notes': 'FoodSeg103 fine-tuned'
    },
]

# Print by category
current_category = None
for model in models:
    if model['category'] != current_category:
        current_category = model['category']
        print()
        print("─" * 80)
        print(f"  {current_category}")
        print("─" * 80)
        print(f"{'Model':<35} {'Size':<12} {'Params':<12} {'FPS':<8} {'Notes':<20}")
        print("─" * 80)
    
    print(f"{model['name']:<35} {format_size(model['size_mb']):<12} "
          f"{format_params(model['params_m']):<12} {model['fps']:<8} {model['notes']:<20}")

print()
print("="*80)
print("KEY INSIGHTS")
print("="*80)
print()
print("Model Sizes (File Size):")
print(f"  • Smallest:  YOLO11s-seg         ({format_size(19.66)})")
print(f"  • Largest:   SAM2.1 Hiera Large  ({format_size(856.48)})")
print(f"  • Ratio:     43.6x difference")
print()
print("Parameter Counts:")
print(f"  • Smallest:  YOLO11s-seg         ({format_params(10.12)})")
print(f"  • Largest:   SAM2.1 Hiera Large  ({format_params(224.45)})")
print(f"  • Ratio:     22.2x difference")
print()
print("Performance Notes:")
print("  • XMem2 is 3.6x smaller than SAM2 Large (both file size and params)")
print("  • XMem2 achieves 16-33x faster inference than SAM2 Large")
print("  • YOLO11s-seg is the most compact model at only 19.66 MB")
print("  • YOLO has 6.1x fewer parameters than XMem2")
print()
print("="*80)
print("Speed Test Results Summary:")
print("  - FoodSeg103 models: TESTED ✓ (7 models on 4 images)")
print("  - XMem2:             TESTED ✓ (3 video sequences, 33 frames)")
print("  - SAM2 Large:        TESTED ✓ (3 video sequences, 33 frames)")
print("  - YOLO11s-seg:       Available (not yet speed tested)")
print("="*80)
