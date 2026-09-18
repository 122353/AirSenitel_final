# AirSentinel Government-Facing Pilot Requirements

## Purpose

AirSentinel is a proposed decision-support pilot design for CPCB/SPCB/PCC/ULB and district teams. It is not an approved government deployment or partnership. It is intended to complement official monitoring and NCAP workflows; it does not replace official AQI, statutory enforcement, laboratory confirmation, or human decision-making.

## Operator outcomes

An operator should be able to answer, for every case:

1. What changed, where, and when?
2. Which sources support the case and how fresh are they?
3. Is the spike forecasted, observed, unexpected, or data-unavailable?
4. What is the confidence level and what is still unknown?
5. Which response should be reviewed, by whom, and by when?
6. What action was taken and what happened afterwards?

## Case record: minimum fields

```text
case_id
created_at_utc
locality_id / grid_id / ward_id
location_precision
event_type
observed_pm25 / predicted_pm25 / forecast_residual
anomaly_score
data_freshness_minutes
evidence_summary
confidence_level
possible_contributors (hypotheses only)
recommended_next_step
owner_agency / assigned_to / due_at
review_status / action_taken / outcome
model_version / rule_version
```

## Evidence and escalation policy

- Verified outdoor stations are the strongest public-air evidence.
- Satellite/weather data are context, not source proof.
- Purifier/home-sensor data are opt-in indoor evidence and remain separate from outdoor AQI.
- A single anonymous report cannot trigger enforcement or claim a pollution source.
- A case can be escalated when verified station evidence exists, or when multiple independent lower-tier signals corroborate an unusual event.
- All automated output requires human review before external enforcement or public-source attribution.

## Pilot success measures

- Forecast MAE/RMSE for each horizon and locality.
- Anomaly precision, recall, and false-alert rate on held-out or simulated events.
- Percentage of observations with source, timestamp, freshness, and confidence fields.
- Data coverage by locality and evidence tier.
- Median time from anomaly detection to operator triage.
- Percentage of cases with recorded review/action/outcome.

## Mandatory safeguards

- No public display of resident address, account token, raw device identifier, or personally identifying report data.
- Consent, deletion, and withdrawal for all community/device data.
- Role-based authority access and immutable event/evidence snapshots.
- Source-health checks; no alert based solely on stale/failed API data.
- Model versioning, evaluation logs, uncertainty labels, and a manual override.
