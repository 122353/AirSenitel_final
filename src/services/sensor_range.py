import math
import pandas as pd

EFFECTIVE_RANGES = {
    "pm25": {"effective": 1500, "decay": 800},
    "pm10": {"effective": 2000, "decay": 1000},
    "no2": {"effective": 2000, "decay": 1200},
    "o3": {"effective": 3000, "decay": 1500},
    "so2": {"effective": 2000, "decay": 1000},
    "co": {"effective": 1500, "decay": 800}
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # Radius of earth in meters
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def compute_sensor_weight(distance_m: float, pollutant_code: str) -> float:
    ranges = EFFECTIVE_RANGES.get(pollutant_code.lower())
    if not ranges:
        return 0.0
        
    eff_radius = ranges["effective"]
    decay_start = ranges["decay"]
    
    if distance_m <= decay_start:
        return 1.0
    elif distance_m >= eff_radius:
        return 0.0
    else:
        # Linear decay from decay_start to eff_radius
        return 1.0 - ((distance_m - decay_start) / (eff_radius - decay_start))

def filter_stations_by_effective_range(stations: pd.DataFrame, pollutant_code: str) -> pd.DataFrame:
    ranges = EFFECTIVE_RANGES.get(pollutant_code.lower())
    if not ranges or stations.empty or 'distance_m' not in stations.columns:
        return pd.DataFrame()
        
    eff_radius = ranges["effective"]
    filtered = stations[stations['distance_m'] <= eff_radius].copy()
    filtered['weight'] = filtered['distance_m'].apply(lambda d: compute_sensor_weight(d, pollutant_code))
    return filtered

def get_effective_coverage_area(station_lat: float, station_lon: float, pollutant_code: str) -> dict:
    ranges = EFFECTIVE_RANGES.get(pollutant_code.lower())
    if not ranges:
        return {}
        
    return {
        "center_lat": station_lat,
        "center_lon": station_lon,
        "pollutant_code": pollutant_code,
        "effective_radius_m": ranges["effective"],
        "confidence_decay_start_m": ranges["decay"]
    }
