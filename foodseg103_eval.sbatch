#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH -J fs103eval
#SBATCH -o logs/fs103eval_%j.out
#SBATCH -e logs/fs103eval_%j.out
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
echo "### $(hostname) ###"; nvidia-smi --query-gpu=name --format=csv,noheader

LIMIT="${LIMIT:-0}"          # 0 = full 2135; >0 = smoke
ONLY="${ONLY:-}"             # space-separated TAG subset; empty = all
RUNTAG="${RUNTAG:-}"         # per-run id for 5x repeatability; empty = main run
[ -n "${SLURM_ARRAY_TASK_ID:-}" ] && RUNTAG="run${SLURM_ARRAY_TASK_ID}"
SIF=containers/python310.sif
PY="venvs/foodseg/bin/python"
TEST_IMG=/workspace/data/FoodSeg103/Images/img_dir/test
GT=data/FoodSeg103/Images/ann_dir/test
if [ -n "$RUNTAG" ]; then
  PRED_ROOT="data/preds/FoodSeg103_runs/$RUNTAG"; LINEDIR="results/_fs103_runs/$RUNTAG"
else
  PRED_ROOT="data/preds/FoodSeg103"; LINEDIR="results/_fs103"
fi
mkdir -p "$PRED_ROOT" results "$LINEDIR"
LIMARG=""; [ "$LIMIT" -gt 0 ] && LIMARG="--limit $LIMIT"
NEED=$LIMIT; [ "$LIMIT" -eq 0 ] && NEED=2135
echo "### RUNTAG='$RUNTAG' PRED_ROOT=$PRED_ROOT ###"

PYV(){ singularity exec --nv --pwd /workspace --bind "$PWD":/workspace "$SIF" $PY "$@"; }
want(){ [ -z "$ONLY" ] && return 0; for t in $ONLY; do [ "$t" = "$1" ] && return 0; done; return 1; }

# TAG|CONFIG(rel assets/ckpts)|CKPT(rel assets/ckpts)
METHODS=(
  "FPN|FPN/fpn_r50_512x1024_80k.py|FPN/iter_80000.pth"
  "FPN_ReLeM|FPN_ReLeM/fpn_r50_512x1024_80k.py|FPN_ReLeM/iter_80000.pth"
  "CCNet|CCNet/ccnet_r101-d8_512x1024_80k.py|CCNet/iter_80000.pth"
  "CCNet_ReLeM|CCNet_ReLeM/ccnet_r50-d8_512x1024_80k.py|CCNet_ReLeM/iter_80000.pth"
  "SETR_Naive|SETR_Naive/SETR_Naive_768x768_80k_base.py|SETR_Naive/iter_80000.pth"
  "SETR_Naive_ReLeM|SETR_Naive_ReLeM/SETR_Naive_768x768_80k_base.py|SETR_Naive_ReLeM/iter_80000.pth"
  "SETR_MLA_L384|SETR_MLA_L384/SETR_MLA_768x768_80k.py|SETR_MLA_L384/iter_80000.pth"
  "SETR_MLA_ReLeM|SETR_MLA_ReLeM/SETR_MLA_768x768_80k_base.py|SETR_MLA_ReLeM/iter_80000.pth"
  "swin_small|swin_small/upernet_swin_small_patch4_window7_512x1024_80k.py|swin_small/iter_80000.pth"
  "swin_base|swin_base/upernet_swin_base_patch4_window7_512x1024_80k.py|swin_base/iter_80000.pth"
)

echo "########## mmseg inference ##########"
for m in "${METHODS[@]}"; do
  IFS='|' read -r TAG CFG CKPT <<< "$m"
  want "$TAG" || continue
  OUT="$PRED_ROOT/$TAG"
  have=$(ls "$OUT" 2>/dev/null | wc -l)
  if [ "$LIMIT" -eq 0 ] && [ "$have" -ge "$NEED" ]; then
    echo ">>> $TAG: $have preds present, skip"; continue
  fi
  echo ">>> $TAG  ($CFG)"
  PYV /workspace/src/foodseg_batch.py $LIMARG \
    --config /workspace/assets/ckpts/$CFG \
    --checkpoint /workspace/assets/ckpts/$CKPT \
    --img_dir "$TEST_IMG" --out_dir /workspace/$OUT \
    || echo "!!! $TAG FAILED"
done

echo "########## YOLO inference ##########"
YOUT="$PRED_ROOT/YOLO"
yhave=$(ls "$YOUT" 2>/dev/null | wc -l)
if ! want YOLO; then
  echo ">>> YOLO not in ONLY, skip"
elif [ "$LIMIT" -ne 0 ] || [ "$yhave" -lt "$NEED" ]; then
  mkdir -p "$YOUT"
  # YOLO has no --limit; for smoke run on full dir is fine but slow, so cap via a temp subset
  if [ "$LIMIT" -gt 0 ]; then
    SUB=/workspace/data/preds/FoodSeg103/_yolo_smoke_in
    rm -rf "$PWD/data/preds/FoodSeg103/_yolo_smoke_in"; mkdir -p "$PWD/data/preds/FoodSeg103/_yolo_smoke_in"
    ls data/FoodSeg103/Images/img_dir/test/*.jpg | head -n "$LIMIT" | xargs -I{} cp {} "$PWD/data/preds/FoodSeg103/_yolo_smoke_in/"
    YIN="$SUB"
  else
    YIN="$TEST_IMG"
  fi
  singularity exec --nv --pwd /workspace --bind "$PWD":/workspace \
    --env YOLO_OFFLINE=True --env YOLO_CONFIG_DIR=/workspace/.ultra_cfg \
    containers/ultralytics.sif \
    python /workspace/src/yolo/yolo_inference.py \
      /workspace/assets/ckpts/YOLO/yolo11s-seg_foodseg103_2.pt \
      "$YIN" /workspace/$YOUT || echo "!!! YOLO FAILED"
else
  echo ">>> YOLO: $yhave preds present, skip"
fi

echo "########## evaluation (mIoU / mAcc) ##########"
for TAG in FPN FPN_ReLeM CCNet CCNet_ReLeM SETR_Naive SETR_Naive_ReLeM SETR_MLA_L384 SETR_MLA_ReLeM swin_small swin_base YOLO; do
  want "$TAG" || continue
  OUT="$PRED_ROOT/$TAG"
  npred=$(ls "$OUT" 2>/dev/null | wc -l)
  [ "$npred" -ge "$NEED" ] || { echo "skip $TAG ($npred preds < $NEED)"; continue; }
  LINE=$(PYV /workspace/src/foodseg103_eval.py --pred_dir /workspace/$OUT --gt_dir /workspace/$GT --name "$TAG" 2>/dev/null | grep '^RESULT,')
  echo "$LINE"
  # RESULT,<tag>,<n>,<present>,<mIoU>,<mAcc>,<aAcc>  ->  $LINEDIR/<tag>.line
  echo "$LINE" | sed 's/^RESULT,//' > "$LINEDIR/$TAG.line"
done
echo "########## DONE (job $SLURM_JOB_ID, RUNTAG='$RUNTAG', ONLY='$ONLY') ##########"
cat "$LINEDIR"/*.line 2>/dev/null
