#!/bin/bash
#SBATCH -p ladon
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH -J vc_gt
#SBATCH -o logs/vc_gt_%j.out
#SBATCH -e logs/vc_gt_%j.out
cd /mnt/beegfs/amughrabi/projects/BenchSeg
singularity exec --bind "$PWD":/workspace --pwd /workspace containers/ultralytics.sif python /workspace/src/view_magnitude_gt.py
echo VC_GT_DONE
