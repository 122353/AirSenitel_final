import importlib
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'AIRSENTINEL_ENV': 'local', 'AIRSENTINEL_STORE': 'sqlite',
            'AIRSENTINEL_SQLITE_PATH': str(Path(self.tmp.name) / 'api.sqlite3'),
            'CLERK_AUTHORIZED_PARTIES': 'http://localhost:3000'}, clear=True)
        self.env.start()
        from src.services.case_store_v2 import initialize_store
        from src.services.devices_v2 import initialize_devices
        initialize_store()
        initialize_devices()
        self.api = importlib.import_module('src.api.operational')
        self.client = TestClient(self.api.app)

    def tearDown(self):
        self.api.app.dependency_overrides.clear()
        self.client.close()
        self.env.stop()
        self.tmp.cleanup()

    def allow(self):
        actor = lambda: {'user_id': 'user_api_test', 'email': 'test@example.invalid'}
        self.api.app.dependency_overrides[self.api.require_user] = actor
        self.api.app.dependency_overrides[self.api.require_authority] = actor

    def test_private_boundaries_and_retired_api(self):
        for path in ['/v2/authority/session', '/v2/authority/cases', '/v2/authority/models', '/v2/authority/devices', '/v2/authority/local-observations', '/v2/authority/micro-candidates']:
            self.assertEqual(self.client.get(path, headers={'X-User-Email':'admin@example.invalid'}).status_code, 401)
        self.assertEqual(self.client.post('/v2/reports').status_code, 401)
        self.assertEqual(self.client.get('/v1/reports').status_code, 410)
        self.assertEqual(self.client.get('/v2/authority/cases').headers['cache-control'], 'no-store')

    def test_private_device_registration_and_immutable_ingestion(self):
        self.assertEqual(self.client.post('/v2/authority/devices', json={}).status_code, 401)
        self.allow()
        now = datetime.now(timezone.utc)
        registered = self.client.post('/v2/authority/devices', json={
            'physical_device_id':'API-TEST-NOT-A-PHYSICAL-DEVICE', 'name':'Test-only instrument',
            'latitude':28.72,'longitude':77.1,'location_accuracy_m':10,'environment':'outdoor',
            'calibration_reference':'Test fixture only', 'calibration_valid_until':(now+timedelta(days=30)).isoformat(),
            'supported_channels':[{'pollutant':'pm25','unit':'ug/m3'}]})
        self.assertEqual(registered.status_code, 201, registered.text)
        device_id = registered.json()['id']
        self.assertNotIn('physical_device_id', registered.json())
        payload = {'samples':[{'pollutant':'pm25','unit':'ug/m3','value':85,'observed_at':now.isoformat()}]}
        endpoint = '/v2/authority/devices/' + device_id + '/observations'
        self.assertEqual(self.client.post(endpoint, json=payload).status_code, 201)
        self.assertEqual(self.client.post(endpoint, json=payload).status_code, 409)
        self.assertEqual(len(self.client.get('/v2/authority/local-observations').json()['observations']), 1)
        self.assertEqual(self.client.get('/v2/authority/micro-candidates').json()['candidates'], [])

    def test_origin_and_body_size(self):
        self.allow()
        self.assertEqual(self.client.post('/v2/reports', headers={'Origin':'https://untrusted.invalid'}).status_code, 403)
        self.assertEqual(self.client.post('/v2/reports', content=b'x' * 1_500_001).status_code, 413)

    def test_report_photo_action_and_withdrawal(self):
        self.allow()
        image = Image.new('RGB', (20, 20), 'blue')
        data = BytesIO()
        exif = Image.Exif()
        exif[270] = 'Private camera metadata must not survive'
        image.save(data, 'JPEG', exif=exif)
        response = self.client.post('/v2/reports', data={'consent':'true','latitude':'28.72','longitude':'77.1',
            'description':'Test-only smoke observation for verification'}, files={'photo':('photo.jpg',data.getvalue(),'image/jpeg')})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['status'], 'pending_review')
        receipt = response.json()['receipt']
        cases = self.client.get('/v2/authority/cases').json()['cases']
        case = cases[0]
        picture = self.client.get('/v2/authority/cases/' + case['id'] + '/photo')
        self.assertEqual(picture.status_code, 200)
        self.assertEqual(dict(Image.open(BytesIO(picture.content)).getexif()), {})
        action = {'status':'under_review','notes':'Test-only review note','expected_version':case['version']}
        endpoint = '/v2/authority/cases/' + case['id'] + '/actions'
        self.assertEqual(self.client.post(endpoint,json=action).status_code, 200)
        self.assertEqual(self.client.post(endpoint,json=action).status_code, 409)
        self.assertEqual(self.client.post('/v2/reports/withdraw',json={'receipt':receipt}).status_code, 200)
        self.assertEqual(self.client.get('/v2/authority/cases/' + case['id'] + '/photo').status_code, 404)

    def test_invalid_photo_and_consent(self):
        self.allow()
        fields={'latitude':'28.72','longitude':'77.1','description':'Test-only observation','consent':'false'}
        self.assertEqual(self.client.post('/v2/reports',data=fields).status_code, 422)
        fields['consent']='true'
        self.assertEqual(self.client.post('/v2/reports',data=fields,files={'photo':('x.jpg',b'not-an-image','image/jpeg')}).status_code, 422)

    def test_data_route_validates_query_and_preserves_unavailable(self):
        self.assertEqual(self.client.get('/v2/monitoring?pollutant=imaginary').status_code, 422)
        with patch.object(self.api, 'build_snapshot', AsyncMock(return_value={'status':'unavailable','history':{'points':[]}})):
            result=self.client.get('/v2/monitoring')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['status'], 'unavailable')

    def test_monitoring_overload_returns_retry_after(self):
        with patch.object(self.api, 'build_snapshot', AsyncMock(return_value={'status':'overloaded','retry_after_seconds':15})):
            response = self.client.get('/v2/monitoring')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['retry-after'], '15')


if __name__ == '__main__':
    unittest.main()
