# Ontario benchmarking preparation — NOT calibrated or validated

Status: definition mapping only, reviewed 2026-11-01. No CIHI/NACRS or Ontario
aggregate values were ingested, fitted, or used as performance targets.

The corrected model is a reproducible synthetic stress-test platform. It is not
yet an Ontario ED performance model. In particular, the configured Normal arrival
rates may overload its beds; a scenario name is not evidence of realism.

## Definitions consulted

- [CIHI: time to physician initial assessment](https://www.cihi.ca/en/indicators/emergency-department-wait-time-for-physician-initial-assessment): uses the earlier of registration or triage as the start and initial physician assessment as the end; reports hours and percentile statistics.
- [CIHI: total ED time for admitted patients](https://www.cihi.ca/en/indicators/total-time-spent-in-emergency-department-for-admitted-patients): ends when the admitted patient leaves the ED. An ICU treatment completion time is not this endpoint.
- [CIHI: NACRS visits and length-of-stay release](https://www.cihi.ca/en/nacrs-emergency-department-visits-and-lengths-of-stay): candidate source for a separately selected Ontario reporting period and population. No values from this release are used here.

## Mapping and gaps

| Construct | Current simulation | Required before benchmark comparison |
|---|---|---|
| Arrival volume | Poisson CTAS-specific rates × normalized hourly shape × weekday effect | Ontario facility/peer-group scope, year, coverage, visit denominator, seasonality; provincial totals cannot be assigned to one synthetic ED |
| CTAS | Sampled urgency 1–5, available to bed scheduling after nurse triage | Validate final triage distribution and exclusions against selected source; this does not validate clinical scoring |
| Initial physician wait | service_start − arrival; arrival is assumed registration, nurse triage begins afterward | Validate registration/triage semantics, provider eligibility, missing/invalid records and exact fiscal-year methodology |
| Discharged ED time | departure − arrival for ED-pool discharge-intent patients; median/P90 exported separately by CTAS 1–3 and 4–5 | Align discharge definitions, inclusions, percentile algorithm and population; disposition is currently a synthetic flag |
| Admitted ED time | NOT implemented; admit_intent_system is only whole simulated system time | Add ED care → admission decision → inpatient/ICU bed request → actual ED departure; measure boarding separately; do not substitute ICU service time |
| ICU pathway | Fixed routing to a distinct ICU resource pool | ICU patients in actual ED cohorts need an ED/inpatient transition model |
| Utilization | Integral of occupied simulated beds / available bed-minutes over fixed arrival window | Validate staffed/available capacity and observation window from a capacity source; do not infer utilization from a LOS aggregate |
| Tail waits | Per-run median/P90, all patients followed to completion | Match population/period, abandonment and censoring policy; mean of seed P90s is NOT a pooled Ontario P90 |

## Planned separate stage

1. Choose a specific Ontario facility/peer group, fiscal year, release and population.
   Save exact source URLs, downloaded aggregate files, retrieval dates, hashes,
   units, suppression notes, exclusions and definitions. Record unavailable
   quantities rather than filling them with guesses.
2. Implement the missing admitted-patient/boarding pathway before comparing
   admitted ED LOS. Specify registration, triage, initial assessment, disposition
   decision and physical ED departure timestamps separately.
3. Select calibration and external validation periods/facilities before fitting.
   Match volume and CTAS/disposition mix first, then service/capacity parameters.
   Do not fit simultaneously to a benchmark and label agreement with it validation.
4. Predeclare discrepancy tolerances and sensitivity analysis. Aggregate medians
   and P90s alone do not identify arrival distributions, service distributions,
   staffing schedules or causal scheduling benefits.
5. Report out-of-sample discrepancy, uncertainty, case-mix differences and structural
   limitations. Preserve this synthetic experiment and the earlier negative results.

No clinical safety, policy effectiveness or real-hospital improvement claim follows
from model verification. The current nurse and physician roles, diagnostic servers,
fixed capacities and finite arrival horizon are explicit simplifications, not
Ontario staffing standards.
