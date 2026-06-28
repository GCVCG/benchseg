#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH -J segman_smoke
#SBATCH -o logs/segman_smoke_%j.out
#SBATCH -e logs/segman_smoke_%j.out
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
SEG=$ROOT/baselines/SegMan/segmentation
WORK=$ROOT/work_dirs/_segman_smoke
CFG=local_configs/segman/base/segman_b_foodseg103.py
cd "$ROOT"
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
rm -rf "$WORK"; mkdir -p "$WORK" logs
ln -sfn "$ROOT/data" "$SEG/data"
# 50-iter validation: encoder load, dataset/classes parse, SyncBN, selective_scan, loss
singularity exec --nv --bind "$ROOT":"$ROOT" \
  --env CUDA_HOME=/usr/local/cuda \
  --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs:/usr/local/cuda/lib64 \
  --env TRITON_LIBCUDA_PATH=/.singularity.d/libs \
  --env PYTHONPATH=$SEG \
  --pwd "$SEG" "$ROOT/containers/pytorch21_devel.sif" \
  "$ROOT/venvs/segman21/bin/python" -m torch.distributed.launch \
    --nproc_per_node=1 --master_port=$((RANDOM+20000)) \
    tools/train.py "$CFG" --launcher pytorch --work-dir "$WORK" \
    --cfg-options runner.max_iters=50 log_config.interval=10 \
                  data.samples_per_gpu=4 evaluation.interval=100000
echo "### smoke exit=$? $(date) ###"
