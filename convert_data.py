import pandas as pd
import json
import os
from dateutil import parser

def convert_csv_to_json(input_path, output_path, var_name="RAW_DATA"):
    df = pd.read_csv(input_path)
    
    patients = []
    for _, row in df.iterrows():
        # define segments
        # Handle potential parsing errors or NaNs if needed, but assuming generated data is clean
        
        patient = {
            "id": row['patient_id'],
            "urgency": int(row['urgency_level']),
            "bed_type": str(row['bed_assigned_type']).strip().upper() if 'bed_assigned_type' in row else 'ED',
            "status": row['admit_decision'],
            "arrival_ts": row['arrival_ts'],
            "service_start_ts": row['assessment_start_ts'],
            "discharge_ts": row['discharge_ts'],
            "wait_minutes": float(row['waiting_time_minutes']),
            "los_minutes": float(row['los_minutes']),
            # Recalculate service minutes to be safe
            "service_minutes": float(row['los_minutes']) 
        }
        patients.append(patient)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write as JS file
    # We write directly to the output path provided, expecting it to be .js
    
    with open(output_path, 'w') as f:
        json_str = json.dumps(patients, indent=2)
        f.write(f"window.{var_name} = {json_str};")
        
    print(f"Converted {len(patients)} records to {output_path} as window.{var_name}")

if __name__ == "__main__":
    # Convert Original
    convert_csv_to_json('data/patients_2500.csv', 'frontend/data_original.js', "DATA_ORIGINAL")
    # Convert FCFS (if exists)
    if os.path.exists('data/patients_fcfs.csv'):
        convert_csv_to_json('data/patients_fcfs.csv', 'frontend/data_fcfs.js', "DATA_FCFS")
    # Convert Predictive (if exists)
    if os.path.exists('data/patients_predictive.csv'):
        convert_csv_to_json('data/patients_predictive.csv', 'frontend/data_predictive.js', "DATA_PREDICTIVE")
