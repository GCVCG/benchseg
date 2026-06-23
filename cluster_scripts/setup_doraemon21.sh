#!/bin/bash
# DoraemonGPT env on torch-2.1 devel SIF (nvcc + torch2.1) so AOT's old code runs.
set -e
cd /mnt/beegfs/amughrabi/projects/BenchSeg
SIF=$PWD/containers/pytorch21_devel.sif; ROOT=$PWD
RUN(){ singularity exec --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
        --env TORCH_CUDA_ARCH_LIST="8.0;9.0" --env FORCE_CUDA=1 "$SIF" "$@"; }
PY=$ROOT/venvs/deva21/bin/python
rm -rf venvs/deva21
singularity exec "$SIF" python3 -m venv --system-site-packages venvs/deva21
RUN "$PY" -m pip install --upgrade "pip<24" "setuptools<70" wheel
RUN "$PY" -c "import torch;print('base torch',torch.__version__,torch.version.cuda)"
echo "[deps]"
RUN "$PY" -m pip install "numpy<2" "opencv-python-headless<4.12" pillow tqdm hickle gitpython scipy einops pycocotools "supervision==0.18.0" addict yapf timm "transformers==4.44.2" "tokenizers<0.20" pulp Cython scikit-image ipdb gdown
echo "[GroundingDINO compile vs torch2.1]"
RUN "$PY" -m pip install ./baselines/_src/GroundingDINO-main 2>&1 | tail -4
echo "[segment-anything]"
RUN "$PY" -m pip install ./baselines/_src/segment-anything-main
echo "[thinplate + deva]"
RUN "$PY" -m pip install ./baselines/_src/py-thin-plate-spline-master
RUN "$PY" -m pip install -e "$ROOT/baselines/DEVA" --no-deps
echo "[AOT correlation compile]"
( cd "$ROOT/baselines/DoraemonGPT/project/aot-benchmark/Pytorch-Correlation-extension" && RUN "$PY" -m pip install . 2>&1 | tail -3 )
echo "[verify]"
RUN "$PY" -c "import torch; from groundingdino import _C; import spatial_correlation_sampler, segment_anything, deva; print('DEVA21 ENV OK torch',torch.__version__)"
echo DEVA21_ENV_DONE
