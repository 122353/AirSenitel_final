# AirSentinel final project report

**Track:** BRICS Track 2 — Clean Air & Climate Resilience
**Theme:** Sustainability
**Scope:** India-first, city-to-locality evidence and early-warning decision support
**Status:** working local prototype; cloud deployment awaits team-owned Google credentials and billing

## Executive summary

Major cities may publish useful macro-level air quality while a neighbourhood, village edge, industrial cluster or transport corridor experiences a different event. AirSentinel turns multi-source evidence into a locality review workflow: validate the evidence, forecast one to four hours ahead, detect a sudden mismatch, keep the cause unverified, and give an authorised human reviewer an auditable next step.

The system is not official AQI, a pollution-source attribution service, a medical device or automated enforcement. It is a working prototype that demonstrates how a safer government-facing workflow could be built.

## The problem being solved

Current monitoring and dashboards can leave four practical gaps:

1. **Scale gap:** a city average does not describe every ward or industrial edge.
2. **Coverage gap:** some localities do not have enough nearby, fresh, calibrated measurements.
3. **Forecast-failure gap:** burning, dust, traffic, an industrial event or sensor failure can create a sudden observation that the model did not expect.
4. **Coordination gap:** evidence from stations, weather, satellites and citizens is difficult to review consistently without provenance, uncertainty and ownership.

AirSentinel solves these workflow gaps rather than claiming to replace an existing regulator.

## What works now

- Public India overview, citizen-report interface, authority-review interface and FastAPI backend.
- Six-pollutant contract covering PM2.5, PM10, NO2, O3, SO2 and CO.
- Long-history historical-development collection with retry, pagination, deduplication, provenance and safe merging.
- Current CPCB/data.gov.in connector that remains disabled until an authorised API key is provided.
- 1-, 3- and 4-hour conventional research-forecast candidates, with chronological hold-outs and empirical uncertainty for stored evaluated pilot artifacts; newly eligible localities still require a controlled baseline evaluation.
- Unexpected-spike and evidence-gap cases with **cause unverified**, recommended corroboration and audit actions.
- Opt-in Gemini photo/explanation, Translation, Speech-to-Text, Text-to-Speech, Maps and Earth Engine context adapters.
- Firebase pending-review storage and BigQuery approved-analytics loader adapters.
- Local fail-closed access checks, plus least-privilege deployment scaffolds and deny-by-default Firebase client rules for a future configured project.

## Verified data improvement

The latest 181.9-day backfill used labelled OpenAQ-derived development fallback because no authorised CPCB historical export was available in this environment. For Najafgarh and Safdarjung Enclave it retained two reporting stations and all six target pollutants.

| Locality | PM2.5 saved hourly rows | History span | PM2.5 completeness | Reporting stations | Core pollutants present |
|---|---:|---:|---:|---:|---:|
| Najafgarh pilot area | 7,516 | 181.9 days | 86.1% | 2 | 6 of 6 |
| Safdarjung Enclave pilot area | 7,889 | 181.9 days | 90.4% | 2 | 6 of 6 |

This clears the repository’s long-history evidence gate for a **controlled conventional baseline comparison**. It does not make either locality operational and does not turn nearby-station evidence into a physical sensor inside the locality.

## Data trust strategy

### Preferred official Indian path

- [CPCB/data.gov.in real-time air-quality catalogue](https://www.data.gov.in/catalog/real-time-air-quality-index) for official current station observations when authorised access is configured.
- Formal CPCB/SPCB/PCC or authority export for historical data, calibration, uptime and station mapping when available.
- IMD-authorised meteorological data for a production pilot when access is approved.

### Best alternatives when approval/history is unavailable

- [OpenAQ](https://docs.openaq.org/) for historical development data, with the original provider and station provenance preserved and a visible fallback label.
- [Open-Meteo historical weather](https://open-meteo.com/en/docs/historical-weather-api) for development weather context, labelled as gridded/reanalysis context rather than a neighbourhood monitor.
- [Google Earth Engine Sentinel-5P](https://developers.google.com/earth-engine/datasets/catalog/sentinel-5p) and [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) only for contextual gas/aerosol/fire indicators—not surface PM2.5 or source attribution.

The full policy and source catalogue are in `docs/DATA_SOURCE_AND_FALLBACK_POLICY.md` and `docs/OFFICIAL_DATA_SOURCE_CATALOG.md`.

## Forecast and unexpected-event design

AirSentinel does not choose a complicated model for presentation value. It first compares persistence with a conventional tree-boosting candidate using time-ordered data. Each candidate is measured on a newest untouched hold-out and accompanied by an empirical error interval.

When a measured value differs sharply from the forecast, the system does not force the prediction to look correct. It creates a review case and asks the reviewer to check neighbouring stations, station freshness, sensor health, wind/rain, satellite/fire context and moderated community reports. The case remains **cause unverified** until corroborated.

The submission does not promote deep learning or federated learning. Vertex AI may later host a conventional candidate only after approved data, stable gains over persistence and governance review.

## Google technology jobs

| Google technology | Meaningful AirSentinel job | Current state |
|---|---|---|
| Gemini API / AI Studio | Guarded case explanation and in-memory photo description; never numeric AQI/source proof | Code complete, feature-flagged; secret required |
| Vertex AI | Optional managed hosting/monitoring for an approved conventional model | Readiness gate only |
| Firebase Auth / Firestore | Verified citizen identity and minimum pending-review metadata | ADC-ready adapter and deny-all client rules; project setup required |
| BigQuery | Governed coverage, readiness and reviewed analytical tables | Loader/bootstrap ready; dataset/IAM required |
| Google Maps | Reviewer map context for configured pilot anchors | Key-gated context helper; restricted key required |
| Earth Engine | Sentinel-5P NO2/CO/SO2/aerosol context around a locality | Context adapter ready; project registration required |
| Speech-to-Text | Convert consented voice evidence for moderation | Adapter ready; API/consent required |
| Translation | Translate report text into a reviewer language | Adapter ready; API/language QA required |
| Text-to-Speech | Read reviewed guidance accessibly | Adapter ready; API/language QA required |
| Dialogflow | Optional conversational front door if the hackathon explicitly requires it | Integration point documented; agent configuration external |
| Cloud Run | Private API and authority portal; public aggregate dashboard | Secure scripts ready; GCP auth/billing required |

## Security, privacy and human review

1. Production citizen submissions require a verified Firebase identity; authority endpoints require an authority role or trusted Cloud Run identity context.
2. Direct Firestore and Storage client access is denied by default.
3. Citizen storage excludes exact coordinates, raw media and unnecessary personal details; pending evidence has a 90-day review/retention policy placeholder.
4. Images are accepted only as bounded JPEG/PNG/WebP payloads and processed in memory by the helper.
5. Gemini and contextual services return constrained evidence summaries, not AQI, liability, enforcement or health decisions.
6. Every case action remains human initiated and auditable.
7. Secret values are excluded from source, image contexts and deployment arguments.

## Phase status

The project now uses phases 0–8 described in `docs/PROJECT_PHASES.md`. The repository contains the local implementation through submission preparation. Remaining items include controlled baseline evaluation for newly eligible locality candidates and external account/governance actions: authorised source access, GCP configuration, real identity tests, GitHub publication, deployed-link tests and demo recording.

## Known limitations

- The 182-day improvement is development-fallback data, not an approved government historical export.
- Pilot areas are anchor/proxy regions; their legal/administrative geometries and physical station relationships need authority validation.
- Current forecasts are historical research outputs, not live alerts.
- Satellite vertical-column products cannot be read as surface PM2.5.
- A photo, purifier/home sensor or citizen report may support review but cannot substitute for verified outdoor monitoring.
- The local file-based audit path is for development; Cloud Run needs Firestore/BigQuery persistence before operational use.
- No public or authority URL exists until the team supplies a GCP project and runs the deployment scripts.

## Submission package

Included:

- curated, independently tested `AirSentinel_Submission_Package.zip`;
- source code and tests;
- Markdown report, source policy, deployment guide and workflow diagrams;
- updated Word report;
- 10–12 slide pitch deck;
- 3–5 minute demo script and runbook;
- short project description and release checklist.

The archive uses an explicit allowlist. It excludes credentials, raw downloads, citizen/audit JSONL, trained binaries, large feature tables, virtual environments, render output and the retired federated experiment. Its packaged test suite passes 38 of 38 checks.

Account-bound completion:

- create/push the GitHub repository;
- configure and deploy the Google services;
- test the public and authority URLs with real identities;
- record the demo video and insert the final links.

## Short judge-facing message

> AirSentinel is a locality-aware clean-air early-warning and human-review platform. It combines provenance-labelled station measurements, weather, satellite context and consented community evidence to detect unsupported coverage and unexpected pollution changes, forecast one to four hours ahead, and guide an auditable sustainable response—without inventing hyper-local precision or automating blame.
