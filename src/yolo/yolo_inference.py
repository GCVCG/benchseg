
from ultralytics import YOLO
import torch, cv2, numpy as np, glob, os
import sys

print(sys.argv[1:4])
model = YOLO(sys.argv[1]) 
imgdir = sys.argv[2]
outdir = sys.argv[3]

def instance2semantic(r, background_id: int = 0, out_dtype: np.dtype = np.uint8, offset_classes: bool = True):
    # No detections
    if r.masks is None:
        H, W = r.orig_shape
        return np.full((H, W), background_id, dtype=out_dtype)

    # Tensors
    masks   = r.masks.data.bool()          # (N, H, W)
    classes = r.boxes.cls.to(torch.int64)  # (N,)
    confs   = r.boxes.conf                 # (N,)

    H, W = masks.shape[-2:]

    # Sort so high-confidence FIRST (so they claim pixels earliest)
    order = torch.argsort(confs, descending=True)

    # Reserve 0 or given class for background. The FoodSeg103 YOLO checkpoint
    # predicts 0-indexed food classes (0..102), while the GT ann ids are 1..103
    # with 0=background, so a +1 offset aligns predictions to the GT label space
    # (verified empirically: GT id == predicted cls + 1).
    class_offset = 1 if (offset_classes and background_id == 0) else 0

    # Init canvas on same device as masks
    semantic = torch.full((H, W), background_id, dtype=torch.int64, device=masks.device)

    # Paint: keep "only paint background" so earlier (higher-conf classes) win
    for i in order:
        cls_id = int(classes[i].item()) + class_offset
        mask = masks[i]
        semantic[mask & (semantic == background_id)] = cls_id

    return semantic.cpu().numpy().astype(out_dtype)



os.makedirs(outdir, exist_ok=True)
for r in model.predict(imgdir, batch=16, retina_masks=True, stream=True, imgsz=640):
    path = r.path
    fname = os.path.splitext(os.path.basename(path))[0]
    sem   = instance2semantic(r)
    cv2.imwrite(f"{outdir}/{fname}.png", sem)

print("All done! images saved to", outdir)
print(sys.argv[1:4])