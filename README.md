# VayuNirikshak — evidence-aware India air-quality network (v2.1)

**Current entrypoint:** React in `dashboard/`, FastAPI in `backend/main.py` and `src/api/operational.py`. The older Streamlit/GCP description below is historical, not a statement of the v2 deployment or connected integrations. The insecure demonstration `/v1` API is retired (HTTP 410).

The rebuild includes India-wide OpenAQ station discovery, pollutant history, chronological ridge-versus-persistence forecast comparison, a pitched geographic map, separate citizen reporting and an authority-authenticated review workflow. It does not invent neighbourhood AQI, sensor coverage or confirmed pollution sources.

## Run the current application

Use Python 3.11+ and Node.js 22.12+ or a supported newer release:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ./backend
npm.cmd --prefix dashboard ci --ignore-scripts
.\.venv\Scripts\python.exe scripts/dev_v2.py --env-file PRIVATE_ENV_PATH --check
.\.venv\Scripts\python.exe scripts/dev_v2.py --env-file PRIVATE_ENV_PATH --initialize-store
.\.venv\Scripts\python.exe scripts/dev_v2.py --env-file PRIVATE_ENV_PATH
```

Open `http://localhost:3000`. Ctrl+C stops both services. The helper explicitly selects local SQLite; `--store postgres` requires `DATABASE_URL`. It never silently substitutes local storage in production.

Private configuration needs `CLERK_SECRET_KEY`, `VITE_CLERK_PUBLISHABLE_KEY` (or `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`) and `AUTHORITY_ALLOWED_EMAILS`. Add `OPENAQ_API_KEY` for current API access. Only the Clerk **publishable** key belongs in a `VITE_` browser variable. Keep all secrets in ignored private files, never source control.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*v2.py' -v
npm.cmd --prefix dashboard run build
npm.cmd --prefix dashboard audit
```

See [the current rebuild/runbook](docs/REBUILD_STATUS.md), [evidence engine](docs/EVIDENCE_ENGINE.md), [security](docs/SECURITY_V2.md) and [registered-device integration](docs/DEVICE_INGESTION.md). A successful local build does not by itself mean a cloud release is live.

## Historical project description (pre-v2; reference only)

VayuNirikshak (formerly AirSentinel) is an India-first, locality-aware clean-air and climate-resilience decision-support prototype for **BRICS Track 2 — Clean Air & Climate Resilience** and the **Sustainability** theme.

It joins outdoor monitoring, weather, contextual satellite layers, privacy-minimised citizen evidence, short-horizon forecasts and anomaly review. The goal is to help a human authority reviewer identify **where evidence needs attention and what to verify next**—without inventing locality AQI, blaming a source, or automating enforcement.

> **Status:** the local end-to-end prototype works. Google Cloud deployment is fully scaffolded but cannot be activated without a team-owned GCP project, billing, identities and credentials. OpenAQ is currently the labelled historical-development fallback; CPCB/data.gov.in is the preferred official current-data source when the team supplies authorised access.

## What is implemented

- Public, citizen and authority Streamlit applications plus a FastAPI backend.
- Eight-city overview and separate Delhi locality pilot anchors.
- Six-pollutant observation contract: PM2.5, PM10, NO2, O3, SO2 and CO.
- Approximately 182 days of historical fallback evidence for Najafgarh and Safdarjung, each using two reporting stations.
- Leakage-safe historical 1-, 3- and 4-hour PM2.5 forecast candidates with chronological hold-outs and empirical uncertainty.
- Unexpected-spike and evidence-gap cases that always remain **cause unverified** until human review.
- Privacy-minimised citizen text/photo/voice contracts and guarded Gemini, translation, speech and text-to-speech adapters.
- BigQuery, Firebase, Google Maps, Earth Engine and Cloud Run integration code with opt-in feature flags and fail-closed production authentication.
- Secure Docker and deployment scripts, deny-by-default Firebase rules, tests, runbooks, flowcharts, Word report and pitch deck.

The submission does **not** promote a deep-learning or federated-learning model. A conventional model may be hosted on Vertex AI only after it beats a simple baseline on approved, quality-controlled data and passes human governance review.

## Start locally

Run each long-lived application in a separate Command Prompt:

```bat
cd C:\Users\Rupesh\AirSentinel\AirSentinel
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m streamlit run authority_app.py --server.port 8502
.\.venv\Scripts\python.exe -m streamlit run citizen_app.py --server.port 8503
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

API documentation: `http://localhost:8000/docs`.

## Refresh the evidence and model outputs

```bat
cd C:\Users\Rupesh\AirSentinel\AirSentinel
.\.venv\Scripts\python.exe src\data\report_multiscale_coverage.py
.\.venv\Scripts\python.exe src\data\build_locality_evidence_profile.py
.\.venv\Scripts\python.exe src\models\report_model_promotion_readiness.py
.\.venv\Scripts\python.exe src\run_locality_model_and_review_refresh.py
```

The long-history downloader is intentionally explicit because it makes external API calls:

```bat
.\.venv\Scripts\python.exe src\data\fetch_multiscale_pollutant_history.py --areas DEL_NAJ DEL_SFE --days 182 --pollutants pm25 pm10 no2 o3 so2 co
```

## Trust and safety rules

1. CPCB/data.gov.in or another authorised Indian source is the production target; OpenAQ is a provenance-labelled development fallback.
2. Satellite, weather, photographs, purifier readings and citizen reports are supporting context—not proof of a source.
3. A nearby-station result is a proxy, not a monitor physically inside the named locality.
4. Public and authority outputs must preserve uncertainty, provenance and data freshness.
5. Production citizen endpoints require verified identity; authority routes require stronger reviewer identity; every action is audited.
6. Never commit `.env`, API keys, service-account files, raw reports, audit logs or raw source downloads.

## Project documents

- [Final project report](docs/FINAL_PROJECT_REPORT.md)
- [Phases and ownership](docs/PROJECT_PHASES.md)
- [Workflow diagrams](docs/FLOWCHARTS.md)
- [Data source and fallback policy](docs/DATA_SOURCE_AND_FALLBACK_POLICY.md)
- [Official data source catalogue](docs/OFFICIAL_DATA_SOURCE_CATALOG.md)
- [Google Cloud deployment guide](deploy/README_GOOGLE_CLOUD.md)
- [Demo video script](docs/DEMO_VIDEO_SCRIPT.md)
- [Submission checklist](docs/SUBMISSION_CHECKLIST.md)
- [Final verification](docs/FINAL_VERIFICATION.md)

## Account-bound work still required

The team must create/select the Google Cloud project, enable billing, choose a region and retention policy, authenticate `gcloud`/Firebase/Earth Engine, add Secret Manager values, run the deployment scripts, test the generated URLs, create/push the GitHub repository and record the demo video. The repository does not pretend those external actions have already happened.

