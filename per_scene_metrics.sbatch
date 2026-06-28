#!/bin/bash
#SBATCH -p ladon
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH -J per_scene
#SBATCH -o logs/per_scene_%j.out
#SBATCH -e logs/per_scene_%j.out
cd /mnt/beegfs/amughrabi/projects/BenchSeg
M="SeTM+S3,FoodMem,SETR_MLA,SF+X2,SegMan_FS,SegMan_ADE,Seg+S3,YOLO,Y+S3,BiRefNet,SeTM+S2"
singularity exec --bind "$PWD":/workspace --pwd /workspace containers/ultralytics.sif \
  python /workspace/src/per_scene_metrics.py --only_methods "$M" --out_csv /workspace/results/per_scene_metrics.csv
echo PSM_DONE
