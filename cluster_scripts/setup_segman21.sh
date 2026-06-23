#!/bin/bash
# SegMan env on torch-2.1 devel SIF. Key: natten 0.17.1 has use_fused_na + na2d
# (what segman_decoder needs) but predates the _device_t/torch-2.4 requirement,
# so it coexists with mmcv-1.7/selective_scan (torch 2.1).
set -e
cd /mnt/beegfs/amughrabi/projects/BenchSeg
SIF=$PWD/containers/pytorch21_devel.sif; ROOT=$PWD
RUN(){ singularity exec --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
        --env TORCH_CUDA_ARCH_LIST="8.0;9.0" --env FORCE_CUDA=1 "$SIF" "$@"; }
PY=$ROOT/venvs/segman21/bin/python
rm -rf venvs/segman21
singularity exec "$SIF" python3 -m venv --system-site-packages venvs/segman21
RUN "$PY" -m pip install --upgrade "pip<24" "setuptools<70" wheel
RUN "$PY" -c "import torch,sys;print('torch',torch.__version__,'py',sys.version.split()[0])"
echo "[mmcv 1.7.2 prebuilt cu121/torch2.1]"
RUN "$PY" -m pip install mmcv-full==1.7.2 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.1.0/index.html 2>&1 | tail -2
RUN "$PY" -m pip install mmsegmentation==0.30.0 mmcls==0.25.0 "numpy<2" "opencv-python-headless<4.12" "timm==0.6.12" einops ninja "yapf<0.41" prettytable scipy pillow ftfy regex fvcore
echo "[selective_scan compile vs torch2.1]"
( cd "$ROOT/baselines/SegMan/kernels/selective_scan" && RUN "$PY" -m pip install . 2>&1 | tail -3 )
echo "[natten 0.17.1 prebuilt cu121/torch2.1]"
RUN "$PY" -m pip install natten==0.17.1 -f https://shi-labs.com/natten/wheels/cu121/torch2.1.0/index.html 2>&1 | tail -3
echo "[verify base]"
RUN "$PY" -c "import torch,mmcv,mmseg,selective_scan_cuda_oflex,natten; from natten.functional import na2d, na2d_av, na2d_qk; from natten import use_fused_na; print('SEGMAN21 OK natten',natten.__version__,'has_cuda',natten.has_cuda())" 2>&1 | tail -3
echo SEGMAN21_ENV_DONE
