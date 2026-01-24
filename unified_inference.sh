#!/usr/bin/env bash
set -uo pipefail

# =============================================================================
# Unified Inference Script - Single entrypoint for all models
# =============================================================================

# Global GPU logging state
GPU_LOG_PID=""
LOG_GPU=0
GPU_LOG_PATH=""

# Main entry point - parses flags and delegates to appropriate function
inference() {
  local mixed=false
  local args=()
  
  # Parse flags
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mixed)
        mixed=true
        shift
        ;;
      --log_gpu)
        LOG_GPU=1
        shift
        ;;
      *)
        args+=("$1")
        shift
        ;;
    esac
  done
  
  # Set GPU log path at the start (before any functions modify OUTPUT_DIR)
  if [[ $LOG_GPU -eq 1 && -n "$OUTPUT_DIR" ]]; then
    GPU_LOG_PATH="$OUTPUT_DIR/gpu_log.csv"
  fi
  
  if [[ "$mixed" == true ]]; then
    process_multi_video_dir "${args[@]}"
  else
    local timer_start=$(start_timer)
    execute_spec "${args[@]}"
    end_timer "$timer_start"
  fi
}

# Execute a single function spec (e.g., "yolo", "sam2 3", etc.)
execute_spec() {
  local func_key="$1"
  shift
  local extra_params=("$@")
  
  case "$func_key" in
    yolo)
      run_yolo "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    sam2)
      local n_masks="${extra_params[0]:-3}"
      run_sam2 "$INPUT_DIR" "$OUTPUT_DIR" "$MASK_DIR" "$n_masks" 
      ;;
    xmem2)
      local n_masks="${extra_params[0]:-3}"
      run_xmem2 "$INPUT_DIR" "$OUTPUT_DIR" "$MASK_DIR" "$n_masks" 
      ;;
    foodseg_swin_small)
      run_foodseg_swin_small "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_swin_base)
      run_foodseg_swin_base "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_fpn_relem)
      run_foodseg_fpn_relem "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_ccnet)
      run_foodseg_ccnet "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_ccnet_relem)
      run_foodseg_ccnet_relem "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_setr_mla_l384)
      run_foodseg_setr_mla_l384 "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    foodseg_setr_naive)
      run_foodseg_setr_naive "$INPUT_DIR" "$OUTPUT_DIR"
      ;;
    *)
      echo "Unknown function spec: $func_key"
      return 1
      ;;
  esac
}

# Video orchestrator: processes multiple videos sequentially with mixed workflow
process_multi_video_dir() {
  local segmentor_spec="$1"
  local tracker_spec="$2"
  local n_seed_frames="$3"
  local temp_base="data/temp_video_processing"
  local temp_output_base="data/temp_video_output"
  
  rm -rf "$temp_base" 2>/dev/null || true
  rm -rf "$temp_output_base" 2>/dev/null || true
  mkdir -p "$temp_base" "$temp_output_base"
  
  # Discover unique video IDs from input directory
  declare -A videos
  while IFS= read -r img_path; do
    local filename=$(basename "$img_path")
    local filename_no_ext="${filename%.*}"
    local video_id="${filename_no_ext%_*}"  # Everything before last underscore
    videos["$video_id"]=1
  done < <(find "$INPUT_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \))
  
  # Process each video separately
  for video_id in "${!videos[@]}"; do
    echo "Processing video: $video_id"
    
    local video_temp_dir="$temp_base/${video_id}_temp"
    local video_output_dir="$temp_output_base/${video_id}_output"
    mkdir -p "$video_temp_dir" "$video_output_dir"
    
    # Copy all frames for this video to temp directory
    for img_path in "$INPUT_DIR"/${video_id}_*; do
      [[ -f "$img_path" && ("$img_path" == *.jpg || "$img_path" == *.jpeg || "$img_path" == *.png) ]] && cp -f "$img_path" "$video_temp_dir/" 2>/dev/null || true
    done
    
    # Run mixed workflow on this video with separate output directory
    local saved_input_dir="$INPUT_DIR"
    local saved_output_dir="$OUTPUT_DIR"
    
    # Convert absolute path to relative for docker mounting
    # temp_video_processing is in data/, so it will be under /workspace/data in docker
    INPUT_DIR="$video_temp_dir"
    OUTPUT_DIR="$video_output_dir"
    
    # Directly call mixed workflow for this video
    run_mixed_workflow "$segmentor_spec" "$tracker_spec" "$n_seed_frames"
    
    # Restore original dirs
    INPUT_DIR="$saved_input_dir"
    OUTPUT_DIR="$saved_output_dir"
    
    rm -rf "$video_temp_dir"
  done
  
  # Copy all video outputs to final OUTPUT_DIR
  mkdir -p "$OUTPUT_DIR"
  for video_output_dir in "$temp_output_base"/*_output; do
    if [[ -d "$video_output_dir" ]]; then
      cp -r "$video_output_dir"/* "$OUTPUT_DIR/"
    fi
  done
  
  # Clean up before returning
  rm -rf "$temp_base" "$temp_output_base" 2>/dev/null || true
}

# =============================================================================
# Unified Inference Script - Single entrypoint for all models
# =============================================================================

# Configuration
YOLO_MODEL="assets/ckpts/YOLO/yolo11s-seg_foodseg103_2.pt"
SAM2_CHECKPOINT="/workspace/tracking_models/sam2/sam2.1_hiera_large.pt"
GPU_LOG_INTERVAL_MS=100

# Start GPU memory logger
start_gpu_logger() {
  local tag="${1:-}"
  [[ -z "$GPU_LOG_PATH" ]] && return 0

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "GPU logging requested but nvidia-smi is not available; skipping." >&2
    return 0
  fi

  mkdir -p "$(dirname "$GPU_LOG_PATH")"

  # Write header only if file doesn't exist
  if [[ ! -f "$GPU_LOG_PATH" ]]; then
    local header="timestamp,index,name,memory.used [MiB],memory.total [MiB],utilization.gpu [%]"
    [[ -n "$tag" ]] && header+=",run_tag"
    echo "$header" > "$GPU_LOG_PATH"
  fi

  local tag_pipe=(cat)
  if [[ -n "$tag" ]]; then
    tag_pipe=(awk -v tag="$tag" 'BEGIN{FS=OFS=","} {print $0 "," tag}')
  fi

  nvidia-smi \
    --query-gpu="timestamp,index,name,memory.used,memory.total,utilization.gpu" \
    --format="csv,noheader" \
    -lms "$GPU_LOG_INTERVAL_MS" | "${tag_pipe[@]}" >> "$GPU_LOG_PATH" &
  GPU_LOG_PID=$!
}

# Stop GPU memory logger
stop_gpu_logger() {
  if [[ -n "${GPU_LOG_PID:-}" && $GPU_LOG_PID -gt 0 ]]; then
    # Try gentle kill first
    kill -TERM "$GPU_LOG_PID" 2>/dev/null || true
    sleep 0.2
    
    # Check if still alive, use SIGKILL if needed
    if kill -0 "$GPU_LOG_PID" 2>/dev/null; then
      kill -KILL "$GPU_LOG_PID" 2>/dev/null || true
    fi
    
    # Wait for it to finish
    wait "$GPU_LOG_PID" 2>/dev/null || true
    GPU_LOG_PID=""
  fi

  cleanup_gpu_log_tail
}

cleanup_all() {
  stop_gpu_logger
}
trap cleanup_all EXIT INT TERM

cleanup_gpu_log_tail() {
  [[ -n "$GPU_LOG_PATH" && -f "$GPU_LOG_PATH" ]] || return 0

  local header_fields
  header_fields=$(awk -F',' 'NR==1{print NF; exit}' "$GPU_LOG_PATH")
  [[ -n "$header_fields" ]] || return 0

  local last_line
  last_line=$(tail -n 1 "$GPU_LOG_PATH")
  if [[ -z "$last_line" ]]; then
    remove_last_log_line
    return 0
  fi

  local last_fields
  last_fields=$(awk -F',' '{print NF}' <<< "$last_line")
  if [[ "$last_fields" -ne "$header_fields" ]]; then
    remove_last_log_line
  fi
}

remove_last_log_line() {
  local tmp="${GPU_LOG_PATH}.tmp.$$"
  sed '$d' "$GPU_LOG_PATH" > "$tmp" && mv "$tmp" "$GPU_LOG_PATH"
}

# Timing helpers
start_timer() {
  date +%s%N
}

end_timer() {
  local start_time=$1
  local end_time=$(date +%s%N)
  local elapsed_ns=$((end_time - start_time))
  local elapsed=$(awk "BEGIN {printf \"%.3f\", $elapsed_ns / 1000000000}")
  
  # Count images in INPUT_DIR
  local num_images=0
  if [[ -d "$INPUT_DIR" ]]; then
    num_images=$(find "$INPUT_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | wc -l)
  fi
  
  # Calculate time per image
  local time_per_image=0
  if [[ $num_images -gt 0 ]]; then
    time_per_image=$(awk "BEGIN {printf \"%.3f\", $elapsed_ns / 1000000000 / $num_images}")
  fi
  
  # Write to CSV (overwrite existing)
  mkdir -p "$OUTPUT_DIR"
  local csv_file="$OUTPUT_DIR/raw_inference_script_runtime.csv"
  
  # Write header and data
  {
    echo "total_time_s,num_images,time_per_image_s"
    echo "$elapsed,$num_images,$time_per_image"
  } > "$csv_file"
}

# Helper: Run YOLO inference
run_yolo() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  mkdir -p "$output_dir"
  
  start_gpu_logger "yolo"
  docker run -it --gpus all --rm --ipc=host \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd)/assets:/workspace/assets" \
    -v "$(pwd)/data:/workspace/data" \
    -v "$(pwd)/src/yolo:/workspace/src" \
    --entrypoint "" \
    yolo \
    python /workspace/src/yolo_inference.py \
    "$YOLO_MODEL" \
    "$input_dir" \
    "$output_dir"
  stop_gpu_logger
}

# Helper: Merge multiple object masks into a single binary mask
merge_masks() {
  local output_dir="$1"
  
  python3 << PYTHON_EOF
import os
import glob
from PIL import Image
import numpy as np
from collections import defaultdict

output_dir = "$output_dir"

# Group masks by frame (everything before _obj)
frame_masks = defaultdict(list)
for mask_path in sorted(glob.glob(os.path.join(output_dir, '*.png'))):
    filename = os.path.basename(mask_path)
    if '_obj' in filename:
        frame_name = filename.rsplit('_obj', 1)[0]
        frame_masks[frame_name].append(mask_path)

# Merge each frame's masks into one binary mask
for frame_name, masks in sorted(frame_masks.items()):
    merged = None
    for mask_path in masks:
        img = np.array(Image.open(mask_path).convert('L')) > 0
        merged = img if merged is None else (merged | img)
    
    Image.fromarray((merged * 255).astype(np.uint8)).save(
        os.path.join(output_dir, f"{frame_name}.png")
    )
PYTHON_EOF
}

# Helper: Binarize masks (convert to pure black/white)
binarize_masks() {
  local mask_dir="$1"
  
  python3 << PYTHON_EOF
import os
import glob
from PIL import Image
import numpy as np

mask_dir = "$mask_dir"

for mask_path in glob.glob(os.path.join(mask_dir, '*.png')):
    img = np.array(Image.open(mask_path).convert('L'))
    binary = (img > 0).astype(np.uint8) * 255
    Image.fromarray(binary).save(mask_path)
PYTHON_EOF
}

# Helper: Run foodseg103 model (generic)
run_foodseg_model() {
  local config_path="$1"
  local checkpoint_path="$2"
  local model_tag="$3"
  local input_dir="${4:-$INPUT_DIR}"
  local output_dir="${5:-$OUTPUT_DIR}"
  
  mkdir -p "$output_dir"
  
  # Process each image individually
  mapfile -t image_list < <(find "$input_dir" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \))
  
  for img_path in "${image_list[@]}"; do
    local rel_path="${img_path#$input_dir/}"
    local out_subdir="$output_dir/$(dirname "$rel_path")"
    mkdir -p "$out_subdir"
    
    start_gpu_logger "$model_tag"
    docker run -i --gpus all --rm --ipc=host \
      --user "$(id -u):$(id -g)" \
      -v "$(pwd)/assets:/workspace/assets" \
      -v "$(pwd)/data:/workspace/data" \
      -v "$(pwd)/src:/workspace/src" \
      foodseg103 \
      python /workspace/src/semantic.py \
      --img_path "$img_path" \
      --out_path "$out_subdir" \
      --log_path "$out_subdir/runtime_log.csv" \
      --semantic_config "$config_path" \
      --semantic_checkpoint "$checkpoint_path"
    stop_gpu_logger
  done
}

# Specific foodseg103 models
run_foodseg_swin_small() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/swin_small/upernet_swin_small_patch4_window7_512x1024_80k.py" \
    "assets/ckpts/swin_small/iter_80000.pth" \
    "foodseg_swin_small" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_swin_base() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/swin_base/upernet_swin_base_patch4_window7_512x1024_80k.py" \
    "assets/ckpts/swin_base/iter_80000.pth" \
    "foodseg_swin_base" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_fpn_relem() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/FPN_ReLeM/fpn_r50_512x1024_80k.py" \
    "assets/ckpts/FPN_ReLeM/iter_80000.pth" \
    "foodseg_fpn_relem" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_ccnet() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/CCNet/ccnet_r101-d8_512x1024_80k.py" \
    "assets/ckpts/CCNet/iter_80000.pth" \
    "foodseg_ccnet" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_ccnet_relem() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/CCNet_ReLeM/ccnet_r50-d8_512x1024_80k.py" \
    "assets/ckpts/CCNet_ReLeM/iter_80000.pth" \
    "foodseg_ccnet_relem" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_setr_mla_l384() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/SETR_MLA_L384/SETR_MLA_768x768_80k.py" \
    "assets/ckpts/SETR_MLA_L384/iter_80000.pth" \
    "foodseg_setr_mla_l384" \
    "$input_dir" \
    "$output_dir"
}

run_foodseg_setr_naive() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  run_foodseg_model \
    "assets/ckpts/SETR_Naive/SETR_Naive_768x768_80k_base.py" \
    "assets/ckpts/SETR_Naive/iter_80000.pth" \
    "foodseg_setr_naive" \
    "$input_dir" \
    "$output_dir"
}

# Helper: Run mixed workflow (segmentation on first N frames, then tracking)
run_mixed_workflow() {
  local segmentor_spec="$1"
  local tracker_spec="$2"
  local n_seed_frames="$3"
  
  local temp_seg_input="data/temp_mixed/seg_input"
  local temp_seg_output="data/temp_mixed/seg_masks"
  rm -rf "$temp_seg_input" "$temp_seg_output" # Not really needed, but safe
  mkdir -p "$temp_seg_input" "$temp_seg_output"
  
  # Copy only first N frames to temp input directory
  mapfile -t image_list < <(find "$INPUT_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | sort)
  for ((i=0; i<n_seed_frames && i<${#image_list[@]}; i++)); do
    cp -f "${image_list[$i]}" "$temp_seg_input/"
  done
  
  # Run segmentation on first N frames
  local saved_input_dir="$INPUT_DIR"
  local saved_output_dir="$OUTPUT_DIR"
  INPUT_DIR="$temp_seg_input"
  OUTPUT_DIR="$temp_seg_output"
  
  execute_spec "$segmentor_spec"
  
  # Binarize the segmentation masks
  binarize_masks "$temp_seg_output"
  
  INPUT_DIR="$saved_input_dir"
  OUTPUT_DIR="$saved_output_dir"
  MASK_DIR="$temp_seg_output"
  
  # Run tracking with generated masks
  execute_spec "$tracker_spec" "$n_seed_frames"
  
  OUTPUT_DIR="$saved_output_dir"
  
  # Clean up entire temp_mixed folder (created by run_mixed_workflow)
  rm -rf "data/temp_mixed" 2>/dev/null || true
}

# Helper: Run SAM2 inference
run_sam2() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  local mask_dir="${3:-$MASK_DIR}"
  local n_masks="${4:-3}"
  
  mkdir -p "$output_dir"
  
  # SAM2's internal library only looks for .jpg files, so convert any .png files
  if compgen -G "$input_dir/*.png" > /dev/null 2>&1; then
    python3 -c "
import glob
from PIL import Image
for png_file in glob.glob('$input_dir/*.png'):
    jpg_file = png_file.rsplit('.', 1)[0] + '.jpg'
    Image.open(png_file).convert('RGB').save(jpg_file, 'JPEG')
" 2>/dev/null || true
  fi
  
  start_gpu_logger "sam2"
  docker run -it --gpus all --rm --ipc=host \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd)/assets:/workspace/assets" \
    -v "$(pwd)/data:/workspace/data" \
    -v "$(pwd)/test_runs:/workspace/test_runs" \
    -v "$(pwd)/src:/workspace/src" \
    -v "$(pwd)/tracking_models:/workspace/tracking_models" \
    sam2 \
    python /workspace/src/sam2_track_from_mask.py \
    --video_path "$input_dir" \
    --mask_dir "$mask_dir" \
    --n_masks "$n_masks" \
    --checkpoint "$SAM2_CHECKPOINT" \
    --out_dir "$output_dir" \
    --device cuda
  stop_gpu_logger
  
  # Merge multi-object masks into single binary mask
  merge_masks "$output_dir"
  
  # Delete unmerged per-object masks
  find "$output_dir" -name "*_obj*.png" -delete
}

# Helper: Run XMem2 inference
run_xmem2() {
  local input_dir="${1:-$INPUT_DIR}"
  local output_dir="${2:-$OUTPUT_DIR}"
  local mask_dir="${3:-$MASK_DIR}"
  local n_masks="${4:-3}"
  
  mkdir -p "$output_dir"
  
  # Paths need adjustment for Docker call, xmem2 needs absolute paths
  local workspace_root="$(pwd)"
  
  start_gpu_logger "xmem2"
  docker run --gpus all --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e TORCH_CUDA_ARCH_LIST="8.6" \
    -e CUDA_ARCH="860" \
    -e TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1 \
    -v "$(pwd)/assets:/workspace/assets" \
    -v "$(pwd)/data:/workspace/data" \
    -v "$(pwd)/test_runs:/workspace/test_runs" \
    -v "$(pwd)/src:/workspace/src" \
    -v "$(pwd)/tracking_models:/workspace/tracking_models" \
    xmem2 \
    python3 process_video.py \
    --video "/workspace$(cd "$input_dir" && pwd | sed "s|^$workspace_root||")" \
    --masks "/workspace$(cd "$mask_dir" && pwd | sed "s|^$workspace_root||")" \
    --output "/workspace$(cd "$(dirname "$output_dir")" && pwd | sed "s|^$workspace_root||")/$(basename "$output_dir")"
  stop_gpu_logger
  
  # Move masks from output/masks/ to output/ level
  mv "$output_dir/masks"/* "$output_dir/" 2>/dev/null || true
  rm -rf "$output_dir/masks"
}
