#!/usr/bin/env python3
"""
Count parameters for YOLO model
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

def analyze_yolo_model(model_path):
    """Analyze YOLO model checkpoint"""
    print("="*70)
    print("YOLO MODEL ANALYSIS")
    print("="*70)
    print(f"\nModel Path: {model_path}")
    
    # File size
    file_size = os.path.getsize(model_path)
    print(f"File Size:  {format_size(file_size)}")
    
    # Load checkpoint
    try:
        # First try with weights_only=True to avoid needing ultralytics
        try:
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=True)
        except:
            # If that fails, try unsafe loading but catch the ultralytics import
            import sys
            import types
            
            # Create a dummy ultralytics module to bypass the import
            class DummyUltralytics:
                def __getattr__(self, name):
                    return DummyUltralytics()
                def __call__(self, *args, **kwargs):
                    return DummyUltralytics()
            
            sys.modules['ultralytics'] = DummyUltralytics()
            sys.modules['ultralytics.nn'] = DummyUltralytics()
            sys.modules['ultralytics.nn.tasks'] = DummyUltralytics()
            
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        print(f"\nCheckpoint Structure:")
        if isinstance(checkpoint, dict):
            print(f"  Top-level keys: {list(checkpoint.keys())}")
            
            # Try to find the model weights
            if 'model' in checkpoint:
                model = checkpoint['model']
                if hasattr(model, 'state_dict'):
                    state_dict = model.state_dict()
                elif isinstance(model, dict):
                    state_dict = model
                else:
                    state_dict = {}
                    for name, param in model.named_parameters():
                        state_dict[name] = param
            elif 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            else:
                state_dict = checkpoint
            
            # Count parameters
            total_params = count_parameters(state_dict)
            
            print(f"\nTotal Parameters: {format_number(total_params)} ({total_params/1e6:.2f}M)")
            
            # Show some layer info
            print(f"\nModel Layers (first 10):")
            layer_count = 0
            for key, value in state_dict.items():
                if isinstance(value, torch.Tensor):
                    print(f"  {key}: {value.shape}")
                    layer_count += 1
                    if layer_count >= 10:
                        break
            
            if len(state_dict) > 10:
                print(f"  ... and {len(state_dict) - 10} more layers")
            
            # Additional info from checkpoint
            if 'epoch' in checkpoint:
                print(f"\nTraining Info:")
                print(f"  Epoch: {checkpoint['epoch']}")
            if 'best_fitness' in checkpoint:
                print(f"  Best Fitness: {checkpoint['best_fitness']:.4f}")
            
            return {
                'file_size': file_size,
                'total_params': total_params
            }
            
    except Exception as e:
        print(f"\nError loading checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    model_path = '/workspace/assets/ckpts/YOLO/yolo11s-seg_foodseg1032.pt'
    result = analyze_yolo_model(model_path)
    
    if result:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Size:       {format_size(result['file_size'])}")
        print(f"Parameters: {result['total_params']/1e6:.2f}M")
        print("="*70)
