"""Batch FoodLMM (LISA-based) referring segmentation over a folder.

Adapted from FoodLMM's online_demo.py: loads the model once and, for each image,
issues a fixed food-segmentation prompt, runs model.evaluate, unions the predicted
[SEG] masks into a binary foreground mask, and saves {stem}.png (0=bg, 255=food)
to match the GT naming for per-frame IoU.

Run from inside the FoodLMM repo dir with its venv:
  cd baselines/FoodLMM && <venv>/bin/python ../batch_foodlmm.py \
    --version <FoodLMM-Chat> --cfg_file train_config_Stage2.yaml \
    --img_dir <dir> --out_dir <dir>
"""
import argparse, glob, os, sys, time
import numpy as np, torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoTokenizer, CLIPImageProcessor

from utils.config import Config
from utils import conversation as conversation_lib
from model.LISA import LISAForCausalLM
from model.llava.mm_utils import tokenizer_image_token
from model.segment_anything.utils.transforms import ResizeLongestSide
from utils.utils import (DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX,
                         DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN)

IMG_EXTS = (".png", ".jpg", ".jpeg")


def sam_preprocess(x, img_size=1024):
    pixel_mean = torch.Tensor([123.675, 116.28, 103.53]).view(-1, 1, 1)
    pixel_std = torch.Tensor([58.395, 57.12, 57.375]).view(-1, 1, 1)
    x = (x - pixel_mean) / pixel_std
    h, w = x.shape[-2:]
    x = F.pad(x, (0, img_size - w, 0, img_size - h))
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--cfg_file", default="train_config_Stage2.yaml")
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--prompt", default="Please segment the food in this image. Please output segmentation mask.")
    # placeholders filled by Config from the yaml
    ap.add_argument("--options", default=None, nargs="+")
    ap.add_argument("--local_rank", default=0, type=int)
    ap.add_argument("--load_in_4bit", action="store_true", default=False)
    ap.add_argument("--load_in_8bit", action="store_true", default=False)
    ap.add_argument("--use_mm_start_end", action="store_true", default=True)
    ap.add_argument("--lora_r", default=8, type=int)
    args = ap.parse_args()

    Config(args)  # populates conv_type, max_seg_num, vision_tower, out_dim, precision, image_size, model_max_length

    torch_dtype = torch.bfloat16 if args.precision == "bf16" else (
        torch.half if args.precision == "fp16" else torch.float32)

    tokenizer = AutoTokenizer.from_pretrained(
        args.version, model_max_length=args.model_max_length, padding_side="right", use_fast=False)
    tokenizer.pad_token = tokenizer.unk_token
    args.seg_token_idx = tokenizer("[SEG]", add_special_tokens=False).input_ids[0]
    for tok in ("MASS_TOTAL", "CAL_TOTAL", "FAT_TOTAL", "CARB_TOTAL", "PRO_TOTAL"):
        setattr(args, {"MASS_TOTAL": "mass_token_idx", "CAL_TOTAL": "calorie_token_idx",
                       "FAT_TOTAL": "fat_token_idx", "CARB_TOTAL": "carbohydrate_token_idx",
                       "PRO_TOTAL": "protein_token_idx"}[tok],
                tokenizer(f"[{tok}]", add_special_tokens=False).input_ids[0])

    kwargs = {"torch_dtype": torch_dtype, "seg_token_idx": args.seg_token_idx,
              "mass_token_idx": args.mass_token_idx, "calorie_token_idx": args.calorie_token_idx,
              "fat_token_idx": args.fat_token_idx, "carbohydrate_token_idx": args.carbohydrate_token_idx,
              "protein_token_idx": args.protein_token_idx}
    ad = vars(args)
    for i in range(1, args.max_seg_num + 1):
        for pfx, tk in (("seg", "SEG"), ("mass", "MASS"), ("calorie", "CAL"),
                        ("fat", "FAT"), ("carbohydrate", "CARB"), ("protein", "PRO")):
            key = f"{pfx}_token_idx_{i}"
            ad[key] = tokenizer(f"[{tk}{i}]", add_special_tokens=False).input_ids[0]
            kwargs[key] = ad[key]

    print("loading FoodLMM ...", flush=True)
    model = LISAForCausalLM.from_pretrained(args.version, low_cpu_mem_usage=True, **kwargs)
    model.config.eos_token_id = tokenizer.eos_token_id
    model.config.bos_token_id = tokenizer.bos_token_id
    model.config.pad_token_id = tokenizer.pad_token_id
    model.get_model().initialize_vision_modules(model.get_model().config)
    model.get_model().get_vision_tower().to(dtype=torch_dtype)
    model = model.bfloat16().cuda() if args.precision == "bf16" else model.float().cuda()
    model.get_model().get_vision_tower().to(device=args.local_rank)
    clip_image_processor = CLIPImageProcessor.from_pretrained(model.config.vision_tower)
    transform = ResizeLongestSide(args.image_size)
    model.eval()

    # Fixed prompt
    q = args.prompt
    img_tok = DEFAULT_IMAGE_TOKEN
    if args.use_mm_start_end:
        img_tok = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN
    conv = conversation_lib.conv_templates[args.conv_type].copy()
    conv.append_message(conv.roles[0], img_tok + "\n" + q)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()

    os.makedirs(args.out_dir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(args.img_dir, "*")) if f.lower().endswith(IMG_EXTS))
    if args.limit:
        imgs = imgs[: args.limit]
    print(f"running {len(imgs)} images -> {args.out_dir}", flush=True)
    t0 = time.time()
    for i, ip in enumerate(imgs):
        image_np = np.array(Image.open(ip).convert("RGB"))
        H, W = image_np.shape[:2]
        image_clip = clip_image_processor.preprocess(image_np, return_tensors="pt")["pixel_values"][0].unsqueeze(0).cuda()
        image_clip = image_clip.bfloat16() if args.precision == "bf16" else image_clip.float()
        img_s = transform.apply_image(image_np)
        resize_list = [img_s.shape[:2]]
        image = sam_preprocess(torch.from_numpy(img_s).permute(2, 0, 1).contiguous(), args.image_size).unsqueeze(0).cuda()
        image = image.bfloat16() if args.precision == "bf16" else image.float()
        input_ids = tokenizer_image_token(prompt, tokenizer, return_tensors="pt").unsqueeze(0).cuda()
        with torch.no_grad():
            _, pred_masks, _ = model.evaluate(image_clip, image, input_ids, resize_list, [(H, W)],
                                              max_new_tokens=512, tokenizer=tokenizer)
        merged = np.zeros((H, W), dtype=bool)
        if len(pred_masks) and pred_masks[0].shape[0] > 0:
            for idx in range(pred_masks[0].shape[0]):
                merged |= (pred_masks[0][idx].detach().cpu().numpy() > 0)
        stem = os.path.splitext(os.path.basename(ip))[0]
        Image.fromarray((merged * 255).astype(np.uint8)).save(os.path.join(args.out_dir, f"{stem}.png"))
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(imgs)}", flush=True)
    dt = time.time() - t0
    print(f"done {len(imgs)} imgs in {dt:.1f}s ({dt/max(len(imgs),1)*1000:.0f} ms/img)", flush=True)


if __name__ == "__main__":
    main()
