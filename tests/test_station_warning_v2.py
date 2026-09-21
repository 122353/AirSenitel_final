"""Synthetic, offline regression cases; these are never production readings."""
import copy
import math
import unittest
from datetime import datetime, timedelta, timezone

import httpx

from src.services.forecast_v2 import iso
from src.services.monitoring_v2 import build_snapshot
from src.services.station_warning_v2 import screen_station

NOW = datetime(2026, 9, 21, 12, 30, tzinfo=timezone.utc)


def snapshot():
    origin = NOW.replace(minute=0)
    points = [{"station_id": 1, "sensor_id": 10, "pollutant": "pm25", "unit": "µg/m³",
               "observed_at": iso(origin-timedelta(hours=i)), "value": 30.0,
               "quality": {"status": "valid"}, "averaging_period": "hour"}
              for i in reversed(range(48))]
    return {"selected_station_id": 1, "selected_pollutant": "pm25", "requested_mode": "live",
            "stations": [{"id": 1, "name": "Test-only station", "is_mobile": False}],
            "history": {"points": points},
            "forecast": {"station_id": 1, "sensor_id": 10, "pollutant": "pm25", "unit": "µg/m³",
                         "origin_at": iso(origin), "status": "research_forecast", "trained_model": True,
                         "model_label": "Test fixture model", "evaluation": {"status": "evaluated"},
                         "points": [{"observed_at": iso(origin+timedelta(hours=i)), "value": value,
                                     "unit": "µg/m³"} for i, value in ((1, 46), (3, 68), (4, 42))]}}


class StationWarningTests(unittest.TestCase):
    def test_first_crossing_not_peak_sets_lead(self):
        result = screen_station(snapshot(), now=NOW)
        self.assertEqual(result['status'], 'forecast_watch')
        self.assertEqual(result['lead_time_hours'], .5)
        self.assertEqual(result['peak_value'], 68)
        self.assertFalse(result['operationally_validated'])

    def test_two_hours_rise_is_observed_not_pre_event(self):
        data = snapshot()
        for row in data['history']['points'][-2:]:
            row['value'] = 80
        result = screen_station(data, now=NOW)
        self.assertEqual(result['status'], 'observed_rise')
        self.assertIsNone(result['lead_time_hours'])
        self.assertIsNone(result['first_crossing_at'])

    def test_single_spike_not_confirmed_and_not_future(self):
        data = snapshot()
        data['history']['points'][-1]['value'] = 80
        self.assertEqual(screen_station(data, now=NOW)['status'], 'no_qualified_signal')

    def test_stale_archive_or_mobile_cannot_warn(self):
        data = snapshot()
        self.assertEqual(screen_station(data, now=NOW+timedelta(hours=4))['status'], 'stale_input')
        data['requested_mode'] = 'archive'
        self.assertEqual(screen_station(data, now=NOW)['status'], 'archive')
        data['requested_mode'] = 'live'
        data['stations'][0]['is_mobile'] = True
        self.assertEqual(screen_station(data, now=NOW)['status'], 'station_not_fixed')

    def test_missing_or_provisional_hour_blocks_screen(self):
        for mutation in ('missing', 'provisional', 'negative', 'nan', 'duplicate_conflict'):
            data = snapshot()
            row = data['history']['points'][-5]
            if mutation == 'missing': data['history']['points'].remove(row)
            if mutation == 'provisional': row['quality']['status'] = 'provisional'
            if mutation == 'negative': row['value'] = -1
            if mutation == 'nan': row['value'] = float('nan')
            if mutation == 'duplicate_conflict': data['history']['points'].append({**copy.deepcopy(row), 'value': 100})
            self.assertEqual(screen_station(data, now=NOW)['status'], 'insufficient_data', mutation)

    def test_mixed_sensor_rejected(self):
        data = snapshot()
        data['history']['points'][-4]['sensor_id'] = 11
        self.assertEqual(screen_station(data, now=NOW)['status'], 'insufficient_data')

    def test_forecast_wrong_identity_origin_or_quality_not_used(self):
        for key, value in (('sensor_id', 11), ('unit', 'ppb'), ('origin_at', iso(NOW-timedelta(days=1))),
                           ('status', 'stale_input'), ('evaluation', {'status': 'insufficient_data'})):
            data = snapshot()
            data['forecast'][key] = value
            self.assertEqual(screen_station(data, now=NOW)['status'], 'no_qualified_signal', key)

    def test_mass_unit_conversion_preserves_screen_not_gas_guess(self):
        data = snapshot()
        for row in data['history']['points']:
            row['unit'] = 'mg/m³'; row['value'] /= 1000
        data['forecast']['unit'] = 'mg/m³'
        for row in data['forecast']['points']:
            row['unit'] = 'mg/m³'; row['value'] /= 1000
        self.assertEqual(screen_station(data, now=NOW)['status'], 'forecast_watch')
        for row in data['history']['points']: row['unit'] = 'ppb'
        self.assertEqual(screen_station(data, now=NOW)['status'], 'unsupported_unit')


class RealSnapshotContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_snapshot_fields_flow_into_observed_rise(self):
        import httpx
        from src.services.monitoring_v2 import build_snapshot
        from tests.test_monitoring_v2 import location, raw_hour
        origin = NOW.replace(minute=0)
        hours = [raw_hour(80 if i < 2 else 30, origin-timedelta(hours=i)) for i in reversed(range(96))]
        def handler(request):
            if request.url.path == '/v3/locations':
                return httpx.Response(200, json={'meta':{'found':1}, 'results':[location(17)]})
            if request.url.path.endswith('/latest'):
                return httpx.Response(200, json={'meta':{'found':1}, 'results':[{'sensorsId':1700,'locationsId':17,'value':80,'datetime':{'utc':iso(origin)}}]})
            if request.url.path.endswith('/hours'):
                return httpx.Response(200, json={'meta':{'found':96}, 'results':hours})
            return httpx.Response(200, json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            data = await build_snapshot(station_id=17, pollutant='pm25', now=NOW, client=client, api_key='fixture-key')
        self.assertEqual(data['selected_pollutant'], 'pm25')
        self.assertEqual(screen_station(data, now=NOW)['status'], 'observed_rise')
        data['requested_mode'] = 'archive'
        self.assertEqual(screen_station(data, now=NOW)['status'], 'archive')


if __name__ == '__main__':
    unittest.main()
