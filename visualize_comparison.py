import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_comparison_report(fcfs_path, predictive_path, output_csv, output_img):
    print(f"Loading FCFS data from {fcfs_path}...")
    df_fcfs = pd.read_csv(fcfs_path)
    
    print(f"Loading Predictive data from {predictive_path}...")
    df_pred = pd.read_csv(predictive_path)
    
    # Calculate stats per urgency level
    stats_fcfs = df_fcfs.groupby('urgency_level').agg({
        'waiting_time_minutes': 'mean',
        'los_minutes': 'mean'
    }).reset_index()
    stats_fcfs.columns = ['Urgency', 'FCFS_Avg_Wait', 'FCFS_Avg_LOS']
    
    stats_pred = df_pred.groupby('urgency_level').agg({
        'waiting_time_minutes': 'mean',
        'los_minutes': 'mean'
    }).reset_index()
    stats_pred.columns = ['Urgency', 'Predictive_Avg_Wait', 'Predictive_Avg_LOS']
    
    # Merge for comparison
    comparison = pd.merge(stats_fcfs, stats_pred, on='Urgency')
    
    # Calculate difference for Wait
    comparison['Wait_Diff'] = comparison['Predictive_Avg_Wait'] - comparison['FCFS_Avg_Wait']
    # Calculate difference for LOS
    comparison['LOS_Diff'] = comparison['Predictive_Avg_LOS'] - comparison['FCFS_Avg_LOS']
    
    # Save to CSV
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    comparison.to_csv(output_csv, index=False)
    print(f"Comparison statistics saved to {output_csv}")
    
    # Visualization using Matplotlib
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    urgencies = comparison['Urgency'].tolist()
    x = range(len(urgencies))
    width = 0.35
    
    # Plot 1: Wait Time
    ax1.bar([i - width/2 for i in x], comparison['FCFS_Avg_Wait'], width, label='Baseline (FCFS)', color='#64748b')
    ax1.bar([i + width/2 for i in x], comparison['Predictive_Avg_Wait'], width, label='AI Predictive', color='#2563eb')
    ax1.set_title('Average Wait Time comparison', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Urgency Level')
    ax1.set_ylabel('Minutes')
    ax1.set_xticks(x)
    ax1.set_xticklabels(urgencies)
    ax1.legend()
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Plot 2: Length of Stay (Total)
    ax2.bar([i - width/2 for i in x], comparison['FCFS_Avg_LOS'], width, label='Baseline (FCFS)', color='#94a3b8')
    ax2.bar([i + width/2 for i in x], comparison['Predictive_Avg_LOS'], width, label='AI Predictive', color='#3b82f6')
    ax2.set_title('Average Length of Stay (Total)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Urgency Level')
    ax2.set_ylabel('Minutes')
    ax2.set_xticks(x)
    ax2.set_xticklabels(urgencies)
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_img)
    plt.close()
    print(f"Comparison visualization saved to {output_img}")
    
    # 2. Dedicated Wait Time Plot (for clarity)
    plt.figure(figsize=(12, 7))
    plt.bar([i - width/2 for i in x], comparison['FCFS_Avg_Wait'], width, label='Baseline (FCFS)', color='#64748b', alpha=0.8)
    plt.bar([i + width/2 for i in x], comparison['Predictive_Avg_Wait'], width, label='AI Predictive', color='#2563eb', alpha=0.9)
    
    plt.title('Emergency Department Wait Times: Baseline vs AI Predictive', fontsize=16, fontweight='bold', pad=25)
    plt.xlabel('Urgency Level (1=Critical, 5=Non-Urgent)', fontsize=12)
    plt.ylabel('Average Wait Time (Minutes)', fontsize=12)
    plt.xticks(x, urgencies)
    plt.legend(title='Simulation Mode', frameon=True, shadow=True)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Add value labels
    for i, v in enumerate(comparison['FCFS_Avg_Wait']):
        plt.text(i - width/2, v + 2, f"{v:.1f}", ha='center', fontsize=10, fontweight='bold', color='#475569')
    for i, v in enumerate(comparison['Predictive_Avg_Wait']):
        plt.text(i + width/2, v + 2, f"{v:.1f}", ha='center', fontsize=10, fontweight='bold', color='#1e3a8a')

    plt.tight_layout()
    wait_img = output_img.replace('comparison_plot.png', 'wait_time_comparison.png')
    plt.savefig(wait_img)
    plt.close()
    print(f"Dedicated Wait Time visualization saved to {wait_img}")

if __name__ == "__main__":
    generate_comparison_report(
        'data/patients_fcfs.csv',
        'data/patients_predictive.csv',
        'data/simulation_comparison_stats.csv',
        'data/comparison_plot.png'
    )
