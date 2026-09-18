# AirSentinel phases and team ownership

## Main goal

Build a working India-first platform that turns trustworthy local evidence into an early-warning review case for government and community teams. The system must work from city scale down to a defined locality, preserve uncertainty, handle sudden forecast failures, and require human verification before any response.

## Phase plan

| Phase | Purpose | Delivered in this repository | Account/team work still needed |
|---|---|---|---|
| 0. Foundation and safety | Reproducible Python project, secrets policy and clear non-claims | Environment templates, exclusions, tests, evidence language | Nominate data/privacy owner |
| 1. Trusted multi-scale data | Ingest six outdoor pollutants with provenance | Station discovery, canonical fields, source registry and quality checks | Obtain authorised CPCB historical export if available |
| 2. Long-history locality coverage | Build enough evidence for Najafgarh and Safdarjung | 181.9 days, two stations each, all six pollutants; PM2.5 completeness 86.1% and 90.4% | Validate station mapping/calibration with the relevant authority |
| 3. Forecast and spike detection | Give reviewers 1h/3h/4h lead time and catch sudden misses | Forecasting framework, uncertainty and historical residual cases; prior local prototype evaluations | Run controlled chronological conventional baselines for newly eligible Najafgarh/Safdarjung candidates, then re-evaluate on fresh approved data before live use |
| 4. Human authority workflow | Turn evidence into an accountable review task | Evidence-gap/unexpected-spike queues, reviewer actions, audit trail | Define official roles, service levels and escalation route |
| 5. Citizen and accessibility evidence | Accept privacy-safe reports without treating them as measurements | Text/photo/voice contracts, moderation, translation/STT/TTS adapters | Configure Firebase Auth, consent, retention and abuse response |
| 6. Google data and AI services | Add real Google services where they have a clear job | BigQuery/Firebase/Gemini/Maps/Earth Engine/language adapters and readiness checks | Create GCP project, enable APIs, add secrets and validate quotas |
| 7. Secure deployment | Make the demo reachable without exposing authority controls | Docker, private API/authority and public aggregate-dashboard scripts | Run Cloud Run deployment and test generated URLs with real identities |
| 8. Submission and governance | Produce an evaluable end-to-end package | Reports, flowcharts, pitch deck, demo script, checklists and tests | Push GitHub, record 3–5 minute video and insert deployed links |

## Suggested team split

- **Data lead:** official source access, station mapping, units, completeness and calibration evidence.
- **ML lead:** chronological evaluation, baseline comparison, uncertainty and drift monitoring.
- **Backend/cloud lead:** GCP IAM, Secret Manager, Firebase, BigQuery and Cloud Run.
- **Frontend/demo lead:** dashboards, multilingual flow, screenshots and demo recording.
- **Governance lead:** consent, retention, reviewer roles, non-claims and authority pilot approval.

## Definition of done

AirSentinel is ready for a controlled pilot only when approved current data is fresh, locality geometry and station mapping are reviewed, cloud identities are least-privilege, citizen evidence is moderated, a reviewer can close a case with an audit record, and the deployed links pass an end-to-end test. A good local metric alone is not enough.
