#!/usr/bin/env python3
"""
Complete model comparison for ALL models in SpiceSeg
"""

def format_size_mb(mb):
    if mb >= 1000:
        return f"{mb/1000:.2f} GB"
    return f"{mb:.0f} MB"

def format_params(m):
    if m >= 1000:
        return f"{m/1000:.2f}B"
    return f"{m:.1f}M"

print("="*85)
print("COMPLETE MODEL COMPARISON: All Models in SpiceSeg")
print("="*85)
print()

# All model data
models = [
    # FoodSeg103 Semantic Segmentation Models
    ('FoodSeg103', 'FPN-ReLeM', 217.76, 28.54, 'Feature Pyramid Network with ReLeM'),
    ('FoodSeg103', 'FPN', 217.91, 28.56, 'Feature Pyramid Network'),
    ('FoodSeg103', 'CCNet-ReLeM', 380.89, 49.93, 'Criss-Cross Network with ReLeM'),
    ('FoodSeg103', 'CCNet', 381.04, 49.95, 'Criss-Cross Network'),
    ('FoodSeg103', 'SWIN_SMALL', 930.44, 81.29, 'Swin Transformer Small'),
    ('FoodSeg103', 'SETR_MLA', 710.21, 93.20, 'SETR Multi-Level Aggregation'),
    ('FoodSeg103', 'SETR_MLA-ReLeM', 710.21, 93.20, 'SETR MLA with ReLeM'),
    ('FoodSeg103', 'SETR_Naive-ReLeM', 722.78, 94.83, 'SETR Naive with ReLeM'),
    ('FoodSeg103', 'SETR_Naive', 722.78, 94.83, 'SETR Naive'),
    ('FoodSeg103', 'SWIN_BASE', 1360.00, 121.31, 'Swin Transformer Base'),
    ('FoodSeg103', 'SETR_MLA_L384', 2320.00, 311.51, 'SETR MLA Large (384)'),
    
    # Instance Segmentation
    ('Instance Seg', 'YOLO11s-seg', 19.66, 10.12, 'FoodSeg103 fine-tuned'),
    
    # Video Tracking Models
    ('Video Tracking', 'SAM2.1 Tiny', 148.78, 38.96, 'Segment Anything 2 Tiny'),
    ('Video Tracking', 'SAM2.1 Small', 175.87, 46.06, 'Segment Anything 2 Small'),
    ('Video Tracking', 'XMem2', 237.49, 62.22, 'Memory-based video segmentation'),
    ('Video Tracking', 'SAM2.1 Base+', 308.62, 80.85, 'Segment Anything 2 Base+'),
    ('Video Tracking', 'SAM2.1 Large', 856.48, 224.45, 'Segment Anything 2 Large (used in tests)'),
]

# Print by category
current_category = None
for category, name, size_mb, params_m, desc in sorted(models, key=lambda x: (x[0], x[2])):
    if category != current_category:
        current_category = category
        print()
        print("─" * 85)
        print(f"  {current_category}")
        print("─" * 85)
        print(f"{'Model':<25} {'Size':<12} {'Params':<10} {'Description':<35}")
        print("─" * 85)
    
    print(f"{name:<25} {format_size_mb(size_mb):<12} {format_params(params_m):<10} {desc:<35}")

print()
print("="*85)
print("CROSS-CATEGORY COMPARISONS")
print("="*85)
print()

# Find extremes
all_models_sorted = sorted(models, key=lambda x: x[2])
smallest = all_models_sorted[0]
largest = all_models_sorted[-1]

print(f"Smallest Model Overall:  {smallest[1]}")
print(f"  Category: {smallest[0]}")
print(f"  Size: {format_size_mb(smallest[2])}")
print(f"  Params: {format_params(smallest[3])}")
print()

print(f"Largest Model Overall:   {largest[1]}")
print(f"  Category: {largest[0]}")
print(f"  Size: {format_size_mb(largest[2])}")
print(f"  Params: {format_params(largest[3])}")
print()

ratio = largest[2] / smallest[2]
param_ratio = largest[3] / smallest[3]
print(f"Size Difference:      {ratio:.1f}x")
print(f"Parameter Difference: {param_ratio:.1f}x")

print()
print("="*85)
print("CATEGORY STATISTICS")
print("="*85)
print()

# FoodSeg103 stats
foodseg_models = [m for m in models if m[0] == 'FoodSeg103']
print(f"FoodSeg103 Semantic Segmentation Models: {len(foodseg_models)}")
print(f"  Size Range:   {min(m[2] for m in foodseg_models):.0f} MB - {max(m[2] for m in foodseg_models):.0f} MB")
print(f"  Params Range: {min(m[3] for m in foodseg_models):.1f}M - {max(m[3] for m in foodseg_models):.1f}M")
print(f"  Smallest:     {min(foodseg_models, key=lambda x: x[2])[1]} ({min(m[3] for m in foodseg_models):.1f}M)")
print(f"  Largest:      {max(foodseg_models, key=lambda x: x[2])[1]} ({max(m[3] for m in foodseg_models):.1f}M)")

# Video tracking stats
tracking_models = [m for m in models if m[0] == 'Video Tracking']
print(f"\nVideo Tracking Models: {len(tracking_models)}")
print(f"  Size Range:   {min(m[2] for m in tracking_models):.0f} MB - {max(m[2] for m in tracking_models):.0f} MB")
print(f"  Params Range: {min(m[3] for m in tracking_models):.1f}M - {max(m[3] for m in tracking_models):.1f}M")
print(f"  Tested:       XMem2 ({62.22:.1f}M) and SAM2.1 Large ({224.45:.1f}M)")

# Instance seg
print(f"\nInstance Segmentation Models: 1")
print(f"  YOLO11s-seg:  {19.66:.0f} MB, {10.12:.1f}M params (most compact overall)")

print()
print("="*85)
print("KEY INSIGHTS")
print("="*85)
print()
print("• YOLO11s-seg is the most efficient model across ALL categories")
print("• SETR_MLA_L384 is the largest FoodSeg103 model (311.51M params)")
print("• SAM2.1 Large (224.45M params) is larger than any FoodSeg103 model except SETR_MLA_L384")
print("• FPN models are the most compact FoodSeg103 options (~28M params)")
print("• XMem2 (62.22M) is smaller than most FoodSeg103 models")
print("• YOLO is 30.8x smaller than SETR_MLA_L384 (the largest overall)")
print()
print("="*85)
