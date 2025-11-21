import argparse
import os
import numpy as np
from PIL import Image
import torch
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
from collections import defaultdict

from torchmetrics.classification import (
    BinaryRecall,
    MulticlassJaccardIndex,
    MulticlassAccuracy,
)


def get_base_filename(filename):
    """Strip file extension from filename."""
    return os.path.splitext(filename)[0]


def get_mask_filenames(directory):
    """Get all image files and map base filenames to full filenames."""
    all_files = os.listdir(directory)
    image_files = [f for f in all_files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    return {get_base_filename(f): f for f in sorted(image_files)}


def process_single_image(args, num_classes):
    """
    Process a single image pair and compute metrics.
    
    Returns dict with 'map', 'recall', 'counts_per_class' for binary (num_classes=2)
    or 'miou', 'macc', 'counts_per_class' for multiclass.
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

    if num_classes == 2:
        pred_np = (pred_np > 0).astype(np.int64)
        gt_np = (gt_np > 0).astype(np.int64)

    if pred_np.shape != gt_np.shape:
        raise ValueError(f"Shape mismatch: pred {pred_np.shape} vs gt {gt_np.shape}")
    if pred_np.min() < 0 or gt_np.min() < 0:
        raise ValueError("Negative label found")
    if pred_np.max() >= num_classes or gt_np.max() >= num_classes:
        raise ValueError(f"Label >= num_classes found: pred max={pred_np.max()}, gt max={gt_np.max()}")

    pred = torch.from_numpy(pred_np).long()
    gt = torch.from_numpy(gt_np).long()

    counts_per_class = {}
    for c in range(num_classes):
        pred_c = (pred == c)
        gt_c = (gt == c)
        tp = (pred_c & gt_c).sum().item()
        fp = (pred_c & (~gt_c)).sum().item()
        fn = ((~pred_c) & gt_c).sum().item()
        tn = ((~pred_c) & (~gt_c)).sum().item()
        counts_per_class[c] = {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}

    if num_classes == 2:
        rec_metric = BinaryRecall()
        recall_val = float(rec_metric(pred, gt))
        
        tp = counts_per_class[1]['tp']
        fp = counts_per_class[1]['fp']
        precision_val = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        
        return base_filename, {
            'map': precision_val,
            'recall': recall_val,
            'counts_per_class': counts_per_class
        }
    else:
        miou_metric = MulticlassJaccardIndex(num_classes=num_classes, average='macro')
        macc_metric = MulticlassAccuracy(num_classes=num_classes, average='macro')
        
        miou = float(miou_metric(pred, gt))
        macc = float(macc_metric(pred, gt))
        
        return base_filename, {
            'miou': miou,
            'macc': macc,
            'counts_per_class': counts_per_class
        }


def generate_error_image(submit_mask, truth_mask):
    """Create RGB visualization: green=TP, red=FN, blue=FP."""
    error_image = np.zeros((*submit_mask.shape, 3), dtype=np.uint8)
    error_image[~submit_mask & truth_mask] = [255, 0, 0]  # FN: red
    error_image[submit_mask & ~truth_mask] = [0, 0, 255]  # FP: blue
    error_image[submit_mask & truth_mask] = [0, 255, 0]   # TP: green
    return error_image


def evaluate_masks(submit_dir, truth_dir, output_dir, num_classes, show_error=False):
    """Main evaluation function."""
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

    num_processes = min(cpu_count(), 8)
    print(f"Using {num_processes} processes...")

    with Pool(processes=num_processes) as pool:
        worker = partial(process_single_image, num_classes=num_classes)
        results = list(tqdm(
            pool.imap(worker, process_args),
            total=len(process_args),
            desc="Processing images"
        ))

    sum_tp = defaultdict(int)
    sum_fp = defaultdict(int)
    sum_fn = defaultdict(int)
    sum_gt = defaultdict(int)

    per_image_metrics = {fname: m for fname, m in results}

    for _, m in results:
        for c in range(num_classes):
            cnts = m['counts_per_class'][c]
            sum_tp[c] += cnts['tp']
            sum_fp[c] += cnts['fp']
            sum_fn[c] += cnts['fn']
            sum_gt[c] += cnts['tp'] + cnts['fn']

    iou_per_class_ds = {}
    acc_per_class_ds = {}
    recall_per_class_ds = {}

    for c in range(num_classes):
        tp = sum_tp[c]
        fp = sum_fp[c]
        fn = sum_fn[c]
        gt = sum_gt[c]
        denom_iou = tp + fp + fn
        iou_per_class_ds[c] = (tp / denom_iou) if denom_iou > 0 else 0.0
        acc_per_class_ds[c] = (tp / gt) if gt > 0 else 0.0
        recall_per_class_ds[c] = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    mIoU = float(np.mean([iou_per_class_ds[c] for c in range(num_classes)]))
    mAcc = float(np.mean([acc_per_class_ds[c] for c in range(num_classes)]))
    mean_recallC = float(np.mean([recall_per_class_ds[c] for c in range(num_classes)]))

    mean_map_images = None
    dataset_recall_binary = None
    if num_classes == 2:
        mean_map_images = float(np.mean([m['map'] for _, m in results])) if results else 0.0
        dataset_recall_binary = recall_per_class_ds.get(1, 0.0)

    report_path = os.path.join(output_dir, "metrics.txt")
    with open(report_path, "w") as f:
        f.write("Per-image results:\n")
        for filename in all_gt_files:
            m = per_image_metrics[filename]
            if num_classes == 2:
                f.write(f"{filename}: AP {m['map']:.4f} | Recall {m['recall']:.4f}\n")
            else:
                f.write(f"{filename}: mIoU {m['miou']:.4f} | mAcc {m['macc']:.4f}\n")

        f.write("\nOverall metrics:\n")
        if num_classes == 2:
            f.write(f"Mean AP (image-wise): {mean_map_images:.4f}\n")
            f.write(f"Recall (dataset, positive class): {dataset_recall_binary:.4f}\n")
        else:
            f.write(f"mIoU: {mIoU:.4f}\n")
            f.write(f"mAcc: {mAcc:.4f}\n")

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

            if num_classes == 2:
                submit_mask = (pred > 0)
                truth_mask = (gt > 0)
                error_image = generate_error_image(submit_mask, truth_mask)
                output_filename = submit_file if submit_file else truth_files[base_filename]
                Image.fromarray(error_image).save(os.path.join(error_masks_dir, output_filename))
            else:
                mismatch = (pred != gt).astype(np.uint8) * 255
                output_filename = submit_file if submit_file else truth_files[base_filename]
                Image.fromarray(mismatch).save(os.path.join(error_masks_dir, output_filename))

    return mIoU, mAcc, mean_recallC, iou_per_class_ds, acc_per_class_ds, recall_per_class_ds


def main():
    parser = argparse.ArgumentParser(description='Segmentation Evaluation')
    parser.add_argument('--submit_dir', '-i', type=str, required=True,
                        help='Directory with prediction masks')
    parser.add_argument('--truth_dir', type=str, required=True,
                        help='Directory with ground truth masks')
    parser.add_argument('--output_dir', type=str, default='../output',
                        help='Output directory for results')
    parser.add_argument('--num_classes', type=int, required=True,
                        help='Number of classes (2 for binary)')
    parser.add_argument('--show_error', action="store_true",
                        help='Generate error visualization images')
    
    args = parser.parse_args()
    
    start_time = time.time()
    evaluate_masks(
        args.submit_dir,
        args.truth_dir,
        args.output_dir,
        args.num_classes,
        args.show_error
    )
    end_time = time.time()
    
    print(f"\nExecution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
