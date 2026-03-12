import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

def analyze_advanced_metrics(log_path, output_csv, output_img_pie, output_img_bar):
    if not os.path.exists(log_path):
        print(f"Error: Log file {log_path} not found.")
        return

    print(f"Parsing log file {log_path}...")
    
    try:
        df = pd.read_csv(log_path)
    except Exception as e:
        print(f"Error reading log: {e}")
        return

    # Use correct event names from predictive_engine.py
    # Events: reserved, reservation_used, reservation_expired, admitted, waited_and_admitted
    
    total_res_starts = len(df[df['event'] == 'reserved'])
    succ_res = len(df[df['event'] == 'reservation_used'])
    expired_res = len(df[df['event'] == 'reservation_expired'])
    
    # Accuracy
    accuracy = (succ_res / total_res_starts * 100) if total_res_starts > 0 else 0
    
    # Calculate Bed Occupancy Rate for both models
    # Sim duration from log
    df['ts_dt'] = pd.to_datetime(df['timestamp'])
    sim_duration_mins = (df['ts_dt'].max() - df['ts_dt'].min()).total_seconds() / 60.0
    
    ED_CAP = 50
    ICU_CAP = 20
    total_ed_mins = ED_CAP * sim_duration_mins
    total_icu_mins = ICU_CAP * sim_duration_mins
    
    # Predictive Occupancy
    df_pred_res = pd.read_csv('data/patients_predictive.csv')
    df_pred_res['service_time'] = df_pred_res['los_minutes'] - df_pred_res['waiting_time_minutes']
    pred_ed_occ = (df_pred_res[df_pred_res['bed_assigned_type'] == 'ED']['service_time'].sum() / total_ed_mins) * 100
    pred_icu_occ = (df_pred_res[df_pred_res['bed_assigned_type'] == 'ICU']['service_time'].sum() / total_icu_mins) * 100
    
    # FCFS Occupancy
    df_fcfs_res = pd.read_csv('data/patients_fcfs.csv')
    df_fcfs_res['service_time'] = df_fcfs_res['los_minutes'] - df_fcfs_res['waiting_time_minutes']
    fcfs_ed_occ = (df_fcfs_res[df_fcfs_res['bed_assigned_type'] == 'ED']['service_time'].sum() / total_ed_mins) * 100
    fcfs_icu_occ = (df_fcfs_res[df_fcfs_res['bed_assigned_type'] == 'ICU']['service_time'].sum() / total_icu_mins) * 100

    # Calculate Precise Wasted Minutes (holds only exist in predictive)
    wasted_minutes = expired_res * 30
    wasted_occ_rate = (wasted_minutes / (total_ed_mins + total_icu_mins)) * 100
    
    # Generate Stats Summary
    stats = {
        "Metric": [
            "Prediction Accuracy (%)",
            "Opportunity Cost (Bed-Minutes Wasted)",
            "ED Occupancy (Baseline FCFS) %",
            "ED Occupancy (Predictive AI) %",
            "ICU Occupancy (Baseline FCFS) %",
            "ICU Occupancy (Predictive AI) %",
            "Wasted Capacity Rate (Predictive) %"
        ],
        "Value": [
            round(accuracy, 2),
            wasted_minutes,
            round(fcfs_ed_occ, 2),
            round(pred_ed_occ, 2),
            round(fcfs_icu_occ, 2),
            round(pred_icu_occ, 2),
            round(wasted_occ_rate, 2)
        ]
    }
    df_stats = pd.DataFrame(stats)
    df_stats.to_csv(output_csv, index=False)
    print(f"Advanced metrics saved to {output_csv}")

    # Visualization 1: Pie Chart (Accuracy)
    if total_res_starts > 0:
        plt.figure(figsize=(8, 8))
        labels = ['Successful Catch', 'Expired Hold']
        sizes = [max(0.1, succ_res), max(0.1, expired_res)]
        colors = ['#22c55e', '#ef4444']
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
        plt.title('AI Bed Reservation Efficiency', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_img_pie)
        plt.close()

    # Visualization 2: Comparative Occupancy Bar Chart
    plt.figure(figsize=(12, 7))
    
    categories = ['ED Occupancy', 'ICU Occupancy']
    fcfs_vals = [fcfs_ed_occ, fcfs_icu_occ]
    pred_vals = [pred_ed_occ, pred_icu_occ]
    
    x = range(len(categories))
    width = 0.35
    
    plt.bar([i - width/2 for i in x], fcfs_vals, width, label='Baseline (FCFS)', color='#94a3b8')
    plt.bar([i + width/2 for i in x], pred_vals, width, label='AI Predictive', color='#3b82f6')
    
    # Add a phantom bar for Wasted Capacity to show in legend if needed? 
    # Or just keep it separate as a footnote.
    
    plt.ylabel('Capacity Utilization (%)')
    plt.title('Bed Utilization Comparison: Baseline vs AI Predictive', fontsize=14, fontweight='bold')
    plt.xticks(x, categories)
    plt.ylim(0, 100)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i, v in enumerate(fcfs_vals):
        plt.text(i - width/2, v + 2, f"{v:.1f}%", ha='center', fontweight='bold')
    for i, v in enumerate(pred_vals):
        plt.text(i + width/2, v + 2, f"{v:.1f}%", ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_img_bar)
    plt.close()
    print(f"Visualizations saved to {output_img_pie} and {output_img_bar}")

if __name__ == "__main__":
    analyze_advanced_metrics(
        'data/simulation_events.log',
        'data/reservation_efficiency_stats.csv',
        'data/reservation_pie.png',
        'data/bed_time_bar.png'
    )
