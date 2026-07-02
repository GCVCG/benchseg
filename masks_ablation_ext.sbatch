#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH -J masks_abl2
#SBATCH -o logs/masks_abl2_%j.out
#SBATCH -e logs/masks_abl2_%j.out
# Parameterized M-ablation runner (XMem2 family). Env vars:
#   COMBOS  space-sep "combo:seed" pairs (default: SF+X2:SegMan_FS)
#   MS      space-sep M values        (default: "3 6 9")
#   MODE    first|random              (default: first)
#   RNGS    space-sep draw seeds       (default: "0 1 2"; only used for MODE=random)
# Output dirs: <combo>_M<M>  (first)   or  <combo>_M<M>_r<draw>  (random)
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
: "${COMBOS:=SF+X2:SegMan_FS}"; : "${MS:=3 6 9}"; : "${MODE:=first}"; : "${RNGS:=0 1 2}"
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )

run(){ # combo seed partition M outsuffix seedrng
  local C=$1 S=$2 P=$3 M=$4 SUF=$5 RNG=$6
  local sd="data/preds/$P/$S" md="data/preds/$P/${C}_M${M}${SUF}"
  [ -d "$sd" ] || { echo "skip ${C}_M${M}${SUF}/$P (no seed $S)"; return; }
  local need=$(ls "$sd" 2>/dev/null | wc -l) have=$(ls "$md" 2>/dev/null | wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete ${C}_M${M}${SUF}/$P, skip"; return; }
  # timeout+retry: intermittent XMem2/FKIT GPU hangs are killed at 50m and retried (fresh process)
  for attempt in 1 2 3; do
    [ "$(ls "$md" 2>/dev/null | wc -l)" -ge "$need" ] && break
    rm -rf "$md"
    echo ">>> ${C}_M${M}${SUF}/$P (seed $S, n_seed=$M, $MODE rng=$RNG) attempt $attempt $(date +%H:%M:%S)"
    timeout 50m singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/${IMGS[$P]}/images --seed_preds_dir /workspace/$sd \
        --out_dir /workspace/$md --tracker xmem2 --n_seed $M \
        --seed_select $MODE --seed_rng $RNG \
        --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
    rc=$?; [ $rc -eq 124 ] && echo "  TIMED OUT (hang) attempt $attempt"
  done
  echo "### ${C}_M${M}${SUF}/$P: $(ls $md 2>/dev/null | wc -l)/$need $(date +%H:%M:%S) ###"
}

for P in N5K VF MTF FKIT; do
  for pair in $COMBOS; do
    C=${pair%%:*}; S=${pair##*:}
    for M in $MS; do
      if [ "$MODE" = "random" ]; then
        for d in $RNGS; do run "$C" "$S" "$P" "$M" "_r$d" "$d"; done
      else
        run "$C" "$S" "$P" "$M" "" 0
      fi
    done
  done
done
echo MASKS_ABL_EXT_DONE
