#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH -J masks_abl
#SBATCH -o logs/masks_abl_%j.out
#SBATCH -e logs/masks_abl_%j.out
# Mask-count (M) ablation: YOLO+XMem2 (Y+X2) and SegMan+XMem2 (S+X2) seeded from
# M = {3,6,9} frames (M=1 already exists as Y+X2 / S+X2). Output -> <combo>_M<M>.
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
# combo -> seed method
declare -A SEED=( [Y+X2]=YOLO [S+X2]=SegMan_ADE )

run(){ # combo seed partition M
  local C=$1 S=$2 P=$3 M=$4
  local sd="data/preds/$P/$S" md="data/preds/$P/${C}_M${M}"
  [ -d "$sd" ] || { echo "skip ${C}_M${M}/$P (no seed $S)"; return; }
  local need=$(ls "$sd" 2>/dev/null | wc -l) have=$(ls "$md" 2>/dev/null | wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete ${C}_M${M}/$P ($have/$need), skip"; return; }
  [ "$have" -gt 0 ] && { echo "partial ${C}_M${M}/$P, wiping"; rm -rf "$md"; }
  echo ">>> ${C}_M${M}/$P (seed $S, n_seed=$M) $(date +%H:%M:%S)"
  singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
    /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
      --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
      --out_dir /workspace/$md --tracker xmem2 --n_seed $M \
      --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
  echo "### ${C}_M${M}/$P: $(ls $md 2>/dev/null | wc -l)/$need $(date +%H:%M:%S) ###"
}

for P in N5K VF MTF FKIT; do
  for M in 3 6 9; do
    run "Y+X2" YOLO       "$P" "$M"
    run "S+X2" SegMan_ADE "$P" "$M"
  done
done
echo MASKS_ABL_DONE
