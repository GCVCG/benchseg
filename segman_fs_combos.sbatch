#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH -J segfs_combos
#SBATCH -o logs/segfs_combos_%j.out
#SBATCH -e logs/segfs_combos_%j.out
# Fine-tuned SegMAN (SegMan_FS) hybrids: SF+X2 (XMem2), SF+S2 (SAM2), SF+S3 (SAM3)
# across all 4 partitions. Seed = data/preds/<P>/SegMan_FS (binary food>0).
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
export HF_HUB_OFFLINE=1
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )

run_one(){ # method seed tracker partition
  local M=$1 S=$2 T=$3 P=$4
  local sd="data/preds/$P/$S" md="data/preds/$P/$M"
  [ -d "$sd" ] || { echo "skip $M/$P (no seed $S)"; return; }
  local need=$(ls "$sd" 2>/dev/null | wc -l) have=$(ls "$md" 2>/dev/null | wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete $M/$P ($have/$need), skip"; return; }
  [ "$have" -gt 0 ] && { echo "partial $M/$P ($have/$need), wiping"; rm -rf "$md"; }
  echo ">>> $M/$P (seed $S, tracker $T, $need frames) $(date +%H:%M:%S)"
  if [ "$T" = sam3 ]; then
    singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/sam3/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
        --out_dir /workspace/$md --tracker sam3 --n_seed 1 \
        --venv_py /workspace/venvs/sam3/bin/python --tracker_dir /workspace
  else
    local VENV TDIR EXTRA
    if [ "$T" = xmem2 ]; then VENV=venvs/xmem2/bin/python; TDIR=baselines/XMem2; EXTRA="--xmem_ckpt saves/XMem.pth";
    else VENV=venvs/sam2/bin/python; TDIR=baselines/SAM2; EXTRA="--sam2_ckpt $ROOT/baselines/_weights/sam2.1_hiera_large.pt"; fi
    singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
        --out_dir /workspace/$md --tracker $T --n_seed 1 \
        --venv_py /workspace/$VENV --tracker_dir /workspace/$TDIR $EXTRA
  fi
  echo "### $M/$P: $(ls $md 2>/dev/null | wc -l)/$need $(date +%H:%M:%S) ###"
}

# lighter partitions first so results land early; FKIT (20606 frames) last
for P in N5K VF MTF FKIT; do
  run_one "SF+X2" SegMan_FS xmem2 "$P"
  run_one "SF+S2" SegMan_FS sam2  "$P"
  run_one "SF+S3" SegMan_FS sam3  "$P"
done
echo SEGFS_COMBOS_DONE
