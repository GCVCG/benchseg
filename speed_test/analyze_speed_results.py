#!/usr/bin/env python3
"""
Analyze FoodSeg speed test results and generate a comprehensive report.

Usage:
    python analyze_speed_results.py [results_dir]
    
Example:
    python analyze_speed_results.py data/speed_test/results
"""

import os
import sys
import csv
from pathlib import Path
from collections import defaultdict
import json


def parse_log_csv(log_path):
    """Parse timing CSV file and extract timing information."""
    times = []
    image_names = []
    
    if not os.path.exists(log_path):
        return [], []
    
    try:
        with open(log_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try to find timing column
                time_value = None
                for key in ['inference_time', 'total_time', 'time', 'runtime', 'elapsed']:
                    if key in row:
                        try:
                            time_value = float(row[key])
                            break
                        except (ValueError, TypeError):
                            continue
                
                if time_value is not None:
                    times.append(time_value)
                    # Try to get image name
                    for key in ['image', 'img_path', 'filename', 'name']:
                        if key in row:
                            image_names.append(row[key])
                            break
                    else:
                        image_names.append(f"image_{len(times)}")
    except Exception as e:
        print(f"Warning: Error parsing {log_path}: {e}")
    
    return times, image_names


def get_image_size_from_name(image_name):
    """Extract resolution from image filename."""
    name = os.path.basename(image_name).lower()
    if 'small' in name or '512x384' in name:
        return 'Small (512×384)'
    elif 'large' in name or '1920x1080' in name:
        return 'Large (1920×1080)'
    elif 'medium' in name:
        if '1365' in name or '1024' in name:
            return 'Medium (1365×1024)'
        else:
            return 'Medium (720×960)'
    return 'Unknown'


def analyze_results(results_dir):
    """Analyze all timing results in the results directory."""
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return
    
    # Collect all model results
    model_stats = {}
    
    for model_dir in sorted(results_path.iterdir()):
        if not model_dir.is_dir():
            continue
        
        model_name = model_dir.name
        log_file = model_dir / 'log.csv'
        
        times, image_names = parse_log_csv(log_file)
        
        if not times:
            print(f"⚠️  No timing data found for {model_name}")
            continue
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
        
        # Group by image size
        size_stats = defaultdict(list)
        for time, img_name in zip(times, image_names):
            size = get_image_size_from_name(img_name)
            size_stats[size].append(time)
        
        model_stats[model_name] = {
            'count': len(times),
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'std_dev': std_dev,
            'fps': 1 / avg_time if avg_time > 0 else 0,
            'size_stats': {k: sum(v)/len(v) for k, v in size_stats.items()},
            'times': times,
            'images': image_names
        }
    
    return model_stats


def print_report(model_stats):
    """Print a formatted report of the timing results."""
    if not model_stats:
        print("No results to display.")
        return
    
    print("\n" + "="*80)
    print("FoodSeg Model Speed Test Results".center(80))
    print("="*80 + "\n")
    
    # Overall ranking by average speed
    print("📊 Overall Model Ranking (by average inference time)")
    print("-" * 80)
    
    sorted_models = sorted(model_stats.items(), key=lambda x: x[1]['avg_time'])
    
    for rank, (model_name, stats) in enumerate(sorted_models, 1):
        print(f"\n{rank}. {model_name}")
        print(f"   Average time: {stats['avg_time']*1000:.1f} ms ({stats['fps']:.2f} FPS)")
        print(f"   Range: {stats['min_time']*1000:.1f} - {stats['max_time']*1000:.1f} ms")
        print(f"   Std dev: {stats['std_dev']*1000:.1f} ms")
        print(f"   Images: {stats['count']}")
    
    # Performance by image size
    print("\n\n" + "="*80)
    print("📏 Performance by Image Size")
    print("="*80 + "\n")
    
    all_sizes = set()
    for stats in model_stats.values():
        all_sizes.update(stats['size_stats'].keys())
    
    for size in sorted(all_sizes):
        print(f"\n{size}:")
        print("-" * 80)
        size_results = []
        for model_name, stats in model_stats.items():
            if size in stats['size_stats']:
                size_results.append((model_name, stats['size_stats'][size]))
        
        size_results.sort(key=lambda x: x[1])
        for model_name, time in size_results:
            fps = 1/time if time > 0 else 0
            print(f"  {model_name:20s}: {time*1000:6.1f} ms ({fps:5.2f} FPS)")
    
    # Speed comparison table
    print("\n\n" + "="*80)
    print("📈 Speedup Comparison (relative to slowest model)")
    print("="*80 + "\n")
    
    if sorted_models:
        slowest_time = sorted_models[-1][1]['avg_time']
        
        print(f"{'Model':<20s} {'Avg Time (ms)':<15s} {'FPS':<10s} {'Speedup':<10s}")
        print("-" * 80)
        
        for model_name, stats in sorted_models:
            speedup = slowest_time / stats['avg_time']
            print(f"{model_name:<20s} {stats['avg_time']*1000:<15.1f} "
                  f"{stats['fps']:<10.2f} {speedup:<10.2f}x")
    
    print("\n" + "="*80 + "\n")


def save_json_report(model_stats, output_file):
    """Save results as JSON for further analysis."""
    # Convert to serializable format
    json_data = {}
    for model_name, stats in model_stats.items():
        json_data[model_name] = {
            'count': stats['count'],
            'avg_time_ms': stats['avg_time'] * 1000,
            'min_time_ms': stats['min_time'] * 1000,
            'max_time_ms': stats['max_time'] * 1000,
            'std_dev_ms': stats['std_dev'] * 1000,
            'fps': stats['fps'],
            'size_stats': {k: v*1000 for k, v in stats['size_stats'].items()},
            'individual_times_ms': [t*1000 for t in stats['times']],
            'images': stats['images']
        }
    
    with open(output_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Results saved to: {output_file}")


def main():
    """Main function."""
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "data/speed_test/results"
    
    print(f"Analyzing results from: {results_dir}")
    
    model_stats = analyze_results(results_dir)
    
    if model_stats:
        print_report(model_stats)
        
        # Save JSON report
        json_output = Path(results_dir) / 'speed_test_summary.json'
        save_json_report(model_stats, json_output)
    else:
        print("No results found to analyze.")
        print(f"Make sure timing logs exist in: {results_dir}/*/log.csv")


if __name__ == '__main__':
    main()
