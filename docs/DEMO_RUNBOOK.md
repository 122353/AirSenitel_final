# AirSentinel demo runbook

## Start the four local services

Use separate Command Prompt windows from the project directory:

```bat
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m streamlit run authority_app.py --server.port 8502
.\.venv\Scripts\python.exe -m streamlit run citizen_app.py --server.port 8503
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
```

## Three-to-five minute demo order

1. **Problem (20 seconds):** city-wide visibility can miss a locality event or a sudden forecast failure.
2. **Public dashboard (40 seconds):** show the India overview, six-pollutant/locality evidence and any stored 1h/3h/4h historical research forecast with uncertainty.
3. **Data trust (30 seconds):** show Najafgarh and Safdarjung’s 181.9-day fallback coverage, explain official-current versus historical-fallback labels, and state that their next step is controlled conventional evaluation.
4. **Unexpected spike (45 seconds):** open one case, state “cause unverified”, and show the recommended corroboration checks.
5. **Authority review (45 seconds):** authenticate in the local demo, record a review action and show the audit state. State that no alert or enforcement is automatic.
6. **Citizen evidence (40 seconds):** submit a consented coarse-area report or photo/voice example. Show that it remains unverified supporting evidence.
7. **Google architecture (30 seconds):** explain Firebase identity/storage, BigQuery analytics, Gemini photo/explanation, Maps/Earth Engine context, language services and Cloud Run separation.
8. **Close (20 seconds):** explain what is working locally and what requires team-owned GCP/GitHub credentials.

## Required phrases

- “historical prototype forecast”
- “nearby-station proxy”
- “cause unverified”
- “human review required”
- “not official AQI or automated enforcement”

Do not claim a live CPCB partnership, a live BRICS connection, a deployed Google service, or official source attribution unless the team has verifiable evidence and a working URL.
