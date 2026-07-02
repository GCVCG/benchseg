#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH -J test_pad
#SBATCH -o logs/test_pad_%j.out
#SBATCH -e logs/test_pad_%j.out
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
for M in 1 3; do
  singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
    /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
      --img_dir /workspace/data/n5k_reordered/images --seed_preds_dir /workspace/data/preds/N5K/YOLO \
      --out_dir /workspace/data/_testpad/Y+X2_M${M} --tracker xmem2 --n_seed $M \
      --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
done
# also a random M=1
singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
  /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
    --img_dir /workspace/data/n5k_reordered/images --seed_preds_dir /workspace/data/preds/N5K/YOLO \
    --out_dir /workspace/data/_testpad/Y+X2_M1_r0 --tracker xmem2 --n_seed 1 --seed_select random --seed_rng 0 \
    --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
singularity exec --bind "$ROOT":/workspace --pwd /workspace "$ROOT/containers/ultralytics.sif" python -c "
import numpy as np, glob, os
from PIL import Image
for d in ['Y+X2_M1','Y+X2_M3','Y+X2_M1_r0']:
    fs=sorted(glob.glob(f'data/_testpad/{d}/*.png'))
    nz=sum(1 for f in fs if np.array(Image.open(f)).any())
    print(f'{d}: {nz}/{len(fs)} nonempty')
"
echo TEST_PAD_DONE
