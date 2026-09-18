# AirSentinel submission package

This package is the reviewable, secret-free AirSentinel hackathon prototype. It contains the three local interfaces, private FastAPI source, tests, Google Cloud deployment scaffolding, reviewed aggregate/example data, final documentation, Word report and pitch deck.

## Scope and truth boundary

- Najafgarh contains 7,516 stored PM2.5 fallback rows over 181.9 days with 86.1% completeness and two reporting stations.
- Safdarjung Enclave contains 7,889 stored PM2.5 fallback rows over 181.9 days with 90.4% completeness and two reporting stations.
- PM2.5, PM10, NO2, O3, SO2 and CO are represented in the locality evidence contract.
- OpenAQ is a labelled historical-development fallback. It is not presented as an authorised CPCB archive.
- CPCB/data.gov.in remains the preferred Indian current-data path when authorised credentials are supplied.
- Forecasts, uncertainty ranges and anomaly cases are historical prototype decision support, not official AQI or live alerts.
- The submission does not promote deep learning or federated learning.

## Run locally

Create a Python 3.11 virtual environment, install `requirements-dev.txt`, and open separate terminals for the services:

```bat
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m streamlit run authority_app.py --server.port 8502
.\.venv\Scripts\python.exe -m streamlit run citizen_app.py --server.port 8503
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

The production authority interface is intentionally view-only. Production writes must go through the authenticated private API and a reviewed durable audit store.

## Intentionally excluded

The archive excludes `.env`, keys, service-account files, Git metadata, virtual environments, `node_modules`, raw observations, citizen report logs, authority action audit logs, trained binaries, large feature tables, render/inspection output, and the retired experimental federated demonstration.

## External owner steps

The team must still create and configure its Google Cloud/Firebase project, add secrets through Secret Manager, obtain authorised CPCB/data.gov.in access, deploy and test Cloud Run URLs, create/push the GitHub repository, and record the demo video. No external account action or live URL is fabricated in this package.
