"""Synthetic contracts for regional screening; these are not forecast-skill tests."""
from __future__ import annotations

import asyncio
import copy
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx

from src.services import early_warning_v2 as service
from src.services.forecast_v2 import iso

NOW = datetime(2026, 9, 21, 12, 30, tzinfo=timezone.utc)


def model_payload(latitude=28.6139, longitude=77.2090, *, values=None):
    times = [(NOW.replace(minute=0) + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M")
             for h in range(-12, 7)]
    hourly = {"time": times}
    for pollutant, field in service.POLLUTANT_FIELDS.items():
        baseline = 400 if pollutant == "co" else 40
        hourly[field] = [baseline] * 19
    hourly["pm2_5"] = values or [40] * 13 + [45, 60, 80, 70, 60, 50]
    return {"latitude": latitude, "longitude": longitude, "utc_offset_seconds": 0,
            "hourly": hourly, "hourly_units": {field: "μg/m³" for field in service.POLLUTANT_FIELDS.values()}}


def weather_payload(latitude=28.6139, longitude=77.2090):
    return {"latitude": latitude, "longitude": longitude, "utc_offset_seconds": 0,
            "current": {"time": "2026-09-21T12:15", "wind_speed_10m": 1.2,
                        "wind_direction_10m": 180, "relative_humidity_2m": 60, "precipitation": 0},
            "current_units": {"wind_speed_10m": "m/s", "wind_direction_10m": "°",
                              "relative_humidity_2m": "%", "precipitation": "mm"}}


class ScreeningTests(unittest.TestCase):
    def screen(self, payload, pollutant="pm25"):
        return service.screen_pollutant(payload, pollutant, NOW)

    def test_first_crossing_is_before_peak_and_uses_fractional_lead(self):
        result = self.screen(model_payload())
        self.assertEqual("forecast_watch", result["status"])
        self.assertEqual("2026-09-21T14:00:00Z", result["first_crossing_at"])
        self.assertEqual(1.5, result["lead_time_hours"])
        self.assertEqual("2026-09-21T15:00:00Z", result["peak_at"])
        self.assertEqual(54, result["threshold"])
        self.assertFalse(result["trained_model"])
        self.assertFalse(result["operationally_validated"])

    def test_current_exceedance_is_not_advance_warning_or_observation(self):
        payload = model_payload()
        payload["hourly"]["pm2_5"][12] = 70
        result = self.screen(payload)
        self.assertEqual("model_current_rise", result["status"])
        self.assertIsNone(result["first_crossing_at"])
        self.assertIsNone(result["lead_time_hours"])
        self.assertIn("not an advance warning", result["message"])

    def test_no_signal_is_not_a_safety_claim(self):
        result = self.screen(model_payload(values=[40] * 19))
        self.assertEqual("no_model_spike_signal", result["status"])
        self.assertIn("not a safety", result["message"])

    def test_pollutant_specific_absolute_floor(self):
        payload = model_payload()
        payload["hourly"]["carbon_monoxide"][-6:] = [520] * 6
        result = self.screen(payload, "co")
        self.assertEqual(600, result["threshold"])
        self.assertEqual("no_model_spike_signal", result["status"])
        payload["hourly"]["carbon_monoxide"][-5] = 700
        self.assertEqual("forecast_watch", self.screen(payload, "co")["status"])

    def test_negative_nonfinite_bool_and_missing_current_block(self):
        for value in (-1, float("nan"), float("inf"), True, None, "bad"):
            with self.subTest(value=value):
                payload = model_payload()
                payload["hourly"]["pm2_5"][12] = value
                result = self.screen(payload)
                self.assertEqual("insufficient_data", result["status"])
                self.assertIsNone(result["current"])

    def test_negative_or_missing_future_is_unknown_not_clear(self):
        for value in (-1, None, float("nan")):
            payload = model_payload()
            payload["hourly"]["pm2_5"][-6] = value
            result = self.screen(payload)
            self.assertEqual("insufficient_data", result["status"])
            self.assertEqual("incomplete_future_horizon", result["quality"]["reason"])

    def test_missing_or_gas_mixing_ratio_units_are_not_guessed(self):
        for unit in (None, "mg/m3", "ppm", "ppb", "unknown"):
            payload = model_payload()
            payload["hourly_units"]["pm2_5"] = unit
            result = self.screen(payload)
            self.assertEqual("insufficient_data", result["status"])
            self.assertEqual([], result["series"])

    def test_supported_microgram_unit_spellings(self):
        for unit in ("μg/m³", "µg/m³", "ug/m3", "ug/m^3"):
            payload = model_payload()
            payload["hourly_units"]["pm2_5"] = unit
            self.assertEqual("forecast_watch", self.screen(payload)["status"])

    def test_stale_model_does_not_become_fresh_on_fetch(self):
        payload = model_payload()
        payload["hourly"]["time"] = [(NOW.replace(minute=0) + timedelta(hours=h - 24)).isoformat()
                                      for h in range(-12, 7)]
        result = self.screen(payload)
        self.assertEqual("insufficient_data", result["status"])
        self.assertEqual("current_model_hour_missing_or_stale", result["quality"]["reason"])

    def test_conflicting_duplicate_timestamp_removed(self):
        payload = model_payload()
        payload["hourly"]["time"].append(payload["hourly"]["time"][12])
        payload["hourly"]["pm2_5"].append(500)
        result = self.screen(payload)
        self.assertEqual("insufficient_data", result["status"])
        self.assertEqual(1, result["quality"]["conflicting_timestamps"])

    def test_equal_duplicate_timestamp_not_extra_baseline_weight(self):
        payload = model_payload()
        payload["hourly"]["time"].append(payload["hourly"]["time"][0])
        payload["hourly"]["pm2_5"].append(40)
        result = self.screen(payload)
        self.assertEqual(12, result["quality"]["baseline_points"])
        self.assertEqual("forecast_watch", result["status"])

    def test_future_outside_six_hours_cannot_trigger(self):
        payload = model_payload(values=[40] * 19)
        payload["hourly"]["time"].append("2026-09-21T19:00")
        payload["hourly"]["pm2_5"].append(500)
        self.assertEqual("no_model_spike_signal", self.screen(payload)["status"])

    def test_insufficient_or_gapped_baseline_blocks_screen(self):
        for indices, reason in ((range(6), "insufficient_baseline"), (range(7, 10), "baseline_gap")):
            payload = model_payload()
            for index in indices:
                payload["hourly"]["pm2_5"][index] = None
            result = self.screen(payload)
            self.assertEqual("insufficient_data", result["status"])
            self.assertEqual(reason, result["quality"]["reason"])

    def test_timezone_mismatch_is_rejected(self):
        payload = model_payload()
        payload["utc_offset_seconds"] = 19800
        self.assertEqual("insufficient_data", self.screen(payload)["status"])

    def test_current_model_rise_survives_missing_future_without_forecast_claim(self):
        payload = model_payload()
        payload["hourly"]["pm2_5"][12] = 90
        payload["hourly"]["pm2_5"][-1] = None
        self.assertEqual("model_current_rise", self.screen(payload)["status"])

    def test_weather_negative_units_stale_and_range_checks(self):
        payload = weather_payload()
        self.assertEqual("available", service._weather(payload, NOW)["status"])
        payload["current"]["relative_humidity_2m"] = 150
        payload["current"]["wind_direction_10m"] = 361
        payload["current"]["precipitation"] = -1
        payload["current_units"]["wind_speed_10m"] = "km/h"
        result = service._weather(payload, NOW)
        self.assertEqual("unavailable", result["status"])
        self.assertFalse(result["used_in_spike_threshold"])
        payload = weather_payload()
        payload["current"]["time"] = "2026-09-20T12:00"
        self.assertEqual("unavailable", service._weather(payload, NOW)["status"])

    def test_cache_expiry_refreshes_on_hour_boundary(self):
        payload = {"generated_at": iso(NOW), "alerts": [], "locations": []}
        service._CACHE[("test",)] = (time.monotonic(), payload)
        self.assertIsNotNone(service._cache_get(("test",), NOW + timedelta(seconds=60)))
        self.assertIsNone(service._cache_get(("test",), NOW.replace(hour=13, minute=0)))

    def test_cache_recomputes_lead_and_never_serves_past_crossing(self):
        generated = NOW.replace(minute=59)
        alert = {"first_crossing_at": iso(NOW.replace(hour=13, minute=0)), "lead_time_hours": 1 / 60}
        payload = {"generated_at": iso(generated), "alerts": [alert],
                   "locations": [{"pollutants": {"pm25": copy.deepcopy(alert)}}]}
        service._CACHE[("crossing",)] = (time.monotonic(), payload)
        fresh = service._cache_get(("crossing",), generated + timedelta(seconds=30))
        self.assertAlmostEqual(0.008, fresh["alerts"][0]["lead_time_hours"], places=3)
        self.assertIsNone(service._cache_get(("crossing",), generated + timedelta(seconds=60)))


class EarlyWarningRequestTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        service._CACHE.clear()

    def handler(self, requests):
        def request_handler(request):
            requests.append(request)
            latitudes = [float(value) for value in request.url.params["latitude"].split(",")]
            longitudes = [float(value) for value in request.url.params["longitude"].split(",")]
            model = "air-quality-api" in request.url.host
            factory = model_payload if model else weather_payload
            rows = [factory(lat, lon) for lat, lon in zip(latitudes, longitudes)]
            return httpx.Response(200, json=rows if len(rows) > 1 else rows[0])
        return request_handler

    async def test_national_batch_covers_36_administrations_in_two_requests(self):
        requests = []
        async with httpx.AsyncClient(transport=httpx.MockTransport(self.handler(requests))) as client:
            result = await service.build_early_warning(now=NOW, client=client)
        self.assertEqual(2, len(requests))
        self.assertEqual(36, result["coverage"]["requested_locations"])
        self.assertEqual(36, result["coverage"]["states_uts_represented"])
        self.assertEqual(36, result["coverage"]["forecast_locations"])
        self.assertEqual("available", result["status"])
        self.assertFalse(result["coverage"]["all_india_places_preloaded"])
        self.assertFalse(result["coverage"]["continuously_monitored_all_india"])
        self.assertIsNone(result["summary"]["observed_rise_count"])
        self.assertEqual(36, result["summary"]["forecast_watch_count"])
        self.assertEqual(6, len(result["locations"][0]["pollutants"]))
        model_request = next(request for request in requests if "air-quality-api" in request.url.host)
        self.assertEqual("cams_global", model_request.url.params["domains"])
        self.assertEqual("7", model_request.url.params["forecast_hours"])
        self.assertEqual(6, len(model_request.url.params["hourly"].split(",")))

    async def test_coordinate_on_demand_outside_default_watchlist(self):
        requests = []
        async with httpx.AsyncClient(transport=httpx.MockTransport(self.handler(requests))) as client:
            result = await service.build_early_warning(24.58, 73.68, "Udaipur", now=NOW, client=client)
        self.assertEqual("on_demand_coordinate", result["coverage"]["mode"])
        self.assertEqual("Udaipur", result["locations"][0]["name"])
        self.assertEqual(1, len(result["locations"]))

    async def test_bad_coordinates_rejected_before_network(self):
        for coordinates in ((None, 77), (12, None), (0, 77), (27, 140), (True, 75), (float("nan"), 75)):
            with self.assertRaises(ValueError):
                await service.build_early_warning(*coordinates, now=NOW)

    async def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            await service.build_early_warning(now=NOW.replace(tzinfo=None))

    async def test_model_failure_never_empty_success_no_risk(self):
        def handler(request):
            if "air-quality-api" in request.url.host:
                return httpx.Response(429, json={"error": "rate limit"})
            return httpx.Response(200, json=weather_payload())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await service.build_early_warning(28.6139, 77.2090, now=NOW, client=client)
        self.assertEqual("unavailable", result["status"])
        self.assertEqual(6, result["summary"]["insufficient_count"])
        self.assertEqual("source_http_429", result["sources"][0]["reason"])
        self.assertIsNone(result["summary"]["observed_rise_count"])

    async def test_weather_failure_does_not_fabricate_or_block_model_watch(self):
        def handler(request):
            if "air-quality-api" in request.url.host:
                return httpx.Response(200, json=model_payload())
            return httpx.Response(500)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await service.build_early_warning(28.6139, 77.2090, now=NOW, client=client)
        self.assertEqual(1, result["summary"]["forecast_watch_count"])
        self.assertEqual("unavailable", result["locations"][0]["weather"]["status"])

    async def test_truncated_or_wrong_location_batch_not_misassigned(self):
        for payload in ([model_payload()], [model_payload(51.5, -0.1)] * 36):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))) as client:
                result = await service.build_early_warning(now=NOW, client=client)
            self.assertEqual("unavailable", result["status"])
            self.assertEqual(0, result["coverage"]["assessed_locations"])

    async def test_malformed_nested_payload_does_not_crash_or_signal(self):
        payload = {"latitude": 28.6139, "longitude": 77.2090, "hourly": [], "current": 1, "hourly_units": None}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))) as client:
            result = await service.build_early_warning(28.6139, 77.2090, now=NOW, client=client)
        self.assertEqual("unavailable", result["status"])

    async def test_coalesced_requests_and_cached_results_do_not_share_mutation(self):
        calls = []
        async def build(places, now, client):
            calls.append(places)
            await asyncio.sleep(0.02)
            return {"generated_at": iso(now), "alerts": [], "locations": [], "marker": "original"}
        with patch.object(service, "_build", side_effect=build):
            first, second = await asyncio.gather(service.build_early_warning(), service.build_early_warning())
            first["marker"] = "changed"
            cached = await service.build_early_warning()
        self.assertEqual(1, len(calls))
        self.assertEqual("original", second["marker"])
        self.assertEqual("original", cached["marker"])
        self.assertTrue(cached["cache"]["hit"])


if __name__ == "__main__":
    unittest.main()
