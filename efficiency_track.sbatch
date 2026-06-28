#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH -J eff_track
#SBATCH -o logs/eff_track_%j.out
#SBATCH -e logs/eff_track_%j.out
# Per-frame tracking speed + peak VRAM for XMem2 / SAM2 / SAM3 on one N5K scene
# (the tracker cost dominates every hybrid's Speed/VRAM; hybrid params = seed + tracker).
set -u
ROOT=/mnt/beegfs/amughrabi/projects/BenchSeg
cd "$ROOT"
export HF_HUB_OFFLINE=1
echo "### $(hostname) $(date) ###"; nvidia-smi --query-gpu=name --format=csv,noheader
OUT=results/efficiency_track.csv; mkdir -p results logs
echo "tracker,speed_ms_img,vram_MB,nframes" > "$OUT"

# build a one-scene sample (N5K scene "10": frames 10_*.png) with matching seeds
SI=$ROOT/data/_eff_track/img; SS=$ROOT/data/_eff_track/seed
rm -rf "$ROOT/data/_eff_track"; mkdir -p "$SI" "$SS"
cp $ROOT/data/n5k_reordered/images/10_*.png "$SI"/ 2>/dev/null
cp $ROOT/data/preds/N5K/SegMan_FS/10_*.png "$SS"/ 2>/dev/null
NF=$(ls "$SI" | wc -l); echo "scene frames: $NF"

measure(){  # tag  cmd...
  local TAG=$1; shift
  local mlog=$(mktemp) t0 t1
  ( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; sleep 0.2; done ) > "$mlog" &
  local smi=$!
  t0=$(date +%s.%N); "$@" > /tmp/eff_$TAG.log 2>&1; t1=$(date +%s.%N)
  kill $smi 2>/dev/null
  local peak=$(sort -n "$mlog" | tail -1); rm -f "$mlog"
  local spd=$(awk "BEGIN{printf \"%.1f\", ($t1-$t0)/$NF*1000}")
  echo "$TAG -> ${spd} ms/img, peak ${peak} MB ($NF frames)"
  echo "$TAG,${spd},${peak},${NF}" >> "$OUT"
}

run_track(){  # tracker venv tdir extra...
  local T=$1 VENV=$2 TDIR=$3; shift 3
  rm -rf "$ROOT/data/_eff_track/out_$T"
  if [ "$T" = sam3 ]; then
    singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/sam3/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/_eff_track/img --seed_preds_dir /workspace/data/_eff_track/seed \
        --out_dir /workspace/data/_eff_track/out_$T --tracker sam3 --n_seed 1 \
        --venv_py /workspace/venvs/sam3/bin/python --tracker_dir /workspace
  else
    singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
      /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
        --img_dir /workspace/data/_eff_track/img --seed_preds_dir /workspace/data/_eff_track/seed \
        --out_dir /workspace/data/_eff_track/out_$T --tracker $T --n_seed 1 \
        --venv_py /workspace/$VENV --tracker_dir /workspace/$TDIR "$@"
  fi
}

measure xmem2 run_track xmem2 venvs/xmem2/bin/python baselines/XMem2 --xmem_ckpt saves/XMem.pth
measure sam2  run_track sam2  venvs/sam2/bin/python  baselines/SAM2  --sam2_ckpt "$ROOT/baselines/_weights/sam2.1_hiera_large.pt"
measure sam3  run_track sam3  x x

rm -rf "$ROOT/data/_eff_track"
echo "########## EFF_TRACK DONE ##########"; cat "$OUT"
