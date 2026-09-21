"""Offline synthetic spike feed and private review boundary regression tests."""
import copy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api import operational
from src.services import case_store_v2 as store
from src.services.forecast_v2 import iso
from src.services.spikes_v2 import spike_feed, verification_report


NOW = datetime(2026, 9, 21, 12, 30, tzinfo=timezone.utc)


def snapshot(now=NOW):
    origin = now.replace(minute=0, second=0, microsecond=0)
    return {
        'status': 'live', 'generated_at': iso(now), 'requested_mode': 'live',
        'selected_station_id': 17, 'selected_pollutant': 'pm25',
        'stations': [
            {'id': 17, 'name': 'Synthetic test station', 'latitude': 28.7, 'longitude': 77.1, 'is_mobile': False},
            {'id': 18, 'name': 'Synthetic peer station', 'latitude': 28.8, 'longitude': 77.2, 'is_mobile': False},
        ],
        'history': {'points': [
            {'station_id': 17, 'sensor_id': 1700, 'pollutant': 'pm25', 'unit': 'µg/m³',
             'observed_at': iso(origin-timedelta(hours=i)), 'value': 80 if i < 2 else 30,
             'quality': {'status': 'valid'}, 'averaging_period': 'hour', 'source': 'openaq_v3'}
            for i in reversed(range(48))]},
        'sources': [{'id': 'openaq_v3', 'status': 'live', 'live': True}],
        'coverage': {'returned': 700, 'complete': True, 'latest_stations_requested': 2},
        'candidate_status': {'stations_evaluated': 2}, 'candidates': [],
    }


def candidate(station_id=18, now=NOW):
    stamp = iso(now.replace(minute=0, second=0, microsecond=0))
    return {'station_id': station_id, 'name': 'Synthetic candidate', 'pollutant': 'pm25',
            'unit': 'µg/m³', 'observed_at': stamp, 'value': 80, 'baseline': 30,
            'screening_threshold': 15, 'status': 'human_review_required',
            'corroboration': [{'station_id': 17 if station_id == 18 else 18,
                               'observed_at': stamp, 'value': 80, 'baseline': 30, 'station_distance_km': 15}]}


class SpikeFeedTests(unittest.TestCase):
    def test_observed_feed_is_unverified_and_coverage_is_explicit(self):
        feed = spike_feed(snapshot(), now=NOW)
        event = feed['events'][0]
        self.assertEqual(event['verification_status'], 'unverified')
        self.assertEqual(event['basis'], 'two_consecutive_hourly_rises')
        self.assertEqual(event['value'], 80)
        self.assertAlmostEqual(event['threshold'], 40.5)
        self.assertFalse(event['enforcement_allowed'])
        self.assertFalse(event['official_aqi'])
        self.assertIsNone(event['representativeness_radius_km'])
        self.assertFalse(feed['coverage']['continuously_monitored_all_india'])
        self.assertEqual(feed['coverage']['latest_stations_requested'], 2)
        self.assertEqual(feed['refresh_seconds'], 60)
        self.assertEqual(feed['external_notifications'], 'not_connected')
        self.assertNotIn('forecast', feed)

    def test_forecasts_cannot_enter_measured_event_list(self):
        data = snapshot()
        for row in data['history']['points']:
            row['value'] = 30
        data['station_warning'] = {'status': 'observed_rise', 'current': 900}  # Never trust a prefilled screen.
        data['forecast'] = {'status': 'research_forecast', 'station_id': 17, 'sensor_id': 1700,
                            'pollutant': 'pm25', 'unit': 'µg/m³',
                            'origin_at': data['history']['points'][-1]['observed_at'],
                            'evaluation': {'status': 'evaluated'},
                            'points': [{'observed_at': iso(NOW+timedelta(hours=1)), 'value': 200, 'unit': 'µg/m³'}]}
        feed = spike_feed(data, now=NOW)
        self.assertEqual(feed['station_warning']['status'], 'forecast_watch')
        self.assertEqual(feed['events'], [])

    def test_archived_stale_failed_and_provisional_evidence_cannot_enter(self):
        self.assertEqual(spike_feed(snapshot(), now=NOW+timedelta(hours=4))['events'], [])
        for mutation in ('archive', 'no_live_source', 'unavailable', 'provisional', 'mobile'):
            data = snapshot()
            data['candidates'] = [candidate()]
            if mutation == 'archive': data['requested_mode'] = 'archive'
            if mutation == 'no_live_source': data['sources'][0]['live'] = False
            if mutation == 'unavailable': data['status'] = 'unavailable'
            if mutation == 'provisional':
                data['candidates'] = []
                data['history']['points'][-1]['quality']['status'] = 'provisional'
            if mutation == 'mobile':
                for station in data['stations']: station['is_mobile'] = True
            self.assertEqual(spike_feed(data, now=NOW)['events'], [], mutation)

    def test_peer_candidates_use_absolute_threshold_and_are_deduplicated(self):
        data = snapshot()
        data['candidates'] = [candidate(), candidate(17)]
        events = spike_feed(data, now=NOW)['events']
        self.assertEqual(len(events), 2)
        peer = next(e for e in events if e['station_id'] == 18)
        self.assertEqual(peer['threshold'], 45)
        selected = next(e for e in events if e['station_id'] == 17)
        self.assertEqual(selected['basis'], 'two_consecutive_hourly_rises')
        self.assertEqual(len(selected['corroboration']), 1)

    def test_peer_future_stale_wrong_pollutant_or_self_corroboration_rejected(self):
        for mutation in ('future', 'stale', 'wrong_pollutant', 'self', 'no_peers'):
            data = snapshot()
            item = candidate()
            if mutation == 'future': item['observed_at'] = iso(NOW+timedelta(hours=1))
            if mutation == 'stale': item['corroboration'][0]['observed_at'] = iso(NOW-timedelta(hours=4))
            if mutation == 'wrong_pollutant': item['pollutant'] = 'no2'
            if mutation == 'self': item['corroboration'][0]['station_id'] = 18
            if mutation == 'no_peers': item['corroboration'] = []
            data['candidates'] = [item]
            self.assertEqual([e['station_id'] for e in spike_feed(data, now=NOW)['events']], [17], mutation)

    def test_ids_bind_source_revision_and_report_does_not_invent_citizen_measurement(self):
        data = snapshot()
        first = spike_feed(data, now=NOW)['events'][0]
        data['history']['points'][-1]['value'] = 81
        second = spike_feed(data, now=NOW)['events'][0]
        self.assertNotEqual(first['id'], second['id'])
        report = verification_report(first, 'Please inspect this observed rise.')
        self.assertNotIn('reading', report)
        self.assertIn(first['id'], report['description'])
        self.assertIn('not a verified event', report['description'])
        self.assertEqual(report['latitude'], 28.7)


class SpikeApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'AIRSENTINEL_ENV': 'local', 'AIRSENTINEL_STORE': 'sqlite',
                             'AIRSENTINEL_SQLITE_PATH': str(Path(self.tmp.name)/'spikes.sqlite3'),
                             'CLERK_AUTHORIZED_PARTIES': 'http://localhost:3000'}, clear=True)
        self.env.start()
        store.initialize_store()
        self.client = TestClient(operational.app)
        self.now = datetime.now(timezone.utc)
        self.data = snapshot(self.now)
        self.source = patch.object(operational, 'build_snapshot', AsyncMock(return_value=self.data))
        self.build = self.source.start()
        self.event_id = spike_feed(self.data)['events'][0]['id']

    def tearDown(self):
        operational.app.dependency_overrides.clear()
        self.source.stop()
        self.client.close()
        self.env.stop()
        self.tmp.cleanup()

    def allow(self):
        actor = lambda: {'user_id': 'user_spike_test', 'email': 'spike-test@example.invalid'}
        operational.app.dependency_overrides[operational.require_user] = actor
        operational.app.dependency_overrides[operational.require_authority] = actor

    def payload(self, **changes):
        return {'station_id': 17, 'pollutant': 'pm25', 'event_id': self.event_id,
                'notes': 'Test-only request for independent review.', 'consent': True, **changes}

    def test_public_feed_query_validation_and_no_store_leak(self):
        response = self.client.get('/v2/spikes?station_id=17&pollutant=pm25')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['events'][0]['id'], self.event_id)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('receipt', response.text)
        self.assertNotIn('reporter_id', response.text)
        self.build.assert_called_once_with(station_id=17, pollutant='pm25', mode='live')
        self.assertEqual(self.client.get('/v2/spikes?pollutant=aqi').status_code, 422)
        self.assertEqual(self.client.get('/v2/spikes?station_id=-1').status_code, 422)

    def test_submission_authenticates_before_source_or_storage(self):
        response = self.client.post('/v2/spikes/verification', json=self.payload(), headers={'X-User-Email': 'admin@example.invalid'})
        self.assertEqual(response.status_code, 401)
        self.build.assert_not_called()
        self.assertEqual(store.list_reports(), [])

    def test_consent_strict_types_and_extra_evidence_are_rejected(self):
        self.allow()
        for changes in ({'consent': False}, {'consent': 'true'}, {'consent': 1},
                        {'value': 999}, {'station_id': '17'}, {'event_id': 'made-up'}, {'notes': 'x'*1501}):
            response = self.client.post('/v2/spikes/verification', json=self.payload(**changes))
            self.assertEqual(response.status_code, 422, str(changes))
        self.build.assert_not_called()

    def test_verified_submission_enters_private_queue_and_can_be_withdrawn(self):
        self.allow()
        response = self.client.post('/v2/spikes/verification', json=self.payload())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['status'], 'pending_review')
        self.assertEqual(response.json()['external_notifications'], 'not_connected')
        cases = self.client.get('/v2/authority/cases').json()['cases']
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['status'], 'pending_review')
        self.assertIn('VERIFICATION REQUEST', cases[0]['description'])
        self.assertIn(self.event_id, cases[0]['description'])
        receipt = response.json()['receipt']
        self.assertEqual(self.client.post('/v2/reports/withdraw', json={'receipt': receipt}).status_code, 200)
        withdrawn = store.list_reports()[0]
        self.assertEqual(withdrawn['status'], 'withdrawn')
        self.assertTrue(withdrawn['redacted'])
        self.assertNotIn('description', withdrawn)
        self.assertNotIn('latitude', withdrawn)

    def test_mismatch_revised_measurement_stale_or_forecast_rejected(self):
        self.allow()
        for mutation in ('identity', 'revision', 'stale', 'forecast', 'unavailable'):
            data = copy.deepcopy(self.data)
            if mutation == 'identity': data['selected_station_id'] = 18
            if mutation == 'revision': data['history']['points'][-1]['value'] = 81
            if mutation == 'stale':
                for row in data['history']['points']:
                    row['observed_at'] = iso(datetime.fromisoformat(row['observed_at'].replace('Z', '+00:00'))-timedelta(hours=5))
            if mutation == 'forecast':
                for row in data['history']['points']: row['value'] = 30
            if mutation == 'unavailable': data['status'] = 'unavailable'
            self.build.return_value = data
            response = self.client.post('/v2/spikes/verification', json=self.payload())
            self.assertEqual(response.status_code, 409, mutation)
        self.assertEqual(store.list_reports(), [])

    def test_peer_request_uses_original_selected_context(self):
        self.allow()
        self.data['candidates'] = [candidate(now=self.now)]
        peer = next(e for e in spike_feed(self.data)['events'] if e['station_id'] == 18)
        response = self.client.post('/v2/spikes/verification', json=self.payload(event_id=peer['id']))
        self.assertEqual(response.status_code, 201, response.text)
        self.build.assert_called_with(station_id=17, pollutant='pm25', mode='live')
        self.assertEqual(store.list_reports()[0]['latitude'], 28.8)

    def test_overload_preserved_without_false_empty_result(self):
        self.build.return_value = {'status': 'overloaded'}
        self.assertEqual(self.client.get('/v2/spikes').status_code, 429)
        self.allow()
        response = self.client.post('/v2/spikes/verification', json=self.payload())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['retry-after'], '60')
        self.assertEqual(store.list_reports(), [])


if __name__ == '__main__':
    unittest.main()
