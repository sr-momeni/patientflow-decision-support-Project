"""Compatibility entry point for the versioned, non-overwriting evaluation.

Legacy calculations and outputs are preserved under reports/resume_evaluation.
Use validate_simulation for the frozen train/validation/final protocol.
"""
from datetime import timedelta
from backend.simulation.metrics import create_patients as create_sim_patients,calculate_kpis


def calculate_metrics(patients,scenario_cfg,days,metrics_dict=None,observation_start=None):
    if observation_start is None:
        if not patients:
            raise ValueError('An empty cohort requires an explicit observation start')
        observation_start=min(p.arrival for p in patients).replace(hour=0,minute=0,second=0,microsecond=0)
    return calculate_kpis(patients,observation_start,observation_start+timedelta(days=days),
                          scenario_cfg.ed_beds,scenario_cfg.icu_beds,metrics_dict)


def main():
    import argparse,sys
    from backend.optimization.validate_simulation import main as evaluate
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['scenarios'],default='scenarios')
    parser.add_argument('--phase',choices=['develop','final'],default='develop')
    args=parser.parse_args()
    sys.argv=[sys.argv[0],'--phase',args.phase]
    evaluate()

if __name__=='__main__': main()
