#!/usr/bin/env python3
"""
Count parameters for YOLO model using ultralytics
"""

import torch
import os

def count_parameters(model):
    """Count total parameters in a model"""
    total_params = 0
    trainable_params = 0
    
    for param in model.parameters():
        params = param.numel()
        total_params += params
        if param.requires_grad:
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
    print("\nLoading checkpoint...")
    try:
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        print(f"Checkpoint Keys: {list(checkpoint.keys())}")
        
        # Get the model
        if 'model' in checkpoint:
            model = checkpoint['model']
            print(f"Model Type: {type(model)}")
            
            # Count parameters
            total_params, trainable_params = count_parameters(model)
            
            print(f"\nTotal Parameters:     {format_number(total_params)} ({total_params/1e6:.2f}M)")
            print(f"Trainable Parameters: {format_number(trainable_params)} ({trainable_params/1e6:.2f}M)")
            
            # Show model structure info
            if hasattr(model, 'model'):
                print(f"\nModel Structure:")
                layer_count = 0
                for name, module in model.model.named_children():
                    params = sum(p.numel() for p in module.parameters())
                    print(f"  {name}: {type(module).__name__} ({params:,} params)")
                    layer_count += 1
                    if layer_count >= 10:
                        break
                
                total_layers = len(list(model.model.named_children()))
                if total_layers > 10:
                    print(f"  ... and {total_layers - 10} more layers")
            
            # Additional info
            if 'epoch' in checkpoint:
                print(f"\nTraining Info:")
                print(f"  Epoch: {checkpoint['epoch']}")
            
            if 'train_args' in checkpoint:
                print(f"  Train args available: {list(checkpoint['train_args'].keys())[:5]}")
            
            return {
                'file_size': file_size,
                'total_params': total_params,
                'trainable_params': trainable_params
            }
        else:
            print("⚠ Could not find 'model' key in checkpoint")
            return None
            
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
        print(f"Model:      YOLO11s-seg (FoodSeg103 trained)")
        print(f"File Size:  {format_size(result['file_size'])}")
        print(f"Parameters: {result['total_params']/1e6:.2f}M ({format_number(result['total_params'])})")
        print("="*70)
