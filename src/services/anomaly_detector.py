import pandas as pd
import uuid
from datetime import datetime

def detect_unexpected_spikes(observations: pd.DataFrame, forecasts: pd.DataFrame) -> list[dict]:
    cases = []
    if observations.empty or forecasts.empty:
        return cases
        
    # Dummy implementation for detecting spikes
    for _, obs in observations.iterrows():
        area = obs.get('area_name', 'Unknown')
        obs_val = obs.get('pm25', 0)
        
        # Match forecast
        fc_match = forecasts[forecasts['area_name'] == area]
        if not fc_match.empty:
            fc_val = fc_match.iloc[0].get('predicted_pm25', 0)
            interval_high = fc_match.iloc[0].get('empirical_interval_high', fc_val * 1.5)
            
            if obs_val > interval_high:
                cases.append({
                    "case_id": str(uuid.uuid4()),
                    "area_name": area,
                    "case_category": "Unexpected Spike",
                    "evidence_summary": f"Observed PM2.5 of {obs_val} exceeds forecast upper bound {interval_high}",
                    "recommended_action": "Investigate local sources",
                    "review_state": "pending",
                    "review_state_limit": "72h",
                    "automation_limit": "24h",
                    "created_at_utc": datetime.utcnow().isoformat() + "Z",
                    "observed_pm25": obs_val,
                    "predicted_pm25": fc_val,
                    "forecast_residual": obs_val - fc_val,
                    "anomaly_score": (obs_val - interval_high) / interval_high if interval_high > 0 else 0,
                    "data_freshness_minutes": 15.0,
                    "confidence_level": "high"
                })
    return cases

def detect_evidence_gaps(locality_profiles: pd.DataFrame) -> list[dict]:
    cases = []
    if locality_profiles.empty:
        return cases
        
    for _, loc in locality_profiles.iterrows():
        freshness = loc.get('data_freshness_minutes', 0)
        if freshness > 120:  # Older than 2 hours
            cases.append({
                "case_id": str(uuid.uuid4()),
                "area_name": loc.get('area_name', 'Unknown'),
                "case_category": "Evidence Gap",
                "evidence_summary": f"Data is {freshness} minutes old, exceeding threshold",
                "recommended_action": "Check sensor status",
                "review_state": "pending",
                "review_state_limit": "24h",
                "automation_limit": "12h",
                "created_at_utc": datetime.utcnow().isoformat() + "Z",
                "observed_pm25": 0.0,
                "predicted_pm25": 0.0,
                "forecast_residual": 0.0,
                "anomaly_score": min(freshness / 120.0, 10.0),
                "data_freshness_minutes": freshness,
                "confidence_level": "medium"
            })
    return cases

def generate_case_queue(observations: pd.DataFrame, forecasts: pd.DataFrame, locality_profiles: pd.DataFrame) -> pd.DataFrame:
    spikes = detect_unexpected_spikes(observations, forecasts)
    gaps = detect_evidence_gaps(locality_profiles)
    
    all_cases = spikes + gaps
    if not all_cases:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_cases)
    # Save to CSV for queue processing
    df.to_csv("d:/AirSentinel/data/processed/case_queue.csv", index=False)
    return df
