#!/bin/bash
# DoraemonGPT segmentation tool = GroundedSAM('food') + AOT (R50_DeAOTL).
# Reuses the deva venv (GroundingDINO+SAM compiled); adds AOT correlation ext + weights.
set -e
cd /mnt/beegfs/amughrabi/projects/BenchSeg
SIF=containers/pytorch_devel.sif; ROOT=$PWD
RUN(){ singularity exec --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
        --env TORCH_CUDA_ARCH_LIST="8.0;9.0" --env FORCE_CUDA=1 "$SIF" "$@"; }
PY=$ROOT/venvs/deva/bin/python
AOT=$ROOT/baselines/DoraemonGPT/project/aot-benchmark
echo "[compile Pytorch-Correlation-extension]"
( cd "$AOT/Pytorch-Correlation-extension" && RUN "$PY" -m pip install . 2>&1 | tail -4 )
RUN "$PY" -m pip install gdown timm scipy 2>&1 | tail -1
mkdir -p "$ROOT/baselines/DoraemonGPT/checkpoints/AOT" "$ROOT/baselines/DoraemonGPT/checkpoints/GroundedSAM"
cd "$ROOT/baselines/DoraemonGPT/checkpoints"
[ -f AOT/R50_DeAOTL_PRE_YTB_DAV.pth ] || RUN "$PY" -m gdown "1QXLFkbtxoQGZQHB5GcMjOlPbQTZxNFpO" -O AOT/R50_DeAOTL_PRE_YTB_DAV.pth 2>&1 | tail -2 || echo "AOT gdown id may need fixing"
[ -f GroundedSAM/groundingdino_swinb_cogcoor.pth ] || wget -q https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha2/groundingdino_swinb_cogcoor.pth -O GroundedSAM/groundingdino_swinb_cogcoor.pth
[ -f GroundedSAM/sam_vit_h_4b8939.pth ] || cp "$ROOT/baselines/_weights/sam_vit_h_4b8939.pth" GroundedSAM/
RUN "$PY" -c "import spatial_correlation_sampler, torch; print('AOT correlation OK torch', torch.__version__)" 2>&1 | tail -2
echo "AOT weight: $(ls -la AOT/*.pth 2>/dev/null|awk '{print $5}')"
echo DORAEMON_ENV_DONE
