from pathlib import Path
from sklearn.model_selection import train_test_split
import shutil

root = Path("/workspace/data/FoodSeg103_yolo_train")

imgs = sorted((root/"images").glob("*.jpg"))

print(f"Total images: {len(imgs)}")

train, tmp = train_test_split(imgs, test_size=0.3, random_state=42)
val, test = train_test_split(tmp, test_size=0.5, random_state=42)

print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

for split, files in zip(("train","val","test"), (train,val,test)):
    (root/f"images/{split}").mkdir(parents=True, exist_ok=True)
    (root/f"masks/{split}").mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {split} split with {len(files)} files...")
    
    for f in files:
        # Copy images
        img_dst = root/f"images/{split}"/f.name
        shutil.copy2(f, img_dst)
        
        # Copy corresponding masks (convert .jpg to .png extension)
        mask_name = f.stem + ".png"  # Replace .jpg with .png
        mask_src = root/"masks"/mask_name
        mask_dst = root/f"masks/{split}"/mask_name
        
        if mask_src.exists():
            shutil.copy2(mask_src, mask_dst)
        else:
            print(f"Warning: Mask not found for {mask_name} (image: {f.name})")

print("Dataset splitting completed!")
