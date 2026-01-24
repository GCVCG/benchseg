#!/usr/bin/env python3
"""
Background removal for FoodKit dataset using k-means++ clustering.
Uses the k-mean-plusplus implementation from GCVCG.
"""

import argparse
import cv2
import numpy as np
from skimage.morphology import binary_erosion, binary_dilation, disk
import faiss
import os
from pathlib import Path
from tqdm import tqdm


def preprocess_image(img, threshold1=93, threshold2=110):
    """
    Preprocess image with Gaussian blur and HSV thresholding.
    
    Args:
        img: Input BGR image
        threshold1: First threshold value for Otsu's method
        threshold2: Second threshold value for Otsu's method
    
    Returns:
        Grayscale preprocessed image
    """
    # Apply Gaussian filter
    img_blur = cv2.GaussianBlur(img, (5, 5), 0)

    # Convert RGB to HSV
    hsv_img = cv2.cvtColor(img_blur, cv2.COLOR_BGR2HSV)

    # First thresholding using Otsu's method
    _, thresh1 = cv2.threshold(hsv_img[:, :, 1], threshold1, 255, cv2.THRESH_BINARY)

    # Second thresholding using Otsu's method
    _, thresh2 = cv2.threshold(thresh1, threshold2, 255, cv2.THRESH_BINARY)

    # Combine thresholds
    final_thresh = cv2.bitwise_and(img, img, mask=thresh2)

    return cv2.cvtColor(final_thresh, cv2.COLOR_BGR2GRAY)


def kmeans_clustering(preprocessed_img, k=2, niter=200, verbose=False):
    """
    Perform k-means++ clustering using FAISS.
    
    Args:
        preprocessed_img: Preprocessed grayscale image
        k: Number of clusters
        niter: Number of iterations for k-means
        verbose: Print clustering progress
    
    Returns:
        Binary mask of the smallest cluster and centroids
    """
    # Reshape image
    pixels = preprocessed_img.reshape(-1, 1).astype('float32')

    # Instantiate the index
    d = pixels.shape[1]  # Dimension of the data points
    index = faiss.IndexFlatL2(d)

    # Train the index with k-means++
    clus = faiss.Clustering(d, k)
    clus.verbose = verbose
    clus.niter = niter
    clus.train(pixels, index)

    # Get the centroids
    centroids = faiss.vector_float_to_array(clus.centroids).reshape(k, d)

    # Assign each pixel to the nearest centroid
    _, labels = index.search(pixels, 1)

    # Reshape labels to match original image shape
    clustered_img = labels.reshape(preprocessed_img.shape)

    # Count the number of pixels for each label
    unique_labels, label_counts = np.unique(clustered_img, return_counts=True)

    # Find the label with the minimum size (foreground object)
    min_size_label = unique_labels[np.argmin(label_counts)]

    # Create binary image with only the smallest label
    smallest_label_img = np.where(clustered_img == min_size_label, 255, 0).astype(np.uint8)

    return smallest_label_img, centroids


def morphology_operation(img, selem_radius=3):
    """
    Apply morphological operations (erosion + dilation).
    
    Args:
        img: Binary mask image
        selem_radius: Radius of disk structuring element
    
    Returns:
        Cleaned binary mask
    """
    # Define structuring element (disk with radius)
    selem = disk(selem_radius)

    # Erosion followed by dilation (morphological opening)
    eroded_img = binary_erosion(img, selem)
    morph_img = binary_dilation(eroded_img, selem)

    return morph_img.astype(np.uint8) * 255


def remove_background(original_img, binary_mask):
    """
    Remove background using binary mask.
    
    Args:
        original_img: Original BGR image
        binary_mask: Binary mask (255 = foreground, 0 = background)
    
    Returns:
        Image with background removed
    """
    # Ensure binary mask is uint8
    binary_mask = binary_mask.astype(np.uint8)

    # Apply mask to remove background
    segmented_img = cv2.bitwise_and(original_img, original_img, mask=binary_mask)
    
    return segmented_img


def process_single_image(image_path, output_dir, args):
    """
    Process a single image for background removal.
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save output
        args: Command line arguments
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read original image
        original_img = cv2.imread(str(image_path))
        if original_img is None:
            print(f"Error reading image: {image_path}")
            return False

        # Preprocess image
        preprocessed_img = preprocess_image(
            original_img, 
            threshold1=args.threshold1, 
            threshold2=args.threshold2
        )

        # K-means++ clustering
        kmeans_mask, _ = kmeans_clustering(
            preprocessed_img, 
            k=args.num_clusters,
            niter=args.niter,
            verbose=args.verbose
        )

        # Morphology operation for cleaner mask
        morph_mask = morphology_operation(kmeans_mask, selem_radius=args.morph_radius)

        # Remove background
        result_img = remove_background(original_img, morph_mask)

        # Save output
        output_path = Path(output_dir) / Path(image_path).name
        cv2.imwrite(str(output_path), result_img)

        # Optionally save mask
        if args.save_masks:
            mask_dir = Path(output_dir).parent / "masks"
            mask_dir.mkdir(exist_ok=True)
            mask_path = mask_dir / Path(image_path).name
            cv2.imwrite(str(mask_path), morph_mask)

        return True

    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return False


def process_dataset(input_dir, output_dir, args):
    """
    Process entire FoodKit dataset.
    
    Args:
        input_dir: Input directory containing images
        output_dir: Output directory for processed images
        args: Command line arguments
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(list(input_path.glob(f'*{ext}')))
        image_files.extend(list(input_path.glob(f'*{ext.upper()}')))

    if not image_files:
        print(f"No images found in {input_dir}")
        return

    print(f"Found {len(image_files)} images to process")

    # Process each image
    successful = 0
    for img_path in tqdm(image_files, desc="Processing images"):
        if process_single_image(img_path, output_path, args):
            successful += 1

    print(f"\nProcessed {successful}/{len(image_files)} images successfully")
    print(f"Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Background removal for FoodKit dataset using k-means++ clustering."
    )
    
    # Input/Output
    parser.add_argument(
        "input",
        help="Path to input image or directory"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="output/background_removed",
        help="Directory to save processed images"
    )
    
    # K-means parameters
    parser.add_argument(
        "--num_clusters",
        type=int,
        default=2,
        help="Number of clusters for k-means++ (default: 2 for background/foreground)"
    )
    parser.add_argument(
        "--niter",
        type=int,
        default=200,
        help="Number of iterations for k-means clustering"
    )
    
    # Preprocessing parameters
    parser.add_argument(
        "--threshold1",
        type=int,
        default=93,
        help="First threshold value for HSV preprocessing"
    )
    parser.add_argument(
        "--threshold2",
        type=int,
        default=110,
        help="Second threshold value for HSV preprocessing"
    )
    
    # Morphology parameters
    parser.add_argument(
        "--morph_radius",
        type=int,
        default=3,
        help="Radius of disk structuring element for morphological operations"
    )
    
    # Options
    parser.add_argument(
        "--save_masks",
        action="store_true",
        help="Save binary masks alongside output images"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed clustering information"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process entire directory instead of single image"
    )
    
    args = parser.parse_args()

    # Check if input is a file or directory
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: Input path '{args.input}' does not exist")
        return

    if args.batch or input_path.is_dir():
        # Process directory
        process_dataset(args.input, args.output_dir, args)
    else:
        # Process single image
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        success = process_single_image(input_path, output_path, args)
        if success:
            print(f"Successfully processed: {input_path}")
            print(f"Output saved to: {output_path / input_path.name}")


if __name__ == "__main__":
    main()
