import pandas as pd
import os
from dateutil import parser
from backend.simulation.event_model import SimulationPatient
from backend.simulation.engine import SimulationEngine

def run_fcfs_simulation(input_path, output_path, ed_capacity=50, icu_capacity=20):
    print(f"Loading data from {input_path}...")
    df = pd.read_csv(input_path)
    
    # 1. Convert DataFrame to SimulationPatients
    patients = []
    
    # We must preserve the original arrival time and LOS assumption
    # But we will wipe out the 'waiting_time_minutes' and recalculate 'service_start_ts'
    
    for _, row in df.iterrows():
        # Clean bed type
        bed_type = str(row['bed_assigned_type']).strip().upper()
        
        sim_p = SimulationPatient(
            id=row['patient_id'],
            arrival=parser.parse(row['arrival_ts']),
            urgency=int(row['urgency_level']),
            los_minutes=float(row['los_minutes']),
            bed_type=bed_type
        )
        patients.append(sim_p)
        
    print(f"Running FCFS Simulation for {len(patients)} patients...")
    print(f"Capacity: ED={ed_capacity}, ICU={icu_capacity}")
    
    # 2. Run Engine
    engine = SimulationEngine(ed_capacity=ed_capacity, icu_capacity=icu_capacity)
    engine.run(patients)
    
    # 3. Export Results
    # We want a DataFrame with the same structure but updated values
    results = []
    for p in patients:
        results.append({
            "patient_id": p.id,
            "urgency_level": p.urgency,
            "bed_assigned_type": p.bed_type,
            "admit_decision": "admit", # simplification
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
    print(f"Saved FCFS results to {output_path}")

if __name__ == "__main__":
    run_fcfs_simulation('data/patients_2500.csv', 'data/patients_fcfs.csv')
