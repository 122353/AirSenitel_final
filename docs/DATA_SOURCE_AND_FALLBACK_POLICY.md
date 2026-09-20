# AirSentinel Data Source and Fallback Policy

**Status:** development and historical-prototype policy
**Scope:** India city and locality pilots, with an architecture that can later support interoperable BRICS deployments.

## Purpose

AirSentinel is designed to help human public-health and environmental teams identify areas that need further investigation. It is not an official AQI publisher, a regulatory monitoring network, a pollution-source attribution system, or an automated enforcement tool.

This policy prevents a common failure mode in air-quality prototypes: presenting an aggregated, delayed, or proxy measurement as though it were a fresh official locality observation. Every ingested record must retain its source, collection time, station identity, geographic precision, quality state, and permitted use.

## Non-negotiable claim boundary

- A model forecast is decision-support research, not a live alert or official AQI.
- A locality label is not proof that a monitor sits inside that locality.
- Satellite, weather, citizen reports, and purifier readings are contextual or supporting evidence; they do not independently prove an outdoor pollution source.
- A detected residual or anomaly is a review case, not a cause determination, violation finding, or enforcement instruction.
- No record may be relabelled as CPCB, SPCB, or official simply because OpenAQ exposes a station whose name contains an agency name.
- Sensitive personal details, household purifier telemetry, and unmoderated reports must not be exposed in an authority queue.

## Source priority and permitted use

| Priority | Source | Intended use | Current limitation |
| --- | --- | --- | --- |
| 1 | Authorised CPCB data.gov.in real-time AQI snapshot | Preferred current official-source station snapshot after source and unit checks | The published endpoint is a current hourly snapshot, not an assured 180-day historical archive. |
| 2 | Approved CPCB or State Pollution Control Board historical export | Model development after data-sharing approval, provenance checks, station QA, and chronological validation | Requires a documented licence/access path and station-level metadata. |
| 3 | OpenAQ v3 historical fallback | Development-only historical coverage while approved official history is unavailable | Third-party aggregation; upstream provider conditions and quality must be verified. It is never relabelled as official. |
| 4 | CAMS global atmospheric model via Open-Meteo | India-wide regional screening and a six-hour pre-spike watch when ground coverage is absent | Approximately 45 km model grid; not a station reading, official AQI, or microscopic measurement. |
| 5 | IMD-authorised weather, approved satellite or fire context | Weather covariates, plume or fire context, and human review support | Cannot prove a locality-level source or replace an outdoor monitor. |
| 6 | Opt-in community reports and connected-device signals | Supporting evidence and investigation triage after moderation | No AQI calculation, source attribution, enforcement, or personal-data publication. |

The repository source registry at data/reference/approved_data_source_registry.csv is the operational shortlist. It records the access method, owner, role, official-status wording, limitations, and canonical URL for each source. Adding a source to that registry is not the same as successfully collecting approved data from it.

## Official CPCB current-snapshot path

The repository contains the connector at src/data/fetch_cpcb_realtime_snapshot.py. It uses the Government of India data.gov.in CPCB real-time AQI resource:

- Catalogue: https://www.data.gov.in/catalog/real-time-air-quality-index
- Resource identifier used by the connector: 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69
- Credential name expected locally: CPCB_DATA_GOV_API_KEY
- Saved snapshot path: data/raw/cpcb_realtime_snapshot.csv
- Immutable raw-response archive directory: data/raw/cpcb_snapshot_archive

The connector is deliberately snapshot-oriented. A scheduler must collect and preserve successive snapshots to make a future archive, or the project must ingest an explicitly approved CPCB/SPCB historical export. It must not invent history by treating the latest endpoint response as past data.

Official-source snapshot checks before a record enters a decision-support view:

1. Confirm the resource, access conditions, timestamp, station identifier, pollutant unit, and field mapping.
2. Preserve the raw payload and the original record timestamp.
3. Retain the labels source_system, source_agency, source_url, source_license, quality_flag, regulatory_use, and historical_limit.
4. Mark missing or abnormal readings as needing review rather than silently imputing them.
5. Keep the publication wording as a source-published snapshot; AirSentinel does not certify, change, or recalculate an official reading.

## Approved historical-data path

An approved historical CPCB/SPCB export is the preferred route for serious model development. Before it is used, the team must document:

- written access authority, licence, permitted redistribution, and retention period;
- station coordinates, station type, instrument method, calibration or maintenance information where available;
- pollutant units, averaging period, timezone, duplicate policy, and missing-data semantics;
- whether the record is a station observation, city aggregate, modelled field, or manually entered report;
- provenance fields carried into the normalized dataset; and
- a chronological held-out test period that is not used for tuning.

The advanced-model evidence target is at least **180 complete calendar days** of PM2.5 history, at least 85% completeness, at least two reporting stations where the locality claim needs cross-station support, and evidence for the configured core pollutants. Passing a data threshold alone does not make a model operational.

## OpenAQ historical development fallback

The repository fallback collector is src/data/fetch_multiscale_pollutant_history.py. It is configured to attempt a 180-day lookback using bounded 14-day windows, pagination, retry/backoff, candidate-station selection, and a two-working-sensor cap per area and pollutant.

Fallback records are explicitly labelled as:

- source system: OpenAQ v3 historical fallback;
- source agency: upstream provider exposed through OpenAQ; verify before use;
- regulatory use: prohibited - development fallback only;
- location precision: nearby station proxy; and
- quality state: raw provisional input - source and unit QA required.

Older saved rows can carry the legacy label OpenAQ development connector. Both labels refer to development data, not official CPCB ingestion. The fallback enables pipeline development and historical validation experiments, but it cannot support a claim that AirSentinel has a live government feed or an official local AQI.

Where a fallback coverage row meets the 180-day data threshold, it is eligible only for a controlled non-deep comparison after its source, units, local geometry, weather join, and chronological split have been checked. A passed coverage gate does not upgrade OpenAQ data to an official source and does not promote a deep or federated model.

## Locality and proxy safeguards

The initial locality pilots are Mehrauli, Najafgarh, Rohini, and Safdarjung Enclave. Their anchors are planning references, not verified ward boundaries or proof that an outdoor monitor is physically located in the named locality.

Before displaying a local hotspot claim, the team must have all of the following:

1. approved locality geometry or a clearly disclosed grid/ward definition;
2. a fresh, quality-checked station observation with documented station distance and precision;
3. at least one independent corroborating signal where feasible;
4. source, time, unit, and missingness checks;
5. a human review of the evidence packet; and
6. conservative wording when evidence is incomplete.

The safe alternative is a coverage-gap or review-needed case. The system must not say that an industry, village, burning event, or named person caused a spike without verified evidence and authorised investigation.

## India-wide model fallback

The national intelligence routes support searching an Indian city, village or
postcode and screening the selected coordinate. When a nearby fixed OpenAQ
station is available and the server has authorised API access, its fresh
observation remains separate from the model output. When no qualifying monitor
is available, AirSentinel may show the CAMS global atmospheric-model estimate
and its next-six-hour trend with an explicit `model_estimate_only` state.

This fallback provides geographic continuity, not street-level truth. Its
approximately 45 km grid can miss brief traffic, construction, industrial,
waste-burning and neighbourhood events. Microscopic detection therefore
requires a local calibrated outdoor sensor cluster: at least two agreeing
devices in a 250 m inspection cell plus contemporaneous nearby background
devices under the private screening rules. Satellite imagery and citizen
reports may prioritise where to place or move sensors, but do not replace them.

## Weather, satellite, community, and purifier context

- **Weather:** Use IMD-authorised data when access is available. Reanalysis or Open-Meteo-style weather feeds are contextual development covariates, not a local monitor replacement.
- **Satellite or fire context:** Use approved Earth Engine, NASA FIRMS, or similar feeds as contextual indicators only. A satellite pixel or fire detection cannot independently assign a ground-level source.
- **Community reports:** accept only opt-in reports with moderation, duplicate/spam control, consent, and coarse location handling. Keep report evidence separate from regulated measurements.
- **Purifier or indoor-device readings:** require explicit owner consent, a documented vendor API or export, device calibration context, and privacy minimisation. Indoor readings must be labelled indoor/private and must never be merged into outdoor AQI or used as a proxy for a whole neighbourhood.

## Fallback operating states

| State | What AirSentinel may show | What it must not claim |
| --- | --- | --- |
| Official current snapshot available and validated | Source-published current station snapshot with provenance | That AirSentinel independently certifies the value, or that it is historical coverage. |
| Approved official historical export available | Historical research, coverage analysis, and held-out evaluation | Live alerting, causation, or enforcement based on a model alone. |
| Only OpenAQ history available | Historical prototype results and development coverage gaps | Official CPCB integration, operational readiness, or neighbourhood-level source proof. |
| No verified locality station, CAMS model available | Explicit regional model estimate, six-hour model trend, low-confidence pre-spike watch, and a request for local sensing | Official/local AQI, microscopic measurement, source proof, or enforcement claim. |
| No verified station or usable model | Coverage gap, requested-data status, moderated supporting reports | Local AQI, hotspot, or enforcement claim. |

## Required provenance fields

Every normalized measurement or evidence item must preserve, when applicable:

- area identifier and area type;
- station, sensor, or evidence identifier;
- latitude, longitude, station distance, and location-precision label;
- pollutant code, value, unit, averaging type, timezone, and observation timestamp;
- source system, source agency, source URL, source licence, collection timestamp, and collection status;
- quality flag, evidence tier, regulatory-use boundary, and raw-data-sharing boundary; and
- whether the record is a verified observation, a proxy, a model result, or a moderated report.

## Publication and model gates

The model-promotion report deliberately blocks advanced/deep/federated promotion until the saved data meets the long-history evidence gate. All user-facing and authority-facing outputs must preserve the following language where relevant:

> Historical prototype decision support only. Requires fresh quality-controlled inputs and human review before any operational use. This is not official AQI.

An authority queue may recommend a human review, data-quality check, or request for local verification. It must never automate enforcement, source attribution, or a public health order.

## Authoritative references

- CPCB Control Room for Air Quality Management: https://airquality.cpcb.gov.in/ccr/
- CPCB CAAQMS protocol: https://app.cpcbccr.com/ccr_docs/Protocol_CAAQM.pdf
- CPCB all-India CAAQMS list: https://app.cpcbccr.com/ccr_docs/caaqms_list_All_India.pdf
- Government of India data.gov.in CPCB real-time AQI catalogue: https://www.data.gov.in/catalog/real-time-air-quality-index
- IMD Data Supply Portal: https://dsp.imdpune.gov.in/
- IITM/MoES SAFAR Early Warning System: https://ews.tropmet.res.in/
- OpenAQ measurement documentation: https://docs.openaq.org/resources/measurements
- OpenAQ pagination documentation: https://docs.openaq.org/using-the-api/pagination
- Open-Meteo Air Quality API/CAMS model documentation: https://open-meteo.com/en/docs/air-quality-api

Do not scrape CAPTCHA-protected or undocumented government endpoints. If approved data access is unavailable, retain the fallback label and report the coverage gap instead of weakening provenance.
