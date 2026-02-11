"""Small runner to exercise the synthetic generator and allocation agent."""

from __future__ import annotations

import argparse
from dataclasses import asdict

from backend.agents.resource_allocation_agent import allocate_resources
from backend.data.synthetic_generator import generate_events, summarize
from backend.optimization.congestion_scenarios import get_scenario


def run(scenario_name: str, n: int = 200, seed: int = 42) -> None:
    scenario = get_scenario(scenario_name)
    events = generate_events(n=n, scenario=scenario, seed=seed)
    summary = summarize(events)

    recs, alerts, metrics = allocate_resources([asdict(ev) for ev in events], scenario)

    print(f"Scenario: {scenario.name} — generated {summary['count']} patients")
    print(f"Average waiting time: {summary['avg_wait']} minutes")
    print(f"Average LOS: {summary['avg_los']} minutes")
    print(f"ED utilization: {metrics['ed_util']*100:.1f}%")
    print(f"ICU utilization: {metrics['icu_util']*100:.1f}%")
    print(f"Overflow (waiting): {metrics['overflow']}")
    if alerts:
        print("Alerts:", ", ".join(alerts))
    # show a couple of recommendations
    for rec in recs[:5]:
        print(
            f"{rec.patient_id}: bed={rec.recommended_bed}, "
            f"est_wait={rec.estimated_wait_minutes}m, "
            f"los_delta={rec.estimated_los_delta_minutes}m"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic flow and allocation agent.")
    parser.add_argument("--scenario", default="normal", help="Scenario name")
    parser.add_argument("--n", type=int, default=200, help="Number of synthetic patients")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    run(args.scenario, n=args.n, seed=args.seed)


if __name__ == "__main__":
    main()
