#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH -J mem_abl
#SBATCH -o logs/mem_abl_%j.out
#SBATCH -e logs/mem_abl_%j.out
# Memory-size ablation (R3.8): FoodMem (SETR_MLA seed + XMem2), varying XMem2
# working-memory size max_mid_term_frames. Default 10 == existing FoodMem (reused).
# Output: FoodMem_mem<V>.
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
SEED=SETR_MLA

run(){ # partition memval
  local P=$1 V=$2
  local sd="data/preds/$P/$SEED" md="data/preds/$P/FoodMem_mem${V}"
  [ -d "$sd" ] || { echo "skip mem$V/$P (no seed)"; return; }
  local need=$(ls "$sd"|wc -l) have=$(ls "$md" 2>/dev/null|wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete mem$V/$P, skip"; return; }
  for attempt in 1 2 3; do
    [ "$(ls "$md" 2>/dev/null|wc -l)" -ge "$need" ] && break
    rm -rf "$md"
    echo ">>> FoodMem_mem$V/$P (max_mid_term_frames=$V) attempt $attempt $(date +%H:%M:%S)"
    timeout 50m singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
        --out_dir /workspace/$md --tracker xmem2 --n_seed 1 --xmem_max_mid $V \
        --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
    rc=$?; [ $rc -eq 124 ] && echo "  TIMED OUT (hang) attempt $attempt"
  done
  echo "### FoodMem_mem$V/$P: $(ls $md 2>/dev/null|wc -l)/$need $(date +%H:%M:%S) ###"
}

for P in N5K VF MTF FKIT; do
  for V in 5 20 40; do run "$P" "$V"; done
done
echo MEM_ABL_DONE
