#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=48G
#SBATCH --time=1:30:00
#SBATCH -o logs/natten_cuda_%j.out
#SBATCH -e logs/natten_cuda_%j.out
# Standalone, one-time: compile natten 0.17.1 WITH CUDA into venvs/segman21.
# Must run on a GPU node (natten gates CUDA on torch.cuda.is_available()).
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD; SIF=$ROOT/containers/pytorch21_devel.sif; PY=$ROOT/venvs/segman21/bin/python
nvidia-smi --query-gpu=name --format=csv,noheader
singularity exec --nv --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
  --env TORCH_CUDA_ARCH_LIST="8.0;9.0" --env NATTEN_CUDA_ARCH="8.0;9.0" --env NATTEN_N_WORKERS=12 "$SIF" bash -c "
    python3 -c 'import torch;print(\"cuda avail at build:\",torch.cuda.is_available())'
    $PY -m pip install natten==0.17.1 --no-binary :all: --no-cache-dir --force-reinstall 2>&1 | tail -5
    $PY -c 'import torch,natten; from natten.functional import na2d,na2d_av,na2d_qk; from natten import use_fused_na; print(\"NATTEN_CUDA_OK\",natten.__version__,\"has_cuda\",natten.has_cuda())'
"
