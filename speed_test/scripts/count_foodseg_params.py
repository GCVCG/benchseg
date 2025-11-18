#!/usr/bin/env python3
"""
Count parameters for FoodSeg103 models
"""

import torch
import os

def count_parameters(state_dict):
    """Count total parameters in a state dict"""
    total_params = 0
    
    for key, tensor in state_dict.items():
        if isinstance(tensor, torch.Tensor):
            params = tensor.numel()
            total_params += params
    
    return total_params

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
    
    # File size
    file_size = os.path.getsize(model_path)
    
    # Load checkpoint
    try:
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # Handle different checkpoint formats
        if isinstance(checkpoint, dict):
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model' in checkpoint:
                state_dict = checkpoint['model']
            else:
                # Might be the state_dict itself
                state_dict = checkpoint
        else:
            state_dict = checkpoint
        
        # Count parameters
        total_params = count_parameters(state_dict)
        
        return {
            'name': model_name,
            'file_size': file_size,
            'total_params': total_params,
            'success': True
        }
            
    except Exception as e:
        print(f"  ⚠ Error loading {model_name}: {e}")
        return {
            'name': model_name,
            'file_size': file_size,
            'total_params': None,
            'success': False
        }

def main():
    # Model paths relative to assets/ckpts
    base_path = '/workspace/assets/ckpts'
    
    models = [
        ('CCNet/iter_80000.pth', 'CCNet'),
        ('CCNet_ReLeM/iter_80000.pth', 'CCNet-ReLeM'),
        ('FPN_ReLeM/iter_80000.pth', 'FPN-ReLeM'),
        ('SETR_MLA_L384/iter_80000.pth', 'SETR_MLA_L384'),
        ('SETR_Naive_ReLeM/iter_80000.pth', 'SETR_Naive-ReLeM'),
        ('swin_small/iter_80000.pth', 'SWIN_SMALL'),
        ('swin_base/iter_80000.pth', 'SWIN_BASE'),
    ]
    
    # Also add other models for comparison
    other_models = [
        ('FPN/iter_80000.pth', 'FPN'),
        ('SETR_MLA/iter_80000.pth', 'SETR_MLA'),
        ('SETR_MLA_ReLeM/iter_80000.pth', 'SETR_MLA-ReLeM'),
        ('SETR_Naive/iter_80000.pth', 'SETR_Naive'),
    ]
    
    results = []
    
    print("="*80)
    print("FOODSEG103 MODEL ANALYSIS")
    print("="*80)
    print("\nAnalyzing requested models...")
    print()
    
    for model_path, model_name in models:
        full_path = os.path.join(base_path, model_path)
        if os.path.exists(full_path):
            print(f"Processing: {model_name}...")
            result = analyze_model(full_path, model_name)
            if result['success']:
                print(f"  ✓ {format_size(result['file_size'])}, {result['total_params']/1e6:.2f}M params")
                results.append(result)
        else:
            print(f"  ✗ Not found: {model_path}")
    
    print("\n" + "="*80)
    print("OTHER AVAILABLE FOODSEG103 MODELS")
    print("="*80)
    print()
    
    for model_path, model_name in other_models:
        full_path = os.path.join(base_path, model_path)
        if os.path.exists(full_path):
            print(f"Processing: {model_name}...")
            result = analyze_model(full_path, model_name)
            if result['success']:
                print(f"  ✓ {format_size(result['file_size'])}, {result['total_params']/1e6:.2f}M params")
                results.append(result)
    
    # Summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"\n{'Model':<25} {'File Size':<15} {'Parameters':<20} {'Params (M)':<12}")
    print("-"*80)
    
    # Sort by parameters
    results_sorted = sorted(results, key=lambda x: x['total_params'] if x['total_params'] else 0)
    
    for r in results_sorted:
        if r['total_params']:
            print(f"{r['name']:<25} {format_size(r['file_size']):<15} "
                  f"{format_number(r['total_params']):<20} {r['total_params']/1e6:>8.2f}M")
    
    print("\n" + "="*80)
    print("KEY STATISTICS")
    print("="*80)
    
    if results_sorted:
        smallest = results_sorted[0]
        largest = results_sorted[-1]
        
        print(f"\nSmallest Model:  {smallest['name']}")
        print(f"  Size: {format_size(smallest['file_size'])}")
        print(f"  Params: {smallest['total_params']/1e6:.2f}M")
        
        print(f"\nLargest Model:   {largest['name']}")
        print(f"  Size: {format_size(largest['file_size'])}")
        print(f"  Params: {largest['total_params']/1e6:.2f}M")
        
        if smallest['total_params'] and largest['total_params']:
            ratio = largest['total_params'] / smallest['total_params']
            print(f"\nSize Ratio: {ratio:.1f}x difference")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
