"""Train the expected-arrivals predictor model."""

import pandas as pd
import numpy as np
import os
from backend.ml.predictor import HighUrgencyPredictor

def prepare_training_data(csv_path, prediction_window_minutes=60):
    """
    Prepare regressor training data.
    """
    df = pd.read_csv(csv_path)
    df['arrival_ts'] = pd.to_datetime(df['arrival_ts'])
    df['assessment_start_ts'] = pd.to_datetime(df['assessment_start_ts'])
    df['discharge_ts'] = pd.to_datetime(df['discharge_ts'])
    
    df = df.sort_values('arrival_ts').reset_index(drop=True)
    
    features_list = []
    labels_list = []
    
    # Convert to lists for fast iteration
    arrival_times = df['arrival_ts'].tolist()
    assess_times = df['assessment_start_ts'].tolist()
    disc_times = df['discharge_ts'].tolist()
    bed_types = df['bed_assigned_type'].tolist()
    urgencies = df['urgency_level'].tolist()
    
    n = len(df)
    
    for i in range(n):
        current_time = arrival_times[i]
        
        # 1. Occupancy & Acuity Density
        ed_count = 0
        icu_count = 0
        acuity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # Look backwards to find currently active patients
        for j in range(i - 1, -1, -1):
            if (current_time - arrival_times[j]).total_seconds() > 24 * 3600:
                break # Nobody stays > 24 hours
            if assess_times[j] <= current_time < disc_times[j]:
                if bed_types[j] == 'ICU':
                    icu_count += 1
                else:
                    ed_count += 1
                acuity_counts[urgencies[j]] += 1
                
        ed_occupancy = min(1.0, ed_count / 50.0)
        icu_occupancy = min(1.0, icu_count / 20.0)
        
        # 2. Rolling arrival rates
        rates = {'15m': 0, '30m': 0, '1h': 0, '4h': 0}
        for j in range(i - 1, -1, -1):
            delta = (current_time - arrival_times[j]).total_seconds() / 60.0
            if delta <= 15: rates['15m'] += 1
            if delta <= 30: rates['30m'] += 1
            if delta <= 60: rates['1h'] += 1
            if delta <= 240: rates['4h'] += 1
            if delta > 240: break
            
        # 3. Target Label: Count of L1/L2 in next prediction_window_minutes
        future_l1_l2_count = 0
        for j in range(i + 1, n):
            delta = (arrival_times[j] - current_time).total_seconds() / 60.0
            if delta > prediction_window_minutes:
                break
            if urgencies[j] in (1, 2):
                future_l1_l2_count += 1
                
        hour_sin = np.sin(2 * np.pi * current_time.hour / 24.0)
        hour_cos = np.cos(2 * np.pi * current_time.hour / 24.0)
        dow_sin = np.sin(2 * np.pi * current_time.weekday() / 7.0)
        dow_cos = np.cos(2 * np.pi * current_time.weekday() / 7.0)
        
        feat = [
            hour_sin, hour_cos, dow_sin, dow_cos,
            ed_occupancy, icu_occupancy,
            rates['15m'], rates['30m'], rates['1h'], rates['4h'],
            acuity_counts[1], acuity_counts[2], acuity_counts[3]
        ]
        features_list.append(feat)
        labels_list.append(future_l1_l2_count)
        
    return np.array(features_list), np.array(labels_list)

def main():
    print("Loading historical data...")
    prediction_window = 60
    X, y = prepare_training_data('data/patients_2500.csv', prediction_window)
    
    print(f"Prepared {len(X)} training samples")
    print(f"Average L1/L2 arrivals per 60m window: {np.mean(y):.2f}")
    
    print("\nTraining Regression Model...")
    predictor = HighUrgencyPredictor(prediction_window_minutes=prediction_window)
    metrics = predictor.train(X, y)
    
    print("\n=== Training Results (Regression) ===")
    print(f"Mean Absolute Error: {metrics.get('mae', 0):.3f} patients")
    print(f"Root Mean Squared Error: {np.sqrt(metrics.get('mse', 0)):.3f}")
    print(f"R2 Target Variance Explained: {metrics.get('r2', 0):.3f}")
    print(f"Training samples: {metrics.get('train_size', 0)}")
    print(f"Test samples: {metrics.get('test_size', 0)}")
    
    # Save model
    os.makedirs('models', exist_ok=True)
    predictor.save('models/urgency_predictor.pkl')
    print("\nModel saved to models/urgency_predictor.pkl")

if __name__ == "__main__":
    main()
