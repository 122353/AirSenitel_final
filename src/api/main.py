import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import pandas as pd

from src.api.schemas import CaseActionInput, BRICSModelMetadata
from src.services.data_loader import (
    load_city_conditions, load_locality_profile, load_station_inventory,
    ensure_processed_dir, load_pollutant_history
)
from src.services.sensor_range import get_effective_coverage_area, EFFECTIVE_RANGES
from src.services.forecaster import forecast_pm25
from src.services.anomaly_detector import generate_case_queue
from src.services.case_audit import save_case_action
from src.services.brics_federation import registry as brics_registry

# Ensure processed dir exists on startup
ensure_processed_dir()

app = FastAPI(title="AirSentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8502", "http://localhost:8503"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.get("/api/v1/cities")
def get_cities():
    df = load_city_conditions()
    return df.to_dict(orient="records")

@app.get("/api/v1/localities")
def get_localities():
    df = load_locality_profile()
    return df.to_dict(orient="records")

@app.get("/api/v1/sensors")
def get_sensors():
    df = load_station_inventory()
    sensors = df.to_dict(orient="records") if not df.empty else []
    # Add effective range info
    return {"sensors": sensors, "effective_ranges": EFFECTIVE_RANGES}

@app.get("/api/v1/sensors/{station_id}/range")
def get_sensor_range(station_id: str, pollutant: str = "pm25"):
    df = load_station_inventory()
    if df.empty or station_id not in df['station_id'].values:
        raise HTTPException(status_code=404, detail="Station not found")
    
    station = df[df['station_id'] == station_id].iloc[0]
    coverage = get_effective_coverage_area(station['latitude'], station['longitude'], pollutant)
    return coverage

@app.get("/api/v1/forecasts/{area_id}")
def get_forecasts(area_id: str):
    history = load_pollutant_history(area_id)
    forecasts = forecast_pm25(area_id, history)
    return forecasts

@app.get("/api/v1/cases")
def get_cases():
    # In a real app we'd load these from actual history/forecasts
    df_obs = pd.DataFrame([{"area_name": "Delhi NCR", "pm25": 150.0}])
    df_fc = pd.DataFrame([{"area_name": "Delhi NCR", "predicted_pm25": 100.0, "empirical_interval_high": 120.0}])
    df_loc = load_locality_profile()
    
    cases = generate_case_queue(df_obs, df_fc, df_loc)
    return cases.to_dict(orient="records") if not cases.empty else []

@app.post("/api/v1/cases/{case_id}/actions")
def post_case_action(case_id: str, action: CaseActionInput):
    record = save_case_action(case_id, action)
    return record

@app.get("/api/v1/alerts")
def get_alerts():
    # Return dummy active alerts
    return [{
        "alert_id": "a1",
        "alert_type": "High Pollution",
        "severity": "high",
        "area_name": "Delhi NCR",
        "message": "PM2.5 exceeding dangerous levels",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "pollutant_code": "pm25",
        "value": 180.5,
        "threshold": 150.0
    }]

@app.get("/api/v1/live-data")
async def live_data():
    async def event_generator():
        while True:
            data = {"timestamp": datetime.utcnow().isoformat() + "Z", "city": "Delhi NCR", "pm25": 150.5 + (datetime.utcnow().second % 10)}
            yield {"event": "pollutant_update", "data": str(data)}
            await asyncio.sleep(5)
    
    return EventSourceResponse(event_generator())

@app.get("/api/v1/brics/models")
def list_brics_models():
    return brics_registry.list_models()

@app.post("/api/v1/brics/share")
def share_brics_model(model: BRICSModelMetadata):
    model_id = brics_registry.register_model(model)
    return {"status": "success", "model_id": model_id}
