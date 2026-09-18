# AirSentinel team handoff

## One-sentence goal

AirSentinel helps a verified human reviewer move from national/city visibility to a specific locality evidence gap or unexpected pollution event, with one-to-four-hour warning, provenance, uncertainty and an auditable sustainable response.

## Current truth

- The local prototype pipeline has completed its saved-artifact test flow.
- Najafgarh and Safdarjung have 181.9 days of six-pollutant fallback history and meet the data gate to enter a controlled conventional baseline comparison; neither has a confirmed current historical evaluation or operational promotion.
- The historical source is OpenAQ and is labelled development fallback; it is not presented as an authorised CPCB archive.
- A CPCB/data.gov.in current-data connector is present but cannot run without an authorised API key.
- Google integrations are implemented as feature-flagged adapters and deploy scripts; none is claimed live without a GCP project and credentials.
- The local authority workflow is human reviewed and auditable; production privacy and identity enforcement require the team-owned cloud configuration.
- Deep learning and federated learning are not submission features and are not promoted.

## Main components

- `app.py` — reviewed public aggregate dashboard.
- `citizen_app.py` — consented coarse-area text/photo/voice evidence interface.
- `authority_app.py` — private review queue and audited human actions.
- `src/api/main.py` — FastAPI contracts, readiness and guarded integrations.
- `src/data/` — source discovery, collection, validation, coverage and locality evidence.
- `src/models/` — conventional historical forecast comparison and readiness gates.
- `src/scoring/` and `src/authority/` — unexpected-spike/evidence-gap cases and review queue.
- `src/cloud/` and `src/services/` — Firebase, BigQuery, Gemini, Maps, Earth Engine and language adapters.
- `deploy/` — least-privilege GCP bootstrap and Cloud Run deployment.
- `docs/` — report, phases, source policy, flowcharts, pitch deck, Word report and demo materials.

## Exact data milestone

| Locality | PM2.5 rows | Span | Completeness | Stations | Six pollutants |
|---|---:|---:|---:|---:|---:|
| Najafgarh | 7,516 | 181.9 days | 86.1% | 2 | yes |
| Safdarjung Enclave | 7,889 | 181.9 days | 90.4% | 2 | yes |

Keep the phrase **nearby-station proxy** until physical station placement and locality geometry are approved.

## Local verification commands

```bat
cd C:\Users\Rupesh\AirSentinel\AirSentinel
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src app.py authority_app.py citizen_app.py
.\.venv\Scripts\python.exe src\data\report_multiscale_coverage.py
.\.venv\Scripts\python.exe src\models\report_model_promotion_readiness.py
```

## Team tasks that require ownership

1. **Cloud owner:** create/select GCP project, billing, region, service identities and secrets; run deploy scripts.
2. **Data owner:** obtain CPCB/data.gov.in key/current access and request approved historical export plus calibration/uptime metadata.
3. **Governance owner:** approve locality geometry, consent, retention, moderation, reviewer roles and escalation policy.
4. **Release owner:** scan/push GitHub, run identity/deployed-link tests and insert final URLs.
5. **Demo owner:** record the 3–5 minute walkthrough from `docs/DEMO_VIDEO_SCRIPT.md`.

## Non-negotiable claims

- Historical prototype, not official AQI.
- Cause unverified, not pollution-source attribution.
- Human review required, not automatic enforcement.
- Fallback data visibly labelled.
- Satellite/photo/purifier/community evidence is context only.
