#!/usr/bin/env python3
"""
Analyze tracking model speed test results and generate a comprehensive report.

Usage:
    python analyze_tracking_results.py [results_dir]
    
Examples:
    python analyze_tracking_results.py data/speed_test/results_tracking
"""

import os
import sys
import csv
from pathlib import Path
import json


def parse_timing_csv(csv_path):
    """Parse timing CSV file."""
    results = []
    
    if not os.path.exists(csv_path):
        return results
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append({
                    'sequence': row['sequence'],
                    'frames': int(row['frames']),
                    'total_time': float(row['total_time']),
                    'avg_time_per_frame': float(row['avg_time_per_frame']),
                    'fps': float(row['fps'])
                })
    except Exception as e:
        print(f"Warning: Error parsing {csv_path}: {e}")
    
    return results


def analyze_tracking_results(results_dir):
    """Analyze all tracking model results."""
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return {}
    
    model_stats = {}
    
    # Check for XMem2 results
    xmem2_csv = results_path / 'xmem2' / 'timing_summary.csv'
    if xmem2_csv.exists():
        model_stats['XMem2'] = parse_timing_csv(xmem2_csv)
    
    # Check for SAM2 results
    sam2_csv = results_path / 'sam2' / 'timing_summary.csv'
    if sam2_csv.exists():
        model_stats['SAM2'] = parse_timing_csv(sam2_csv)
    
    return model_stats


def print_tracking_report(model_stats):
    """Print a formatted report of tracking model results."""
    if not model_stats:
        print("No tracking results to display.")
        return
    
    print("\n" + "="*80)
    print("Tracking Model Speed Test Results".center(80))
    print("="*80 + "\n")
    
    # Per-model results
    for model_name, sequences in model_stats.items():
        if not sequences:
            continue
            
        print(f"{'='*80}")
        print(f"{model_name} Performance".center(80))
        print(f"{'='*80}\n")
        
        print(f"{'Sequence':<20s} {'Frames':<8s} {'Total (s)':<12s} {'Avg/Frame (s)':<15s} {'FPS':<10s}")
        print("-" * 80)
        
        total_frames = 0
        total_time = 0
        
        for seq in sequences:
            print(f"{seq['sequence']:<20s} {seq['frames']:<8d} "
                  f"{seq['total_time']:<12.3f} {seq['avg_time_per_frame']:<15.3f} "
                  f"{seq['fps']:<10.2f}")
            total_frames += seq['frames']
            total_time += seq['total_time']
        
        if total_frames > 0:
            overall_fps = total_frames / total_time if total_time > 0 else 0
            overall_avg = total_time / total_frames if total_frames > 0 else 0
            
            print("-" * 80)
            print(f"{'OVERALL':<20s} {total_frames:<8d} "
                  f"{total_time:<12.3f} {overall_avg:<15.3f} "
                  f"{overall_fps:<10.2f}")
        
        print()
    
    # Model comparison
    if len(model_stats) > 1:
        print("="*80)
        print("Model Comparison".center(80))
        print("="*80 + "\n")
        
        # Get common sequences
        all_sequences = set()
        for sequences in model_stats.values():
            all_sequences.update(seq['sequence'] for seq in sequences)
        
        for seq_name in sorted(all_sequences):
            print(f"\n{seq_name}:")
            print("-" * 80)
            print(f"{'Model':<20s} {'Avg Time (s)':<15s} {'FPS':<10s} {'Speedup':<10s}")
            print("-" * 80)
            
            seq_results = []
            for model_name, sequences in model_stats.items():
                for seq in sequences:
                    if seq['sequence'] == seq_name:
                        seq_results.append((model_name, seq['avg_time_per_frame'], seq['fps']))
                        break
            
            if seq_results:
                # Sort by time (fastest first)
                seq_results.sort(key=lambda x: x[1])
                slowest_time = max(r[1] for r in seq_results)
                
                for model_name, avg_time, fps in seq_results:
                    speedup = slowest_time / avg_time if avg_time > 0 else 0
                    print(f"{model_name:<20s} {avg_time:<15.3f} {fps:<10.2f} {speedup:<10.2f}x")
    
    print("\n" + "="*80 + "\n")


def save_json_report(model_stats, output_file):
    """Save tracking results as JSON."""
    json_data = {}
    
    for model_name, sequences in model_stats.items():
        json_data[model_name] = {
            'sequences': {},
            'overall': {}
        }
        
        total_frames = 0
        total_time = 0
        
        for seq in sequences:
            json_data[model_name]['sequences'][seq['sequence']] = {
                'frames': seq['frames'],
                'total_time_s': seq['total_time'],
                'avg_time_per_frame_s': seq['avg_time_per_frame'],
                'fps': seq['fps']
            }
            total_frames += seq['frames']
            total_time += seq['total_time']
        
        if total_frames > 0:
            json_data[model_name]['overall'] = {
                'total_frames': total_frames,
                'total_time_s': total_time,
                'avg_time_per_frame_s': total_time / total_frames,
                'fps': total_frames / total_time
            }
    
    with open(output_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Results saved to: {output_file}")


def main():
    """Main function."""
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "data/speed_test/results_tracking"
    
    print(f"Analyzing tracking results from: {results_dir}")
    
    model_stats = analyze_tracking_results(results_dir)
    
    if model_stats:
        print_tracking_report(model_stats)
        
        # Save JSON report
        json_output = Path(results_dir) / 'tracking_speed_summary.json'
        save_json_report(model_stats, json_output)
    else:
        print("No tracking results found to analyze.")
        print(f"Expected timing files:")
        print(f"  - {results_dir}/xmem2/timing_summary.csv")
        print(f"  - {results_dir}/sam2/timing_summary.csv")


if __name__ == '__main__':
    main()
