import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.api import operational


class WarningApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(operational.app)

    def tearDown(self):
        operational.app.dependency_overrides.clear()
        self.client.close()

    def test_authority_endpoint_fails_closed(self):
        response = self.client.get('/v2/authority/early-warning', headers={'X-User-Email': 'admin@example.invalid'})
        self.assertEqual(response.status_code, 401)

    def test_coordinate_pair_required_and_bounded(self):
        for path in ('?latitude=28', '?longitude=77', '?latitude=0&longitude=77', '?latitude=nan&longitude=77'):
            self.assertEqual(self.client.get('/v2/early-warning'+path).status_code, 422)

    def test_public_sources_kept_separate(self):
        with patch.object(operational, 'build_early_warning', AsyncMock(return_value={'status': 'partial', 'alerts': []})), \
             patch.object(operational, 'get_source_context', AsyncMock(return_value={'sources': [{'id': 'nasa_firms', 'status': 'not_configured'}]})):
            response = self.client.get('/v2/early-warning')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['official_context']['sources'][0]['status'], 'not_configured')
        self.assertEqual(response.json()['operating_mode'], 'on_request_cached_screening')
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_failure_is_not_all_clear_or_secret_exception(self):
        with patch.object(operational, 'build_early_warning', AsyncMock(side_effect=RuntimeError('SECRET_SENTINEL'))), \
             patch.object(operational, 'get_source_context', AsyncMock(side_effect=RuntimeError('SECRET_SENTINEL'))):
            response = self.client.get('/v2/early-warning')
        self.assertEqual(response.json()['status'], 'unavailable')
        self.assertNotIn('SECRET_SENTINEL', response.text)

    def test_authorized_feed_and_monitoring_station_screen(self):
        operational.app.dependency_overrides[operational.require_authority] = lambda: {'email': 'fixture@example.invalid'}
        with patch.object(operational, 'build_early_warning', AsyncMock(return_value={'status': 'available'})), \
             patch.object(operational, 'get_source_context', AsyncMock(return_value={'sources': []})):
            self.assertEqual(self.client.get('/v2/authority/early-warning').status_code, 200)
        with patch.object(operational, 'build_snapshot', AsyncMock(return_value={'status': 'unavailable'})):
            self.assertIn('station_warning', self.client.get('/v2/monitoring').json())


if __name__ == '__main__':
    unittest.main()
