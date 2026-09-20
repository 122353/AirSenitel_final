"""Offline contract and evidence-gate tests; fixtures are never production data."""
from __future__ import annotations

import copy
import asyncio
import gzip
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx

from src.services.forecast_v2 import accepted_series, build_forecast, iso
from src.services import monitoring_v2 as monitoring_service
from src.services.monitoring_v2 import (
    _Fetcher, build_candidates, build_snapshot, deduplicate_measurements,
    normalize_measurement, normalize_unit, station_from_location,
)

NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def raw_hour(value=30.0, stamp=NOW, pollutant="pm25", unit="µg/m³"):
    return {"value": value, "parameter": {"name": pollutant, "units": unit},
            "flagInfo": {"hasFlags": False}, "coverage": {"percentCoverage": 100},
            "period": {"datetimeFrom": {"utc": iso(stamp - timedelta(hours=1))},
                       "datetimeTo": {"utc": iso(stamp)}}}


def measurement(raw=None, **kwargs):
    options = {"station_id": 17, "sensor_id": 100, "pollutant": "pm25", "unit": "µg/m³",
               "now": NOW, "source": "openaq_v3", "source_url": "https://api.openaq.org/v3/sensors/100/hours", "hourly": True}
    options.update(kwargs)
    return normalize_measurement(raw if raw is not None else raw_hour(), **options)


def history_points(count=96, station_id=17, unit="µg/m³", pollutant="pm25"):
    return [measurement(raw_hour(20 + i % 7, NOW - timedelta(hours=count - 1 - i), pollutant, unit),
                        station_id=station_id, sensor_id=station_id * 100, unit=unit, pollutant=pollutant)
            for i in range(count)]


def location(station_id=17):
    return {"id": station_id, "name": f"Test location {station_id}", "isMobile": False,
            "isMonitor": True, "datetimeLast": {"utc": iso(NOW)},
            "coordinates": {"latitude": 28.56, "longitude": 77.18 + station_id / 10000},
            "provider": {"name": "Test provider"}, "sensors": [
                {"id": station_id * 100, "parameter": {"name": "pm25", "units": "µg/m³"}},
                {"id": station_id * 100 + 1, "parameter": {"name": "no2", "units": "ppb"}}]}


class QualityTests(unittest.TestCase):
    def test_normalizes_only_equivalent_unit_spellings(self):
        self.assertEqual(normalize_unit("ug/m^3"), "µg/m³")
        self.assertEqual(normalize_unit("μg/m³"), "µg/m³")
        self.assertEqual(normalize_unit("ppb"), "ppb")
        self.assertIsNone(normalize_unit("AQI"))

    def test_gas_ppb_is_preserved_without_conversion(self):
        point = measurement(raw_hour(12, pollutant="no2", unit="ppb"), pollutant="no2", unit="ppb")
        self.assertEqual((point["value"], point["unit"]), (12, "ppb"))
        self.assertEqual(point["quality"]["status"], "valid")

    def test_unit_mismatch_is_rejected(self):
        point = measurement(raw_hour(1, pollutant="no2", unit="ppm"), pollutant="no2", unit="ppb")
        self.assertIn("unit_mismatch", point["quality"]["reasons"])
        self.assertFalse(point["usable_for_current_analysis"])

    def test_particulate_ppb_is_rejected(self):
        point = measurement(raw_hour(1, unit="ppb"), unit="ppb")
        self.assertIn("unsupported_unit", point["quality"]["reasons"])

    def test_stale_reading_is_historical_only(self):
        point = measurement(raw_hour(stamp=NOW - timedelta(hours=4)))
        self.assertFalse(point["fresh"])
        self.assertFalse(point["usable_for_current_analysis"])
        self.assertEqual(point["quality"]["status"], "valid")

    def test_even_small_future_timestamp_is_rejected(self):
        point = measurement(raw_hour(stamp=NOW + timedelta(seconds=1)))
        self.assertIn("future_observation", point["quality"]["reasons"])
        self.assertFalse(point["fresh"])

    def test_unknown_quality_is_provisional(self):
        raw = raw_hour()
        raw.pop("flagInfo")
        point = measurement(raw)
        self.assertEqual(point["quality"]["status"], "provisional")
        self.assertFalse(point["usable_for_current_analysis"])

    def test_flagged_low_coverage_and_invalid_values_are_rejected(self):
        for value in (-1, None, float("nan"), float("inf"), True):
            self.assertEqual(measurement(raw_hour(value))["quality"]["status"], "rejected")
        raw = raw_hour()
        raw["flagInfo"]["hasFlags"] = True
        raw["coverage"]["percentCoverage"] = 40
        self.assertEqual(set(measurement(raw)["quality"]["reasons"]), {"upstream_quality_flag", "low_or_invalid_hourly_coverage"})

    def test_naive_timestamp_and_non_hourly_period_rejected(self):
        raw = raw_hour()
        raw["period"]["datetimeTo"] = {"utc": "2026-09-20T12:00:00"}
        self.assertIn("missing_or_timezone_naive_timestamp", measurement(raw)["quality"]["reasons"])
        raw = raw_hour()
        raw["period"]["datetimeFrom"] = {"utc": iso(NOW - timedelta(minutes=15))}
        self.assertIn("invalid_hourly_period", measurement(raw)["quality"]["reasons"])

    def test_conflicting_duplicates_rejected_and_identical_collapsed(self):
        first, second = measurement(), measurement(raw_hour(99))
        result = deduplicate_measurements([first, first])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["duplicate_count"], 1)
        result = deduplicate_measurements([first, second])
        self.assertEqual(result[0]["quality"]["status"], "rejected")
        self.assertEqual(first["quality"]["status"], "valid")

    def test_archive_string_parameter_and_timezone_preserved(self):
        raw = {"value": "8", "parameter": "no2", "units": "ppb", "datetime": "2026-09-16T12:30:00+05:30"}
        point = measurement(raw, hourly=False, pollutant="no2", unit="ppb", source="openaq_archive")
        self.assertEqual(point["observed_at"], "2026-09-16T07:00:00Z")
        self.assertEqual(point["unit"], "ppb")
        self.assertFalse(point["fresh"])

    def test_station_has_no_assumed_radius(self):
        station = station_from_location(location())
        self.assertIsNone(station["representativeness_radius_km"])
        self.assertIsNone(station["search_distance_km"])
        self.assertEqual(station["location_precision"], "station_point")
        raw = location()
        raw["coordinates"].update({"latitude": 19.07, "longitude": 72.88})
        self.assertIsNotNone(station_from_location(raw))
        raw["coordinates"].update({"latitude": 0.0, "longitude": 72.88})
        self.assertIsNone(station_from_location(raw))

    def test_mobile_and_unknown_station_coordinates_are_not_labelled_fixed(self):
        raw = location()
        raw["isMobile"] = True
        self.assertEqual(station_from_location(raw)["location_precision"], "mobile_initial_point")
        raw.pop("isMobile")
        self.assertEqual(station_from_location(raw)["location_precision"], "mobility_unknown_point")


class ForecastTests(unittest.TestCase):
    def test_forecast_orders_rows_and_uses_persistence(self):
        points = history_points()
        forecast = build_forecast(list(reversed(points)), now=NOW)
        self.assertEqual(forecast["status"], "research_forecast")
        self.assertFalse(forecast["trained_model"])
        self.assertEqual({p["horizon_hours"] for p in forecast["points"]}, {1, 3, 4})
        self.assertTrue(all(p["value"] == points[-1]["value"] for p in forecast["points"]))
        for metric in forecast["evaluation"]["horizons"]:
            self.assertGreaterEqual(metric["test_rows"], 8)
            self.assertLessEqual(metric["empirical_coverage"], 1)

    def test_holdout_does_not_influence_interval_calibration(self):
        points = history_points()
        original = build_forecast(points, now=NOW)
        altered = copy.deepcopy(points)
        for row in altered[len(altered) * 3 // 4:]:
            row["value"] += 1000
        changed = build_forecast(altered, now=NOW)
        original_metrics = original["evaluation"]["horizons"]
        changed_metrics = changed["evaluation"]["horizons"]
        self.assertEqual([p["interval_half_width"] for p in original_metrics], [p["interval_half_width"] for p in changed_metrics])
        self.assertNotEqual(original_metrics[0]["mae"], changed_metrics[0]["mae"])
        for metric in original_metrics:
            lookup = {p["observed_at"]: p["value"] for p in points}
            for row in metric["test_predictions"]:
                self.assertLess(row["origin_at"], row["target_at"])
                self.assertEqual(row["prediction"], lookup[row["origin_at"]])

    def test_future_samples_and_conflicting_duplicates_cannot_enter_fit(self):
        points = history_points()
        points.append(measurement(raw_hour(500, NOW + timedelta(hours=1))))
        conflicting = copy.deepcopy(points[0])
        conflicting["value"] = 123456
        points.append(conflicting)
        accepted = accepted_series(points, NOW)
        self.assertEqual(len(accepted), 95)
        self.assertTrue(all(p["observed_at"] <= iso(NOW) for p in accepted))

    def test_stale_series_has_evaluation_but_no_current_points(self):
        result = build_forecast(history_points(), now=NOW + timedelta(hours=4))
        self.assertEqual(result["status"], "stale_input")
        self.assertEqual(result["evaluation"]["status"], "evaluated")
        self.assertEqual(result["points"], [])

    def test_mixed_station_or_unit_and_sparse_history_are_blocked(self):
        points = history_points()
        mixed = copy.deepcopy(points)
        mixed[-1]["station_id"] = 99
        self.assertEqual(build_forecast(mixed, now=NOW)["status"], "mixed_series")
        mixed[-1]["station_id"] = 17
        mixed[-1]["unit"] = "mg/m³"
        self.assertEqual(build_forecast(mixed, now=NOW)["status"], "mixed_series")
        self.assertEqual(build_forecast(history_points(168)[::3], now=NOW)["status"], "insufficient_coverage")

    def test_forecast_points_in_past_are_not_shown(self):
        result = build_forecast(history_points(), now=NOW + timedelta(hours=2))
        self.assertEqual([p["horizon_hours"] for p in result["points"]], [3, 4])


class CandidateTests(unittest.TestCase):
    @staticmethod
    def histories():
        result = []
        for sid in (17, 235):
            points = history_points(station_id=sid)
            points[-1]["value"] = 150
            result.append({"points": points})
        return result

    def test_single_spike_is_not_a_corroborated_candidate(self):
        candidates, meta = build_candidates(self.histories()[:1], [station_from_location(location())], now=NOW)
        self.assertEqual(candidates, [])
        self.assertEqual(meta["uncorroborated_anomalies"], 1)

    def test_concurrent_station_spikes_request_review_without_source_claim(self):
        candidates, _ = build_candidates(self.histories(), [station_from_location(location(sid)) for sid in (17, 235)], now=NOW)
        self.assertEqual(len(candidates), 2)
        for candidate in candidates:
            self.assertEqual(candidate["cause"], "unverified")
            self.assertFalse(candidate["enforcement_allowed"])
            self.assertIsNone(candidate["representativeness_radius_km"])
            self.assertIsNone(candidate["source_attribution"])

    def test_stale_or_mixed_unit_corroboration_cannot_create_candidate(self):
        histories = self.histories()
        stations = [station_from_location(location(sid)) for sid in (17, 235)]
        self.assertEqual(build_candidates(histories, stations, now=NOW + timedelta(hours=4))[0], [])
        for point in histories[1]["points"]:
            point["unit"] = "mg/m³"
        self.assertEqual(build_candidates(histories, stations, now=NOW)[0], [])

    def test_mobile_and_unknown_mobility_cannot_corroborate_locality_candidate(self):
        for mobility in (True, None):
            stations = [station_from_location(location(sid)) for sid in (17, 235)]
            stations[1]["is_mobile"] = mobility
            candidates, metadata = build_candidates(self.histories(), stations, now=NOW)
            self.assertEqual(candidates, [])
            self.assertEqual(metadata["mobile_or_unknown_stations_excluded"], 1)


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        monitoring_service._CACHE.clear()
        monitoring_service._INFLIGHT.clear()
        monitoring_service._DISCOVERY_CACHE.clear()
        monitoring_service._DISCOVERY_INFLIGHT.clear()

    async def test_same_key_coalesces_and_third_unique_snapshot_is_rejected(self):
        release, first_started, both_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
        calls = []

        async def collect(station_id, pollutant, mode, timestamp, client, key, cache_key, use_cache):
            calls.append(station_id)
            first_started.set()
            if len(calls) == 2:
                both_started.set()
            await release.wait()
            result = monitoring_service._base_snapshot(timestamp, pollutant, mode)
            result["cache"] = {"hit": False}
            return result

        with patch.object(monitoring_service, "_collect_snapshot", side_effect=collect):
            first = asyncio.create_task(build_snapshot(station_id=17, api_key="test-only-key"))
            await first_started.wait()
            duplicate = asyncio.create_task(build_snapshot(station_id=17, api_key="test-only-key"))
            second = asyncio.create_task(build_snapshot(station_id=235, api_key="test-only-key"))
            await both_started.wait()
            rejected = await build_snapshot(station_id=99, api_key="test-only-key")
            self.assertEqual(rejected["status"], "overloaded")
            self.assertEqual(rejected["retry_after_seconds"], 15)
            self.assertEqual(rejected["network_requests"], 0)
            self.assertEqual(len(calls), 2)
            release.set()
            first_result, duplicate_result, _ = await asyncio.gather(first, duplicate, second)
        self.assertFalse(first_result["cache"]["coalesced"])
        self.assertTrue(duplicate_result["cache"]["coalesced"])
        self.assertEqual(monitoring_service._INFLIGHT, {})
        duplicate_result["stations"].append({"id": 123})
        self.assertEqual(first_result["stations"], [])

    async def test_disconnected_waiter_does_not_cancel_shared_work(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def collect(station_id, pollutant, mode, timestamp, client, key, cache_key, use_cache):
            started.set()
            await release.wait()
            result = monitoring_service._base_snapshot(timestamp, pollutant, mode)
            result["cache"] = {"hit": False}
            return result

        with patch.object(monitoring_service, "_collect_snapshot", side_effect=collect):
            first = asyncio.create_task(build_snapshot(api_key="test-only-key"))
            await started.wait()
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertEqual(len(monitoring_service._INFLIGHT), 1)
            second = asyncio.create_task(build_snapshot(api_key="test-only-key"))
            release.set()
            result = await second
            self.assertTrue(result["cache"]["coalesced"])
        self.assertEqual(monitoring_service._INFLIGHT, {})

    async def test_discovery_is_coalesced_cached_and_expires_at_sixty_seconds(self):
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def handler(request):
            calls.append(request)
            started.set()
            await release.wait()
            return httpx.Response(200, json={"results": [location()]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            fetcher = _Fetcher(client, "test-only-key", shared_discovery=True)
            first = asyncio.create_task(monitoring_service._discover_locations(fetcher))
            await started.wait()
            duplicate = asyncio.create_task(monitoring_service._discover_locations(fetcher))
            release.set()
            _, duplicate_result = await asyncio.gather(first, duplicate)
            self.assertTrue(duplicate_result[1]["discovery_cache"]["coalesced"])
            self.assertEqual(len(calls), 1)
            cached = await monitoring_service._discover_locations(fetcher)
            self.assertTrue(cached[1]["discovery_cache"]["hit"])
            cache_key = next(iter(monitoring_service._DISCOVERY_CACHE))
            inserted, cached_result = monitoring_service._DISCOVERY_CACHE[cache_key]
            monitoring_service._DISCOVERY_CACHE[cache_key] = (inserted - 61, cached_result)
            await monitoring_service._discover_locations(fetcher)
            self.assertEqual(len(calls), 2)

    async def test_discovery_and_snapshot_caches_have_entry_caps(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))) as client:
            for index in range(6):
                await monitoring_service._discover_locations(_Fetcher(client, f"test-key-{index}", shared_discovery=True))
            self.assertEqual(len(monitoring_service._DISCOVERY_CACHE), 4)
            async def build(fetcher, station_id, pollutant, mode, now):
                return monitoring_service._base_snapshot(now, pollutant, mode)
            with patch.object(monitoring_service, "_build", side_effect=build):
                for index in range(26):
                    await monitoring_service._collect_snapshot(index + 1, "pm25", "live", NOW, client, "test-only-key", (index,), True)
            self.assertEqual(len(monitoring_service._CACHE), 24)


class TrainedForecastTests(unittest.TestCase):
    @staticmethod
    def trend_points(count=168):
        points = history_points(count)
        for index, point in enumerate(points):
            point["value"] = 40 + index * 0.5
        return points

    def test_ridge_is_actually_fitted_and_selected_when_validation_improves(self):
        points = self.trend_points()
        forecast = build_forecast(points, now=NOW)
        self.assertEqual(forecast["status"], "research_forecast")
        self.assertTrue(forecast["trained_model"])
        self.assertEqual(forecast["evaluation"]["trained_candidate"]["status"], "fitted_and_compared")
        self.assertEqual(forecast["evaluation"]["trained_candidate"]["lags"], [1, 2, 3, 6, 24])
        self.assertTrue(any(point["value"] != points[-1]["value"] for point in forecast["points"]))
        for metric in forecast["evaluation"]["horizons"]:
            candidates = {candidate["model"]: candidate for candidate in metric["candidates"]}
            selected = candidates[metric["selected_model"]]
            self.assertEqual(selected["validation_mae"], min(candidate["validation_mae"] for candidate in candidates.values()))
            self.assertLess(metric["fit"]["training_target_to"], forecast["evaluation"]["calibration_start"])
            self.assertEqual(set(candidates), {"persistence", "ridge_autoregression"})

    def test_holdout_never_affects_ridge_selection_fit_or_intervals(self):
        points = self.trend_points()
        original = build_forecast(points, now=NOW)
        altered = copy.deepcopy(points)
        for point in altered[len(altered) * 80 // 100:]:
            point["value"] += 1000
        changed = build_forecast(altered, now=NOW)
        self.assertEqual(original["model"], changed["model"])
        for before, after in zip(original["evaluation"]["horizons"], changed["evaluation"]["horizons"]):
            self.assertEqual(before["selected_model"], after["selected_model"])
            self.assertEqual(before["fit"]["training_signature"], after["fit"]["training_signature"])
            self.assertEqual(before["interval_half_width"], after["interval_half_width"])
            self.assertNotEqual(before["mae"], after["mae"])
            for candidate_before, candidate_after in zip(before["candidates"], after["candidates"]):
                self.assertEqual(candidate_before["validation_mae"], candidate_after["validation_mae"])
                self.assertEqual(candidate_before["interval_half_width"], candidate_after["interval_half_width"])

    def test_every_evaluation_origin_is_at_or_after_its_fit_cutoff(self):
        forecast = build_forecast(self.trend_points(), now=NOW)
        for metric in forecast["evaluation"]["horizons"]:
            horizon = metric["horizon_hours"]
            self.assertGreaterEqual(metric["validation_origin_from"], metric["initial_training_target_to"])
            self.assertGreaterEqual(metric["calibration_origin_from"], metric["fit"]["training_target_to"])
            self.assertEqual(metric["validation_purged_rows"], horizon - 1)
            self.assertEqual(metric["calibration_purged_rows"], horizon - 1)
            self.assertEqual(metric["candidates"][0]["validation_rows"], 25 - (horizon - 1))
            self.assertEqual(metric["calibration_rows"], 25 - (horizon - 1))
            for prediction in metric["test_predictions"]:
                self.assertGreaterEqual(prediction["origin_at"], metric["fit"]["training_target_to"])

    def test_calibration_never_affects_selection_or_refitting(self):
        points = self.trend_points()
        original = build_forecast(points, now=NOW)
        for point in points[len(points) * 65 // 100:len(points) * 80 // 100]:
            point["value"] += 500
        changed = build_forecast(points, now=NOW)
        for before, after in zip(original["evaluation"]["horizons"], changed["evaluation"]["horizons"]):
            self.assertEqual(before["selected_model"], after["selected_model"])
            self.assertEqual(before["fit"]["training_signature"], after["fit"]["training_signature"])
            self.assertNotEqual(before["interval_half_width"], after["interval_half_width"])

    def test_trained_candidate_declines_short_history(self):
        forecast = build_forecast(self.trend_points(119), now=NOW)
        self.assertFalse(forecast["trained_model"])
        self.assertEqual(forecast["model"], "persistence")
        self.assertEqual(forecast["evaluation"]["trained_candidate"]["status"], "insufficient_data")

    def test_persistence_can_win_and_stale_ridge_remains_historical(self):
        constant = self.trend_points()
        for point in constant:
            point["value"] = 30
        forecast = build_forecast(constant, now=NOW)
        self.assertEqual(forecast["model"], "persistence")
        self.assertFalse(forecast["trained_model"])
        self.assertTrue(forecast["evaluation"]["trained_candidate"]["trained"])
        stale = build_forecast(self.trend_points(), now=NOW + timedelta(hours=4))
        self.assertEqual(stale["status"], "stale_input")
        self.assertTrue(stale["trained_model"])
        self.assertEqual(stale["points"], [])

    def test_missing_lags_do_not_trigger_an_untrained_ml_claim(self):
        points = self.trend_points(168)
        # >120 rows and >=75% total coverage, but insufficient exact lag pairs.
        points = [point for index, point in enumerate(points) if index % 6 != 0]
        forecast = build_forecast(points, now=NOW)
        self.assertFalse(forecast["trained_model"])
        self.assertEqual(forecast["model"], "persistence")
        self.assertEqual(forecast["evaluation"]["trained_candidate"]["status"], "insufficient_lag_coverage")


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_snapshot_uses_real_response_shape_and_keeps_key_on_openaq(self):
        requests = []

        def handler(request):
            requests.append(request)
            if request.url.host == "api.open-meteo.com":
                self.assertNotIn("X-API-Key", request.headers)
                return httpx.Response(200, json={"current": {"time": "2026-09-20T12:00", "temperature_2m": 28}, "current_units": {"temperature_2m": "°C"}})
            self.assertEqual(request.headers["X-API-Key"], "test-only-key")
            path = request.url.path
            if path == "/v3/locations":
                self.assertEqual(request.url.params["bbox"], "68.0,6.0,98.5,38.5")
                self.assertNotIn("radius", request.url.params)
                return httpx.Response(200, json={"meta": {"found": 1}, "results": [location()]})
            if path == "/v3/locations/17/latest":
                return httpx.Response(200, json={"results": [{"sensorsId": 1700, "locationsId": 17, "value": 45, "datetime": {"utc": iso(NOW)}}]})
            if path == "/v3/sensors/1700/hours":
                return httpx.Response(200, json={"results": [raw_hour(20 + i % 7, NOW - timedelta(hours=95 - i)) for i in range(96)]})
            raise AssertionError(f"Unexpected URL: {request.url}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            snapshot = await build_snapshot(now=NOW, client=client, api_key="test-only-key")
        self.assertEqual(snapshot["status"], "live")
        self.assertEqual(snapshot["forecast"]["status"], "research_forecast")
        self.assertEqual(len(snapshot["history"]["points"]), 96)
        self.assertEqual(snapshot["stations"][0]["measurements"][0]["value"], 45)
        self.assertEqual(snapshot["weather"]["kind"], "weather_model_estimate")
        self.assertEqual(len(requests), 4)
        self.assertNotIn("test-only-key", str(snapshot))

    async def test_pagination_string_total_is_bounded_and_not_claimed_complete(self):
        def handler(request):
            page = int(request.url.params["page"])
            return httpx.Response(200, json={"meta": {"found": ">100"}, "results": [{"id": page * 2}, {"id": page * 2 + 1}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch("src.services.monitoring_v2.PAGE_SIZE", 2):
                rows, meta = await _Fetcher(client, "test").pages("/locations", {}, 2)
        self.assertEqual(len(rows), 4)
        self.assertFalse(meta["complete"])
        self.assertEqual(meta["incomplete_reason"], "page_limit")
        self.assertIsNone(meta["total_reported"])
        self.assertEqual(meta["total_reported_raw"], ">100")

    async def test_repeated_page_and_partial_error_report_incomplete(self):
        def repeated(_request):
            return httpx.Response(200, json={"results": [{"id": 1}, {"id": 2}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(repeated)) as client:
            with patch("src.services.monitoring_v2.PAGE_SIZE", 2):
                rows, meta = await _Fetcher(client, "test").pages("/locations", {}, 4)
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta["incomplete_reason"], "repeated_page")
        self.assertFalse(meta["complete"])

    async def test_missing_key_uses_delayed_archive_and_preserves_gas_unit(self):
        def handler(request):
            self.assertNotIn("X-API-Key", request.headers)
            if request.url.host == "api.open-meteo.com":
                return httpx.Response(503)
            self.assertEqual(request.url.host, "openaq-data-archive.s3.amazonaws.com")
            sid = 17 if "locationid=17/" in request.url.path else 235
            data = "location_id,sensors_id,location,datetime,lat,lon,parameter,units,value\n"
            data += f"{sid},{sid * 100},Archive test,2026-09-16T12:30:00+05:30,28.56,77.18,no2,ppb,12\n"
            return httpx.Response(200, content=gzip.compress(data.encode()))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            snapshot = await build_snapshot(pollutant="no2", now=NOW, client=client, api_key="")
        self.assertEqual(snapshot["status"], "delayed")
        self.assertEqual(snapshot["history"]["unit"], "ppb")
        self.assertEqual(snapshot["history"]["points"][0]["value"], 12)
        self.assertFalse(snapshot["history"]["points"][0]["fresh"])
        self.assertEqual(snapshot["forecast"]["points"], [])
        self.assertEqual(snapshot["candidates"], [])
        self.assertFalse(snapshot["coverage"]["complete"])
        self.assertEqual(snapshot["network_requests"], 7)

    async def test_upstream_error_never_becomes_mock_data_or_leaks_body(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403, text="private upstream error"))) as client:
            snapshot = await build_snapshot(now=NOW, client=client, api_key="test-only-key")
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertEqual(snapshot["stations"], [])
        self.assertEqual(snapshot["history"]["points"], [])
        self.assertNotIn("private upstream error", str(snapshot))

    async def test_unavailable_archive_has_no_hardcoded_station_values(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as client:
            snapshot = await build_snapshot(now=NOW, client=client, api_key="")
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertEqual(snapshot["stations"], [])
        self.assertEqual(snapshot["history"]["points"], [])


if __name__ == "__main__":
    unittest.main()
