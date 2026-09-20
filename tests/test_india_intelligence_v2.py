"""Offline tests for national/model fallback contracts; fixtures are synthetic."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import httpx

from src.services.india_intelligence_v2 import (
    NATIONAL_WATCHLIST, assess_location, india_overview, search_india_places, validate_coordinates,
)


NOW = datetime(2026, 9, 20, 12, 30, tzinfo=timezone.utc)


def model_payload(latitude=28.6, longitude=77.2, *, rise=True):
    times = [(NOW.replace(minute=0) + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M") for offset in range(-12, 7)]
    values = [40 + (index % 2) for index in range(13)]
    values.extend([55, 68, 84, 78, 70, 62] if rise else [42, 43, 42, 41, 40, 39])
    return {
        "latitude": latitude, "longitude": longitude,
        "current_units": {"time": "iso8601", "pm2_5": "μg/m³"},
        "current": {"time": NOW.replace(minute=0).strftime("%Y-%m-%dT%H:%M"), "pm2_5": values[12]},
        "hourly_units": {"time": "iso8601", "pm2_5": "μg/m³"},
        "hourly": {"time": times, "pm2_5": values},
    }


class IndiaIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    def test_coordinate_contract_rejects_outside_india_operating_bounds(self):
        self.assertEqual((19.076, 72.8777), validate_coordinates(19.076, 72.8777))
        for coordinates in ((0, 77), (28, 120), (float("nan"), 77)):
            with self.assertRaises(ValueError):
                validate_coordinates(*coordinates)

    async def test_place_search_filters_to_india_and_keeps_source_boundary(self):
        def handler(request):
            self.assertEqual("IN", request.url.params["countryCode"])
            return httpx.Response(200, json={"results": [
                {"id": 1, "name": "Rohini", "country_code": "IN", "latitude": 28.74, "longitude": 77.11,
                 "admin1": "Delhi", "postcodes": ["110085"], "timezone": "Asia/Kolkata"},
                {"id": 2, "name": "Outside", "country_code": "XX", "latitude": 28.7, "longitude": 77.1},
            ]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await search_india_places("Rohini", client=client)
        self.assertEqual(1, len(result["places"]))
        self.assertEqual("Rohini, Delhi", result["places"][0]["label"])
        self.assertIn("not authoritative", result["boundary_warning"])

    async def test_no_monitor_uses_coarse_model_without_claiming_micro_aqi(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=model_payload()))) as client:
            result = await assess_location(28.6139, 77.209, "pm25", "Delhi", now=NOW, client=client, openaq_key="")
        self.assertEqual("model_estimate_only", result["status"])
        self.assertEqual("not_configured", result["ground"]["status"])
        self.assertEqual(45, result["model"]["spatial_resolution_km"])
        self.assertFalse(result["model"]["official_aqi"])
        self.assertFalse(result["model"]["micro_area_measurement"])
        self.assertEqual("model_spike_watch", result["model"]["spike_screen"]["status"])
        self.assertEqual("local_sensor_evidence_required", result["micro_area"]["status"])

    async def test_national_watchlist_is_bounded_and_other_places_are_on_demand(self):
        payloads = [model_payload(city[2], city[3], rise=False) for city in NATIONAL_WATCHLIST]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payloads))) as client:
            result = await india_overview("pm25", now=NOW, client=client)
        self.assertEqual(len(NATIONAL_WATCHLIST), len(result["cities"]))
        self.assertTrue(result["coverage"]["on_demand_search"])
        self.assertFalse(result["coverage"]["all_india_places_preloaded"])
        self.assertTrue(all(city["model"]["official_aqi"] is False for city in result["cities"]))


if __name__ == "__main__":
    unittest.main()
