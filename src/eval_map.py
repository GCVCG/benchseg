import argparse
import os
import numpy as np
from PIL import Image
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
from collections import defaultdict

def get_base_filename(filename):
    """Retur        for base_filename in tqdm(all_gt_files):
            gt_path = os.path.join(truth_dir, truth_files[base_filename])
            gt = np.array(Image.open(gt_path).convert('L'))
            
            # Handle missing submission files
            submit_file = submit_files.get(base_filename, None)
            if submit_file is None:
                # Create background-only prediction
                pred = np.zeros_like(gt)
            else:
                pred_path = os.path.join(submit_dir, submit_file)
                pred = np.array(Image.open(pred_path).convert('L')) filename without extension"""
    return os.path.splitext(filename)[0]

def get_mask_filenames(directory):
    """Returns a list of mask filenames from the directory"""
    all_files = os.listdir(directory)
    image_files = [f for f in all_files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    return {get_base_filename(f): f for f in sorted(image_files)}


import os
import numpy as np
from PIL import Image
import torch

# TorchMetrics (v0.11+ task-specific classes)
from torchmetrics.classification import (
    BinaryAveragePrecision,
    BinaryRecall,
    MulticlassJaccardIndex,
    MulticlassAccuracy,
)

def process_single_image(args, num_classes):
    """
    Compute metrics for one prediction/ground-truth pair using TorchMetrics.

    Binary (num_classes=2):
      returns: {
        'map': float,     # Average Precision (AP) over thresholds
        'recall': float,  # Recall
        'counts_per_class': {c: {'tp','fp','fn','tn'}}
      }

    Multiclass (num_classes>2):
      returns: {
        'miou': float,    # mean IoU (macro Jaccard)
        'macc': float,    # mean Accuracy (macro)
        'counts_per_class': {c: {'tp','fp','fn','tn'}}
      }

    Assumes label ids are integers in [0, num_classes-1] and images are single-channel.
    """
    base_filename, submit_file, truth_file, submit_dir, truth_dir = args

    # Load ground truth
    gt_np = np.array(Image.open(os.path.join(truth_dir, truth_file)).convert('L'), dtype=np.int64)
    
    # Load prediction or create background-only prediction if file doesn't exist
    if submit_file is None:
        # Create fully background prediction (all zeros) with same shape as ground truth
        pred_np = np.zeros_like(gt_np, dtype=np.int64)
    else:
        pred_np = np.array(Image.open(os.path.join(submit_dir, submit_file)).convert('L'), dtype=np.int64)

    if num_classes == 2:
        # Binarize to {0,1} for binary metrics
        pred_np = (pred_np > 0).astype(np.int64)
        gt_np   = (gt_np   > 0).astype(np.int64)

    if pred_np.shape != gt_np.shape:
        raise ValueError(f"Shape mismatch: pred {pred_np.shape} vs gt {gt_np.shape}")
    if pred_np.min() < 0 or gt_np.min() < 0:
        raise ValueError("Negative label id found.")
    if pred_np.max() >= num_classes or gt_np.max() >= num_classes:
        raise ValueError(f"Found label id >= num_classes, pred:{pred_np.max()} gt:{gt_np.max()} — check inputs.")

    # To tensors
    pred = torch.from_numpy(pred_np).long()
    gt   = torch.from_numpy(gt_np).long()

    # Per-class counts (useful for any later aggregation)
    counts_per_class = {}
    for c in range(num_classes):
        pred_c = (pred == c)
        gt_c   = (gt   == c)
        tp = (pred_c & gt_c).sum().item()
        fp = (pred_c & (~gt_c)).sum().item()
        fn = ((~pred_c) & gt_c).sum().item()
        tn = ((~pred_c) & (~gt_c)).sum().item()
        counts_per_class[c] = {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}

    # ---- Metrics by setting ----
    if num_classes == 2:
        # mAP (AP) & Recall for binary classification
        # If you have probabilities/logits, pass them to BinaryAveragePrecision instead of hard 0/1.
        ap_metric = BinaryAveragePrecision()
        rec_metric = BinaryRecall()

        # TorchMetrics flattens extra dims; cast preds to float for AP
        map_val = float(ap_metric(pred.float(), gt))
        recall_val = float(rec_metric(pred, gt))

        return base_filename, {
            'map': map_val,
            'recall': recall_val,
            'counts_per_class': counts_per_class
        }

    else:
        # mIoU (macro Jaccard) & mAcc (macro) for multiclass
        # If class 0 is background and should be ignored, set ignore_index=0.
        miou_metric = MulticlassJaccardIndex(num_classes=num_classes, average='macro', ignore_index=None)
        macc_metric = MulticlassAccuracy(num_classes=num_classes, average='macro', ignore_index=None)

        miou = float(miou_metric(pred, gt))
        macc = float(macc_metric(pred, gt))

        return base_filename, {
            'miou': miou,
            'macc': macc,
            'counts_per_class': counts_per_class
        }



def generate_error_image(submit_mask, truth_mask):
    """Generate visualization of errors"""
    error_image = np.zeros((*submit_mask.shape, 3), dtype=np.uint8)
    
    # False negatives in red
    error_image[~submit_mask & truth_mask] = [255, 0, 0]
    # False positives in blue
    error_image[submit_mask & ~truth_mask] = [0, 0, 255]
    # True positives in green
    error_image[submit_mask & truth_mask] = [0, 255, 0]
    
    return error_image

# assumes process_single_image(args, num_classes) is available
# and generate_error_image(pred_bool, gt_bool) is available for binary

def evaluate_masks(submit_dir, truth_dir, output_dir, num_classes, show_error=False):
    """Compute per-image metrics and aggregate dataset metrics."""
    # Get file lists
    submit_files = get_mask_filenames(submit_dir)
    truth_files  = get_mask_filenames(truth_dir)
    print(f"Found {len(submit_files)} submission masks and {len(truth_files)} ground truth masks.")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    if show_error:
        error_masks_dir = os.path.join(output_dir, "error_masks")
        os.makedirs(error_masks_dir, exist_ok=True)

    # Process all ground truth files - use None for missing submission files
    all_gt_files = sorted(truth_files.keys())
    missing_submission_count = 0
    
    process_args = []
    for base_filename in all_gt_files:
        truth_file = truth_files[base_filename]
        submit_file = submit_files.get(base_filename, None)  # None if missing
        if submit_file is None:
            missing_submission_count += 1
        process_args.append((base_filename, submit_file, truth_file, submit_dir, truth_dir))
    
    print(f"Processing {len(all_gt_files)} ground truth files.")
    if missing_submission_count > 0:
        print(f"Warning: {missing_submission_count} submission files are missing and will be treated as background-only predictions.")

    num_processes = min(cpu_count(), 8)
    print(f"Processing images using {num_processes} processes...")

    with Pool(processes=num_processes) as pool:
        worker = partial(process_single_image, num_classes=num_classes)
        results = list(tqdm(
            pool.imap(worker, process_args),
            total=len(process_args),
            desc="Processing images"
        ))

    # results: list of (base_filename, metrics_dict)
    # metrics_dict includes:
    #   if num_classes == 2: {'map': float, 'recall': float, 'counts_per_class': {...}}
    #   else:                {'miou': float, 'macc': float, 'counts_per_class': {...}}

    # -------- Aggregate (sum counts per class across images) --------
    sum_tp = defaultdict(int)
    sum_fp = defaultdict(int)
    sum_fn = defaultdict(int)
    sum_gt = defaultdict(int)  # |G_c| per class

    # Keep per-image metrics for the report
    per_image_metrics = {fname: m for fname, m in results}

    for _, m in results:
        for c in range(num_classes):
            cnts = m['counts_per_class'][c]
            sum_tp[c] += cnts['tp']
            sum_fp[c] += cnts['fp']
            sum_fn[c] += cnts['fn']
            sum_gt[c] += cnts['tp'] + cnts['fn']  # == |G_c|

    # Compute dataset-level summary values we actually need to print
    # From counts we can get macro IoU/Acc (multiclass) and binary recall.
    iou_per_class_ds    = {}
    acc_per_class_ds    = {}
    recall_per_class_ds = {}

    for c in range(num_classes):
        tp = sum_tp[c]; fp = sum_fp[c]; fn = sum_fn[c]; gt = sum_gt[c]
        denom_iou = tp + fp + fn
        iou_per_class_ds[c]    = (tp / denom_iou) if denom_iou > 0 else 0.0
        acc_per_class_ds[c]    = (tp / gt)        if gt > 0         else 0.0
        recall_per_class_ds[c] = (tp / (tp + fn)) if (tp + fn) > 0  else 0.0

    # Overall (macro) means for multiclass case
    mIoU         = float(np.mean([iou_per_class_ds[c] for c in range(num_classes)]))
    mAcc         = float(np.mean([acc_per_class_ds[c] for c in range(num_classes)]))
    mean_recallC = float(np.mean([recall_per_class_ds[c] for c in range(num_classes)]))  # kept for return compatibility

    # Binary-only summaries
    mean_map_images = None
    dataset_recall_binary = None
    if num_classes == 2:
        mean_map_images = float(np.mean([m['map'] for _, m in results])) if results else 0.0
        # treat class 1 as the positive (foreground) class
        dataset_recall_binary = recall_per_class_ds.get(1, 0.0)

    # -------- Save results (ONLY the requested metrics) --------
    report_path = os.path.join(output_dir, "metrics.txt")
    with open(report_path, "w") as f:
        f.write("Per-image results:\n")
        for filename in all_gt_files:
            m = per_image_metrics[filename]
            if num_classes == 2:
                # Only AP and Recall
                f.write(f"{filename}: AP {m['map']:.4f} | Recall {m['recall']:.4f}\n")
            else:
                # Only mIoU and mAcc
                f.write(f"{filename}: mIoU {m['miou']:.4f} | mAcc {m['macc']:.4f}\n")

        f.write("\nOverall metrics:\n")
        if num_classes == 2:
            # Only mAP (mean across images) and Recall (dataset, positive class)
            f.write(f"Mean AP (image-wise): {mean_map_images:.4f}\n")
            f.write(f"Recall (dataset, positive class): {dataset_recall_binary:.4f}\n")
        else:
            # Only mIoU and mAcc (macro over classes)
            f.write(f"mIoU: {mIoU:.4f}\n")
            f.write(f"mAcc: {mAcc:.4f}\n")

    # -------- Error visualization (optional) --------
    if show_error:
        print("\nGenerating error visualization images...")
        for base_filename in tqdm(all_gt_files):
            submit_file = submit_files.get(base_filename, None)
            gt_path = os.path.join(truth_dir, truth_files[base_filename])

            if submit_file is None:
                # Create background-only prediction for missing submission
                gt = np.array(Image.open(gt_path).convert('L'))
                pred = np.zeros_like(gt)
            else:
                pred_path = os.path.join(submit_dir, submit_file)
                pred = np.array(Image.open(pred_path).convert('L'))
                gt = np.array(Image.open(gt_path).convert('L'))

            if num_classes == 2:
                # Expecting labels {0,>0}; turn into booleans for the helper
                submit_mask = (pred > 0)
                truth_mask  = (gt > 0)
                error_image = generate_error_image(submit_mask, truth_mask)
                # Use the ground truth filename for output if submission is missing
                output_filename = submit_file if submit_file else truth_files[base_filename]
                Image.fromarray(error_image).save(os.path.join(error_masks_dir, output_filename))
            else:
                # Simple mismatch map: 0 where correct, 255 where labels differ
                mismatch = (pred != gt).astype(np.uint8) * 255
                output_filename = submit_file if submit_file else truth_files[base_filename]
                Image.fromarray(mismatch).save(os.path.join(error_masks_dir, output_filename))

    # Return unchanged tuple for compatibility
    return mIoU, mAcc, mean_recallC, iou_per_class_ds, acc_per_class_ds, recall_per_class_ds



def main():
    parser = argparse.ArgumentParser(description='Binary Segmentation Evaluation')
    parser.add_argument('--submit_dir', '-i', type=str, required=True,
                      help='Directory containing prediction masks')
    parser.add_argument('--truth_dir', type=str, required=True,
                      help='Directory containing ground truth masks')
    parser.add_argument('--output_dir', type=str, default='../output',
                      help='Output directory for metrics and visualizations')
    parser.add_argument('--num_classes', type=int, required=True,
                      help='number of classes in the masks')
    parser.add_argument('--show_error', action="store_true",
                      help='generate error visualization images')
    
    args = parser.parse_args()
    
    start_time = time.time()
    _, _, _, _, _, _= evaluate_masks(
        args.submit_dir,
        args.truth_dir,
        args.output_dir,
        args.num_classes,
        args.show_error
    )
    end_time = time.time()
    
    print(f"\nExecution time: {end_time - start_time:.2f} seconds")
    # print(f"\nResults:")
    # print(f"Mean Precision: {mean_precision:.4f}")
    # print(f"Mean Recall: {mean_recall:.4f}")
    # print(f"F1 Score: {f1_score:.4f}")

if __name__ == "__main__":
    main()
