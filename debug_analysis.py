import pandas as pd

def analyze_data(path):
    df = pd.read_csv(path)
    print(f"File: {path}")
    print(f"Total rows: {len(df)}")
    
    # Check wait vs LOS
    df['net_service_time'] = df['los_minutes'] - df['waiting_time_minutes']
    
    print("\nSample Data (Top 5):")
    cols = ['patient_id', 'urgency_level', 'waiting_time_minutes', 'los_minutes', 'net_service_time']
    print(df[cols].head())
    
    print("\nStats:")
    print(f"Avg Waiting Time: {df['waiting_time_minutes'].mean():.2f}")
    print(f"Avg LOS: {df['los_minutes'].mean():.2f}")
    print(f"Avg Net Service Time: {df['net_service_time'].mean():.2f}")
    
    # Check if Net Service Time matches the generation logic (e.g., Level 1: 240-420)
    for level in sorted(df['urgency_level'].unique()):
        level_df = df[df['urgency_level'] == level]
        print(f"\nLevel {level} Net Service Time Stats:")
        print(f"  Min: {level_df['net_service_time'].min():.2f}")
        print(f"  Max: {level_df['net_service_time'].max():.2f}")
        print(f"  Avg: {level_df['net_service_time'].mean():.2f}")

if __name__ == "__main__":
    analyze_data('data/patients_2500.csv')
    print("\n" + "="*50 + "\n")
    if pd.io.common.file_exists('data/patients_predictive.csv'):
        analyze_data('data/patients_predictive.csv')
