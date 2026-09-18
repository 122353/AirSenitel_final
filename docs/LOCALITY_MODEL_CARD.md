# AirSentinel locality forecast model card

**Historical-evaluation artifact:** 25 August 2026
**Promotion-status snapshot:** 26 August 2026

The evaluation table below is a stored historical-prototype artifact. Its promotion rows have been reconciled with the current model-promotion readiness CSV; meeting a coverage gate does not mean a new model has been trained, selected, or approved.

## Purpose

AirSentinel evaluates short-horizon PM2.5 research forecasts for configured Delhi pilot anchors. Each pilot uses nearby-station proxy measurements and weather context. The outputs support human review only; they are not official AQI, live alerts, source attribution or enforcement decisions.

## Selection protocol

For a locality and horizon with enough leakage-safe rows, persistence and Histogram Gradient Boosting are compared using training-only time-series cross-validation. The candidate with the lower training-only cross-validation MAE is selected, then evaluated once on the newest chronological hold-out period. The hold-out period is not used to choose a candidate.

## Historical evaluation results

| Locality | Horizon | Selected candidate | Persistence hold-out MAE | Gradient boosting hold-out MAE | Evaluation rows |
|---|---:|---|---:|---:|---:|
| Mehrauli pilot area | 1h | Persistence baseline | 6.78 | 6.27 | 338 |
| Mehrauli pilot area | 3h | Persistence baseline | 11.74 | 11.13 | 323 |
| Mehrauli pilot area | 4h | Histogram gradient boosting | 12.25 | 11.02 | 316 |
| Najafgarh pilot area | 1h | Not selected — no confirmed historical evaluation | n/a | n/a | 224 |
| Najafgarh pilot area | 3h | Not selected — no confirmed historical evaluation | n/a | n/a | 207 |
| Najafgarh pilot area | 4h | Not selected — no confirmed historical evaluation | n/a | n/a | 202 |
| Rohini pilot area | 1h | Histogram gradient boosting | 8.60 | 7.45 | 385 |
| Rohini pilot area | 3h | Histogram gradient boosting | 12.50 | 9.82 | 371 |
| Rohini pilot area | 4h | Histogram gradient boosting | 13.59 | 9.48 | 363 |
| Safdarjung Enclave pilot area | 1h | Not selected — no confirmed historical evaluation | n/a | n/a | 151 |
| Safdarjung Enclave pilot area | 3h | Not selected — no confirmed historical evaluation | n/a | n/a | 135 |
| Safdarjung Enclave pilot area | 4h | Not selected — no confirmed historical evaluation | n/a | n/a | 131 |

## Promotion gates

| Locality | Historical evaluation | Advanced-model gate |
|---|---|---|
| Mehrauli pilot area | Historical prototype evaluated — not operational | Blocked — advanced model evidence gate not met |
| Najafgarh pilot area | No confirmed historical evaluation | Evidence gate passed for controlled non-deep comparison — not promoted |
| Rohini pilot area | Historical prototype evaluated — not operational | Blocked — advanced model evidence gate not met |
| Safdarjung Enclave pilot area | No confirmed historical evaluation | Evidence gate passed for controlled non-deep comparison — not promoted |

## Known limitations and required controls

- Pilot anchors are configured locations, not certified ward boundaries or monitors.
- Nearby-station proxy evidence must be checked for freshness, distance, provider coverage and unit consistency before an operational interpretation.
- A hold-out residual can create a human-review case, but cannot identify a source such as traffic, industry or agricultural burning.
- Najafgarh and Safdarjung Enclave meet the initial 180-day coverage gate for a controlled conventional comparison only. Neither has a confirmed current chronological evaluation, and neither is operational.
- The evidence is still insufficient for deep/spatiotemporal or federated-model promotion. Those approaches are not submission features and require substantially broader approved, geographically diverse, quality-controlled history.
- Every external action requires an authorised human process outside this prototype.
