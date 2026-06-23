#!/bin/bash
# SegMan env on the pytorch-devel SIF (nvcc). torch 2.1.0+cu121 satisfies both
# mmcv-full 1.7.2 (prebuilt cu121/torch2.1) and VMamba selective_scan (>=2.1).
set -e
cd /mnt/beegfs/amughrabi/projects/BenchSeg
SIF=containers/pytorch_devel.sif; ROOT=$PWD
RUN(){ singularity exec --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
        --env TORCH_CUDA_ARCH_LIST="8.0;9.0" --env FORCE_CUDA=1 "$SIF" "$@"; }
PY=$ROOT/venvs/segman/bin/python
rm -rf venvs/segman
singularity exec "$SIF" python3 -m venv venvs/segman
RUN "$PY" -m pip install --upgrade "pip<24" "setuptools<70" wheel
echo "[torch 2.1.0 cu121]"
RUN "$PY" -m pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121
echo "[mmcv-full 1.7.2 prebuilt cu121/torch2.1]"
RUN "$PY" -m pip install mmcv-full==1.7.2 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.1.0/index.html 2>&1 | tail -3
echo "[mmseg 0.30 + mmcls + deps]"
RUN "$PY" -m pip install mmsegmentation==0.30.0 mmcls==0.25.0 mmengine==0.10.5 "numpy<2" opencv-python-headless timm==0.6.12 triton==2.1.0 einops ninja "yapf<0.41" prettytable scipy pillow ftfy regex setuptools-scm
echo "[selective_scan compile]"
( cd baselines/SegMan/kernels/selective_scan && RUN "$PY" -m pip install . 2>&1 | tail -5 )
echo "[gdown ADE20k SegMan weights]"
RUN "$PY" -m pip install gdown
mkdir -p baselines/SegMan/pretrained_seg
# SegMan trained segmentation weights folder (from README google drive)
RUN "$PY" -m gdown --folder "https://drive.google.com/drive/folders/1C2bmb7KP7mECm9c04NCrUAJQGsEf_bQ4" -O baselines/SegMan/pretrained_seg 2>&1 | tail -4 || echo "gdown folder may need manual"
echo "[import check]"
RUN "$PY" -c "import torch, mmcv, mmseg, selective_scan_cuda; print('SegMan env OK torch', torch.__version__, 'mmcv', mmcv.__version__)" 2>&1 | tail -2
echo SEGMAN_ENV_DONE
