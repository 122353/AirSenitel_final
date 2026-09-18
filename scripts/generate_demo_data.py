import os
import json
import random
from datetime import datetime, timedelta

PROCESSED_DIR = r"d:\AirSentinel\data\processed"

def generate_live_readings():
    print("Generating simulated live readings...")
    pollutants = ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO"]
    stations = ["Delhi-Anand Vihar", "Delhi-RK Puram", "Delhi-Punjabi Bagh"]
    
    readings = []
    now = datetime.utcnow()
    
    for i in range(24):
        t = now - timedelta(hours=23-i)
        timestamp = t.strftime("%Y-%m-%dT%H:00:00Z")
        hour = t.hour
        
        # Diurnal pattern (peaks at 7-9 AM and 8-11 PM)
        if 7 <= hour <= 9 or 20 <= hour <= 23:
            multiplier = random.uniform(1.5, 2.5)
        else:
            multiplier = random.uniform(0.5, 1.2)
            
        is_anomaly = random.random() < (3 / 24.0) # 2-3 per day
            
        for station in stations:
            for p in pollutants:
                base = 50 if p.startswith("PM") else 20
                val = base * multiplier * random.uniform(0.8, 1.2)
                
                if is_anomaly and p == "PM2.5":
                    val *= 3.0
                    
                readings.append({
                    "station": station,
                    "pollutant": p,
                    "value": round(val, 2),
                    "timestamp": timestamp,
                    "unit": "µg/m³" if p != "CO" else "mg/m³",
                    "is_anomaly": is_anomaly and p == "PM2.5"
                })
                
    with open(os.path.join(PROCESSED_DIR, "demo_live_readings.json"), "w") as f:
        json.dump(readings, f, indent=2)

def generate_alerts():
    print("Generating demo alerts...")
    alerts = []
    now = datetime.utcnow()
    
    locations = ["Anand Vihar", "RK Puram", "Okhla", "Dwarka", "Rohini"]
    types = ["Threshold Exceeded", "Sensor Anomaly", "Forecast Warning"]
    
    for i in range(random.randint(5, 8)):
        alerts.append({
            "alert_id": f"ALT-{random.randint(1000, 9999)}",
            "location": random.choice(locations),
            "type": random.choice(types),
            "severity": random.choice(["Critical", "Warning", "Info"]),
            "message": f"PM2.5 levels expected to rise significantly in the next 3 hours.",
            "timestamp": (now - timedelta(minutes=random.randint(5, 300))).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "Active"
        })
        
    with open(os.path.join(PROCESSED_DIR, "demo_alerts.json"), "w") as f:
        json.dump(alerts, f, indent=2)

def generate_brics_models():
    print("Generating BRICS model registry...")
    models = [
        {"nation": "India", "model_id": "IND-NCAP-01", "type": "Gradient Boosting", "accuracy": 0.91, "latency_ms": 45},
        {"nation": "Brazil", "model_id": "BRA-AMZ-02", "type": "Random Forest", "accuracy": 0.88, "latency_ms": 60},
        {"nation": "Russia", "model_id": "RUS-SBR-01", "type": "LSTM Neural Net", "accuracy": 0.94, "latency_ms": 120},
        {"nation": "China", "model_id": "CHN-BEJ-03", "type": "Transformer", "accuracy": 0.96, "latency_ms": 150},
        {"nation": "South Africa", "model_id": "ZAF-CPT-01", "type": "XGBoost", "accuracy": 0.89, "latency_ms": 50}
    ]
    
    with open(os.path.join(PROCESSED_DIR, "demo_brics_models.json"), "w") as f:
        json.dump(models, f, indent=2)

if __name__ == "__main__":
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    generate_live_readings()
    generate_alerts()
    generate_brics_models()
    print("Demo data generation completed successfully.")
