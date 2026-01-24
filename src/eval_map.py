import argparse
import os
import numpy as np
from PIL import Image
import torch
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial

from torchmetrics.classification import BinaryRecall


def get_base_filename(filename):
    """Strip file extension from filename."""
    return os.path.splitext(filename)[0]


def get_mask_filenames(directory):
    """Get all image files and map base filenames to full filenames."""
    all_files = os.listdir(directory)
    image_files = [f for f in all_files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    return {get_base_filename(f): f for f in sorted(image_files)}


def process_single_image(args):
    """
    Process a single image pair and compute binary metrics.
    
    Returns dict with 'precision', 'recall', 'iou', and 'counts'.
    """
    base_filename, submit_file, truth_file, submit_dir, truth_dir = args

    gt_np = np.array(Image.open(os.path.join(truth_dir, truth_file)).convert('L'), dtype=np.int64)
    
    if submit_file is None:
        pred_np = np.zeros_like(gt_np, dtype=np.int64)
    else:
        try:
            pred_np = np.array(Image.open(os.path.join(submit_dir, submit_file)).convert('L'), dtype=np.int64)
        except (OSError, IOError, Image.UnidentifiedImageError) as e:
            print(f"Warning: Could not read {submit_file}: {e}. Treating as background-only prediction.")
            pred_np = np.zeros_like(gt_np, dtype=np.int64)

    # Convert to binary
    pred_np = (pred_np > 0).astype(np.int64)
    gt_np = (gt_np > 0).astype(np.int64)

    if pred_np.shape != gt_np.shape:
        raise ValueError(f"Shape mismatch: pred {pred_np.shape} vs gt {gt_np.shape}")

    pred = torch.from_numpy(pred_np).long()
    gt = torch.from_numpy(gt_np).long()

    # Compute TP, FP, FN, TN for positive class
    pred_pos = (pred == 1)
    gt_pos = (gt == 1)
    tp = (pred_pos & gt_pos).sum().item()
    fp = (pred_pos & ~gt_pos).sum().item()
    fn = (~pred_pos & gt_pos).sum().item()
    tn = ((~pred_pos) & (~gt_pos)).sum().item()

    # Compute metrics
    rec_metric = BinaryRecall()
    recall_val = float(rec_metric(pred, gt))
    
    precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    iou_val = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    f1_val = 2 * (precision_val * recall_val) / (precision_val + recall_val) if (precision_val + recall_val) > 0 else 0.0
    accuracy_val = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    
    return base_filename, {
        'precision': precision_val,
        'recall': recall_val,
        'iou': iou_val,
        'f1': f1_val,
        'accuracy': accuracy_val,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'tn': tn
    }


def generate_error_image(submit_mask, truth_mask):
    """Create RGB visualization: green=TP, red=FN, blue=FP."""
    error_image = np.zeros((*submit_mask.shape, 3), dtype=np.uint8)
    error_image[~submit_mask & truth_mask] = [255, 0, 0]  # FN: red
    error_image[submit_mask & ~truth_mask] = [0, 0, 255]  # FP: blue
    error_image[submit_mask & truth_mask] = [0, 255, 0]   # TP: green
    return error_image


def evaluate_masks(submit_dir, truth_dir, output_dir, show_error=False, num_workers=None):
    """Main evaluation function for binary segmentation."""
    submit_files = get_mask_filenames(submit_dir)
    truth_files = get_mask_filenames(truth_dir)
    print(f"Found {len(submit_files)} submission masks and {len(truth_files)} ground truth masks.")

    os.makedirs(output_dir, exist_ok=True)
    if show_error:
        error_masks_dir = os.path.join(output_dir, "error_masks")
        os.makedirs(error_masks_dir, exist_ok=True)

    all_gt_files = sorted(truth_files.keys())
    missing_submission_count = 0
    
    process_args = []
    for base_filename in all_gt_files:
        truth_file = truth_files[base_filename]
        submit_file = submit_files.get(base_filename, None)
        if submit_file is None:
            missing_submission_count += 1
        process_args.append((base_filename, submit_file, truth_file, submit_dir, truth_dir))
    
    print(f"Processing {len(all_gt_files)} ground truth files.")
    if missing_submission_count > 0:
        print(f"Warning: {missing_submission_count} files missing, treating as background predictions.")

    if num_workers is None:
        num_processes = min(cpu_count(), 8)
    else:
        num_processes = num_workers
    print(f"Using {num_processes} processes...")

    with Pool(processes=num_processes) as pool:
        results = list(tqdm(
            pool.imap(process_single_image, process_args),
            total=len(process_args),
            desc="Processing images"
        ))

    per_image_metrics = {fname: m for fname, m in results}

    # Aggregate dataset-level metrics
    sum_tp = 0
    sum_fp = 0
    sum_fn = 0
    sum_tn = 0

    for _, m in results:
        sum_tp += m['tp']
        sum_fp += m['fp']
        sum_fn += m['fn']
        sum_tn += m['tn']

    dataset_precision = sum_tp / (sum_tp + sum_fp) if (sum_tp + sum_fp) > 0 else 0.0
    dataset_recall = sum_tp / (sum_tp + sum_fn) if (sum_tp + sum_fn) > 0 else 0.0
    dataset_iou = sum_tp / (sum_tp + sum_fp + sum_fn) if (sum_tp + sum_fp + sum_fn) > 0 else 0.0
    dataset_f1 = 2 * (dataset_precision * dataset_recall) / (dataset_precision + dataset_recall) if (dataset_precision + dataset_recall) > 0 else 0.0
    dataset_accuracy = (sum_tp + sum_tn) / (sum_tp + sum_tn + sum_fp + sum_fn) if (sum_tp + sum_tn + sum_fp + sum_fn) > 0 else 0.0

    # Compute per-image averages
    mean_precision = float(np.mean([m['precision'] for _, m in results])) if results else 0.0
    mean_recall = float(np.mean([m['recall'] for _, m in results])) if results else 0.0
    mean_iou = float(np.mean([m['iou'] for _, m in results])) if results else 0.0
    mean_f1 = float(np.mean([m['f1'] for _, m in results])) if results else 0.0
    mean_accuracy = float(np.mean([m['accuracy'] for _, m in results])) if results else 0.0

    # Compute standard deviations
    precision_values = [m['precision'] for _, m in results]
    recall_values = [m['recall'] for _, m in results]
    iou_values = [m['iou'] for _, m in results]
    f1_values = [m['f1'] for _, m in results]
    accuracy_values = [m['accuracy'] for _, m in results]
    
    precision_std = float(np.std(precision_values))
    recall_std = float(np.std(recall_values))
    iou_std = float(np.std(iou_values))
    f1_std = float(np.std(f1_values))
    accuracy_std = float(np.std(accuracy_values))

    report_path = os.path.join(output_dir, "metrics.txt")
    with open(report_path, "w") as f:
        f.write("Per-image results:\n")
        for filename in all_gt_files:
            m = per_image_metrics[filename]
            f.write(f"{filename}: Precision {m['precision']:.4f} | Recall {m['recall']:.4f} | F1 {m['f1']:.4f} | IoU {m['iou']:.4f} | Accuracy {m['accuracy']:.4f}\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("Overall metrics (image-wise average):\n")
        f.write(f"Mean Precision: {mean_precision:.4f} (Std: {precision_std:.4f})\n")
        f.write(f"Mean Recall: {mean_recall:.4f} (Std: {recall_std:.4f})\n")
        f.write(f"Mean F1: {mean_f1:.4f} (Std: {f1_std:.4f})\n")
        f.write(f"Mean IoU: {mean_iou:.4f} (Std: {iou_std:.4f})\n")
        f.write(f"Mean Accuracy: {mean_accuracy:.4f} (Std: {accuracy_std:.4f})\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("Overall metrics (dataset-level, aggregated):\n")
        f.write(f"Dataset Precision: {dataset_precision:.4f}\n")
        f.write(f"Dataset Recall: {dataset_recall:.4f}\n")
        f.write(f"Dataset F1: {dataset_f1:.4f}\n")
        f.write(f"Dataset IoU: {dataset_iou:.4f}\n")
        f.write(f"Dataset Accuracy: {dataset_accuracy:.4f}\n")
        f.write(f"TP: {sum_tp}, TN: {sum_tn}, FP: {sum_fp}, FN: {sum_fn}\n")

    if show_error:
        print("\nGenerating error visualizations...")
        for base_filename in tqdm(all_gt_files):
            submit_file = submit_files.get(base_filename, None)
            gt_path = os.path.join(truth_dir, truth_files[base_filename])

            if submit_file is None:
                gt = np.array(Image.open(gt_path).convert('L'))
                pred = np.zeros_like(gt)
            else:
                pred_path = os.path.join(submit_dir, submit_file)
                pred = np.array(Image.open(pred_path).convert('L'))
                gt = np.array(Image.open(gt_path).convert('L'))

            submit_mask = (pred > 0)
            truth_mask = (gt > 0)
            error_image = generate_error_image(submit_mask, truth_mask)
            output_filename = submit_file if submit_file else truth_files[base_filename]
            Image.fromarray(error_image).save(os.path.join(error_masks_dir, output_filename))

    print("\nMetrics report saved to:", report_path)
    return dataset_precision, dataset_recall, dataset_iou


def main():
    parser = argparse.ArgumentParser(description='Binary Segmentation Evaluation')
    parser.add_argument('--submit_dir', '-i', type=str, required=True,
                        help='Directory with prediction masks')
    parser.add_argument('--truth_dir', type=str, required=True,
                        help='Directory with ground truth masks')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Output directory for results')
    parser.add_argument('--num_workers', type=int, default=None,
                        help='Number of parallel workers (default: min(cpu_count, 8))')
    parser.add_argument('--show_error', action="store_true",
                        help='Generate error visualization images')
    
    args = parser.parse_args()
    
    start_time = time.time()
    evaluate_masks(
        args.submit_dir,
        args.truth_dir,
        args.output_dir,
        args.show_error,
        args.num_workers
    )
    end_time = time.time()
    
    print(f"Execution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
