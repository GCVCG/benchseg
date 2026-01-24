#!/usr/bin/env python3
"""
Script to merge FoodLLM multi-object masks into single binary masks.
For images named like "paxoco_mini_000480_0.png", this script will:
1. Merge all objects from the same frame (e.g., _0, _1, _2) into a single binary mask
2. Remove the trailing "_X" from filenames
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image


def merge_masks_for_directory(results_dir):
    """
    Merge multi-object masks in a directory.
    
    Args:
        results_dir: Path to the results directory containing masks
    """
    results_path = Path(results_dir)
    
    # Check if masks subdirectory exists (FoodKit uses this structure)
    if (results_path / "masks").exists():
        masks_dir = results_path / "masks"
    else:
        masks_dir = results_path
    
    if not masks_dir.exists():
        print(f"Warning: Directory {masks_dir} does not exist")
        return
    
    # Group files by their base name (without object index)
    file_groups = defaultdict(list)
    
    for file_path in masks_dir.glob("*.png"):
        filename = file_path.name
        
        # Check if filename ends with _X.png where X is a digit
        if "_" in filename:
            parts = filename.rsplit("_", 1)
            if len(parts) == 2:
                base_name, suffix = parts
                # Check if suffix is like "0.png", "1.png", etc.
                if suffix[:-4].isdigit() and suffix.endswith(".png"):
                    object_idx = int(suffix[:-4])
                    file_groups[base_name].append((object_idx, file_path))
    
    print(f"Processing {len(file_groups)} unique frames in {masks_dir}")
    
    # Process each group
    merged_count = 0
    for base_name, files in file_groups.items():
        if len(files) == 1:
            # Single object - just rename
            object_idx, file_path = files[0]
            new_name = f"{base_name}.png"
            new_path = masks_dir / new_name
            
            if file_path != new_path:
                file_path.rename(new_path)
                merged_count += 1
        else:
            # Multiple objects - merge them
            files.sort(key=lambda x: x[0])  # Sort by object index
            
            # Load first mask to get dimensions
            try:
                first_mask = np.array(Image.open(files[0][1]))
                merged_mask = np.zeros_like(first_mask)
            except Exception as e:
                print(f"  Warning: Could not load first mask for {base_name}: {e}")
                continue
            
            # Union all masks
            for object_idx, file_path in files:
                try:
                    mask = np.array(Image.open(file_path))
                    merged_mask = np.maximum(merged_mask, mask)
                except Exception as e:
                    print(f"  Warning: Could not process {file_path}: {e}")
                    continue
            
            # Save merged mask with new name
            new_name = f"{base_name}.png"
            new_path = masks_dir / new_name
            Image.fromarray(merged_mask).save(new_path)
            
            # Remove original files
            for object_idx, file_path in files:
                file_path.unlink()
            
            merged_count += 1
            if merged_count % 100 == 0:
                print(f"  Processed {merged_count} frames...")
    
    print(f"Completed: Processed {merged_count} frames")


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_foodllm_masks.py <results_dir1> [results_dir2] ...")
        print("\nExample:")
        print("  python merge_foodllm_masks.py data/FoodKit_dataset_reordered/results/FoodLLM")
        sys.exit(1)
    
    for results_dir in sys.argv[1:]:
        print(f"\n{'='*60}")
        print(f"Processing: {results_dir}")
        print(f"{'='*60}")
        merge_masks_for_directory(results_dir)


if __name__ == "__main__":
    main()
