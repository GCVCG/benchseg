#!/bin/bash
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH -J k_phi
#SBATCH -o logs/k_phi_%j.out
#SBATCH -e logs/k_phi_%j.out
# FULL K/Phi ablation across ALL 18 hybrid configs (segmentor + tracker).
# Single-frame baselines have no Stage 3, so they are excluded by design.
# The no-reset anchor (keep_propagated / K=inf) is the existing main-table preds.
#
# Fan-out levers (split work across jobs/GPUs; each job resumable + idempotent):
#   PARTS     subset of {N5K VF MTF FKIT}    (default all)
#   TRACKERS  subset of {xmem2 sam2 sam3}    (default all)
#   METHODS   subset of the 18 hybrid names  (default all)
#   CFG_KEYS  subset of the 7 injection keys (default all)
#   DO_REG    1 to run the regression check  (default 0)
set -u
cd /mnt/beegfs/amughrabi/projects/BenchSeg
ROOT=$PWD
export HF_HUB_OFFLINE=1
nvidia-smi --query-gpu=name --format=csv,noheader
declare -A IMGS=( [N5K]=n5k_reordered [MTF]=mtf_foodMem_reordered [VF]=vf_reordered [FKIT]=FoodKit_dataset_reordered )
PARTS="${PARTS:-N5K VF MTF FKIT}"
TRACKERS="${TRACKERS:-xmem2 sam2 sam3}"
METHODS="${METHODS:-ALL}"
CFG_KEYS="${CFG_KEYS:-K10 K20 K30 K45 K60 K30_accept_fresh K30_union}"
DO_REG="${DO_REG:-0}"
KPHI=data/preds_kphi
mkdir -p logs "$KPHI"

# 18 hybrids: "method  segmentor(seed dir)  tracker"  (FoodMem == SeTR-MLA + XMem2)
HYBRIDS=(
  "FoodMem SETR_MLA xmem2"  "S+X2 SegMan_ADE xmem2"   "SC+X2 SegMan_COCO xmem2"
  "SF+X2 SegMan_FS xmem2"   "Y+X2 YOLO xmem2"         "FLMM+X2 FLMM xmem2"
  "SeTM+S2 SETR_MLA sam2"   "Seg+S2 SegMan_ADE sam2"  "SC+S2 SegMan_COCO sam2"
  "SF+S2 SegMan_FS sam2"    "Y+S2 YOLO sam2"          "FLMM+S2 FLMM sam2"
  "SeTM+S3 SETR_MLA sam3"   "Seg+S3 SegMan_ADE sam3"  "SC+S3 SegMan_COCO sam3"
  "SF+S3 SegMan_FS sam3"    "Y+S3 YOLO sam3"          "FLMM+S3 FLMM sam3"
)

key_fusion(){ case "$1" in *accept_fresh) echo accept_fresh;; *union) echo union;; *) echo overlap_gated;; esac; }
key_K(){ local k=${1#K}; echo "${k%%_*}"; }
in_list(){ local x=$1; shift; for e in "$@"; do [ "$e" = "$x" ] && return 0; done; return 1; }

reseed(){ # tracker img seed prop out K fusion
  local T=$1 img=$2 seed=$3 prop=$4 out=$5 K=$6 FUS=$7
  local SEXEC="singularity exec --nv --pwd /workspace --bind $ROOT:/workspace $ROOT/containers/python310.sif"
  case "$T" in
    sam3) $SEXEC /workspace/venvs/sam3/bin/python /workspace/src/track_pipeline_reseed.py \
            --img_dir "$img" --seed_preds_dir "$seed" --propagated_dir "$prop" --out_dir "$out" \
            --tracker sam3 --n_seed 1 --reseed_every "$K" --fusion "$FUS" \
            --venv_py /workspace/venvs/sam3/bin/python --tracker_dir /workspace ;;
    sam2) $SEXEC /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline_reseed.py \
            --img_dir "$img" --seed_preds_dir "$seed" --propagated_dir "$prop" --out_dir "$out" \
            --tracker sam2 --n_seed 1 --reseed_every "$K" --fusion "$FUS" \
            --venv_py /workspace/venvs/sam2/bin/python --tracker_dir /workspace/baselines/SAM2 \
            --sam2_ckpt /workspace/baselines/_weights/sam2.1_hiera_large.pt ;;
    xmem2) $SEXEC /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline_reseed.py \
            --img_dir "$img" --seed_preds_dir "$seed" --propagated_dir "$prop" --out_dir "$out" \
            --tracker xmem2 --n_seed 1 --reseed_every "$K" --fusion "$FUS" \
            --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth ;;
  esac
}

run_cfg(){ # method seg tracker part fusion K key
  local M=$1 S=$2 T=$3 P=$4 FUS=$5 K=$6 KEY=$7
  local sdl="data/preds/$P/$S" pdl="data/preds/$P/$M" mdl="$KPHI/${M}__${KEY}/$P"
  [ -d "$sdl" ] || { echo "skip $M/$KEY/$P (no seed $S)"; return; }
  [ -d "$pdl" ] || { echo "skip $M/$KEY/$P (no anchor $M)"; return; }
  local need=$(ls "$sdl"|wc -l) have=$(ls "$mdl" 2>/dev/null|wc -l)
  [ "$have" -ge "$need" ] && [ "$need" -gt 0 ] && { echo "complete $M/$KEY/$P ($have/$need), skip"; return; }
  [ "$have" -gt 0 ] && rm -rf "$mdl"
  mkdir -p "$mdl"
  echo ">>> $M/$KEY/$P (seg $S, $T, fusion=$FUS K=$K, $need frames) $(date +%H:%M:%S)"
  reseed "$T" "/workspace/data/${IMGS[$P]}/images" "/workspace/$sdl" "/workspace/$pdl" "/workspace/$mdl" "$K" "$FUS"
  echo "### $M/$KEY/$P: $(ls $mdl 2>/dev/null|wc -l)/$need $(date +%H:%M:%S) ###"
}

regression(){  # prove flag-absent == keep_propagated (bit-identical) on N5K / Y+X2
  local img="/workspace/data/n5k_reordered/images" seed="/workspace/data/preds/N5K/YOLO" prop="/workspace/data/preds/N5K/Y+X2"
  local d1=data/_kphi_reg/default d2=data/_kphi_reg/flagged
  rm -rf data/_kphi_reg; mkdir -p "$d1" "$d2"
  echo ">>> REGRESSION default vs keep_propagated (N5K/Y+X2) $(date +%H:%M:%S)"
  singularity exec --nv --pwd /workspace --bind "$ROOT":/workspace "$ROOT/containers/python310.sif" \
    /workspace/venvs/foodseg/bin/python /workspace/src/track_pipeline.py \
      --img_dir "$img" --seed_preds_dir "$seed" --out_dir "/workspace/$d1" --tracker xmem2 --n_seed 1 \
      --venv_py /workspace/venvs/xmem2/bin/python --tracker_dir /workspace/baselines/XMem2 --xmem_ckpt saves/XMem.pth
  reseed xmem2 "$img" "$seed" "$prop" "/workspace/$d2" 30 keep_propagated
  local h1=$(cd "$d1" && find . -name '*.png'|sort|xargs md5sum|md5sum|cut -d' ' -f1)
  local h2=$(cd "$d2" && find . -name '*.png'|sort|xargs md5sum|md5sum|cut -d' ' -f1)
  echo "REGRESSION default=$h1 keep_propagated=$h2"
  [ "$h1" = "$h2" ] && echo "REGRESSION PASS (bit-identical)" || echo "REGRESSION FAIL"
}

[ "$DO_REG" = 1 ] && regression

# light partitions land first within a job; cheap trackers scheduled via TRACKERS lever
for P in $PARTS; do
  for KEY in $CFG_KEYS; do
    FUS=$(key_fusion "$KEY"); K=$(key_K "$KEY")
    for row in "${HYBRIDS[@]}"; do
      set -- $row; M=$1; S=$2; T=$3
      in_list "$T" $TRACKERS || continue
      [ "$METHODS" = ALL ] || in_list "$M" $METHODS || continue
      run_cfg "$M" "$S" "$T" "$P" "$FUS" "$K" "$KEY"
    done
  done
done
echo K_PHI_FULL_DONE
