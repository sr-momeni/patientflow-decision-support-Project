# Ranked resume bullet candidates

Use only if you can explain and take responsibility for this assisted evaluation. These describe this analysis, not sole authorship of the team system. Synthetic simulation only; no hospital deployment or SQL execution claim.

1. Evaluated ED scheduling methods in Python across 30 simulation runs, five configurations and three random seeds, reporting waiting-time and capacity KPIs for 10,920 synthetic scenario-patient inputs.
2. Built reproducible Python KPI reports comparing FCFS and predictive scheduling, identifying 20.9%–46.1% longer average waits across three congested configurations.
3. Validated 21,840 simulated patient outputs against source inputs and timestamps, reconciling waiting time, time in system and bed occupancy across 30 runs.
4. Analyzed urgency-based scheduling trade-offs: ED-congestion CTAS 2 waits fell 27.5% while overall waiting increased 31.4% in a three-seed synthetic evaluation.
5. Audited five simulation configurations and identified an unused arrival-rate setting that made Critical Burst duplicate Normal, limiting surge-performance claims.

## Evidence mapping

- Bullet 1: per_seed_results.csv has 30 successful rows, five scenarios, seeds 42/43/44; patient counts per scenario are 752 + 742 + 690 = 2,184; 5 × 2,184 = 10,920 scenario inputs. Repeated streams across scenarios are not independent people.
- Bullet 2: kpi_comparison.csv, metric avg_wait: ED congestion improvement −31.4413%, severe congestion −20.8793%, ICU bottleneck −46.0898%. Negative improvement means longer waits. run_evaluation.py and build_report.py implement the reporting pipeline.
- Bullet 3: sum(per_seed_results.n_patients) = 21,840; validation_checks.csv and build_report.py verify each raw file against artifacts/raw/*_input.csv. This count includes both methods.
- Bullet 4: kpi_comparison.csv, ed_congestion, wait_l2 and avg_wait. Formula (FCFS mean − Agent mean) / FCFS mean × 100; means are equally weighted across three seeds.
- Bullet 5: synthetic_generator.py generate_events never reads arrival_rates_per_hour; same-seed normal and critical_burst input hashes and outputs match.

The first two are the strongest general Junior Data Analyst / Reporting Analyst candidates. The third suits data-validation roles; the fourth suits healthcare analytics when accompanied by the trade-off. Do not claim a 95.6% overall improvement, clinical prediction accuracy, real bed savings, MySQL work, or personal ownership of the original team system from this evidence.
