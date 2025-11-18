cd /home/guill_unix/repos/SpiceSeg && for model in CCNET CCNET_RELEM FPN_RELEM SETR_MLA_L384 SETR_NAIVE SETR_MLA_L384_SMALLER SWIN_BASE SWIN_SMALL; do
    echo "Processing binary scores for $model..."
    
    SUBMIT_DIR="data/mtf_foodMem_reordered/results/${model}_binary"
    TRUTH_DIR="data/mtf_foodMem_reordered/masks"
    OUTPUT_DIR="data/mtf_foodMem_reordered/metrics/${model}"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Run the evaluation
    docker run -it --gpus all --rm --ipc=host \
      -v "$(pwd)/assets:/workspace/assets" \
      -v "$(pwd)/data:/workspace/data" \
      -v "$(pwd)/yolo/runs:/workspace/runs" \
      -v "$(pwd)/src/:/workspace/src" \
      -v "$(pwd)/automation_scripts:/workspace/automation_scripts" \
      --entrypoint "" \
      yolo \
      python /workspace/src/eval_map.py \
        --submit_dir "${SUBMIT_DIR}" \
        --truth_dir "${TRUTH_DIR}" \
        --output_dir "${OUTPUT_DIR}" \
        --num_classes 2
        
    echo "Completed evaluation for $model"
    echo "---"
done