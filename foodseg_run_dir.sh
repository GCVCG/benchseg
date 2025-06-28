#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# batch_predict.sh      – run semantic.py on every image under ROOT.
#                         SEM_MODEL_TYPE can now be a specific key *or* ALL.
# ----------------------------------------------------------------------------

set -euo pipefail
IFS=$'\n\t'

# --------------------------- positional args ---------------------------
ROOT=${1:? "First arg: root path to search"}
SEM_MODEL_TYPE=${2:? "Second arg: model key (e.g. SWIN_SMALL) – or ALL"}

# --------------------------- optional flags ---------------------------
BINARIZE=0
for arg in "${@:3}"; do
  case "$arg" in
    -b|--binarize) BINARIZE=1 ;;
    *)
      echo "Unknown flag '$arg'. Only --binarize (-b) is supported." >&2
      exit 1 ;;
  esac
done

# --------------------------- model lookup tables ---------------------------
declare -A CONFIG_PATHS=(
  [SWIN_SMALL]="assets/ckpts/swin_small/upernet_swin_small_patch4_window7_512x1024_80k.py"
  [SWIN_BASE]="assets/ckpts/swin_base/upernet_swin_base_patch4_window7_512x1024_80k.py"
  [FPN_RELEM]="assets/ckpts/FPN_ReLeM/fpn_r50_512x1024_80k.py"
  [CCNET]="assets/ckpts/CCNet/ccnet_r101-d8_512x1024_80k.py"
  [CCNET_RELEM]="assets/ckpts/CCNet_ReLeM/ccnet_r50-d8_512x1024_80k.py"
  [SETR_MLA_L384]="assets/ckpts/SETR_MLA_L384/SETR_MLA_768x768_80k.py"
  [SETR_MLA_L384_SMALLER]="assets/ckpts/SETR_MLA_L384/SETR_MLA_768x768_80k_smaller.py"
  [SETR_NAIVE]="assets/ckpts/SETR_Naive/SETR_Naive_768x768_80k_base.py"
)
declare -A CHECKPOINT_PATHS=(
  [SWIN_SMALL]="assets/ckpts/swin_small/iter_80000.pth"
  [SWIN_BASE]="assets/ckpts/swin_base/iter_80000.pth"
  [FPN_RELEM]="assets/ckpts/FPN_ReLeM/iter_80000.pth"
  [CCNET]="assets/ckpts/CCNet/iter_80000.pth"
  [CCNET_RELEM]="assets/ckpts/CCNet_ReLeM/iter_80000.pth"
  [SETR_MLA_L384]="assets/ckpts/SETR_MLA_L384/iter_80000.pth"
  [SETR_MLA_L384_SMALLER]="assets/ckpts/SETR_MLA_L384/iter_80000.pth"
  [SETR_NAIVE]="assets/ckpts/SETR_Naive/iter_80000.pth"
)

# --------------------------- build model list ---------------------------
if [[ ${SEM_MODEL_TYPE^^} == "ALL" ]]; then
  MODEL_LIST=("${!CONFIG_PATHS[@]}")          # every key
else
  if [[ -z ${CONFIG_PATHS[$SEM_MODEL_TYPE]:-} ]]; then
    echo "Unknown SEM_MODEL_TYPE '$SEM_MODEL_TYPE'." >&2
    exit 1
  fi
  MODEL_LIST=("$SEM_MODEL_TYPE")
fi

# so convert doesn’t choke when there are no matches
shopt -s nullglob

# --------------------------- helper: run one model ---------------------------
run_for_model() {
  local MODEL="$1"
  local CONFIG="${CONFIG_PATHS[$MODEL]}"
  local CKPT="${CHECKPOINT_PATHS[$MODEL]}"

  # ---------- count images once per model (for neat % read-out) -------------
  local TOTAL
  TOTAL=$(find "$ROOT" -type d -name images -print0 | \
          xargs -0 -I{} find {} -maxdepth 1 -type f \
            \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print | wc -l)

  [[ $TOTAL -eq 0 ]] && { echo "No images found under '$ROOT'."; return; }

  echo "=== $MODEL: $TOTAL images ==="
  local PROCESSED=0

  while IFS= read -r IMG_DIR; do
    local PARENT OUT_DIR LOG IMG_PATH MASK
    PARENT=$(dirname "$IMG_DIR")
    OUT_DIR="$PARENT/outputs/$MODEL"
    mkdir -p "$OUT_DIR"
    LOG="$OUT_DIR/log.csv"

    for IMG_PATH in "$IMG_DIR"/*.{jpg,jpeg,png,JPG,JPEG,PNG}; do
      [[ -f $IMG_PATH ]] || continue
      MASK="$OUT_DIR/$(basename "${IMG_PATH%.*}.png")"
      if [[ -f $MASK ]]; then
        PROCESSED=$((PROCESSED+1))
        printf "\rProgress [%s]: %d/%d (%d%%)" \
               "$MODEL" "$PROCESSED" "$TOTAL" $((PROCESSED*100/TOTAL))
        continue
      fi

      python3 -u src/semantic.py \
        --img_path "$IMG_PATH" \
        --out_path "$OUT_DIR" \
        --log_path "$LOG" \
        --semantic_config "$CONFIG" \
        --semantic_checkpoint "$CKPT" \
        >/dev/null 2>&1

      if [[ $BINARIZE -eq 1 && -f $MASK ]]; then
        convert "$MASK" -threshold 1% "$MASK"
      fi

      PROCESSED=$((PROCESSED+1))
      printf "\rProgress [%s]: %d/%d (%d%%)" \
             "$MODEL" "$PROCESSED" "$TOTAL" $((PROCESSED*100/TOTAL))
    done
  done < <(find "$ROOT" -type d -name images)

  printf "\n%s complete. %d images processed.\n" "$MODEL" "$PROCESSED"
}

# --------------------------- run all requested models ------------------------
for MODEL in "${MODEL_LIST[@]}"; do
  run_for_model "$MODEL"
done
