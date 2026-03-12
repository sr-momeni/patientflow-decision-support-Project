import pandas as pd
import matplotlib.pyplot as plt
import os

def analyze_arrivals(input_path, output_stats, output_pie, output_hourly):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    print(f"Analyzing patient arrivals from {input_path}...")
    df = pd.read_csv(input_path)
    df['arrival_ts'] = pd.to_datetime(df['arrival_ts'])
    
    # 1. Urgency Distribution
    dist = df['urgency_level'].value_counts().sort_index().reset_index()
    dist.columns = ['Urgency', 'Count']
    dist['Percentage'] = (dist['Count'] / dist['Count'].sum() * 100).round(2)
    
    dist.to_csv(output_stats, index=False)
    print(f"Urgency statistics saved to {output_stats}")

    # Visualization 1: Pie Chart of Urgency
    plt.figure(figsize=(10, 8))
    labels = [f"Level {row['Urgency']}" for _, row in dist.iterrows()]
    colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6'] # Red to Blue
    
    plt.pie(dist['Count'], labels=labels, autopct='%1.1f%%', colors=colors, startangle=140, shadow=True, explode=[0.1 if x==1 else 0 for x in dist['Urgency']])
    plt.title('Patient Population by Urgency Level (CTAS 1-5)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_pie)
    plt.close()

    # 2. Hourly Arrival Rate
    df['hour'] = df['arrival_ts'].dt.hour
    hourly_counts = df.groupby('hour').size()
    
    plt.figure(figsize=(12, 6))
    hourly_counts.plot(kind='line', marker='o', linewidth=2, color='#2563eb')
    plt.fill_between(hourly_counts.index, hourly_counts.values, alpha=0.1, color='#2563eb')
    
    plt.title('Patient Arrival Frequency by Hour of Day', fontsize=14, fontweight='bold')
    plt.xlabel('Hour (00:00 - 23:00)', fontsize=12)
    plt.ylabel('Number of Patients', fontsize=12)
    plt.xticks(range(24))
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(output_hourly)
    plt.close()
    
    print(f"Arrival visualizations saved to {output_pie} and {output_hourly}")

if __name__ == "__main__":
    # Use the raw generated data for pure arrival analysis
    analyze_arrivals(
        'data/patients_2500.csv',
        'data/arrival_urgency_stats.csv',
        'data/arrival_pie.png',
        'data/arrival_hourly.png'
    )
