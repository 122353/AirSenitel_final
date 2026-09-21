"""Deterministic official-source tests; synthetic fixtures, no external calls."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx

from src.services import official_sources_v2 as sources

NOW = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)
KEYS = {"NASA_FIRMS_MAP_KEY": "", "FIRMS_MAP_KEY": "", "CPCB_DATA_GOV_API_KEY": "",
        "CPCB_DATA_GOV_RESOURCE_ID": sources.CPCB_RESOURCE}
FIRE_HEADER = "country_id,latitude,longitude,acq_date,acq_time,confidence,frp\n"


def government_record(**updates):
    return {"country": "India", "state": "Delhi", "city": "Delhi", "station": "Test station",
            "latitude": "28.6", "longitude": "77.2", "last_update": "21-09-2026 16:30:00",
            "pollutant_id": "PM2.5", "pollutant_min": "42", "pollutant_max": "71",
            "pollutant_avg": "58", **updates}


class OfficialSourcesTests(unittest.IsolatedAsyncioTestCase):
    async def _call(self, handler, *, env=None, latitude=None, longitude=None):
        with patch.dict(os.environ, {**KEYS, **(env or {})}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await sources.get_source_context(latitude, longitude, now=NOW, client=client)

    async def test_missing_credentials_never_call_upstream(self):
        result = await self._call(lambda request: self.fail("Unconfigured source must not make a request"))
        self.assertEqual(["not_configured", "not_configured"], [source["status"] for source in result["sources"]])
        self.assertEqual("india", result["scope"]["type"])

    async def test_government_fields_are_not_mislabelled_as_concentrations(self):
        def handler(request):
            self.assertEqual("api.data.gov.in", request.url.host)
            self.assertEqual("test-secret", request.url.params["api-key"])
            return httpx.Response(200, json={"total": 1, "records": [government_record()]})
        result = await self._call(handler, env={"CPCB_DATA_GOV_API_KEY": "test-secret"})
        source = result["sources"][1]
        row = source["records"][0]
        self.assertEqual("available", source["status"])
        self.assertEqual("2026-09-21T11:00:00Z", row["observed_at"])
        self.assertEqual(1, row["age_hours"])
        self.assertEqual(58, row["published_values"]["average"])
        self.assertIsNone(row["unit"])
        self.assertFalse(row["units_verified"])
        self.assertFalse(source["usable_for_concentration_forecast"])
        self.assertNotIn("test-secret", json.dumps(result))

    async def test_invalid_values_unknown_and_future_times_are_not_fresh(self):
        records = [government_record(pollutant_avg="NaN", pollutant_min="-1", last_update="not-a-time"),
                   government_record(station="Future station", last_update="22-09-2026 16:30:00"),
                   government_record(station="Invalid coordinates", latitude="Infinity")]
        result = await self._call(lambda request: httpx.Response(200, json={"total": 3, "records": records}),
                                  env={"CPCB_DATA_GOV_API_KEY": "x"})
        source = result["sources"][1]
        self.assertEqual("delayed", source["status"])
        self.assertEqual(0, source["freshness"]["fresh_records"])
        self.assertEqual(2, source["freshness"]["unknown_time_records"])
        self.assertEqual(1, source["coverage"]["records_rejected"])
        unknown = next(row for row in source["records"] if row["station"] == "Test station")
        self.assertIsNone(unknown["published_values"]["average"])
        self.assertIsNone(unknown["published_values"]["min"])

    async def test_government_pagination_respects_total_even_when_page_short(self):
        offsets = []
        def handler(request):
            offset = int(request.url.params["offset"])
            offsets.append(offset)
            return httpx.Response(200, json={"total": 2, "records": [government_record(station=f"Station {offset}")]})
        result = await self._call(handler, env={"CPCB_DATA_GOV_API_KEY": "x"})
        self.assertEqual([0, 1], offsets)
        self.assertFalse(result["sources"][1]["coverage"]["partial"])
        self.assertEqual(2, result["sources"][1]["coverage"]["records_received"])

    async def test_partial_page_failure_retains_evidence_without_claiming_complete(self):
        def handler(request):
            if request.url.params["offset"] == "0":
                return httpx.Response(200, json={"total": 2, "records": [government_record()]})
            return httpx.Response(429, text="sensitive upstream response")
        result = await self._call(handler, env={"CPCB_DATA_GOV_API_KEY": "never-echo-me"})
        self.assertEqual("partial", result["sources"][1]["status"])
        self.assertEqual(1, result["sources"][1]["coverage"]["records_returned"])
        self.assertNotIn("never-echo-me", json.dumps(result))
        self.assertNotIn("sensitive upstream", json.dumps(result))

    async def test_firms_is_context_and_local_radius_does_not_change_upstream_request(self):
        def handler(request):
            self.assertTrue(request.url.path.endswith("/VIIRS_NOAA20_NRT/IND/2"))
            return httpx.Response(200, text=FIRE_HEADER + "IND,28.7,77.1,2026-09-21,1015,n,14.2\nIND,19.0,72.8,2026-09-21,1000,h,12\n")
        result = await self._call(handler, env={"FIRMS_MAP_KEY": "secret-map-key"}, latitude=28.6, longitude=77.2)
        source = result["sources"][0]
        self.assertEqual(2, source["coverage"]["records_received"])
        self.assertEqual(1, source["coverage"]["records_in_scope"])
        self.assertEqual("satellite_fire_context", source["records"][0]["evidence_type"])
        self.assertEqual("nominal", source["records"][0]["confidence"])
        self.assertEqual(14.2, source["records"][0]["frp_mw"])
        self.assertEqual(100, result["scope"]["radius_km"])
        self.assertNotIn("secret-map-key", json.dumps(result))

    async def test_firms_stale_and_nonfinite_power_are_explicit(self):
        result = await self._call(lambda request: httpx.Response(200, text=FIRE_HEADER +
            "IND,28.6,77.2,2026-09-19,0100,l,Infinity\nIND,NaN,77.2,2026-09-21,0100,n,12\n"),
            env={"NASA_FIRMS_MAP_KEY": "x"})
        source = result["sources"][0]
        self.assertEqual("delayed", source["status"])
        self.assertEqual(1, source["coverage"]["records_rejected"])
        self.assertIsNone(source["records"][0]["frp_mw"])
        self.assertIn("low_or_unknown_confidence", source["records"][0]["quality_flags"])

    async def test_firms_error_never_exposes_key_in_url_or_body(self):
        def handler(request):
            raise httpx.ConnectError(f"Failure at {request.url}", request=request)
        result = await self._call(handler, env={"NASA_FIRMS_MAP_KEY": "secret-url-key"})
        self.assertEqual("unavailable", result["sources"][0]["status"])
        self.assertNotIn("secret-url-key", json.dumps(result))

    async def test_empty_fire_response_is_not_clean_air(self):
        result = await self._call(lambda request: httpx.Response(200, text=FIRE_HEADER), env={"NASA_FIRMS_MAP_KEY": "x"})
        self.assertEqual("available", result["sources"][0]["status"])
        self.assertTrue(result["sources"][0]["empty_does_not_mean_clean_air"])

    async def test_invalid_area_fails_before_network(self):
        for latitude, longitude in [(None, 77), (28, None), (float("nan"), 77), (28, 0)]:
            with self.assertRaises(ValueError):
                await self._call(lambda request: self.fail("Invalid area must not fetch"), latitude=latitude, longitude=longitude)

    async def test_resource_path_is_validated(self):
        result = await self._call(lambda request: self.fail("Invalid resource must not fetch"),
            env={"CPCB_DATA_GOV_API_KEY": "x", "CPCB_DATA_GOV_RESOURCE_ID": "../../other"})
        self.assertEqual("unavailable", result["sources"][1]["status"])

    async def test_size_cap_rejects_provider_payload(self):
        with patch.object(sources, "MAX_RESPONSE_BYTES", 30):
            result = await self._call(lambda request: httpx.Response(200, text=FIRE_HEADER), env={"NASA_FIRMS_MAP_KEY": "x"})
        self.assertEqual("unavailable", result["sources"][0]["status"])

    async def test_warm_cache_reuses_national_snapshot_and_does_not_alias_output(self):
        calls = []
        def handler(request):
            calls.append(request.url.host)
            return httpx.Response(200, text=FIRE_HEADER + "IND,28.6,77.2,2026-09-21,1000,n,12\n")
        with patch.object(sources, "_CACHE", sources.OrderedDict()):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                first = await sources._cached_source("nasa_firms", "test-cache-key", "", client, True)
                first["records"][0]["confidence"] = "edited-by-consumer"
                second = await sources._cached_source("nasa_firms", "test-cache-key", "", client, True)
        self.assertEqual(1, len(calls))
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual("nominal", second["records"][0]["confidence"])


class OfficialSourceConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_simultaneous_cold_calls_share_collection(self):
        import asyncio
        calls = []
        async def handler(request):
            calls.append(request.url.host)
            await asyncio.sleep(.01)
            return httpx.Response(200, text=FIRE_HEADER)
        with patch.object(sources, '_CACHE', sources.OrderedDict()):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                results = await asyncio.gather(*(sources._cached_source('nasa_firms', 'fixture-key', '', client, True) for _ in range(4)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sum(r['cache']['hit'] for r in results), 3)
        self.assertFalse(sources._SOURCE_LOCKS)

    async def test_conflicting_government_values_are_flagged(self):
        row = {'country':'India', 'station':'Fixture', 'pollutant_id':'PM2.5', 'latitude':28.6, 'longitude':77.2,
               'last_update':'21-09-2026 12:00:00', 'pollutant_min':'10', 'pollutant_max':'20', 'pollutant_avg':'30'}
        other = {**row, 'pollutant_avg':'40'}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'records':[row, other], 'total':2}))) as client:
            result = await sources._fetch_cpcb(client, 'fixture-key', sources.CPCB_RESOURCE)
        self.assertEqual(len(result['records']), 1)
        self.assertIn('average_outside_published_range', result['records'][0]['quality_flags'])
        self.assertIn('conflicting_duplicate', result['records'][0]['quality_flags'])


if __name__ == "__main__":
    unittest.main()
