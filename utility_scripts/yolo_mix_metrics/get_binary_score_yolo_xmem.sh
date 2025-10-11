docker run -it --gpus all --rm --ipc=host \
  -v "$(pwd)/assets:/workspace/assets" \
  -v "$(pwd)/data:/workspace/data" \
  -v "$(pwd)/yolo/runs:/workspace/runs" \
  -v "$(pwd)/src/:/workspace/src" \
  -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
  --entrypoint "" \
  yolo \
  python src/eval_map.py \
  --submit_dir data/mtf_foodMem_reordered/results/YOLO_XMEM2_binary \
  --truth_dir data/mtf_foodMem_reordered/masks \
  --output_dir data/mtf_foodMem_reordered/metrics \
  --num_classes 2 \
  --show_error
