#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH -J mem_abl2
#SBATCH -o logs/mem_abl2_%j.out
#SBATCH -e logs/mem_abl2_%j.out
# Small-memory point: max_mid=4, min_mid=2 -> FoodMem_mem4 (genuine low working memory).
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
SEED=SETR_MLA
for P in N5K VF MTF FKIT; do
  sd="data/preds/$P/$SEED" md="data/preds/$P/FoodMem_mem4"
  need=$(ls "$sd"|wc -l)
  for attempt in 1 2 3; do
    [ "$(ls "$md" 2>/dev/null|wc -l)" -ge "$need" ] && break
    rm -rf "$md"
    echo ">>> FoodMem_mem4/$P (max_mid=4,min_mid=2) attempt $attempt $(date +%H:%M:%S)"
    timeout 50m singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
        --out_dir /workspace/$md --tracker xmem2 --n_seed 1 --xmem_max_mid 4 --xmem_min_mid 2 \
        --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
  done
  echo "### FoodMem_mem4/$P: $(ls $md 2>/dev/null|wc -l)/$need ###"
done
echo MEM_ABL2_DONE
