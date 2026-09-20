import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd

from src.api.schemas import (
    CaseActionInput, BRICSModelMetadata, CaseDispatchInput, CitizenReportCreateInput,
    CommunityReportInput
)
from src.services.data_loader import (
    load_city_conditions, load_locality_profile, load_station_inventory,
    ensure_processed_dir, load_pollutant_history
)
from src.services.sensor_range import get_effective_coverage_area, EFFECTIVE_RANGES
from src.services.forecaster import forecast_pm25
from src.services.anomaly_detector import generate_case_queue
from src.services.case_audit import save_case_action
from src.services.community_reports import save_local_report, list_local_reports
from src.services.root_cause_ai import diagnose_spike_cause
from src.services.benchmark_evaluator import (
    get_government_benchmark_metrics, get_brics_interoperability_comparison
)
from src.services.brics_federation import registry as brics_registry

# Ensure processed dir exists on startup
ensure_processed_dir()

app = FastAPI(title="AirSentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",
        "http://localhost:8502",
        "http://localhost:8503",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
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
    from pathlib import Path
    case_path = Path("data/processed/authority_case_queue.csv")
    if case_path.exists():
        df_cases = pd.read_csv(case_path)
        return df_cases.to_dict(orient="records")
    
    # Fallback to generated cases
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
    import json
    async def event_generator():
        while True:
            data = {"timestamp": datetime.utcnow().isoformat() + "Z", "city": "Delhi NCR", "pm25": 150.5 + (datetime.utcnow().second % 10)}
            yield f"event: pollutant_update\ndata: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/v1/brics/models")
def list_brics_models():
    return brics_registry.list_models()

@app.post("/api/v1/brics/share")
def share_brics_model(model: BRICSModelMetadata):
    model_id = brics_registry.register_model(model)
    return {"status": "success", "model_id": model_id}

@app.post("/api/v1/reports")
def create_citizen_report(report_in: CitizenReportCreateInput):
    # Map common Delhi area names to locality IDs
    loc_clean = report_in.location.lower().strip()
    loc_id = "DEL_GEN"
    if "najafgarh" in loc_clean:
        loc_id = "DEL_NAJ"
    elif "rohini" in loc_clean:
        loc_id = "DEL_ROH"
    elif "mehrauli" in loc_clean:
        loc_id = "DEL_MEH"
    elif "safdarjung" in loc_clean:
        loc_id = "DEL_SFE"
    elif "anand vihar" in loc_clean:
        loc_id = "DEL_AV"
    else:
        loc_id = f"DEL_{report_in.location[:6].upper().replace(' ', '_')}"
        
    obs = report_in.observation or report_in.description or f"[{report_in.category or 'general'}] Citizen report at {report_in.location}"
    comm_input = CommunityReportInput(
        locality_id=loc_id,
        report_text=f"[{report_in.location}] {obs}",
        language_code=report_in.language,
        source_type=report_in.source_type,
        consent_to_store=report_in.consent,
        coarse_location_cell=report_in.coarse_grid or report_in.location
    )
    saved = save_local_report(comm_input)
    return {
        "status": "success",
        "message": "Report successfully recorded for authority corroboration",
        "report_id": saved["report_id"],
        "timestamp_utc": saved["timestamp_utc"],
        "locality_id": loc_id
    }

@app.get("/api/v1/reports")
def get_citizen_reports(limit: int = 50):
    reports = list_local_reports(limit=limit)
    return reports

@app.post("/api/v1/cases/{case_id}/dispatch")
def dispatch_case_authority(case_id: str, dispatch: CaseDispatchInput):
    from pathlib import Path
    action_note = (
        f"Assigned to: {dispatch.assigned_authority} "
        f"({dispatch.assigned_unit or 'Enforcement Wing'}). "
        f"Priority: {dispatch.priority}. "
        f"Action: {dispatch.action_type}. "
        f"Notes: {dispatch.officer_notes or 'Standard regulatory response initiated.'}"
    )
    action_input = CaseActionInput(
        actor_role="Central Enforcement Dispatcher",
        action_type=f"Dispatched: {dispatch.action_type}",
        outcome_status=dispatch.outcome_status,
        review_note=action_note
    )
    audit_record = save_case_action(case_id, action_input)
    
    # Update status in authority_case_queue.csv if present
    case_path = Path("data/processed/authority_case_queue.csv")
    if case_path.exists():
        try:
            df = pd.read_csv(case_path)
            if 'case_id' in df.columns and case_id in df['case_id'].values:
                df.loc[df['case_id'] == case_id, 'review_state'] = dispatch.outcome_status
                df.loc[df['case_id'] == case_id, 'assigned_authority'] = dispatch.assigned_authority
                df.to_csv(case_path, index=False)
        except Exception:
            pass

    return {
        "status": "dispatched",
        "case_id": case_id,
        "assigned_authority": dispatch.assigned_authority,
        "action_id": audit_record["action_id"],
        "outcome_status": dispatch.outcome_status,
        "timestamp_utc": audit_record.get("timestamp_utc", audit_record.get("timestamp", datetime.utcnow().isoformat() + "Z"))
    }

@app.get("/api/v1/diagnostics/spikes")
def run_spike_diagnosis(
    pm25: float = 245.0,
    pm10: float = 310.0,
    no2: float = 78.0,
    so2: float = 28.0,
    co: float = 2.4,
    o3: float = 45.0,
    wind_speed: float = 1.3,
    wind_deg: float = 310.0
):
    sensor_data = {"pm25": pm25, "pm10": pm10, "no2": no2, "so2": so2, "co": co, "o3": o3}
    weather_data = {"wind_speed": wind_speed, "wind_deg": wind_deg, "temp": 26, "humidity": 65, "pbl_height": 280}
    diagnosis = diagnose_spike_cause(sensor_data, weather_data)
    return diagnosis

@app.get("/api/v1/benchmarks")
def get_system_benchmarks():
    return {
        "government_comparison": get_government_benchmark_metrics(),
        "brics_platforms": get_brics_interoperability_comparison()
    }

