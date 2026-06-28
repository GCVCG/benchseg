#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH -J eff_seg
#SBATCH -o logs/eff_seg_%j.out
#SBATCH -e logs/eff_seg_%j.out
# Efficiency (Params, Speed/img, peak VRAM) for the segmentor families on a fixed
# H200 sample. Speed comes from each script's "ms/img"; VRAM from an nvidia-smi
# peak sampler (this is the only GPU job -> memory.used is ours).
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
SEG=$ROOT/baselines/SegMan/segmentation
cd "$ROOT"
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
P310=$ROOT/containers/python310.sif
PT21=$ROOT/containers/pytorch21_devel.sif
ULTRA=$ROOT/containers/ultralytics.sif
OUT=results/efficiency_seg.csv
mkdir -p results logs
echo "method,params_M,speed_ms_img,vram_MB" > "$OUT"

# build a fixed 64-frame sample from N5K
SAMP=$ROOT/data/_eff_sample
rm -rf "$SAMP"; mkdir -p "$SAMP"
ls "$ROOT/data/n5k_reordered/images"/* 2>/dev/null | grep -iE "\.(png|jpg|jpeg)$" | head -64 | xargs -I{} cp {} "$SAMP"/
NS=$(ls "$SAMP" | wc -l); echo "sample frames: $NS"

# run a command while sampling peak GPU memory; echo "PEAK_MB <n>"
measure_vram(){
  local mlog=$(mktemp)
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; sleep 0.2; done ) > "$mlog" &
  local smi=$!
  "$@"
  local rc=$?
  kill $smi 2>/dev/null
  local peak=$(sort -n "$mlog" | tail -1); rm -f "$mlog"
  echo "PEAK_MB ${peak:-0}"
  return $rc
}

# ---- mmseg segmentors (foodseg venv) ----
mmseg_one(){ # tag cfg ckpt
  local TAG=$1 CFG=$2 CKPT=$3
  echo "===== $TAG ====="
  local PM=$(singularity exec --nv --bind "$ROOT":"$ROOT" --pwd "$ROOT" "$P310" \
      "$ROOT/venvs/foodseg/bin/python" "$ROOT/src/count_params.py" --framework mmseg \
      --name "$TAG" --config "$ROOT/assets/ckpts/$CFG" --checkpoint "$ROOT/assets/ckpts/$CKPT" 2>/dev/null \
      | grep "^PARAMS," | cut -d, -f3)
  local log=$(mktemp)
  measure_vram singularity exec --nv --bind "$ROOT":"$ROOT" --pwd "$ROOT" "$P310" \
      "$ROOT/venvs/foodseg/bin/python" "$ROOT/src/foodseg_batch.py" \
      --config "$ROOT/assets/ckpts/$CFG" --checkpoint "$ROOT/assets/ckpts/$CKPT" \
      --img_dir "$SAMP" --out_dir "$ROOT/data/_eff_out/$TAG" > "$log" 2>&1
  local SPD=$(grep -oE "[0-9.]+ ms/img" "$log" | grep -oE "[0-9.]+" | head -1)
  local VR=$(grep "PEAK_MB" "$log" | awk "{print \$2}" | tail -1)
  echo "$TAG -> params=${PM} speed=${SPD}ms vram=${VR}MB"; rm -f "$log"
  echo "$TAG,${PM},${SPD},${VR}" >> "$OUT"
}

mmseg_one FPN        FPN/fpn_r50_512x1024_80k.py                              FPN/iter_80000.pth
mmseg_one FPN_ReLeM  FPN_ReLeM/fpn_r50_512x1024_80k.py                        FPN_ReLeM/iter_80000.pth
mmseg_one CCNet      CCNet/ccnet_r101-d8_512x1024_80k.py                      CCNet/iter_80000.pth
mmseg_one CCNet_ReLeM CCNet_ReLeM/ccnet_r50-d8_512x1024_80k.py               CCNet_ReLeM/iter_80000.pth
mmseg_one SETR_Naive SETR_Naive/SETR_Naive_768x768_80k_base.py               SETR_Naive/iter_80000.pth
mmseg_one SETR_MLA_L384 SETR_MLA_L384/SETR_MLA_768x768_80k.py                SETR_MLA_L384/iter_80000.pth
mmseg_one swin_small swin_small/upernet_swin_small_patch4_window7_512x1024_80k.py swin_small/iter_80000.pth
mmseg_one swin_base  swin_base/upernet_swin_base_patch4_window7_512x1024_80k.py   swin_base/iter_80000.pth

# ---- YOLO (ultralytics) ----
echo "===== YOLO ====="
PM=$(singularity exec --nv --bind "$ROOT":"$ROOT" --pwd "$ROOT" "$ULTRA" \
    python "$ROOT/src/count_params.py" --framework yolo --name YOLO \
    --checkpoint "$ROOT/assets/ckpts/YOLO/yolo11s-seg_foodseg103_2.pt" 2>/dev/null | grep "^PARAMS," | cut -d, -f3)
log=$(mktemp)
measure_vram singularity exec --nv --bind "$ROOT":"$ROOT" --pwd "$ROOT" \
    --env YOLO_OFFLINE=True --env YOLO_CONFIG_DIR="$ROOT/.ultra_cfg" "$ULTRA" \
    python "$ROOT/src/yolo/yolo_inference.py" \
    "$ROOT/assets/ckpts/YOLO/yolo11s-seg_foodseg103_2.pt" "$SAMP" "$ROOT/data/_eff_out/YOLO" > "$log" 2>&1
SPD=$(grep -oE "[0-9.]+ms$|[0-9.]+ms " "$log" | head -1)
VR=$(grep "PEAK_MB" "$log" | awk "{print \$2}" | tail -1)
echo "YOLO -> params=${PM} vram=${VR}MB (speed from ultralytics log)"
echo "YOLO,${PM},,${VR}" >> "$OUT"; rm -f "$log"

# ---- SegMAN variants (segman venv) ----
segman_one(){ # tag cfg ckpt food
  local TAG=$1 CFG=$2 CKPT=$3 FOOD=$4
  echo "===== $TAG ====="
  local PM=$(singularity exec --nv --bind "$ROOT":"$ROOT" --env PYTHONPATH=$SEG --pwd "$ROOT" "$PT21" \
      "$ROOT/venvs/segman21/bin/python" "$ROOT/src/count_params.py" --framework segman \
      --name "$TAG" --config "$CFG" --checkpoint "$CKPT" 2>/dev/null | grep "^PARAMS," | cut -d, -f3)
  local log=$(mktemp)
  measure_vram singularity exec --nv --bind "$ROOT":"$ROOT" \
      --env CUDA_HOME=/usr/local/cuda --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs:/usr/local/cuda/lib64 \
      --env TRITON_LIBCUDA_PATH=/.singularity.d/libs --env PYTHONPATH=$SEG --pwd "$ROOT" "$PT21" \
      "$ROOT/venvs/segman21/bin/python" "$ROOT/src/segman_batch.py" \
      --config "$CFG" --checkpoint "$CKPT" --food_classes "$FOOD" \
      --img_dir "$SAMP" --out_dir "$ROOT/data/_eff_out/$TAG" > "$log" 2>&1
  local SPD=$(grep -oE "[0-9.]+ ms/img|[0-9]+ ms/img" "$log" | grep -oE "[0-9.]+" | head -1)
  local VR=$(grep "PEAK_MB" "$log" | awk "{print \$2}" | tail -1)
  echo "$TAG -> params=${PM} speed=${SPD}ms vram=${VR}MB"; rm -f "$log"
  echo "$TAG,${PM},${SPD},${VR}" >> "$OUT"
}
segman_one SegMan_ADE  "$SEG/local_configs/segman/base/segman_b_ade.py"        "$ROOT/baselines/SegMan/pretrained_seg/segman_b_ade.pth"  "120"
segman_one SegMan_COCO "$SEG/local_configs/segman/base/segman_b_coco.py"       "$ROOT/baselines/SegMan/pretrained_seg/segman_b_coco.pth" "120"
segman_one SegMan_FS   "$SEG/local_configs/segman/base/segman_b_foodseg103.py" "$ROOT/work_dirs/segman_b_foodseg103_80k/best_mIoU_iter_80000.pth" "gt0"

rm -rf "$ROOT/data/_eff_out"
echo "########## EFFICIENCY_SEG DONE ##########"; cat "$OUT"
