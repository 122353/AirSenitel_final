import uuid
from typing import List, Dict
from src.api.schemas import BRICSModelMetadata
from datetime import datetime

class BRICSModelRegistry:
    def __init__(self):
        self.models: Dict[str, BRICSModelMetadata] = {}
        self._populate_demo_data()
        
    def _populate_demo_data(self):
        demo_models = [
            BRICSModelMetadata(
                model_id=str(uuid.uuid4()),
                country_code="IN",
                model_type="HistGradientBoosting",
                training_date=datetime.utcnow().isoformat(),
                accuracy_metrics={"rmse": 12.5, "r2": 0.85},
                pollutant_codes=["pm25", "pm10"],
                description="India NCR regional model"
            ),
            BRICSModelMetadata(
                model_id=str(uuid.uuid4()),
                country_code="BR",
                model_type="RandomForest",
                training_date=datetime.utcnow().isoformat(),
                accuracy_metrics={"rmse": 10.2, "r2": 0.88},
                pollutant_codes=["pm25", "o3"],
                description="Brazil Sao Paulo urban model"
            ),
            BRICSModelMetadata(
                model_id=str(uuid.uuid4()),
                country_code="CN",
                model_type="DeepNeuralNetwork",
                training_date=datetime.utcnow().isoformat(),
                accuracy_metrics={"rmse": 8.5, "r2": 0.92},
                pollutant_codes=["pm25", "so2", "no2"],
                description="China Beijing multi-pollutant model"
            ),
            BRICSModelMetadata(
                model_id=str(uuid.uuid4()),
                country_code="RU",
                model_type="XGBoost",
                training_date=datetime.utcnow().isoformat(),
                accuracy_metrics={"rmse": 14.1, "r2": 0.81},
                pollutant_codes=["pm10", "co"],
                description="Russia Moscow winter baseline model"
            ),
            BRICSModelMetadata(
                model_id=str(uuid.uuid4()),
                country_code="ZA",
                model_type="LightGBM",
                training_date=datetime.utcnow().isoformat(),
                accuracy_metrics={"rmse": 11.8, "r2": 0.86},
                pollutant_codes=["pm25", "so2"],
                description="South Africa industrial zone model"
            )
        ]
        for m in demo_models:
            self.models[m.model_id] = m

    def register_model(self, metadata: BRICSModelMetadata) -> str:
        if not metadata.model_id:
            metadata.model_id = str(uuid.uuid4())
        self.models[metadata.model_id] = metadata
        return metadata.model_id

    def list_models(self, country_code: str = None) -> list[dict]:
        res = []
        for m in self.models.values():
            if country_code and m.country_code != country_code:
                continue
            res.append(m.model_dump())
        return res

    def export_model(self, model_id: str) -> dict:
        if model_id not in self.models:
            raise ValueError("Model not found")
        return self.models[model_id].model_dump()

    def import_model(self, payload: dict) -> str:
        model = BRICSModelMetadata(**payload)
        return self.register_model(model)

# Singleton instance
registry = BRICSModelRegistry()
