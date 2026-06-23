#!/bin/bash
# DEVA env on the pytorch-devel SIF (python + torch 2.5.1 + nvcc) so
# GroundingDINO's CUDA op compiles for Hopper (arch 9.0).
set -e
cd /mnt/beegfs/amughrabi/projects/BenchSeg
SIF=containers/pytorch_devel.sif
ROOT=$PWD
RUN(){ singularity exec --bind "$ROOT":"$ROOT" \
        --env CUDA_HOME=/usr/local/cuda \
        --env TORCH_CUDA_ARCH_LIST="8.0;9.0" \
        --env FORCE_CUDA=1 \
        "$SIF" "$@"; }
PY=$ROOT/venvs/deva/bin/python

rm -rf venvs/deva
# venv inherits the image's torch via system site-packages
singularity exec "$SIF" python3 -m venv --system-site-packages venvs/deva
RUN "$PY" -m pip install --upgrade "pip<24" "setuptools<70" wheel
RUN "$PY" -c "import torch; print('base torch', torch.__version__, 'cuda', torch.version.cuda)"
echo "[deps]"
RUN "$PY" -m pip install "numpy<2" opencv-python-headless pillow tqdm hickle gitpython scipy einops pycocotools supervision addict yapf timm transformers
echo "[fetch GroundingDINO + SAM tarballs (image has no git)]"
mkdir -p baselines/_src
wget -q https://github.com/IDEA-Research/GroundingDINO/archive/refs/heads/main.tar.gz -O /tmp/gd.tgz && tar xzf /tmp/gd.tgz -C baselines/_src
wget -q https://github.com/facebookresearch/segment-anything/archive/refs/heads/main.tar.gz -O /tmp/sam.tgz && tar xzf /tmp/sam.tgz -C baselines/_src
echo "[GroundingDINO compile with nvcc]"
RUN "$PY" -m pip install ./baselines/_src/GroundingDINO-main 2>&1 | tail -6
echo "[segment-anything]"
RUN "$PY" -m pip install ./baselines/_src/segment-anything-main
echo "[deva -e]"
( cd baselines/DEVA && RUN "$PY" -m pip install -e . 2>&1 | tail -4 )
echo "[import check]"
RUN "$PY" -c "import torch, groundingdino, deva; from groundingdino import _C; print('DEVA env OK; GD _C compiled; torch', torch.__version__)"
echo DEVA_ENV_DONE
