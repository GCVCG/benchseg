import pandas as pd
import os
import sys
import matplotlib.pyplot as plt

if __name__ == '__main__':
    output_dir = sys.argv[1]

    if not os.path.exists(output_dir):
        raise ValueError(f"Output directory {output_dir} does not exist")

    model_names = [f for f in os.listdir(output_dir)] 

    # Read all CSV files and store cuda_s data for each model
    cuda_times = []
    valid_model_names = []
    
    for model in model_names:
        log_file = os.path.join(output_dir, model, "log.csv")
        if os.path.exists(log_file):
            df = pd.read_csv(log_file)
            if 'infer_ms' in df.columns:
                cuda_times.append(df['infer_ms'].values)
                valid_model_names.append(model)
    
    # Create box plot
    plt.figure(figsize=(10, 6))
    plt.boxplot(cuda_times, labels=valid_model_names)
    plt.title('CUDA Runtime Distribution by Model')
    plt.ylabel('Time (seconds)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'runtime_comparison.png'))
    plt.close()    

