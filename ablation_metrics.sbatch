#!/bin/bash
#SBATCH -p ladon
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=06:00:00
#SBATCH -J abl_metrics
#SBATCH -o logs/abl_metrics_%j.out
#SBATCH -e logs/abl_metrics_%j.out
cd /mnt/beegfs/amughrabi/projects/BenchSeg
P=$1; M=$(cat _abl_methods.txt)
singularity exec --bind "$PWD":/workspace --pwd /workspace containers/ultralytics.sif \
  python /workspace/src/ablation_metrics.py --only_part "$P" --only_methods "$M" \
    --out_spatial /workspace/results/ablation_spatial_${P}.csv
echo "ABL_METRICS_DONE $P"
