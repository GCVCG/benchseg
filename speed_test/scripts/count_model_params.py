#!/usr/bin/env python3
"""
Count parameters and model sizes for tracking models
"""

import torch
import os
import sys

def count_parameters(state_dict):
    """Count total parameters in a state dict"""
    total_params = 0
    trainable_params = 0
    
    for key, tensor in state_dict.items():
        if isinstance(tensor, torch.Tensor):
            params = tensor.numel()
            total_params += params
            # Assume all params in checkpoint are trainable
            trainable_params += params
    
    return total_params, trainable_params

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

def analyze_model(model_path, model_name):
    """Analyze a model checkpoint"""
    print(f"\n{'='*70}")
    print(f"Model: {model_name}")
    print(f"{'='*70}")
    
    # File size
    file_size = os.path.getsize(model_path)
    print(f"File Size:        {format_size(file_size)}")
    
    # Load checkpoint
    try:
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # Handle different checkpoint formats
        if isinstance(checkpoint, dict):
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            elif 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model' in checkpoint:
                state_dict = checkpoint['model']
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint
        
        # Count parameters
        total_params, trainable_params = count_parameters(state_dict)
        
        print(f"Total Parameters: {format_number(total_params)} ({total_params/1e6:.2f}M)")
        print(f"Trainable Params: {format_number(trainable_params)} ({trainable_params/1e6:.2f}M)")
        
        # Show top-level keys
        if isinstance(state_dict, dict):
            print(f"\nCheckpoint Keys:")
            for i, key in enumerate(list(state_dict.keys())[:10]):
                print(f"  - {key}: {state_dict[key].shape if isinstance(state_dict[key], torch.Tensor) else type(state_dict[key])}")
            if len(state_dict.keys()) > 10:
                print(f"  ... and {len(state_dict.keys()) - 10} more keys")
        
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return None
    
    return {
        'name': model_name,
        'file_size': file_size,
        'total_params': total_params,
        'trainable_params': trainable_params
    }

def main():
    # Model paths
    models = [
        ('tracking_models/XMem2/saves/XMem.pth', 'XMem2'),
        ('tracking_models/sam2/sam2.1_hiera_large.pt', 'SAM2.1 (Hiera Large)'),
    ]
    
    # Also show other available SAM2 variants
    other_sam2 = [
        ('tracking_models/sam2/sam2.1_hiera_tiny.pt', 'SAM2.1 (Hiera Tiny)'),
        ('tracking_models/sam2/sam2.1_hiera_small.pt', 'SAM2.1 (Hiera Small)'),
        ('tracking_models/sam2/sam2.1_hiera_base_plus.pt', 'SAM2.1 (Hiera Base+)'),
    ]
    
    results = []
    
    print("="*70)
    print("MODEL ANALYSIS: Tracking Models Used in Speed Tests")
    print("="*70)
    
    for model_path, model_name in models:
        if os.path.exists(model_path):
            result = analyze_model(model_path, model_name)
            if result:
                results.append(result)
        else:
            print(f"\n⚠️  Model not found: {model_path}")
    
    print("\n" + "="*70)
    print("OTHER AVAILABLE SAM2 VARIANTS")
    print("="*70)
    
    for model_path, model_name in other_sam2:
        if os.path.exists(model_path):
            result = analyze_model(model_path, model_name)
            if result:
                results.append(result)
    
    # Summary comparison
    print("\n" + "="*70)
    print("SUMMARY COMPARISON")
    print("="*70)
    print(f"\n{'Model':<30} {'File Size':<15} {'Parameters':<20}")
    print("-"*70)
    
    for r in results:
        print(f"{r['name']:<30} {format_size(r['file_size']):<15} {r['total_params']/1e6:>8.2f}M")
    
    print("\n" + "="*70)
    print("✓ Models used in speed tests are marked at the top")
    print("="*70)

if __name__ == '__main__':
    main()
