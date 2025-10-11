import os
import re

datasets = ["V&F", "n5k", "n5k360", "mtf_foodMem"]
paths = [os.path.join("data", i) for i in datasets]
output_paths = [os.path.join("data", i + "_reordered") for i in datasets]

def natural_sort_key(filename):
    """Sort filenames with numbers in natural order"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]

import os
import shutil

for path, output_path in zip(paths, output_paths):
    dirs = os.listdir(path)
    dirs = [d for d in dirs if os.path.isdir(os.path.join(path, d))]

    os.makedirs(output_path, exist_ok=True)
    os.makedirs(os.path.join(output_path, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "masks"), exist_ok=True)

    for d in dirs:
        images_path = os.path.join(path, d, "imgs")
        masks_path = os.path.join(path, d, "gt_masks")

        # Use natural sorting for proper numeric order
        image_files = sorted(os.listdir(images_path), key=natural_sort_key)
        mask_files = sorted(os.listdir(masks_path), key=natural_sort_key)
        
        images = [os.path.join(images_path, im) for im in image_files]
        masks = [os.path.join(masks_path, im) for im in mask_files]

        print(f"Processing directory: {d}")
        print(f"Found {len(images)} images and {len(masks)} masks")
        
        for i, (im, ma) in enumerate(zip(images, masks)):
            shutil.copy(im, os.path.join(output_path, "images", f"{d}_{i:03d}.png"))
            shutil.copy(ma, os.path.join(output_path, "masks", f"{d}_{i:03d}.png"))
