from pathlib import Path
from sklearn.model_selection import train_test_split   # stratify:contentReference[oaicite:6]{index=6}

root = Path("/workspace/data/mtf_yolo")

imgs   = sorted((root/"images").glob("*.jpg"))
labels = [p.name.split('_')[0] for p in imgs]           # class prefix

train, tmp = train_test_split(imgs, test_size=0.3, stratify=labels,
                              random_state=42)
val, test  = train_test_split(tmp, test_size=0.5,
                              stratify=[p.name.split('_')[0] for p in tmp],
                              random_state=42)

for split, files in zip(("train","val","test"), (train,val,test)):
    (root/f"images/{split}").mkdir(parents=True, exist_ok=True)
    (root/f"binary-masks/{split}").mkdir(parents=True, exist_ok=True)
    for f in files:
        f.rename(root/f"images/{split}"/f.name)
        (root/f"binary-masks"/f.name).rename(root/f"binary-masks/{split}"/f.name)
