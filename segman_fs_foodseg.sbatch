#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH -J segfs_eval
#SBATCH -o logs/segfs_eval_%j.out
#SBATCH -e logs/segfs_eval_%j.out
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
SEG=$ROOT/baselines/SegMan/segmentation
cd "$ROOT"
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
LIMIT="${LIMIT:-0}"; LIMARG=""; [ "$LIMIT" -gt 0 ] && LIMARG="--limit $LIMIT"
CKPT=$ROOT/work_dirs/segman_b_foodseg103_80k/best_mIoU_iter_80000.pth
CFG=$ROOT/baselines/SegMan/segmentation/local_configs/segman/base/segman_b_foodseg103.py
OUT=$ROOT/data/preds/FoodSeg103/SegMan_FS
GT=$ROOT/data/FoodSeg103/Images/ann_dir/test
TEST=$ROOT/data/FoodSeg103/Images/img_dir/test
ln -sfn "$ROOT/data" "$SEG/data"

echo "########## SegMAN 104-class inference on FoodSeg103 test ##########"
singularity exec --nv --bind "$ROOT":"$ROOT" \
  --env CUDA_HOME=/usr/local/cuda \
  --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs:/usr/local/cuda/lib64 \
  --env TRITON_LIBCUDA_PATH=/.singularity.d/libs \
  --env PYTHONPATH=$SEG \
  --pwd "$ROOT" "$ROOT/containers/pytorch21_devel.sif" \
  "$ROOT/venvs/segman21/bin/python" "$ROOT/src/segman_batch.py" \
    --config "$CFG" --checkpoint "$CKPT" --multiclass \
    --img_dir "$TEST" --out_dir "$OUT" $LIMARG

echo "########## dense mIoU / mAcc eval ##########"
singularity exec --nv --bind "$ROOT":"$ROOT" --pwd "$ROOT" "$ROOT/containers/pytorch21_devel.sif" \
  "$ROOT/venvs/segman21/bin/python" "$ROOT/src/foodseg103_eval.py" \
    --pred_dir "$OUT" --gt_dir "$GT" --name SegMan_FS
echo "### done $(date) ###"
