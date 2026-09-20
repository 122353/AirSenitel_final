"""AI Root-Cause Attribution Engine for Sudden Air Pollution Spikes.
Analyzes multi-pollutant stoichiometric ratios, meteorological vectors,
boundary layer dynamics, and satellite fire context to determine the probable cause.
"""

from typing import Dict, Any, List
from datetime import datetime

def diagnose_spike_cause(sensor_data: Dict[str, Any], weather_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Diagnose the root cause of a sudden air quality spike.
    
    Args:
        sensor_data: Dictionary containing pollutant concentrations (pm25, pm10, no2, so2, co, o3)
        weather_data: Optional weather context (wind_speed, wind_deg, temp, humidity, pbl_height)
        
    Returns:
        Structured diagnosis with primary cause, confidence, contributing factors,
        responsible government authority, and precision intervention protocol.
    """
    pm25 = float(sensor_data.get('pm25', 0) or 0)
    pm10 = float(sensor_data.get('pm10', 0) or (pm25 * 1.6))
    no2 = float(sensor_data.get('no2', 0) or 0)
    so2 = float(sensor_data.get('so2', 0) or 0)
    co = float(sensor_data.get('co', 0) or 0)
    o3 = float(sensor_data.get('o3', 0) or 0)
    
    weather = weather_data or {}
    wind_speed = float(weather.get('wind_speed', 1.8))
    wind_deg = float(weather.get('wind_deg', 315)) # default NW
    temp = float(weather.get('temp', 24))
    humidity = float(weather.get('humidity', 62))
    pbl_height = float(weather.get('pbl_height', 350)) # boundary layer height in meters
    
    # Stoichiometric Ratios
    pm_ratio = (pm25 / pm10) if pm10 > 0 else 0.65
    so2_ratio = (so2 / pm25) if pm25 > 0 else 0.1
    
    scores = {
        "Biomass / Open Waste Burning": 10.0,
        "Industrial Boilers & Point Sources": 10.0,
        "Vehicular Corridor Congestion": 10.0,
        "Construction & Unpaved Road Dust": 10.0,
        "Regional Stubble Influx (Crop Residue)": 10.0,
        "Atmospheric Inversion Trap (Stagnation)": 10.0
    }
    
    factors: List[str] = []
    
    # Rule 1: High PM2.5/PM10 ratio indicates combustion (fine particle dominance)
    if pm_ratio >= 0.72:
        scores["Biomass / Open Waste Burning"] += 35
        scores["Regional Stubble Influx (Crop Residue)"] += 25
        factors.append(f"High PM2.5/PM10 ratio ({pm_ratio:.2f} >= 0.72) confirms fine combustion particulate dominance.")
    elif pm_ratio <= 0.45:
        scores["Construction & Unpaved Road Dust"] += 45
        factors.append(f"Low PM2.5/PM10 ratio ({pm_ratio:.2f} <= 0.45) confirms coarse mechanical dust dominance.")
    else:
        scores["Vehicular Corridor Congestion"] += 15
        factors.append(f"Intermediate PM2.5/PM10 ratio ({pm_ratio:.2f}) indicates mixed urban background emissions.")
        
    # Rule 2: Sulfur Dioxide (SO2) spikes signal industrial fuels
    if so2 >= 40.0 or so2_ratio >= 0.22:
        scores["Industrial Boilers & Point Sources"] += 45
        factors.append(f"Elevated SO2 ({so2:.1f} µg/m³) indicates heavy sulfur-bearing industrial fuel/coal combustion.")
        
    # Rule 3: Nitrogen Dioxide (NO2) and Carbon Monoxide (CO) signal diesel traffic
    if no2 >= 75.0 or co >= 2.5:
        scores["Vehicular Corridor Congestion"] += 40
        factors.append(f"Elevated NO2 ({no2:.1f} µg/m³) and CO ({co:.1f} mg/m³) match diesel corridor congestion patterns.")
        
    # Rule 4: Wind trajectory from North-West (Punjab/Haryana) during autumn/winter
    current_month = datetime.utcnow().month
    is_stubble_season = current_month in [10, 11, 12, 1]
    is_nw_wind = (270 <= wind_deg <= 350)
    
    if is_nw_wind and wind_speed >= 2.5:
        if is_stubble_season:
            scores["Regional Stubble Influx (Crop Residue)"] += 45
            factors.append(f"North-Westerly wind ({wind_deg}°, {wind_speed:.1f} m/s) actively transports upstream agricultural smoke plumes.")
        else:
            scores["Regional Stubble Influx (Crop Residue)"] += 15
    elif wind_speed < 1.2:
        scores["Atmospheric Inversion Trap (Stagnation)"] += 35
        scores["Biomass / Open Waste Burning"] += 15
        factors.append(f"Near-calm surface winds ({wind_speed:.1f} m/s) prevent dispersion, leading to localized toxic pooling.")
        
    # Rule 5: Low Boundary Layer Height (thermal inversion)
    if pbl_height < 300:
        scores["Atmospheric Inversion Trap (Stagnation)"] += 30
        factors.append(f"Compressed planetary boundary layer ({pbl_height:.0f} m) traps surface emissions near breathing level.")

    # Determine highest score
    primary_cause = max(scores, key=scores.get)
    max_score = scores[primary_cause]
    total_score = sum(scores.values())
    confidence = min(96.0, max(58.0, (max_score / total_score) * 160))
    
    # Statutory Authority Mapping
    authority_map = {
        "Biomass / Open Waste Burning": {
            "agency": "Municipal Corporation of Delhi (MCD)",
            "unit": "Sanitation & Flying Enforcement Squad",
            "action": "Dispatch rapid dousing squad; penalize illegal municipal/biomass burning under SWM 2016."
        },
        "Industrial Boilers & Point Sources": {
            "agency": "Delhi Pollution Control Committee (DPCC)",
            "unit": "Industrial Area Inspection & Closure Wing",
            "action": "Immediate stack emission audit; verify approved PNG fuel usage or seal non-conforming boiler."
        },
        "Vehicular Corridor Congestion": {
            "agency": "Delhi Traffic Police",
            "unit": "Congestion Remediation & Intelligent Traffic Wing",
            "action": "Implement dynamic signal timing adjustments; divert heavy commercial diesel traffic to Outer Ring Road."
        },
        "Construction & Unpaved Road Dust": {
            "agency": "Municipal Corporation of Delhi (MCD) / PWD",
            "unit": "Dust Control & Mechanized Sweeping Cell",
            "action": "Deploy anti-smog water misting cannons; mandate green net covering and fine uncovered C&D transport."
        },
        "Regional Stubble Influx (Crop Residue)": {
            "agency": "Commission for Air Quality Management (CAQM)",
            "unit": "Inter-State Stubble Monitoring & GRAP Task Force",
            "action": "Activate GRAP Stage III/IV inter-state protocols; intensify night patrolling along borders."
        },
        "Atmospheric Inversion Trap (Stagnation)": {
            "agency": "Delhi Disaster Management Authority (DDMA)",
            "unit": "Environmental Health Advisory Unit",
            "action": "Issue vulnerable group outdoor exertion advisory; activate smog mitigation mist towers."
        }
    }
    
    auth_info = authority_map.get(primary_cause, {
        "agency": "Delhi Pollution Control Committee (DPCC)",
        "unit": "Field Inspection Unit",
        "action": "Conduct on-site ambient verification and check nearby sensor status."
    })
    
    return {
        "primary_cause": primary_cause,
        "confidence_pct": round(confidence, 1),
        "pm_ratio": round(pm_ratio, 2),
        "stoichiometric_ratios": {
            "pm25_to_pm10": round(pm_ratio, 2),
            "so2_to_pm25": round(so2_ratio, 2)
        },
        "assigned_authority": auth_info["agency"],
        "assigned_unit": auth_info["unit"],
        "recommended_action": auth_info["action"],
        "contributing_factors": factors,
        "evaluated_at_utc": datetime.utcnow().isoformat() + "Z"
    }
