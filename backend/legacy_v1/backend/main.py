"""Runner: generate patients, allocate resources, print metrics."""

import argparse
from dataclasses import asdict

from backend.data.synthetic_generator import generate_patients
from backend.agents.resource_allocation_agent import allocate_resources
from backend.optimization.congestion_scenarios import get_scenario


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="normal")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    scenario = get_scenario(args.scenario)
    patients = generate_patients(args.n, scenario, seed=args.seed, inject_cases=True)
    recs, alerts, metrics = allocate_resources([asdict(p) for p in patients], scenario)

    avg_wait = round(sum(r.est_wait_min for r in recs) / len(recs), 2) if recs else 0.0
    avg_los = round(avg_wait + 180, 2)  # rough proxy

    print(f"Scenario: {scenario.name} — patients: {len(patients)}")
    print(f"Avg wait: {avg_wait} min | Avg LOS (rough): {avg_los} min")
    print(f"ED utilization: {metrics['ed_util']*100:.1f}% | ICU utilization: {metrics['icu_util']*100:.1f}%")
    print(f"Overflow (waiting): {metrics['overflow']} | ICU waitlist: {metrics['icu_waitlist']}")
    if alerts:
        print("Alerts:", ", ".join(dict.fromkeys(alerts)))
    print("Top 5 recommendations:")
    for rec in recs[:5]:
        print(f"  {rec.patient_id}: {rec.assigned_location}, wait≈{rec.est_wait_min} min")


if __name__ == "__main__":
    main()
