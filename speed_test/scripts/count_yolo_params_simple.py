#!/usr/bin/env python3
"""
Count parameters for YOLO model - simple approach
"""

import torch
import os
import pickle

def format_number(num):
    """Format number with thousands separator"""
    return f"{num:,}"

def format_size(size_bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def count_tensors_in_obj(obj, prefix=""):
    """Recursively count tensors in any object"""
    total = 0
    tensor_count = 0
    
    if isinstance(obj, torch.Tensor):
        return obj.numel(), 1
    elif isinstance(obj, dict):
        for key, value in obj.items():
            params, count = count_tensors_in_obj(value, f"{prefix}.{key}" if prefix else key)
            total += params
            tensor_count += count
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            params, count = count_tensors_in_obj(item, f"{prefix}[{i}]")
            total += params
            tensor_count += count
    elif hasattr(obj, '__dict__'):
        for key, value in obj.__dict__.items():
            params, count = count_tensors_in_obj(value, f"{prefix}.{key}" if prefix else key)
            total += params
            tensor_count += count
    
    return total, tensor_count

def analyze_yolo_model(model_path):
    """Analyze YOLO model checkpoint"""
    print("="*70)
    print("YOLO MODEL ANALYSIS")
    print("="*70)
    print(f"\nModel Path: {model_path}")
    
    # File size
    file_size = os.path.getsize(model_path)
    print(f"File Size:  {format_size(file_size)}")
    
    # Try to load with weights_only first
    print("\nAttempting to load checkpoint...")
    
    try:
        # Try safe loading first
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=True)
        print("✓ Loaded with weights_only=True (safe mode)")
    except Exception as e:
        print(f"⚠ weights_only=True failed: {e}")
        print("Trying alternative approach...")
        
        # Read raw pickle to inspect structure
        with open(model_path, 'rb') as f:
            # Just count tensors without fully loading the model class
            unpickler = pickle.Unpickler(f)
            try:
                checkpoint = unpickler.load()
            except Exception as e2:
                print(f"✗ Could not load: {e2}")
                print("\nFalling back to file inspection...")
                # At least we have the file size
                return {'file_size': file_size, 'total_params': None}
    
    # Count parameters
    print("\nCounting tensors...")
    total_params, tensor_count = count_tensors_in_obj(checkpoint)
    
    print(f"\nResults:")
    print(f"  Total Tensors Found: {tensor_count}")
    print(f"  Total Parameters:    {format_number(total_params)} ({total_params/1e6:.2f}M)")
    
    # Try to show checkpoint structure
    if isinstance(checkpoint, dict):
        print(f"\nCheckpoint Keys: {list(checkpoint.keys())}")
        
        # Show some layer info if we can find the model
        if 'model' in checkpoint:
            print("\nInspecting 'model' key...")
            model_params, model_tensors = count_tensors_in_obj(checkpoint['model'])
            print(f"  Model parameters: {format_number(model_params)} ({model_params/1e6:.2f}M)")
            print(f"  Model tensors: {model_tensors}")
    
    return {
        'file_size': file_size,
        'total_params': total_params,
        'tensor_count': tensor_count
    }

if __name__ == '__main__':
    model_path = '/workspace/assets/ckpts/YOLO/yolo11s-seg_foodseg1032.pt'
    result = analyze_yolo_model(model_path)
    
    if result and result['total_params']:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"File Size:  {format_size(result['file_size'])}")
        print(f"Parameters: {result['total_params']/1e6:.2f}M ({format_number(result['total_params'])})")
        print(f"Tensors:    {result['tensor_count']}")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠ Could not fully analyze model without ultralytics library")
        print("File size: " + format_size(result['file_size']))
        print("="*70)
