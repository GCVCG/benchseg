#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH -o logs/combos_%j.out
#SBATCH -e logs/combos_%j.out
# Missing seed x tracker combos: FLMM+X2, FLMM+S2, SeTM+S2 (all partitions).
# Same pipeline as FoodMem (SETR_MLA seed + xmem2), different seed/tracker.
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )

run_one(){ # method seed tracker partition
  local M=$1 S=$2 T=$3 P=$4 VENV TDIR EXTRA
  if [ "$T" = xmem2 ]; then VENV=venvs/xmem2/bin/python; TDIR=baselines/XMem2; EXTRA="--xmem_ckpt saves/XMem.pth";
  else VENV=venvs/sam2/bin/python; TDIR=baselines/SAM2; EXTRA="--sam2_ckpt $ROOT/baselines/_weights/sam2.1_hiera_large.pt"; fi
  [ -d "data/preds/$P/$S" ] || { echo "skip $M/$P (no seed $S)"; return; }
  [ "$(ls data/preds/$P/$M 2>/dev/null | wc -l)" -gt 0 ] && { echo "exists $M/$P, skip"; return; }
  singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
    /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
      --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/data/preds/$P/$S \
      --out_dir /workspace/data/preds/$P/$M --tracker $T --n_seed 1 \
      --venv_py /workspace/$VENV --tracker_dir /workspace/$TDIR $EXTRA
  echo "### $M/$P preds: $(ls data/preds/$P/$M 2>/dev/null|wc -l) ###"
}

# Partition-outer: finish small partitions (table-relevant) for ALL combos first; FKit last.
for P in N5K MTF VF FKIT; do
  run_one "FLMM+X2"  FLMM      xmem2 "$P"
  run_one "FLMM+S2"  FLMM      sam2  "$P"
  run_one "SeTM+S2"  SETR_MLA  sam2  "$P"
done
echo COMBOS_DONE
