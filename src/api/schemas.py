from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class CaseActionInput(BaseModel):
    actor_role: str
    action_type: str
    outcome_status: str
    review_note: Optional[str] = None

class CommunityReportInput(BaseModel):
    locality_id: str
    report_text: str
    language_code: str
    source_type: str
    consent_to_store: bool
    coarse_location_cell: Optional[str] = None

class SensorReading(BaseModel):
    timestamp_utc: str
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    pollutant_code: str
    value: float
    unit: str
    quality_flag: str
    distance_metres: float

class PollutantForecast(BaseModel):
    area_name: str
    horizon: str
    input_time_utc: str
    forecast_for_utc: str
    current_pm25_input: float
    predicted_pm25: float
    selected_model: str
    empirical_interval_low: float
    empirical_interval_high: float
    forecast_status: str

class AnomalyCase(BaseModel):
    case_id: str
    area_name: str
    case_category: str
    evidence_summary: str
    recommended_action: str
    review_state: str
    review_state_limit: str
    automation_limit: str
    created_at_utc: str
    observed_pm25: float
    predicted_pm25: float
    forecast_residual: float
    anomaly_score: float
    data_freshness_minutes: float
    confidence_level: str

class AlertPayload(BaseModel):
    alert_id: str
    alert_type: str
    severity: str
    area_name: str
    message: str
    timestamp_utc: str
    pollutant_code: str
    value: float
    threshold: float

class BRICSModelMetadata(BaseModel):
    model_id: str
    country_code: str
    model_type: str
    training_date: str
    accuracy_metrics: Dict[str, Any]
    pollutant_codes: List[str]
    description: str

class SensorEffectiveRange(BaseModel):
    pollutant_code: str
    instrument_class: str
    effective_radius_m: float
    confidence_decay_start_m: float

class CaseDispatchInput(BaseModel):
    assigned_authority: str
    assigned_unit: Optional[str] = None
    priority: str = "High"
    action_type: str
    officer_notes: Optional[str] = None
    outcome_status: str = "dispatched"

class CitizenReportCreateInput(BaseModel):
    location: str
    observation: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    reporter_phone: Optional[str] = None
    language: str = "en"
    source_type: str = "text"
    consent: bool = True
    coarse_grid: Optional[str] = None
