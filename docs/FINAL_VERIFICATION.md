# Final verification record

**Review date:** 26 August 2026  
**Project folder:** `C:\Users\Rupesh\AirSentinel\AirSentinel`

## Verified local system

- Python 3.11 environment and pinned runtime/development requirements.
- Public, citizen and production-view-only authority Streamlit applications plus FastAPI.
- Six-pollutant observation contract: PM2.5, PM10, NO2, O3, SO2 and CO.
- Najafgarh PM2.5 fallback evidence: 7,516 rows, 181.9 days, 86.1% completeness and two reporting stations.
- Safdarjung Enclave PM2.5 fallback evidence: 7,889 rows, 181.9 days, 90.4% completeness and two reporting stations.
- Direct 1-, 3- and 4-hour historical prototype candidates, empirical uncertainty and cause-unverified anomaly review.
- Fail-closed production access checks, human-review-only authority actions and disabled-by-default Google adapters.
- Public Cloud Run builds use a temporary reviewed aggregate allowlist; authority queues, moderation summaries, features, raw data and secrets cannot enter that image.
- OpenAQ remains visibly labelled as historical-development fallback; it is never upgraded to an authorised CPCB archive.
- Deep-learning and federated-learning approaches are not promoted.

## Test and build evidence

- `38/38` offline tests passed, including real in-process ASGI request-boundary checks.
- The same `38/38` tests passed after extracting the curated submission ZIP to a clean temporary directory.
- All four packaged application modules imported successfully from the extracted archive.
- `pip check` passed for the project virtual environment.
- Python compile check passed for `src`, `app.py`, `authority_app.py` and `citizen_app.py`.
- Deployment PowerShell scripts parsed successfully.
- Final Word report: eight pages rendered to images and every page visually inspected; no clipping or unreadable layout found.
- Final pitch deck: 11 slides rendered and visually inspected; the official slide overflow test reported no overflow.
- Submission archive: 146 allowlisted source/artifact files, approximately 1.2 MB, with no `.env`, service-account file, key, JSONL report/audit log, raw data, model binary, virtual environment, `node_modules`, render output or federated demonstration.

## Final artifacts

- `AirSentinel_Submission_Package.zip`
- `docs/AirSentinel_Final_Project_Report.docx`
- `docs/AirSentinel_Final_Project_Report.pdf`
- `docs/AirSentinel_Hackathon_Pitch_Deck.pptx`

## External actions not claimed

- CPCB/data.gov.in live response: an authorised key or approved export was not supplied.
- Google Cloud/Firebase/Earth Engine: no team-owned project, billing identity or production credentials were supplied.
- Cloud Run URLs: `gcloud` is not installed and authenticated in this environment.
- GitHub: the local repository has no commit and no configured remote.
- Demo video: human narration and screen recording are still required.

These account-bound items remain explicitly open in the submission checklist; no URL, partnership, approval or production status is fabricated.
