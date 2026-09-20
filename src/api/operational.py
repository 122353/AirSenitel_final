"""Evidence API. Vercel and the local proxy mount this application at /api."""
from datetime import datetime, timezone
from io import BytesIO
import json
import os
import warnings

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from src.api.auth_v2 import configured_origins, require_authority, require_user
from src.services import case_store_v2 as store
from src.services import federation_v2 as federation
from src.services import devices_v2 as devices
from src.services.monitoring_v2 import build_snapshot
from src.services.india_intelligence_v2 import assess_location, india_overview, search_india_places

MAX_BODY = 1_500_000
MAX_PHOTO = 1_000_000
Image.MAX_IMAGE_PIXELS = 16_000_000
app = FastAPI(title='AirSentinel evidence API', version='2.0.0', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=configured_origins(), allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'], allow_credentials=False)


@app.middleware('http')
async def request_guards(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        if (origin and origin not in configured_origins()) or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Origin is not allowed.'}, status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                return JSONResponse({'detail': 'Request is too large.'}, status_code=413)
            body.extend(chunk)
        # Starlette BaseHTTPMiddleware replays the cached bounded body downstream.
        request._body = bytes(body)
    response = await call_next(request)
    response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'})
    return response


@app.exception_handler(store.StoreError)
async def store_error(request: Request, exc):
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)


@app.get('/health')
def health():
    return {'status': 'ok', 'version': '2.0.0', 'time': datetime.now(timezone.utc).isoformat(),
            'capabilities': {'ground_api_configured': bool(os.getenv('OPENAQ_API_KEY')),
                             'authority_auth_configured': bool(os.getenv('CLERK_SECRET_KEY')),
                             'store': store.store_health()}, 'external_notifications': 'not_connected'}


@app.api_route('/v1/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE'])
def retired(path: str):
    raise HTTPException(410, 'The insecure demonstration API is retired. Use the evidence-aware v2 API.')


@app.get('/v2/monitoring')
async def monitoring(station_id: int | None = Query(None, gt=0), pollutant: str = Query('pm25', pattern='^(pm25|pm10|no2|so2|o3|co)$'), mode: str = Query('live', pattern='^(live|archive)$')):
    result = await build_snapshot(station_id=station_id, pollutant=pollutant, mode=mode)
    if result.get('status') == 'overloaded':
        return JSONResponse(result, status_code=429, headers={'Retry-After': '15'})
    return result


@app.get('/v2/india/overview')
async def national_overview(pollutant: str = Query('pm25', pattern='^(pm25|pm10|no2|so2|o3|co)$')):
    return await india_overview(pollutant=pollutant)


@app.get('/v2/india/places')
async def india_places(query: str = Query(min_length=2, max_length=80), limit: int = Query(8, ge=1, le=20)):
    return await search_india_places(query=query, limit=limit)


@app.get('/v2/india/assessment')
async def india_assessment(
    latitude: float = Query(ge=6.0, le=38.5),
    longitude: float = Query(ge=68.0, le=98.5),
    pollutant: str = Query('pm25', pattern='^(pm25|pm10|no2|so2|o3|co)$'),
    label: str | None = Query(None, max_length=120),
):
    return await assess_location(latitude=latitude, longitude=longitude, pollutant=pollutant, label=label)


@app.get('/v2/session')
def session(actor=Depends(require_user)):
    return {'authenticated': True, 'email': actor['email']}


@app.get('/v2/authority/session')
def authority_session(actor=Depends(require_authority)):
    return {'authorized': True, 'email': actor['email']}


@app.get('/v2/authority/devices')
def registered_devices(actor=Depends(require_authority)):
    return {'devices': devices.list_devices(), 'verification_status': 'operator_attested_not_independently_verified'}


@app.post('/v2/authority/devices', status_code=201)
def register_device(payload: dict, actor=Depends(require_authority)):
    return devices.register_device(payload, actor)


@app.post('/v2/authority/devices/{device_id}/observations', status_code=201)
def ingest_device(device_id: str, payload: dict, actor=Depends(require_authority)):
    return devices.ingest_observations(device_id, payload, actor)


@app.get('/v2/authority/local-observations')
def local_observations(hours: int = Query(24, ge=1, le=72), actor=Depends(require_authority)):
    return devices.recent_observations(hours=hours, limit=2000)


@app.get('/v2/authority/micro-candidates')
def micro_candidates(actor=Depends(require_authority)):
    return devices.micro_candidates(devices.recent_observations(hours=2, limit=10000))


def sanitized_photo(raw, mime):
    if not raw:
        return None, None
    if len(raw) > MAX_PHOTO or mime not in {'image/jpeg', 'image/png'}:
        raise HTTPException(422, 'Use a JPEG or PNG photo smaller than 1 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in {'JPEG', 'PNG'}:
                    raise ValueError()
                image.load()
                image.thumbnail((1600, 1600))
                clean = Image.new('RGB', image.size, 'white')
                rgba = image.convert('RGBA')
                clean.paste(rgba, mask=rgba.getchannel('A'))
                output = BytesIO()
                clean.save(output, format='JPEG', quality=82)
                if output.tell() > MAX_PHOTO:
                    raise ValueError()
                return output.getvalue(), 'image/jpeg'
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Photo could not be safely decoded. Use a smaller JPEG or PNG.')


@app.post('/v2/reports', status_code=201)
async def create_report(request: Request, actor=Depends(require_user)):
    try:
        async with request.form(max_files=1, max_fields=8, max_part_size=MAX_PHOTO) as form:
            if form.get('consent') != 'true':
                raise HTTPException(422, 'Explicit storage consent is required.')
            reading_text = str(form.get('reading', '')).strip()
            if len(reading_text) > 4000:
                raise HTTPException(422, 'Reading metadata is too large.')
            photo = form.get('photo')
            raw = await photo.read(MAX_PHOTO + 1) if hasattr(photo, 'read') else b''
            clean, mime = await run_in_threadpool(sanitized_photo, raw, getattr(photo, 'content_type', ''))
            payload = {'description': str(form.get('description', '')).strip(),
                       'latitude': float(str(form.get('latitude', ''))),
                       'longitude': float(str(form.get('longitude', ''))),
                       'kind': 'photo_report' if clean else 'citizen_report', 'consent_to_store': True}
            if reading_text:
                payload['reading'] = json.loads(reading_text)
            result = await run_in_threadpool(store.create_report, payload, actor, clean, mime)
            return {'receipt': result['report']['id'] + '.' + result['receipt'], 'status': 'pending_review',
                    'message': 'Stored privately for human review. Not a verified source or an emergency service.'}
    except (ValueError, TypeError):
        raise HTTPException(422, 'Provide valid coordinates and reading metadata.')


class Withdrawal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    receipt: str = Field(min_length=40, max_length=180)


@app.post('/v2/reports/withdraw')
def withdraw(payload: Withdrawal):
    receipt = payload.receipt
    if len(receipt) > 180 or '.' not in receipt:
        raise HTTPException(404, 'Receipt not found.')
    report_id, token = receipt.split('.', 1)
    store.withdraw_report(report_id, token)
    return {'status': 'withdrawn', 'message': 'Report text, location, reading and photo withdrawn.'}


@app.get('/v2/authority/cases')
def cases(actor=Depends(require_authority)):
    return {'cases': store.list_reports(limit=100), 'external_notifications': 'not_connected',
            'message': 'Review queue only. No government dispatch or external alert has been sent.'}


class CaseAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = Field(pattern='^(under_review|needs_verification|closed)$')
    notes: str = Field(min_length=5, max_length=2000)
    expected_version: int = Field(ge=1)


@app.post('/v2/authority/cases/{case_id}/actions')
def act(case_id: str, action: CaseAction, actor=Depends(require_authority)):
    return store.transition_report(case_id, action.status, action.notes, action.expected_version, actor)


@app.get('/v2/authority/cases/{case_id}/audit')
def audit(case_id: str, actor=Depends(require_authority)):
    return {'events': store.list_audit(case_id)}


@app.get('/v2/authority/cases/{case_id}/photo')
def photo(case_id: str, actor=Depends(require_authority)):
    data, mime = store.get_photo(case_id)
    return Response(data, media_type=mime, headers={'Content-Disposition': 'inline; filename="evidence.jpg"'})


@app.get('/v2/models')
def models():
    return {'models': federation.list_models(include_pending=False), 'federation_status': 'metadata_interchange_only',
            'message': 'No partner country, remote training round or resource dispatch is connected.'}


@app.get('/v2/models/{model_id}/export')
def export_model(model_id: str):
    return federation.export_metadata(model_id)


@app.get('/v2/authority/models')
def private_models(actor=Depends(require_authority)):
    return {'models': federation.list_models(include_pending=True)}


@app.post('/v2/authority/models', status_code=201)
def import_model(payload: dict, actor=Depends(require_authority)):
    return federation.import_metadata(payload, actor)


class ModelReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    approve: bool
    notes: str = Field(min_length=5, max_length=2000)
    expected_version: int = Field(ge=1)


@app.post('/v2/authority/models/{model_id}/review')
def review_model(model_id: str, review: ModelReview, actor=Depends(require_authority)):
    return federation.review_model(model_id, review.approve, review.notes, review.expected_version, actor)
