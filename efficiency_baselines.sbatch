#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH -J eff_base
#SBATCH -o logs/eff_base_%j.out
#SBATCH -e logs/eff_base_%j.out
# Heavy standalone baselines: speed/img + peak VRAM on one N5K scene (~58 frames).
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
cd "$ROOT"
export HF_HUB_OFFLINE=1
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
OUT=results/efficiency_baselines.csv; mkdir -p results logs
echo "method,speed_ms_img,vram_MB,nframes" > "$OUT"

# one-scene sample (N5K scene 10) as its own partition-like dir with images/
SD=$ROOT/data/_eff_base; rm -rf "$SD"; mkdir -p "$SD/images"
cp $ROOT/data/n5k_reordered/images/10_*.png "$SD/images"/ 2>/dev/null
NF=$(ls "$SD/images" | wc -l); echo "scene frames: $NF"

measure(){ # tag cmd...
  local TAG=$1; shift
  local mlog=$(mktemp) t0 t1
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; sleep 0.3; done ) > "$mlog" &
  local smi=$!
  t0=$(date +%s.%N); "$@" > "logs/effbase_$TAG.log" 2>&1; local rc=$?; t1=$(date +%s.%N)
  kill $smi 2>/dev/null
  local peak=$(sort -n "$mlog" | tail -1); rm -f "$mlog"
  local np=$(ls "$SD/out_$TAG" 2>/dev/null | wc -l); [ "$np" -eq 0 ] && np=$NF
  local spd=$(awk "BEGIN{printf \"%.1f\", ($t1-$t0)/$np*1000}")
  echo "$TAG -> ${spd} ms/img, peak ${peak} MB (rc=$rc, $np out)"
  echo "$TAG,${spd},${peak},${np}" >> "$OUT"
}

# kMean++ (ultralytics)
measure kMean++ singularity exec --nv --bind "$ROOT":/workspace --pwd /workspace "$ROOT/containers/ultralytics.sif" \
  python /workspace/src/kmeans_seg.py --img_dir /workspace/data/_eff_base/images --out_dir /workspace/data/_eff_base/out_kMean++

# BiRefNet
measure BiRefNet singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
  "$ROOT/venvs/birefnet/bin/python" /workspace/baselines/batch_birefnet.py \
    --img_dir /workspace/data/_eff_base/images --out_dir /workspace/data/_eff_base/out_BiRefNet --limit 0

# DEVA (one scene)
measure DEVA singularity exec --nv --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda --pwd "$ROOT" \
  "$ROOT/containers/pytorch_devel.sif" "$ROOT/venvs/deva/bin/python" "$ROOT/src/deva_run.py" \
    --img_dir "$SD/images" --out_dir "$SD/out_DEVA" --deva_dir "$ROOT/baselines/DEVA" \
    --venv_py "$ROOT/venvs/deva/bin/python" --prompt food --limit_scenes 1

# FLMM (FoodLMM, 7.7B) - slow per frame
measure FLMM singularity exec --nv --pwd /workspace/baselines/FoodLMM --bind "$ROOT":/workspace \
  "$ROOT/containers/python310.sif" "$ROOT/venvs/foodlmm/bin/python" batch_foodlmm.py \
    --version /workspace/baselines/_weights/FoodLMM-Chat --cfg_file train_config_Stage2.yaml \
    --img_dir /workspace/data/_eff_base/images --out_dir /workspace/data/_eff_base/out_FLMM

# DoraemonGPT (agent, one scene)
measure DoraemonGPT singularity exec --nv --bind "$ROOT":"$ROOT" --env CUDA_HOME=/usr/local/cuda \
  --env LD_LIBRARY_PATH=$ROOT/xlibs:/.singularity.d/libs --pwd "$ROOT" \
  "$ROOT/containers/pytorch21_devel.sif" "$ROOT/venvs/deva21/bin/python" "$ROOT/src/doraemon_run.py" \
    --img_dir "$SD/images" --out_dir "$SD/out_DoraemonGPT" --dora_root "$ROOT/baselines/DoraemonGPT" \
    --prompt food --limit_scenes 1

rm -rf "$SD"
echo "########## EFF_BASE DONE ##########"; cat "$OUT"
