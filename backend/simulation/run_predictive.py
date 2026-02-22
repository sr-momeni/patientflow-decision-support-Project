"""Run predictive simulation on patient data."""

import pandas as pd
import os
from dateutil import parser
from backend.simulation.event_model import SimulationPatient
from backend.simulation.predictive_engine import PredictiveEngine
from backend.ml.predictor import HighUrgencyPredictor

def run_predictive_simulation(input_path, output_path, ed_capacity=50, icu_capacity=20):
    print(f"Loading model...")
    predictor = HighUrgencyPredictor.load('models/urgency_predictor.pkl')
    
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)
    
    # Convert to SimulationPatients
    patients = []
    for _, row in df.iterrows():
        bed_type = str(row['bed_assigned_type']).strip().upper()
        
        sim_p = SimulationPatient(
            id=row['patient_id'],
            arrival=parser.parse(row['arrival_ts']),
            urgency=int(row['urgency_level']),
            los_minutes=float(row['los_minutes']),
            bed_type=bed_type
        )
        patients.append(sim_p)
    
    print(f"Running Predictive Simulation for {len(patients)} patients...")
    print(f"Capacity: ED={ed_capacity}, ICU={icu_capacity}")
    print(f"Reservation threshold: 70%")
    
    # Run engine
    engine = PredictiveEngine(
        ed_capacity=ed_capacity, 
        icu_capacity=icu_capacity,
        predictor=predictor,
        reservation_threshold=0.7,
        reservation_timeout_minutes=30
    )
    engine.run(patients)
    
    # Export results
    results = []
    for p in patients:
        results.append({
            "patient_id": p.id,
            "urgency_level": p.urgency,
            "bed_assigned_type": p.bed_type,
            "admit_decision": "admit",
            "arrival_ts": p.arrival.isoformat(),
            "assessment_start_ts": p.service_start.isoformat(),
            "discharge_ts": p.discharge.isoformat(),
            "waiting_time_minutes": p.wait_minutes,
            "los_minutes": p.los_minutes
        })
    
    df_out = pd.DataFrame(results)
    
    # Ensure directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_out.to_csv(output_path, index=False)
    print(f"Saved predictive results to {output_path}")
    
    # Print statistics
    avg_wait = df_out['waiting_time_minutes'].mean()
    print(f"\n=== Predictive Simulation Results ===")
    print(f"Average waiting time: {avg_wait:.2f} minutes")
    
    for urgency in [1, 2, 3]:
        urgency_df = df_out[df_out['urgency_level'] == urgency]
        avg_urgency_wait = urgency_df['waiting_time_minutes'].mean()
        print(f"Level {urgency} avg wait: {avg_urgency_wait:.2f} minutes")

if __name__ == "__main__":
    run_predictive_simulation('data/patients_2500.csv', 'data/patients_predictive.csv')
