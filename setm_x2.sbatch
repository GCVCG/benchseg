#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=13:00:00
#SBATCH -J setm_x2
#SBATCH -o logs/setm_x2_%j.out
#SBATCH -e logs/setm_x2_%j.out
# SeTM+X2 = SETR_MLA seed + XMem2 (completes the SeTM hybrid set; headline best model).
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
S=SETR_MLA; M="SeTM+X2"
for P in N5K VF MTF FKIT; do
  sd="data/preds/$P/$S"; md="data/preds/$P/$M"
  [ -d "$sd" ] || { echo "skip $M/$P (no seed)"; continue; }
  need=$(ls "$sd"|wc -l); have=$(ls "$md" 2>/dev/null|wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete $M/$P ($have/$need), skip"; continue; }
  [ "$have" -gt 0 ] && { echo "partial $M/$P, wiping"; rm -rf "$md"; }
  echo ">>> $M/$P ($need frames) $(date +%H:%M:%S)"
  singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
    /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
      --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
      --out_dir /workspace/$md --tracker xmem2 --n_seed 1 \
      --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
  echo "### $M/$P: $(ls $md 2>/dev/null|wc -l)/$need $(date +%H:%M:%S) ###"
done
echo SETM_X2_DONE
