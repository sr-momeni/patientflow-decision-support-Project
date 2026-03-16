import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil import parser
import time
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_theme(style="whitegrid")

from backend.data.synthetic_generator import generate_events
from backend.optimization.congestion_scenarios import list_scenarios
from backend.simulation.event_model import SimulationPatient
from backend.simulation.engine import SimulationEngine
from backend.simulation.predictive_engine import PredictiveEngine
from backend.ml.predictor import HighUrgencyPredictor

def create_sim_patients(events):
    patients = []
    for ev in events:
        sim_p = SimulationPatient(
            id=ev.patient_id,
            arrival=parser.parse(ev.arrival_ts),
            urgency=ev.urgency_level,
            los_minutes=ev.los_minutes,
            bed_type=ev.bed_assigned_type
        )
        patients.append(sim_p)
    return patients

def calculate_metrics(patients, scenario_cfg, days, metrics_dict=None):
    results = {}
    
    waits = [p.wait_minutes for p in patients]
    loses = [p.wait_minutes + p.los_minutes for p in patients]
    
    results['avg_wait'] = np.mean(waits) if waits else 0
    results['avg_los'] = np.mean(loses) if loses else 0
    
    for lvl in range(1, 6):
        lvl_waits = [p.wait_minutes for p in patients if p.urgency == lvl]
        lvl_loses = [p.wait_minutes + p.los_minutes for p in patients if p.urgency == lvl]
        results[f'wait_l{lvl}'] = np.mean(lvl_waits) if lvl_waits else 0
        results[f'los_l{lvl}'] = np.mean(lvl_loses) if lvl_loses else 0
        
    # Occupancy
    ed_los_sum = sum(p.los_minutes for p in patients if p.bed_type == 'ED')
    icu_los_sum = sum(p.los_minutes for p in patients if p.bed_type == 'ICU')
    
    ed_avail = days * 1440 * scenario_cfg.ed_beds
    icu_avail = days * 1440 * scenario_cfg.icu_beds
    
    results['ed_occ'] = min(1.0, ed_los_sum / ed_avail) if ed_avail > 0 else 0
    results['icu_occ'] = min(1.0, icu_los_sum / icu_avail) if icu_avail > 0 else 0
    
    if metrics_dict:
        total = metrics_dict.get('total_reservations', 0)
        expired = metrics_dict.get('expired_reservations', 0)
        catches = metrics_dict.get('successful_catches', 0)
        wasted = metrics_dict.get('wasted_bed_minutes', 0.0)
        
        results['total_reservations'] = total
        results['precision'] = catches / total if total > 0 else 0
        results['expired_rate'] = expired / total if total > 0 else 0
        results['wasted_mins'] = wasted
    else:
        results['total_reservations'] = 0
        results['precision'] = 0
        results['expired_rate'] = 0
        results['wasted_mins'] = 0
        
    return results

def run_scenarios(days=5, seeds=[42, 43, 44]):
    print("Loading Predictor...")
    predictor = HighUrgencyPredictor.load('models/urgency_predictor.pkl')
    scenarios = list_scenarios()
    
    all_results = []
    
    for s_name, cfg in scenarios.items():
        print(f"\n--- Evaluating Scenario: {s_name} ---")
        
        fcfs_metrics = []
        agent_metrics = []
        
        for seed in seeds:
            print(f"  Generating data for seed {seed}...")
            events = generate_events(days=days, scenario=cfg, seed=seed)
            
            # FCFS Baseline
            p_fcfs = create_sim_patients(events)
            fcfs_engine = SimulationEngine(ed_capacity=cfg.ed_beds, icu_capacity=cfg.icu_beds)
            fcfs_engine.run(p_fcfs)
            f_res = calculate_metrics(p_fcfs, cfg, days)
            fcfs_metrics.append(f_res)
            
            # Agent (Predictive Priority)
            p_agent = create_sim_patients(events)
            # Using 0.8 as the default balanced threshold
            agent_engine = PredictiveEngine(
                ed_capacity=cfg.ed_beds, 
                icu_capacity=cfg.icu_beds,
                predictor=predictor,
                reservation_threshold=0.8,
                reservation_timeout_minutes=30
            )
            agent_engine.run(p_agent)
            a_res = calculate_metrics(p_agent, cfg, days, agent_engine.metrics)
            agent_metrics.append(a_res)
            
        # Aggregate FCFS
        f_agg = pd.DataFrame(fcfs_metrics).mean().to_dict()
        a_agg = pd.DataFrame(agent_metrics).mean().to_dict()
        
        all_results.append({
            'Scenario': s_name,
            'Model': 'FCFS',
            **f_agg
        })
        all_results.append({
            'Scenario': s_name,
            'Model': 'Agent',
            **a_agg
        })
        
    df = pd.DataFrame(all_results)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/evaluation_scenarios.csv", index=False)
    
    print("\n=== Eval Complete. Scenarios Exported to data/evaluation_scenarios.csv ===")
    
def run_threshold_sweep(scenario_name="normal", days=5, seed=42):
    print(f"Running Threshold Sweep on '{scenario_name}'...")
    predictor = HighUrgencyPredictor.load('models/urgency_predictor.pkl')
    cfg = list_scenarios()[scenario_name]
    events = generate_events(days=days, scenario=cfg, seed=seed)
    
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.98, 5.0]
    results = []
    
    for t in thresholds:
        p_agent = create_sim_patients(events)
        engine = PredictiveEngine(
            ed_capacity=cfg.ed_beds, 
            icu_capacity=cfg.icu_beds,
            predictor=predictor,
            reservation_threshold=t,
            reservation_timeout_minutes=30
        )
        engine.run(p_agent)
        res = calculate_metrics(p_agent, cfg, days, engine.metrics)
        res['Threshold'] = "Disabled" if t == 5.0 else t
        results.append(res)
        print(f"  Threshold {t}: Avg Wait = {res['avg_wait']:.1f}m, L1 Wait = {res['wait_l1']:.1f}m, Wasted = {res['wasted_mins']:.0f}m")
        
    df = pd.DataFrame(results)
    df.to_csv("data/evaluation_thresholds.csv", index=False)
    
def run_duration_sweep(scenario_name="normal", days=5, seed=42):
    print(f"Running Hold Duration Sweep on '{scenario_name}'...")
    predictor = HighUrgencyPredictor.load('models/urgency_predictor.pkl')
    cfg = list_scenarios()[scenario_name]
    events = generate_events(days=days, scenario=cfg, seed=seed)
    
    durations = [10, 15, 20, 30, 45, 60]
    results = []
    
    for d in durations:
        p_agent = create_sim_patients(events)
        engine = PredictiveEngine(
            ed_capacity=cfg.ed_beds, 
            icu_capacity=cfg.icu_beds,
            predictor=predictor,
            reservation_threshold=0.8,
            reservation_timeout_minutes=d
        )
        engine.run(p_agent)
        res = calculate_metrics(p_agent, cfg, days, engine.metrics)
        res['Hold_Duration'] = d
        results.append(res)
        print(f"  Duration {d}m: Avg Wait = {res['avg_wait']:.1f}m, Wasted = {res['wasted_mins']:.0f}m, Precision = {res['precision']:.2f}")

    df = pd.DataFrame(results)
    df.to_csv("data/evaluation_durations.csv", index=False)

def generate_plots():
    print("\nGenerating Visualization Plots...")
    os.makedirs("data/plots", exist_ok=True)
    
    # 1. Scenario Comparison (Wait Times)
    if os.path.exists("data/evaluation_scenarios.csv"):
        df = pd.read_csv("data/evaluation_scenarios.csv")
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x='Scenario', y='avg_wait', hue='Model')
        plt.title("Average Waiting Time: Baseline vs Agent")
        plt.ylabel("Minutes")
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig("data/plots/scenario_comparison.png")
        plt.close()
        
        # L1/L2 specific
        plt.figure(figsize=(12, 6))
        melted = df.melt(id_vars=['Scenario', 'Model'], value_vars=['wait_l1', 'wait_l2'], var_name='Urgency', value_name='Wait_Time')
        sns.barplot(data=melted, x='Scenario', y='Wait_Time', hue='Model')
        plt.title("High Urgency (L1/L2) Wait Times")
        plt.ylabel("Minutes")
        plt.tight_layout()
        plt.savefig("data/plots/high_urgency_wait.png")
        plt.close()

    # 2. Threshold Sweep (Wasted Minutes vs L1 Wait)
    if os.path.exists("data/evaluation_thresholds.csv"):
        df = pd.read_csv("data/evaluation_thresholds.csv")
        # Handle "Disabled" string in Threshold column if it exists
        df['Threshold_Numeric'] = pd.to_numeric(df['Threshold'].replace("Disabled", "1.0"))
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax2 = ax1.twinx()
        
        sns.lineplot(data=df, x='Threshold_Numeric', y='wasted_mins', ax=ax1, marker='o', color='red', label='Wasted Bed Minutes')
        sns.lineplot(data=df, x='Threshold_Numeric', y='wait_l1', ax=ax2, marker='s', color='blue', label='L1 Wait Time')
        
        ax1.set_xlabel("Reservation Threshold (Probability)")
        ax1.set_ylabel("Wasted Bed Minutes", color='red')
        ax2.set_ylabel("L1 Wait Time (Min)", color='blue')
        plt.title("Threshold Sweep: Waste vs Coverage")
        plt.tight_layout()
        plt.savefig("data/plots/threshold_sweep.png")
        plt.close()

    # 3. Hold Duration Sweep
    if os.path.exists("data/evaluation_durations.csv"):
        df = pd.read_csv("data/evaluation_durations.csv")
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='Hold_Duration', y='precision', marker='o')
        plt.title("Hold Duration vs Reservation Precision")
        plt.xlabel("Hold Duration (Minutes)")
        plt.ylabel("Precision (Catches / Total)")
        plt.tight_layout()
        plt.savefig("data/plots/duration_precision.png")
        plt.close()

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--mode", choices=["scenarios", "thresholds", "durations", "plots", "all"], default="all")
    args = arg_parser.parse_args()
    
    if args.mode in ["scenarios", "all"]:
        run_scenarios(days=5)
    if args.mode in ["thresholds", "all"]:
        run_threshold_sweep()
    if args.mode in ["durations", "all"]:
        run_duration_sweep()
    if args.mode in ["plots", "all"]:
        generate_plots()
