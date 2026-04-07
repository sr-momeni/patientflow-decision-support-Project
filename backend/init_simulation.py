import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path

# Add the project root to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.data.synthetic_generator import generate_events, save_events_to_csv
from backend.optimization.congestion_scenarios import get_scenario
from backend.ml.predictor import HighUrgencyPredictor

def initialize_simulation():
    print("=== Initializing ER Simulation Environment ===")
    
    # 1. Generate 30 days of historical data
    data_dir = os.path.join(ROOT_DIR, "backend", "data", "raw")
    os.makedirs(data_dir, exist_ok=True)
    
    history_file = os.path.join(data_dir, "historical_data_30d.csv")
    
    if not os.path.exists(history_file):
        print(f"Generating 30 days of historical data...")
        scenario = get_scenario("normal")
        # Start from 30 days ago
        start_date = date.today() - timedelta(days=30)
        # Adjust to monday for synthetic_generator compatibility
        start_monday = start_date - timedelta(days=start_date.weekday())
        
        events = generate_events(days=30, scenario=scenario, start_date=start_monday)
        save_events_to_csv(events, Path(history_file))
        print(f"Historical data saved to {history_file}")
    else:
        print(f"Using existing historical data: {history_file}")
        
    # 2. Train the HighUrgencyPredictor
    print("Training HighUrgencyPredictor...")
    df = pd.read_csv(history_file)
    df['arrival_ts'] = pd.to_datetime(df['arrival_ts'])
    
    predictor = HighUrgencyPredictor()
    
    X_list = []
    y_list = []
    
    # Generate training samples for every hour in the history
    start_dt = df['arrival_ts'].min().replace(minute=0, second=0, microsecond=0)
    end_dt = df['arrival_ts'].max()
    curr = start_dt
    
    print(f"Extracting features from {start_dt} to {end_dt}...")
    import numpy as np
    
    while curr < end_dt:
        # Target: arrivals in the next window
        window_end = curr + timedelta(minutes=predictor.prediction_window_minutes)
        high_urg_count = len(df[(df['arrival_ts'] >= curr) & 
                                (df['arrival_ts'] < window_end) & 
                                (df['urgency_level'] <= 2)])
        
        # Features
        feat = predictor._extract_features(curr)
        X_list.append(feat[0])
        y_list.append(high_urg_count)
        
        curr += timedelta(hours=1)
        
    X = np.array(X_list)
    y = np.array(y_list)
    
    print(f"Training on {len(X)} samples...")
    predictor.train(X, y)
    
    # 3. Save the model
    model_dir = os.path.join(ROOT_DIR, "backend", "ml", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "high_urgency_predictor.joblib")
    predictor.save(model_path)
    print(f"Predictive model saved to {model_path}")
    
    print("=== Environment Initialization Complete ===")

if __name__ == "__main__":
    initialize_simulation()
