# AirSentinel Data Improvement Status

**Verified against saved artifacts on 26 August 2026.**
This report describes development data and historical prototype outputs. It does not establish a live government integration, official AQI, a validated pollution cause, or operational deployment readiness.

## Current data position

AirSentinel now has a resilient, provenance-preserving OpenAQ historical collection path and a separately archived CPCB/data.gov.in current snapshot. The latest snapshot was collected successfully on 26 August 2026; it is source-published current data, not a historical training archive or a continuously live integration. The project is still in the data-improvement and historical-validation stage.

The primary design remains:

1. use authorised CPCB/data.gov.in or approved SPCB data for current and historical official-source records;
2. archive every accepted official snapshot with its original metadata;
3. use OpenAQ only as an explicitly labelled development fallback while official historical access is unavailable;
4. report locality coverage gaps rather than turning a nearby station into a local fact; and
5. keep human review between a model/evidence signal and any operational decision.

## Verified saved artifacts

| Artifact | Verified state |
| --- | --- |
| data/raw/multiscale_pollutant_history.csv | Present; 168,839 saved rows; last modified 26 August 2026 01:08 local time. |
| data/processed/multiscale_coverage_report.csv | Present; 78 area-pollutant coverage rows; last modified 26 August 2026 01:08 local time. |
| data/processed/model_promotion_readiness.csv | Present; 13 model-promotion readiness rows. |
| data/raw/cpcb_realtime_snapshot.csv | Present; 139 target-pollutant current-snapshot rows archived on 26 August 2026. |
| data/raw/cpcb_snapshot_archive | Present; immutable raw response archived as `cpcb_snapshot_20260826T182106Z.json`. |
| data/processed/cpcb_realtime_snapshot_coverage.csv | Present; 95 stations across 62 cities and eight states, reported by city/pollutant only. |
| data/processed/cpcb_realtime_snapshot_quality_report.csv | Present; 139 rows checked, 9 missing average values, 5 pollutants returned, and no unit field in the API response. |

The successful archive confirms that the connector and authorised key can retrieve one source-published current snapshot. It does **not** establish an always-live CPCB integration, an official AQI publication, verified units, a 180-day historical archive, or a locality-level claim. The missing unit field and nine missing average values need source-metadata and field-QA review before use beyond availability reporting.

## Historical fallback metrics

The saved historical file contains two OpenAQ-derived labels:

| Source label in saved file | Rows | Policy meaning |
| --- | ---: | --- |
| OpenAQ development connector | 76,056 | Legacy development/fallback data; not official ingestion. |
| OpenAQ v3 historical fallback | 92,783 | Current resilient development fallback; upstream provider, licence, unit, and QA must still be verified. |
| **Total** | **168,839** | Development history only; do not relabel any rows as CPCB/SPCB official records. |

Across the 78 coverage rows, the available history spans from **22.3 to 181.9 days**. Twelve coverage rows now meet the stored long-history evidence threshold, but this is only an eligibility gate for a controlled, non-deep comparison. It is not an official-data, operational, or model-promotion result.

## Locality PM2.5 coverage snapshot

These locality names are pilot anchors and nearby-station proxies, not verified monitor locations or official neighbourhood observations.

| Area | PM2.5 hourly rows | Reporting stations | History span (days) | Completeness | Advanced gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Mehrauli pilot area | 1,333 | 2 | 29.9 | 92.8% | Not ready |
| Najafgarh pilot area | 7,516 | 2 | 181.9 | 86.1% | Eligible for controlled non-deep comparison; not promoted |
| Rohini pilot area | 1,365 | 2 | 29.9 | 95.1% | Not ready |
| Safdarjung Enclave pilot area | 7,889 | 2 | 181.9 | 90.4% | Eligible for controlled non-deep comparison; not promoted |

Najafgarh and Safdarjung Enclave now meet the saved long-history, completeness, and station-count thresholds. They still have **no confirmed historical evaluation** in the current promotion report. They must pass provenance, station-geometry, unit, weather-join, leakage-safe chronological validation, and baseline comparison checks before any advanced-model consideration. Deep and federated models remain unpromoted.

## Model evidence gate

| Gate | Current result |
| --- | --- |
| Coverage combinations marked deep_model_ready | 12 of 78 |
| Areas in model-promotion readiness report | 13 |
| Areas eligible for controlled non-deep comparison | 2 of 13 |
| Areas promoted for advanced/deep/federated use | 0 of 13 |
| Recorded advanced-model result | 2 evidence gates passed for controlled non-deep comparison; 11 long-history gates not met; no advanced/deep/federated model promoted |

Stored locality forecast files and historical model outputs are research artifacts only. Some were generated before the latest extended history refresh; they must be rerun after data-quality review rather than interpreted as current performance evidence. A promising held-out result does not prove readiness for a government operational workflow.

## What has been implemented

- A multi-pollutant collection configuration covering PM2.5, PM10, NO2, O3, SO2, and CO where upstream availability permits.
- A 180-day target collector with 14-day chunks, pagination, bounded retries/backoff, and diagnostics.
- Per-record provenance, location-precision, evidence-tier, source-licence, regulatory-use, and collection-status fields.
- Coverage, model-promotion, locality-evidence, anomaly-review, and human authority-queue safeguards.
- A separate CPCB/data.gov.in snapshot connector that preserves raw payloads, retries temporary portal failures, uses smaller pages and explicitly states its historical limitation.
- A CPCB current-snapshot quality/coverage report that keeps current source availability separate from the historical modelling dataset.
- Conservative language in the pipeline that blocks automatic enforcement and source attribution.

## Priority data-improvement work

1. Obtain authorised access to the CPCB/data.gov.in resource and run the snapshot collector on a controlled schedule.
2. Seek an approved CPCB or relevant State Pollution Control Board historical export for the pilot locations. Preserve the written access/redistribution terms.
3. Build an approved locality geometry and station-to-locality mapping. Replace generic pilot anchors with documented wards, grids, or station service areas.
4. Verify pollutant units, averaging periods, timezone handling, sensor/station identities, duplicates, uptime, and calibration metadata.
5. Continue history collection beyond 180 calendar days for every pilot and rerun coverage and promotion-readiness reports. Treat the current 181.9-day fallback result as a data candidate, not a final evidence base.
6. Create leakage-safe chronological train/validation/test splits, compare persistence and gradient-boosted baselines first, then evaluate a more complex model only if the baseline and data gates are met.
7. Add contextual IMD weather, approved satellite/fire data, and moderated opt-in community evidence without treating them as proof of a local source.
8. Run a human-review simulation for data gaps and residual spikes. Document that review is required before any public or authority action.

## Best alternatives while official historical access is unavailable

- **OpenAQ:** development-history fallback only, with retained source and licence metadata.
- **State-board public reports:** use only where a published download/API and usage conditions permit it; do not scrape undocumented or CAPTCHA-protected services.
- **IMD-authorised weather:** preferred for official weather context; reanalysis can support development but not replace a monitor.
- **IITM/MoES SAFAR and approved satellite/fire sources:** use for forecasting or contextual review, not locality-source proof.
- **Opt-in community and indoor-device reports:** retain consent, coarse location, moderation, and a strict indoor/supporting-evidence label.

## Current decision limit

Until approved official history, verified station-locality geometry, quality checks, and independent chronological evaluation are complete, AirSentinel may show:

- data availability and coverage gaps;
- historically evaluated prototype forecasts with uncertainty;
- review-needed anomaly cases; and
- recommended human verification steps.

It must not show an official AQI, claim a live government feed, identify a pollution source or responsible party, automate an enforcement action, or publish a locality-level alert as fact.
