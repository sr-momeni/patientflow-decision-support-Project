# Patient Flow MVP (Backend)

## Commands
- Generate synthetic data  
  `python -m backend.data.synthetic_generator --scenario normal --n 500 --seed 42 --out backend/data/raw/normal.csv`

- Run end-to-end runner  
  `python -m backend.main --scenario icu_bottleneck --n 200 --seed 1`

- Run tests  
  `pytest backend/tests -q`  
  or `python -m pytest backend/tests -q`

## Expected
- Scenarios validate, columns present, benchmark cases map to CTAS1/2/3 for first three injected patients.
- Runner prints: scenario name, avg wait/LOS (rough), ED/ICU utilization, overflow, ICU waitlist, alerts, and top 5 recommendations.
