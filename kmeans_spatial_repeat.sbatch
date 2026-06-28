#!/bin/bash
#SBATCH -p ladon
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH -J km_sp_rep
#SBATCH -o logs/km_sp_rep_%A_%a.out
#SBATCH -e logs/km_sp_rep_%A_%a.out
# Spatial metrics for kMean++ (the only stochastic method) across 5 seeds, so the
# spatial repeatability table can report a real mean/std for it. Deterministic
# methods are std=0 and handled by aggregate_spatial_runs.py from spatial_metrics.csv.
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD; SIF=containers/ultralytics.sif
run(){ singularity exec --bind "$ROOT":/workspace --pwd /workspace "$SIF" "$@" 2>/dev/null; }
seed="${SLURM_ARRAY_TASK_ID:-0}"
declare -A GT=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
RUN=data/_kmrep/run$seed
OUT=results/_kmspatial; mkdir -p "$OUT" logs
rm -rf "$RUN"
for part in N5K MTF VF FKIT; do
  echo ">>> seed $seed / $part $(date +%H:%M:%S)"
  run python /workspace/src/kmeans_seg.py --img_dir /workspace/data/${GT[$part]}/images \
      --out_dir /workspace/$RUN/$part/kMean++ --seed $seed
done
run python /workspace/src/spatial_metrics.py --preds_root /workspace/$RUN \
    --only_method "kMean++" --out_csv /workspace/$OUT/run$seed.csv
rm -rf "$RUN"
echo "### seed $seed done: $(wc -l < $OUT/run$seed.csv) rows $(date +%H:%M:%S) ###"
