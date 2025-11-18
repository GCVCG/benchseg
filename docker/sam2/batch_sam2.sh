#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

usage() {
  cat >&2 <<'USAGE'
Usage:
  batch_sam2.sh \
    --images DIR \
    --masks DIR \
    --output DIR \
    [--checkpoint PATH] \
    [--config NAME] \
    [--obj-id N] \
    [--temp DIR] \
    [--device cuda|cpu] \
    [--vos-optimized]

Notes:
- Images must be named <video_id>_<frame_number>.jpg  (e.g., apple_pie_00023.jpg)
- Masks must be named  <video_id>_<frame_number>.png  (binary or labeled)
- We pick the *lowest* available frame_number mask as the seed and set --frame_idx accordingly.
USAGE
  exit 1
}

IMAGES_DIR=""
MASKS_DIR=""
OUTPUT_DIR=""
TEMP_DIR="temp_processing_sam2"
CHECKPOINT="/workspace/tracking_models/sam2/sam2.1_hiera_large.pt"
CONFIG="configs/sam2.1/sam2.1_hiera_l.yaml"
OBJ_ID="1"
DEVICE="cuda"
VOS_OPTIMIZED=0

# ---------- parse args ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --images)       IMAGES_DIR="$2"; shift 2 ;;
    --masks)        MASKS_DIR="$2"; shift 2 ;;
    --output)       OUTPUT_DIR="$2"; shift 2 ;;
    --checkpoint)   CHECKPOINT="$2"; shift 2 ;;
    --config)       CONFIG="$2"; shift 2 ;;
    --obj-id)       OBJ_ID="$2"; shift 2 ;;
    --temp)         TEMP_DIR="$2"; shift 2 ;;
    --device)       DEVICE="$2"; shift 2 ;;
    --vos-optimized) VOS_OPTIMIZED=1; shift 1 ;;
    -h|--help)      usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

[[ -d "$IMAGES_DIR" && -d "$MASKS_DIR" ]] || { echo "images/masks dirs required"; usage; }
mkdir -p "$OUTPUT_DIR"

# absolute paths
IMAGES_DIR="$(readlink -f "$IMAGES_DIR")"
MASKS_DIR="$(readlink -f "$MASKS_DIR")"
OUTPUT_DIR="$(readlink -f "$OUTPUT_DIR")"
TEMP_DIR="$(readlink -f "$TEMP_DIR")"
mkdir -p "$TEMP_DIR"

# ---------- discover unique video_ids ----------
# video_id := name without extension, with trailing _<digits> removed
mapfile -t video_ids < <(
  find "$IMAGES_DIR" -maxdepth 1 -type f -name '*.jpg' -printf '%f\n' \
  | sed -E 's/\.[^.]+$//' \
  | sed -E 's/_[0-9]+$//' \
  | sort -u
)

if [[ ${#video_ids[@]} -eq 0 ]]; then
  echo "No JPG frames found in $IMAGES_DIR" >&2
  exit 1
fi

echo "Found ${#video_ids[@]} videos."

# ---------- per-video processing ----------
for vid in "${video_ids[@]}"; do
  echo
  echo "=== Video: $vid ==="

  # Escape special regex characters in video_id for safe pattern matching
  vid_escaped=$(printf '%s\n' "$vid" | sed 's/[.[\*^$()+?{|]/\\&/g')

  # Frames for this video, sorted by the final numeric suffix
  # Use grep to ensure exact video_id match (vid_DIGITS.jpg only)
  mapfile -t frames < <(
    find "$IMAGES_DIR" -maxdepth 1 -type f -name "${vid}_*.jpg" -printf '%f\n' \
    | grep -E "^${vid_escaped}_[0-9]+\.jpg$" \
    | awk -F'[_.]' '{print $(NF-1), $0}' \
    | sort -n -k1,1 \
    | cut -d' ' -f2-
  )
  if [[ ${#frames[@]} -eq 0 ]]; then
    echo "No frames for video_id=$vid, skipping." >&2
    continue
  fi

  # Check if this video has already been fully processed
  # Count expected output masks (one per frame)
  existing_outputs=0
  all_exist=true
  for frame_file in "${frames[@]}"; do
    frame_stem="${frame_file%.jpg}"
    if [[ "$frame_stem" =~ ^(.*)_([0-9]+)$ ]]; then
      frame_num="${BASH_REMATCH[2]}"
      expected_output="$OUTPUT_DIR/${vid}_${frame_num}.png"
      if [[ -f "$expected_output" ]]; then
        ((existing_outputs++)) || true
      else
        all_exist=false
        break
      fi
    fi
  done
  
  if [[ "$all_exist" == true && ${#frames[@]} -gt 0 ]]; then
    echo "Video $vid already fully processed ($existing_outputs/${#frames[@]} outputs exist), skipping."
    continue
  elif [[ $existing_outputs -gt 0 ]]; then
    echo "Video $vid partially processed ($existing_outputs/${#frames[@]} outputs exist), re-processing..."
  fi

  # Masks for this video, sorted by the final numeric suffix
  # Use grep to ensure exact video_id match (vid_DIGITS.png only)
  mapfile -t vid_masks < <(
    find "$MASKS_DIR" -maxdepth 1 -type f -name "${vid}_*.png" -printf '%f\n' \
    | grep -E "^${vid_escaped}_[0-9]+\.png$" \
    | awk -F'[_.]' '{print $(NF-1), $0}' \
    | sort -n -k1,1 \
    | cut -d' ' -f2-
  )
  if [[ ${#vid_masks[@]} -eq 0 ]]; then
    echo "No masks for video_id=$vid in $MASKS_DIR, skipping." >&2
    continue
  fi
  seed_mask_base="${vid_masks[0]}"
  seed_mask="$MASKS_DIR/$seed_mask_base"

  # Make temp dir of symlinks 00000.jpg, 00001.jpg, ...
  tmp_dir="$TEMP_DIR/${vid}_temp"
  rm -rf "$tmp_dir"
  mkdir -p "$tmp_dir"

  mapfile_path="$tmp_dir/index_map.txt"
  : > "$mapfile_path"

  # Extract numeric tail from seed mask name (before .png)
  mask_stem="${seed_mask_base%.png}"
  seed_frame=""
  if [[ "$mask_stem" =~ ^(.*)_([0-9]+)$ ]]; then
    seed_frame="${BASH_REMATCH[2]}"
  fi

  frame_idx_for_mask=""

  for i in "${!frames[@]}"; do
    base="${frames[$i]}"           # e.g., apple_pie_00023.jpg
    stem="${base%.jpg}"
    if [[ "$stem" =~ ^(.*)_([0-9]+)$ ]]; then
      frame_num="${BASH_REMATCH[2]}"
    else
      echo "Skipping malformed frame name: $base" >&2
      continue
    fi

    link_name=$(printf "%05d.jpg" "$i")
    # Absolute target to avoid broken links
    ln -s -- "$IMAGES_DIR/$base" "$tmp_dir/$link_name"
    printf "%05d %s\n" "$i" "$frame_num" >> "$mapfile_path"

    if [[ -n "$seed_frame" && "$frame_num" == "$seed_frame" ]]; then
      frame_idx_for_mask="$i"
    fi
  done

  if [[ -z "$frame_idx_for_mask" ]]; then
    echo "Seed mask '$seed_mask_base' doesn't match any frame for $vid, skipping." >&2
    rm -rf "$tmp_dir"
    continue
  fi

  # Clean up any partial outputs from previous incomplete run
  if [[ $existing_outputs -gt 0 && "$all_exist" == false ]]; then
    echo "Removing $existing_outputs partial output(s) for $vid..."
    for frame_file in "${frames[@]}"; do
      frame_stem="${frame_file%.jpg}"
      if [[ "$frame_stem" =~ ^(.*)_([0-9]+)$ ]]; then
        frame_num="${BASH_REMATCH[2]}"
        partial_output="$OUTPUT_DIR/${vid}_${frame_num}.png"
        [[ -f "$partial_output" ]] && rm -f "$partial_output"
      fi
    done
  fi

  # Per-video SAM2 out dir
  out_tmp="$OUTPUT_DIR/.sam2_tmp/$vid"
  rm -rf "$out_tmp"
  mkdir -p "$out_tmp"

  echo "Running SAM2 on $vid (frames=${#frames[@]}, seed=${seed_mask_base}, frame_idx=$frame_idx_for_mask)"
  PY="/workspace/docker/sam2/track_from_mask.py"

  python "$PY" \
    --video_path "$tmp_dir" \
    --mask_path "$seed_mask" \
    --frame_idx "$frame_idx_for_mask" \
    --checkpoint "$CHECKPOINT" \
    --config "$CONFIG" \
    --out_dir "$out_tmp" \
    --device "$DEVICE" \
    ${OBJ_ID:+--obj_id "$OBJ_ID"} \
    $( (( VOS_OPTIMIZED == 1 )) && printf -- "--vos_optimized" )

  # Collect & rename: 00017_obj1.png -> <vid>_<frame>.png
  mkdir -p "$OUTPUT_DIR/$vid"
  shopt -s nullglob
  for m in "$out_tmp"/*_obj${OBJ_ID}.png; do
    base_out="$(basename "$m")"   # e.g., 00017_obj1.png
    idx5="${base_out%%_*}"        # 00017
    orig_frame="$(awk -v i="$idx5" '$1==i {print $2}' "$mapfile_path")"
    [[ -n "$orig_frame" ]] || continue
    mv "$m" "$OUTPUT_DIR/${vid}_${orig_frame}.png"
  done
  shopt -u nullglob

  # cleanup
  rm -rf "$tmp_dir" "$out_tmp"
done

echo "Done. Outputs in: $OUTPUT_DIR"
