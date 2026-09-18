import unittest
import pandas as pd
from src.api.main import health_check, get_cities, get_sensors, get_cases
from src.api.schemas import CaseActionInput, CommunityReportInput, SensorReading
from src.services.sensor_range import (
    haversine_distance,
    compute_sensor_weight,
    filter_stations_by_effective_range,
    get_effective_coverage_area,
    EFFECTIVE_RANGES
)
from src.services.case_audit import save_case_action, read_case_actions, overlay_review_state
from src.services.community_reports import save_local_report
from src.services.gemini_explainer import explain_case
from src.services.gemini_photo import analyse_photo
from src.services.brics_federation import registry as brics_registry, BRICSModelMetadata

class TestAirSentinel(unittest.TestCase):
    def test_api_health(self):
        data = health_check()
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)

    def test_api_cities(self):
        data = get_cities()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_api_sensors(self):
        data = get_sensors()
        self.assertIn("sensors", data)
        self.assertIn("effective_ranges", data)
        self.assertEqual(data["effective_ranges"]["pm25"]["effective"], 1500)

    def test_sensor_range_haversine(self):
        # Delhi to Gurgaon approx 30km
        d = haversine_distance(28.6139, 77.2090, 28.4595, 77.0266)
        self.assertTrue(20000 < d < 35000)

    def test_sensor_range_weighting(self):
        # Inside decay zone (800m for PM2.5) -> weight 1.0
        w_close = compute_sensor_weight(500, "pm25")
        self.assertEqual(w_close, 1.0)

        # Between decay (800m) and effective (1500m) -> 0.0 < weight < 1.0
        w_mid = compute_sensor_weight(1150, "pm25")
        self.assertTrue(0.0 < w_mid < 1.0)

        # Beyond effective (1500m) -> weight 0.0
        w_far = compute_sensor_weight(1600, "pm25")
        self.assertEqual(w_far, 0.0)

    def test_filter_stations_by_effective_range(self):
        stations_df = pd.DataFrame([
            {"station_id": "s1", "distance_m": 500},
            {"station_id": "s2", "distance_m": 1200},
            {"station_id": "s3", "distance_m": 4500},  # beyond 1500m PM2.5 limit
        ])
        filtered = filter_stations_by_effective_range(stations_df, "pm25")
        self.assertEqual(len(filtered), 2)
        self.assertNotIn("s3", filtered["station_id"].values)
        self.assertIn("weight", filtered.columns)

    def test_case_audit_flow(self):
        action = CaseActionInput(
            actor_role="environment analyst",
            action_type="acknowledged",
            outcome_status="review in progress",
            review_note="Automated test verification"
        )
        record = save_case_action("TEST-CASE-001", action)
        self.assertEqual(record["case_id"], "TEST-CASE-001")
        self.assertEqual(record["actor_role"], "environment analyst")

        history = read_case_actions("TEST-CASE-001")
        self.assertGreaterEqual(len(history), 1)
        self.assertTrue(any(h["case_id"] == "TEST-CASE-001" for h in history))

    def test_community_report_validation(self):
        with self.assertRaises(ValueError):
            save_local_report(CommunityReportInput(
                locality_id="DEL_NAJ",
                report_text="Smoke observed",
                language_code="en",
                source_type="text",
                consent_to_store=False
            ))

        result = save_local_report(CommunityReportInput(
            locality_id="DEL_NAJ",
            report_text="Smoke observed near road",
            language_code="en",
            source_type="text",
            consent_to_store=True
        ))
        self.assertEqual(result["locality_id"], "DEL_NAJ")
        self.assertIn("report_id", result)

    def test_brics_model_registry(self):
        models = brics_registry.list_models()
        self.assertGreaterEqual(len(models), 5)
        countries = [m["country_code"] for m in models]
        self.assertIn("IN", countries)
        self.assertIn("BR", countries)
        self.assertIn("CN", countries)

    def test_guarded_case_explanation(self):
        explanation, generated_by = explain_case({
            "case_id": "CASE-1",
            "area_name": "Najafgarh",
            "case_category": "unexpected spike review",
            "evidence_summary": "Monitored PM2.5 exceeded forecast upper bound by 38 ug/m3"
        })
        self.assertGreater(len(explanation), 0)
        self.assertTrue(
            "unverified" in explanation.lower() or 
            "objective" in explanation.lower() or 
            "evidence" in explanation.lower()
        )

if __name__ == "__main__":
    unittest.main()
