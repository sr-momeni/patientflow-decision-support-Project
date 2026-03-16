import os
import sys

# Add the project root to sys.path
ROOT_DIR = os.getcwd()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend.agents.resource_allocation_agent import ResourceAllocationAgent
    from backend.optimization.congestion_scenarios import get_scenario
except ImportError:
    print("Error: Could not import project modules. Please run this from the project root.")
    sys.exit(1)

def run_demo():
    print("="*60)
    print("ED RESOURCE ALLOCATION - AI EXPLAINER DEMO")
    print("="*60)
    
    agent = ResourceAllocationAgent()
    scenario = get_scenario("normal")
    
    # --- SCENARIO 1: IMMEDIATE CARE ---
    print("\n[CASE 1: Immediate Admission]")
    print(f"Status: ED is 20% full. Patient arrives with CTAS 2 (Emergent).")
    
    # Mock patient data
    patients_1 = [{"patient_id": "PT-001", "urgency_level": 2, "bed_assigned_type": None}]
    
    recs_1, _ = agent.allocate_resources(patients_1, scenario)
    rec_1 = recs_1[0]
    
    print(f"Result: {rec_1.recommended_bed}")
    print(f"AI Explanation: {rec_1.decision_explanation}")
    
    # --- SCENARIO 2: RESERVED FOR CRITICAL ---
    print("\n" + "-"*40)
    print("[CASE 2: Waiting despite free beds (AI Reservation)]")
    print(f"Status: ED is 98% full. 1 bed is physically free, but the AI Predictor")
    print(f"        has reserved it for an expected Level 1 (Critical) arrival.")
    print(f"Patient arrives with CTAS 3 (Urgent).")
    
    # Simulate a full ED batch (capacity 50)
    full_batch = []
    for i in range(49):
        full_batch.append({"patient_id": f"EXT-{i}", "urgency_level": 3, "bed_assigned_type": "ED"})
    
    # New patient
    new_patient = {"patient_id": "PT-WAIT", "urgency_level": 3, "bed_assigned_type": None}
    full_batch.append(new_patient)
    
    # Run allocation with 1 bed reserved
    recs_2, _ = agent.allocate_resources(full_batch, scenario, ed_reserved=1)
    
    # Find our patient's recommendation
    rec_2 = next(r for r in recs_2 if r.patient_id == "PT-WAIT")
    
    print(f"Result: {rec_2.recommended_bed}")
    print(f"AI Explanation: {rec_2.decision_explanation}")
    print("\n" + "="*60)

if __name__ == "__main__":
    run_demo()
