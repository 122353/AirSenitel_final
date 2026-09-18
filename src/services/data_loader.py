import os
import pandas as pd
import numpy as np

def ensure_processed_dir():
    os.makedirs("d:/AirSentinel/data/processed", exist_ok=True)

def load_city_conditions() -> pd.DataFrame:
    path = "d:/AirSentinel/data/processed/city_conditions.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    # Generate dummy data
    df = pd.DataFrame({
        "city_id": ["DEL_CITY", "MUM_CITY"],
        "city_name": ["Delhi NCR", "Mumbai"],
        "pm25": [150.5, 45.2],
        "temperature": [28.5, 30.1],
        "humidity": [65.0, 80.0],
        "timestamp": ["2023-10-01T10:00:00Z", "2023-10-01T10:00:00Z"]
    })
    return df

def load_station_inventory() -> pd.DataFrame:
    path = "d:/AirSentinel/data/reference/multiscale_station_inventory.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def load_pollutant_history(area_id: str = None) -> pd.DataFrame:
    path = "d:/AirSentinel/data/processed/multiscale_pollutant_history.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        if area_id and 'area_id' in df.columns:
            return df[df['area_id'] == area_id]
        return df
    return pd.DataFrame()

def load_cpcb_snapshot() -> pd.DataFrame:
    path = "d:/AirSentinel/data/processed/cpcb_realtime_snapshot.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame([{"station_id": "dummy1", "pm25": 100.0}])

def load_locality_profile() -> pd.DataFrame:
    path = "d:/AirSentinel/data/processed/locality_evidence_profile.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame([{"locality_id": "DEL_MEH", "area_name": "Mehrauli", "data_freshness_minutes": 15}])
