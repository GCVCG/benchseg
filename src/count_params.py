"""Count trainable+buffer parameters (in millions) for a model, across the
several frameworks used in BenchSeg. Prints one line:  PARAMS,<name>,<M>

Frameworks:
  mmseg  : init_segmentor(config, checkpoint)   [foodseg venv / segman venv]
  yolo   : ultralytics YOLO(checkpoint)
  segman : SegMAN mmseg init_segmentor (run with PYTHONPATH=<segman segmentation>)
  sam2   : build_sam2 from a config+checkpoint
  sam3   : build_sam3_video_model(load_from_HF=True)
  xmem2  : XMem network from checkpoint state_dict
  torch  : a raw .pth/.pt state_dict -> sum of tensor sizes (fallback)
"""
import argparse
import os
import sys


def n_params(module):
    return sum(p.numel() for p in module.parameters())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--framework", required=True,
                    choices=["mmseg", "yolo", "segman", "sam2", "sam3", "xmem2", "torch"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--config", default="")
    ap.add_argument("--checkpoint", default="")
    a = ap.parse_args()

    nparam = None
    if a.framework in ("mmseg", "segman"):
        import mmcv
        if a.framework == "mmseg":
            # vendored package is src.mmseg; put repo root on path (like foodseg_batch)
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if root not in sys.path:
                sys.path.insert(0, root)
            from src.mmseg.apis import init_segmentor
        else:
            from mmseg.apis import init_segmentor  # SegMAN mmseg via PYTHONPATH
        cfg = mmcv.Config.fromfile(a.config)
        cfg.model.pretrained = None
        if cfg.model.get("backbone", {}).get("pretrained") is not None:
            cfg.model.backbone.pretrained = None
        if "train_cfg" in cfg.model:
            cfg.model.train_cfg = None
        model = init_segmentor(cfg, a.checkpoint if a.checkpoint else None, device="cpu")
        nparam = n_params(model)
    elif a.framework == "yolo":
        from ultralytics import YOLO
        m = YOLO(a.checkpoint)
        nparam = sum(p.numel() for p in m.model.parameters())
    elif a.framework == "sam2":
        from sam2.build_sam import build_sam2
        model = build_sam2(a.config, a.checkpoint, device="cpu")
        nparam = n_params(model)
    elif a.framework == "sam3":
        from sam3.model_builder import build_sam3_video_model
        model = build_sam3_video_model(load_from_HF=True)
        nparam = n_params(model)
    elif a.framework == "xmem2":
        import torch
        sd = torch.load(a.checkpoint, map_location="cpu")
        sd = sd.get("model", sd) if isinstance(sd, dict) else sd
        nparam = sum(v.numel() for v in sd.values() if hasattr(v, "numel"))
    elif a.framework == "torch":
        import torch
        sd = torch.load(a.checkpoint, map_location="cpu")
        for k in ("state_dict", "model", "weights"):
            if isinstance(sd, dict) and k in sd and isinstance(sd[k], dict):
                sd = sd[k]; break
        nparam = sum(v.numel() for v in sd.values() if hasattr(v, "numel"))

    print(f"PARAMS,{a.name},{nparam/1e6:.2f}", flush=True)


if __name__ == "__main__":
    main()
