# GroundPulse: Test Plan (Design Stage)

Status: planned. No tests have been run yet. Results will be recorded here only after they happen.

## 1. Scope
Three incident categories: blocked or accessible roads, rescue requests, shelter capacity and occupancy.

## 2. Dataset
- Target: 300 to 500 controlled reports, manually labelled.
- Sources: simulated reports written to a fixed scenario script, and authorised public information. No personal data.
- Labels per report: true incident, duplicate of, contradicts, stale at time of review, labeller and date.
- Two labellers per report; disagreements resolved by a third reviewer. Record the agreement rate.
- Template: `GroundPulse_Test_Dataset_Template.csv` (contains an example row only; replace it with labelled data).

## 3. Metrics and targets (engineering targets, not results)

| Metric | Target | Method |
|---|---|---|
| Duplicate matching precision | at least 90% | Pairs predicted as duplicates vs labels |
| Contradiction detection F1 | at least 80% | Harmonic mean of precision and recall on contradiction labels |
| Stale-information detection | at least 95% | Stale flags vs labels at review time |
| Location resolution | at least 85% | Correct locality or admin area vs ground truth label |
| Triage-time reduction | at least 30% | Time to review an incident, system-assisted vs manual baseline, same reports |
| Source traceability | 100% | Every displayed claim links to at least one observation and timestamp |

## 4. Safety tests (must pass)
- No automatic dispatch: a test confirms no resource action is triggered without a human decision record.
- Low-confidence matches are routed to the verification queue, not merged.
- Areas with no recent observation display as UNVERIFIED, not safe.

## 5. Baseline
The manual workflow on the same reports, with time recorded per incident.

## 6. Reporting
Record date, dataset version, labeller agreement, each metric with its confidence interval, and every failure with its cause. Report failures as failures.

## 7. Limitations
- Simulated and public data may not reflect real field conditions.
- Results from the controlled set do not prove operational performance.
- Field validation with district response personnel is still pending.
