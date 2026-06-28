#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH -J segfs_seed
#SBATCH -o logs/segfs_seed_%j.out
#SBATCH -e logs/segfs_seed_%j.out
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
SEG=$ROOT/baselines/SegMan/segmentation
cd "$ROOT"
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
ln -sfn "$ROOT/data" "$SEG/data"
LIMIT="${LIMIT:-0}"; LIMARG=""; [ "$LIMIT" -gt 0 ] && LIMARG="--limit $LIMIT"
CKPT=$ROOT/work_dirs/segman_b_foodseg103_80k/best_mIoU_iter_80000.pth
CFG=$ROOT/baselines/SegMan/segmentation/local_configs/segman/base/segman_b_foodseg103.py
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )

for P in N5K MTF VF FKIT; do
  IMGDIR=$ROOT/data/${IMGS[$P]}/images
  OUT=$ROOT/data/preds/$P/SegMan_FS
  need=$(ls "$IMGDIR" 2>/dev/null | wc -l); have=$(ls "$OUT" 2>/dev/null | wc -l)
  if [ "$LIMIT" -eq 0 ] && [ "$have" -ge "$need" ] && [ "$need" -gt 0 ]; then
    echo ">>> $P complete ($have/$need), skip"; continue; fi
  echo ">>> SegMan_FS seed on $P ($need frames, food=class>0) $(date +%H:%M:%S)"
  singularity exec --nv --bind "$ROOT":"$ROOT" \
    --env CUDA_HOME=/usr/local/cuda \
    --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs:/usr/local/cuda/lib64 \
    --env TRITON_LIBCUDA_PATH=/.singularity.d/libs \
    --env PYTHONPATH=$SEG \
    --pwd "$ROOT" "$ROOT/containers/pytorch21_devel.sif" \
    "$ROOT/venvs/segman21/bin/python" "$ROOT/src/segman_batch.py" \
      --config "$CFG" --checkpoint "$CKPT" --food_classes gt0 \
      --img_dir "$IMGDIR" --out_dir "$OUT" $LIMARG
  echo "### $P: $(ls "$OUT" 2>/dev/null|wc -l)/$need $(date +%H:%M:%S) ###"
done
echo SEGFS_SEED_DONE
