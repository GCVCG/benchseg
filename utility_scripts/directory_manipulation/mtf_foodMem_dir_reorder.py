
path = "data/mtf_foodMem"
output_path = "data/mtf_foodMem_reordered"

import os
import shutil

dirs = os.listdir(path)
dirs = [d for d in dirs if os.path.isdir(os.path.join(path, d))]

os.makedirs(output_path, exist_ok=True)
os.makedirs(os.path.join(output_path, "images"), exist_ok=True)
os.makedirs(os.path.join(output_path, "masks"), exist_ok=True)

for d in dirs:
    images_path = os.path.join(path, d, "images")
    masks_path = os.path.join(path, d, "masks")
    images = sorted([os.path.join(images_path, im) for im in os.listdir(images_path)])
    masks = sorted([os.path.join(masks_path, im) for im in os.listdir(masks_path)])

    print(images)
    print(f"Processing directory: {d}")
    print(len(images), len(masks))
    for i, (im, ma) in enumerate(zip(images, masks)):
        shutil.copy(im, os.path.join(output_path, "images", f"{d}_{i:03d}.png"))
        shutil.copy(ma, os.path.join(output_path, "masks", f"{d}_{i:03d}.png"))
