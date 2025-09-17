from ultralytics.data.converter import convert_segment_masks_to_yolo_seg
from pathlib import Path, PurePath
root = Path("/workspace/data/mtf_yolo")

for split in ["train","val","test"]:
    convert_segment_masks_to_yolo_seg(
        masks_dir  = root/f"binary-masks/{split}",
        output_dir = root/f"labels/{split}",
        classes    = 999)      # placeholder, fixed next
