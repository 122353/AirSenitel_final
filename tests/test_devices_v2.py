"""No hardware or network is contacted. Screening fixtures are synthetic."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.services import case_store_v2 as store
from src.services import devices_v2 as devices


AUTHORITY = {"user_id": "user_device_operator", "email": "operator@example.test"}


def device_payload(identifier="MANUFACTURER-TEST-001", **overrides):
    return {
        "physical_device_id": identifier, "name": "Operator-attested test device",
        "latitude": 28.61, "longitude": 77.21, "location_accuracy_m": 10,
        "environment": "outdoor", "calibration_reference": "Test calibration certificate; synthetic fixture",
        "calibration_valid_until": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "supported_channels": [{"pollutant": "pm25", "unit": "ug/m3"}], **overrides,
    }


def sample(value=120, minutes_ago=10, **overrides):
    return {"pollutant": "pm25", "unit": "ug/m3", "value": value,
            "observed_at": (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(), **overrides}


class DeviceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "devices.sqlite3")
        self.env = patch.dict(os.environ, {
            "AIRSENTINEL_ENV": "local", "AIRSENTINEL_STORE": "sqlite", "AIRSENTINEL_SQLITE_PATH": self.path,
            "VERCEL": "", "K_SERVICE": "", "AWS_LAMBDA_FUNCTION_NAME": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        devices.initialize_devices()

    def assert_error(self, status, fn, *args, **kwargs):
        with self.assertRaises(store.StoreError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(status, caught.exception.status_code)

    def test_registration_is_attestation_with_no_assumed_range_or_raw_identifier(self):
        record = devices.register_device(device_payload(), AUTHORITY)
        self.assertIsNone(record["representativeness_radius_m"])
        self.assertEqual("unknown", record["representativeness_status"])
        self.assertEqual("operator_attestation_only", record["calibration_status"])
        self.assertNotIn("physical_device_id", record)
        self.assertEqual(64, len(record["physical_device_fingerprint"]))
        self.assertNotIn("MANUFACTURER-TEST-001", Path(self.path).read_bytes().decode("latin1"))
        self.assertEqual(record, devices.list_devices()[0])
        self.assert_error(409, devices.register_device, device_payload("  manufacturer-test-001 "), AUTHORITY)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(AUTHORITY["user_id"], connection.execute("SELECT registered_by FROM airv2_devices").fetchone()[0])

    def test_registration_accepts_real_device_locations_across_india(self):
        record = devices.register_device(device_payload(
            "MUMBAI-TEST-DEVICE", latitude=19.076, longitude=72.8777,
            name="Mumbai operator-attested test device"), AUTHORITY)
        self.assertEqual(19.076, record["latitude"])
        self.assertEqual(72.8777, record["longitude"])

    def test_registration_rejects_outside_bounds_credentials_and_invalid_attestations(self):
        invalid = [
            device_payload(latitude=0), device_payload(longitude=100), device_payload(location_accuracy_m=1001),
            device_payload(location_accuracy_m=float("nan")), device_payload(environment="unknown"),
            device_payload(calibration_reference=""), device_payload(calibration_valid_until="2020-01-01T00:00:00Z"),
            device_payload(calibration_valid_until="2030-01-01T00:00:00"), device_payload(api_key="secret"),
            device_payload(supported_channels=[{"pollutant": "pm25", "unit": "ppm"}]),
            device_payload(supported_channels=[{"pollutant": "pm25", "unit": "ug/m3"}] * 2),
            device_payload(representativeness_radius_m=-1),
        ]
        for payload in invalid:
            self.assert_error(422, devices.register_device, payload, AUTHORITY)
        self.assert_error(403, devices.register_device, device_payload(), {"user_id": "forged"})
        self.assertEqual([], devices.list_devices())

    def test_ingestion_validates_channels_bounds_time_and_batch_size(self):
        record = devices.register_device(device_payload(), AUTHORITY)
        invalid_samples = [
            sample(value=float("inf")), sample(value=-1), sample(value=5001), sample(value=True),
            sample(pollutant="co", unit="mg/m3"), sample(observed_at="2026-01-01T00:00:00"),
            sample(observed_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()),
            sample(observed_at=(datetime.now(timezone.utc) - timedelta(days=8)).isoformat()),
            {**sample(), "raw_serial": "not-supported"},
        ]
        for item in invalid_samples:
            self.assert_error(422, devices.ingest_observations, record["id"], {"samples": [item]}, AUTHORITY)
        self.assert_error(422, devices.ingest_observations, record["id"], {"samples": [sample()] * 101}, AUTHORITY)
        self.assert_error(404, devices.ingest_observations, "unregistered", {"samples": [sample()]}, AUTHORITY)
        self.assertEqual([], devices.recent_observations()["observations"])

    def test_immutable_observations_preserve_snapshot_actor_and_no_duplicate_overwrite(self):
        record = devices.register_device(device_payload(), AUTHORITY)
        existing = sample()
        result = devices.ingest_observations(record["id"], {"samples": [existing]}, AUTHORITY)
        self.assertEqual(1, result["accepted"])
        # A duplicate in a mixed batch must roll back its otherwise-new sample.
        self.assert_error(409, devices.ingest_observations, record["id"], {"samples": [sample(minutes_ago=25), {**existing, "value": 800}]}, AUTHORITY)
        observations = devices.recent_observations()["observations"]
        self.assertEqual(1, len(observations))
        self.assertEqual(120, observations[0]["value"])
        self.assertEqual(record, observations[0]["device_snapshot"])
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(AUTHORITY["user_id"], connection.execute("SELECT actor_id FROM airv2_device_observations").fetchone()[0])

    def test_concurrent_duplicate_registration_and_ingestion_have_one_winner(self):
        def register(_):
            try:
                return devices.register_device(device_payload(), AUTHORITY)["id"]
            except store.StoreError as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(register, range(2)))
        self.assertEqual(1, results.count(409))
        device_id = next(value for value in results if value != 409)
        payload = {"samples": [sample()]}
        def ingest(_):
            try:
                return devices.ingest_observations(device_id, payload, AUTHORITY)["accepted"]
            except store.StoreError as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual([1, 409], list(executor.map(ingest, range(2))))

    def test_recent_query_is_time_bounded_and_marks_truncation(self):
        record = devices.register_device(device_payload(), AUTHORITY)
        devices.ingest_observations(record["id"], {"samples": [sample(minutes_ago=10), sample(minutes_ago=20), sample(minutes_ago=180)]}, AUTHORITY)
        data = devices.recent_observations(hours=2, limit=1)
        self.assertTrue(data["truncated"])
        self.assertEqual(1, len(data["observations"]))
        self.assertEqual([], devices.micro_candidates(data)["candidates"])
        self.assertEqual(2, len(devices.recent_observations(hours=2)["observations"]))
        self.assert_error(422, devices.recent_observations, hours=73)
        self.assert_error(422, devices.recent_observations, limit=10001)


class InspectionScreeningTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.data = {"devices": [], "observations": [], "truncated": False}
        self.add_device("hot-a", 28.61, 77.21, 120)
        self.add_device("hot-b", 28.6101, 77.2101, 130)
        self.add_device("background-a", 28.617, 77.213, 20)
        self.add_device("background-b", 28.603, 77.208, 30)

    def add_device(self, identifier, latitude, longitude, value, *, minutes=(30, 20, 10), **overrides):
        metadata = {
            "id": identifier, "physical_device_fingerprint": store._digest(identifier),
            "latitude": latitude, "longitude": longitude, "location_accuracy_m": 10,
            "environment": "outdoor", "calibration_reference": "Synthetic calibration fixture",
            "calibration_status": "operator_attestation_only",
            "calibration_valid_until": (self.now + timedelta(days=30)).isoformat(),
            "verification_status": "operator_attested_not_independently_verified",
            "supported_channels": [{"pollutant": "pm25", "unit": "ug/m3"}],
            "representativeness_radius_m": None, **overrides,
        }
        self.data["devices"].append(metadata)
        for offset in minutes:
            self.data["observations"].append({"device_id": identifier, "pollutant": "pm25", "unit": "ug/m3",
                "value": value, "observed_at": (self.now - timedelta(minutes=offset)).isoformat(), "device_snapshot": deepcopy(metadata)})

    def change_device(self, identifier, **updates):
        for device in self.data["devices"]:
            if device["id"] == identifier:
                device.update(updates)
        for observation in self.data["observations"]:
            if observation["device_id"] == identifier:
                observation["device_snapshot"].update(updates)

    def test_only_supported_screening_candidate_with_clear_uncertainty(self):
        original = deepcopy(self.data)
        result = devices.micro_candidates(self.data, self.now)
        self.assertEqual(original, self.data, "Pure analysis must not mutate evidence")
        self.assertEqual(1, len(result["candidates"]))
        candidate = result["candidates"][0]
        self.assertEqual((2, 2), (candidate["device_count"], candidate["background_count"]))
        self.assertEqual("screening_only", candidate["confidence"])
        self.assertEqual("unverified", candidate["cause"])
        self.assertEqual(250, candidate["cell_size_m"])
        self.assertEqual(125, candidate["cell_median_pm25"])
        self.assertEqual(25, candidate["background_median_pm25"])
        self.assertFalse(result["coverage"]["complete_area_coverage"])

    def test_no_evidence_or_single_device_never_becomes_candidate(self):
        self.assertEqual([], devices.micro_candidates({"devices": [], "observations": []}, self.now)["candidates"])
        self.data["devices"] = [item for item in self.data["devices"] if item["id"] != "hot-b"]
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])

    def test_stale_indoor_expired_or_imprecise_devices_cannot_qualify(self):
        original = deepcopy(self.data)
        for updates in ({"environment": "indoor"}, {"location_accuracy_m": 51},
                        {"calibration_valid_until": (self.now - timedelta(minutes=1)).isoformat()},
                        {"verification_status": "verified_by_client_claim"}):
            self.data = deepcopy(original)
            self.change_device("hot-b", **updates)
            self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])
        self.assertEqual([], devices.micro_candidates(original, self.now + timedelta(hours=2))["candidates"])

    def test_three_samples_must_span_twenty_minutes_and_be_contemporaneous(self):
        for observation in self.data["observations"]:
            if observation["device_id"] == "hot-b":
                timestamp = datetime.fromisoformat(observation["observed_at"])
                observation["observed_at"] = (timestamp - timedelta(minutes=70)).isoformat()
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])
        self.setUp()
        self.data["observations"] = [item for item in self.data["observations"] if not (item["device_id"] == "hot-b" and item["observed_at"] == (self.now - timedelta(minutes=30)).isoformat())]
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])

    def test_two_nearby_contemporaneous_background_devices_required(self):
        self.change_device("background-b", latitude=28.8, longitude=77.5)
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])
        self.setUp()
        for observation in self.data["observations"]:
            if observation["device_id"].startswith("background"):
                observation["observed_at"] = (datetime.fromisoformat(observation["observed_at"]) - timedelta(minutes=70)).isoformat()
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])

    def test_broad_background_elevation_is_not_localized(self):
        for observation in self.data["observations"]:
            if observation["device_id"].startswith("background"):
                observation["value"] = 120
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])

    def test_normal_devices_in_same_cell_are_not_cherry_picked_away(self):
        for index in range(3):
            self.add_device(f"normal-{index}", 28.61005, 77.21005, 20)
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])

    def test_duplicate_physical_identity_and_inconsistent_snapshots_fail_closed(self):
        self.change_device("hot-b", physical_device_fingerprint=store._digest("hot-a"))
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])
        self.setUp()
        self.data["observations"][0]["device_snapshot"]["latitude"] = 28.9
        self.assertEqual([], devices.micro_candidates(self.data, self.now)["candidates"])


if __name__ == "__main__":
    unittest.main()
