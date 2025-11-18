#!/bin/bash

# Script to run segMAN + SAM2 inference on all reordered datasets
# This script runs SAM2 in Docker for each dataset using segMAN results as input masks
# SAM2 requires JPG images, so PNG images are converted to JPG format

set -euo pipefail

echo "Running segMAN + SAM2 inference on all reordered datasets..."

# Function to convert PNG images to JPG
convert_png_to_jpg() {
  local input_dir="$1"
  local output_dir="$2"
  
  echo "Converting PNG images to JPG format..."
  echo "Input: $input_dir"
  echo "Output: $output_dir"
  
  mkdir -p "$output_dir"
  
  # Count total files for progress
  total_files=$(find "$input_dir" -name "*.png" | wc -l)
  echo "Converting $total_files PNG files to JPG..."
  
  # Convert PNG to JPG with parallel processing
  find "$input_dir" -name "*.png" -print0 | \
  xargs -0 -I {} -P 8 bash -c '
    input_file="$1"
    output_dir="$2"
    base=$(basename "$input_file" .png)
    output_file="$output_dir/${base}.jpg"
    if [[ ! -f "$output_file" ]]; then
      convert "$input_file" "$output_file"
    fi
  ' _ {} "$output_dir"
  
  echo "Conversion completed: $total_files files processed"
}

# Function to run SAM2 inference in Docker
run_sam2_docker() {
  local frames_dir="$1"
  local masks_dir="$2"
  local output_dir="$3"
  
  echo "Running SAM2 inference in Docker..."
  echo "Frames: $frames_dir"
  echo "Masks: $masks_dir"
  echo "Output: $output_dir"
  
  mkdir -p "$output_dir"
  
  # Get absolute paths
  FRAMES=$(readlink -f "$frames_dir")
  MASKS=$(readlink -f "$masks_dir")
  OUT=$(readlink -f "$output_dir")
  
  # Create temporary directory for processing
  TEMP_BASE="/tmp/sam2_processing_$$"
  mkdir -p "$TEMP_BASE"
  
  # Group frames by video ID and process each video separately
  declare -A video_frames
  
  # Collect all JPG files and group by video ID
  for frame_file in "$FRAMES"/*.jpg; do
    if [[ -f "$frame_file" ]]; then
      basename_frame=$(basename "$frame_file" .jpg)
      
      # Extract video ID using the fixed parsing logic
      filename_no_ext="$basename_frame"
      frame_digits="${filename_no_ext##*_}"
      if [[ "$frame_digits" =~ ^[0-9]+$ ]]; then
        video_id="${filename_no_ext%_${frame_digits}}"
      else
        video_id="${basename_frame%%_*}"
      fi
      
      if [[ -n "${video_frames[$video_id]:-}" ]]; then
        video_frames[$video_id]="${video_frames[$video_id]} $basename_frame"
      else
        video_frames[$video_id]="$basename_frame"
      fi
    fi
  done
  
  # Process each video separately
  for video_id in "${!video_frames[@]}"; do
    echo "Processing video: $video_id"
    
    # Create temporary directory for this video
    video_temp_dir="$TEMP_BASE/${video_id}_temp"
    mkdir -p "$video_temp_dir/frames"
    
    # Find the first available mask for this video (lowest frame number)
    first_mask=""
    init_frame_idx=0
    frame_idx=0
    
    # Sort frames for this video and create symlinks with sequential naming
    IFS=' ' read -ra frame_list <<< "${video_frames[$video_id]}"
    IFS=$'\n' sorted_frames=($(sort -t '_' -k 2,2n <<< "${frame_list[*]}"))
    
    for frame_base in "${sorted_frames[@]}"; do
      # Create symlink with sequential naming (00000.jpg, 00001.jpg, etc.)
      ln -sf "$FRAMES/${frame_base}.jpg" "$video_temp_dir/frames/$(printf "%05d.jpg" $frame_idx)"
      
      # Check if we have a mask for this frame
      mask_file="$MASKS/${frame_base}.png"
      if [[ -f "$mask_file" && -z "$first_mask" ]]; then
        first_mask="$mask_file"
        init_frame_idx=$frame_idx
        echo "  Using mask from frame $frame_idx: $mask_file"
      fi
      
      ((frame_idx++))
    done
    
    # Skip this video if no mask found
    if [[ -z "$first_mask" ]]; then
      echo "  Warning: No mask found for video $video_id, skipping"
      rm -rf "$video_temp_dir"
      continue
    fi
    
    # Run SAM2 on this video
    video_output_dir="$video_temp_dir/outputs"
    mkdir -p "$video_output_dir"
    
    echo "  Running SAM2 Docker for video $video_id (init_frame_idx=$init_frame_idx)"
    
    # Mount necessary directories so symlinks can be resolved
    if docker run --rm --gpus all \
      -v /home/guill_unix:/home/guill_unix:ro \
      -v "$TEMP_BASE":"$TEMP_BASE" \
      sam2 \
      --frames_dir "$video_temp_dir/frames" \
      --init_mask "$first_mask" \
      --init_frame_idx "$init_frame_idx" \
      --output_dir "$video_output_dir"; then
      
      echo "  SAM2 completed successfully for video $video_id"
      
      # Move results back to main output directory with proper naming
      for result_file in "$video_output_dir"/*.png; do
        if [[ -f "$result_file" ]]; then
          result_base=$(basename "$result_file" .png)
          # Convert back to original frame naming (000000.png -> frame_idx)
          if [[ "$result_base" =~ ^[0-9]+$ ]]; then
            frame_idx_num=$((10#$result_base))
            if [[ $frame_idx_num -lt ${#sorted_frames[@]} ]]; then
              original_frame="${sorted_frames[$frame_idx_num]}"
              mv "$result_file" "$OUT/${original_frame}.png"
            fi
          fi
        fi
      done
    else
      echo "  Error: SAM2 failed for video $video_id"
    fi
    
    # Clean up temporary directory for this video
    rm -rf "$video_temp_dir"
  done
  
  # Clean up main temporary directory
  rm -rf "$TEMP_BASE"
  
  echo "SAM2 processing completed for all videos"
}

# Dataset 1: mtf_foodMem_reordered
echo "Processing mtf_foodMem_reordered..."
convert_png_to_jpg "data/mtf_foodMem_reordered/images" "data/mtf_foodMem_reordered/images_jpg"
run_sam2_docker "data/mtf_foodMem_reordered/images_jpg" "data/mtf_foodMem_reordered/results/segMAN" "data/mtf_foodMem_reordered/results/segMAN_SAM2"

# Dataset 2: FoodKit_dataset_reordered
echo "Processing FoodKit_dataset_reordered..."
convert_png_to_jpg "data/FoodKit_dataset_reordered/images" "data/FoodKit_dataset_reordered/images_jpg"
run_sam2_docker "data/FoodKit_dataset_reordered/images_jpg" "data/FoodKit_dataset_reordered/results/segMAN" "data/FoodKit_dataset_reordered/results/segMAN_SAM2"

# Dataset 3: V&F_reordered
echo "Processing V&F_reordered..."
convert_png_to_jpg "data/V&F_reordered/images" "data/V&F_reordered/images_jpg"
run_sam2_docker "data/V&F_reordered/images_jpg" "data/V&F_reordered/results/segMAN" "data/V&F_reordered/results/segMAN_SAM2"

# Dataset 4: n5k_reordered (already has proper format, no conversion needed)
echo "Processing n5k_reordered..."
run_sam2_docker "data/n5k_reordered/images" "data/n5k_reordered/results/segMAN" "data/n5k_reordered/results/segMAN_SAM2"

echo "All segMAN + SAM2 inference tasks completed!"