"""Train the high-urgency arrival predictor model."""

import pandas as pd
import os
from datetime import datetime
from dateutil import parser as dateparser
from backend.ml.predictor import HighUrgencyPredictor

def prepare_training_data(csv_path):
    """
    Prepare training data from patient CSV.
    
    For each patient arrival, we need to calculate:
    - ED/ICU occupancy at time of arrival
    - Recent arrival rate
    """
    df = pd.read_csv(csv_path)
    df['arrival_ts'] = pd.to_datetime(df['arrival_ts'])
    df['assessment_start_ts'] = pd.to_datetime(df['assessment_start_ts'])
    df['discharge_ts'] = pd.to_datetime(df['discharge_ts'])
    
    # Sort by arrival
    df = df.sort_values('arrival_ts').reset_index(drop=True)
    
    training_records = []
    
    for idx, row in df.iterrows():
        arrival_time = row['arrival_ts']
        
        # Calculate occupancy at this moment
        # Count patients currently in ED/ICU
        mask_active = (df['assessment_start_ts'] <= arrival_time) & (df['discharge_ts'] > arrival_time)
        active_patients = df[mask_active]
        
        ed_count = (active_patients['bed_assigned_type'] == 'ED').sum()
        icu_count = (active_patients['bed_assigned_type'] == 'ICU').sum()
        
        ed_occupancy = min(1.0, ed_count / 50.0)  # 50 ED beds
        icu_occupancy = min(1.0, icu_count / 20.0)  # 20 ICU beds
        
        # Calculate recent arrival rate (last 2 hours)
        lookback_time = arrival_time - pd.Timedelta(hours=2)
        recent_arrivals = df[(df['arrival_ts'] >= lookback_time) & (df['arrival_ts'] < arrival_time)]
        recent_rate = len(recent_arrivals) / 2.0  # patients per hour
        
        training_records.append({
            'arrival_ts': arrival_time,
            'urgency': row['urgency_level'],
            'ed_occupancy': ed_occupancy,
            'icu_occupancy': icu_occupancy,
            'recent_rate': recent_rate
        })
    
    return training_records

def main():
    print("Loading historical data...")
    training_data = prepare_training_data('data/patients_2500.csv')
    
    print(f"Prepared {len(training_data)} training samples")
    
    print("\nTraining model...")
    predictor = HighUrgencyPredictor(prediction_window_minutes=30)
    metrics = predictor.train(training_data)
    
    print("\n=== Training Results (Multiclass) ===")
    print(f"Macro Precision: {metrics.get('precision', 0):.3f}")
    print(f"Macro Recall: {metrics.get('recall', 0):.3f}")
    print(f"Macro F1-Score: {metrics.get('f1', 0):.3f}")
    print(f"Training samples: {metrics.get('train_size', 0)}")
    print(f"Test samples: {metrics.get('test_size', 0)}")
    
    print("\nTarget Class Distribution:")
    dist = metrics.get('class_distribution', {})
    for cls in sorted(dist.keys()):
        label = "No Arrival" if cls == 0 else f"Level {cls}"
        print(f"  {label:12}: {dist[cls]:.2%}")
    
    # Save model
    os.makedirs('models', exist_ok=True)
    predictor.save('models/urgency_predictor.pkl')
    print("\nModel saved to models/urgency_predictor.pkl")

if __name__ == "__main__":
    main()
