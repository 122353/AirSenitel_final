"""Pan-India, evidence-labelled air-quality screening.

This service never turns a coarse atmospheric model into a street-level
measurement.  It provides three deliberately separate evidence tiers:

* OpenAQ station observations, when keyed access and a nearby fixed monitor exist.
* CAMS global model estimates for any coordinate in India (about 45 km grid).
* A pointer to VayuNirikshak's private local-device workflow for micro-area evidence.

Outputs support research screening and human investigation.  They are not CPCB AQI,
regulatory measurements, source attribution, or automatic enforcement decisions.
"""
from __future__ import annotations

import asyncio
import copy
import math
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx

from .forecast_v2 import iso, parse_time
from .monitoring_v2 import API_BASE, normalize_measurement, normalize_unit


INDIA_BBOX = (68.0, 6.0, 98.5, 38.5)
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
POLLUTANT_FIELDS = {
    "pm25": "pm2_5",
    "pm10": "pm10",
    "no2": "nitrogen_dioxide",
    "so2": "sulphur_dioxide",
    "o3": "ozone",
    "co": "carbon_monoxide",
}
SPIKE_FLOORS = {"pm25": 10.0, "pm10": 20.0, "no2": 15.0, "so2": 15.0, "o3": 20.0, "co": 200.0}
SEARCH_RADIUS_M = 25_000
CACHE_TTL_SECONDS = 300
MAX_CACHE_ENTRIES = 64

# A bounded operating watchlist, not a claim that only these cities are supported.
# Any Indian place or postcode can be assessed through the search/assessment routes.
NATIONAL_WATCHLIST = (
    ("Delhi", "Delhi", 28.6139, 77.2090),
    ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Pune", "Maharashtra", 18.5204, 73.8567),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Patna", "Bihar", 25.5941, 85.1376),
    ("Guwahati", "Assam", 26.1445, 91.7362),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("Kochi", "Kerala", 9.9312, 76.2673),
    ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
)

_CACHE: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()


class IndiaSourceError(Exception):
    """Sanitized upstream failure."""


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _inside_india(latitude: float, longitude: float) -> bool:
    west, south, east, north = INDIA_BBOX
    return south <= latitude <= north and west <= longitude <= east


def validate_coordinates(latitude: Any, longitude: Any) -> tuple[float, float]:
    latitude, longitude = _number(latitude), _number(longitude)
    if latitude is None or longitude is None or not _inside_india(latitude, longitude):
        raise ValueError("Coordinates must fall within the VayuNirikshak India operating bounds")
    return latitude, longitude


def _cache_get(key: tuple) -> dict | None:
    cached = _CACHE.get(key)
    if not cached:
        return None
    inserted, payload = cached
    if time.monotonic() - inserted >= CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    _CACHE.move_to_end(key)
    result = copy.deepcopy(payload)
    result["cache"] = {"hit": True, "ttl_seconds": CACHE_TTL_SECONDS,
                       "age_seconds": round(time.monotonic() - inserted, 2)}
    return result


def _cache_put(key: tuple, payload: dict) -> dict:
    _CACHE[key] = (time.monotonic(), copy.deepcopy(payload))
    _CACHE.move_to_end(key)
    while len(_CACHE) > MAX_CACHE_ENTRIES:
        _CACHE.popitem(last=False)
    payload["cache"] = {"hit": False, "ttl_seconds": CACHE_TTL_SECONDS}
    return payload


async def _json(client: httpx.AsyncClient, url: str, params: dict, headers: dict | None = None) -> dict | list:
    try:
        response = await client.get(url, params=params, headers=headers or {}, timeout=8.0, follow_redirects=False)
    except httpx.HTTPError:
        raise IndiaSourceError("source_network_unavailable") from None
    if response.status_code != 200:
        raise IndiaSourceError(f"source_http_{response.status_code}")
    if len(response.content) > 6_000_000:
        raise IndiaSourceError("source_response_too_large")
    try:
        payload = response.json()
    except ValueError:
        raise IndiaSourceError("source_invalid_json") from None
    if not isinstance(payload, (dict, list)):
        raise IndiaSourceError("source_invalid_payload")
    return payload


def _iso_utc(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = parse_time(value + "Z" if value and not value.endswith(("Z", "+00:00")) else value)
    return iso(parsed) if parsed else None


def _spike_screen(model: dict, pollutant: str, now: datetime) -> dict:
    field = POLLUTANT_FIELDS[pollutant]
    hourly = model.get("hourly") or {}
    times, values = hourly.get("time") or [], hourly.get(field) or []
    rows = []
    for stamp, value in zip(times, values):
        parsed, numeric = parse_time(stamp + "Z" if isinstance(stamp, str) and not stamp.endswith("Z") else stamp), _number(value)
        if parsed and numeric is not None:
            rows.append((parsed, numeric))
    rows.sort(key=lambda item: item[0])
    past = [(stamp, value) for stamp, value in rows if stamp <= now][-12:]
    future = [(stamp, value) for stamp, value in rows
              if now < stamp <= now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=6)]
    current = _number((model.get("current") or {}).get(field))
    baseline_values = [value for _, value in past[:-1] or past]
    if current is None or not baseline_values or not future:
        return {"status": "insufficient_model_points", "lead_time_hours": None, "peak_value": None,
                "message": "The atmospheric model did not return enough past and future points for spike screening."}
    baseline = median(baseline_values)
    mad = median(abs(value - baseline) for value in baseline_values)
    threshold = max(3 * 1.4826 * mad, abs(baseline) * 0.35, SPIKE_FLOORS[pollutant])
    peak_at, peak = max(future, key=lambda item: item[1])
    trigger = baseline + threshold
    flagged = peak > trigger and peak > current
    lead = max(0.0, (peak_at - now).total_seconds() / 3600)
    return {
        "status": "model_spike_watch" if flagged else "no_model_spike_signal",
        "baseline": round(baseline, 2), "current": round(current, 2),
        "peak_value": round(peak, 2), "peak_at": iso(peak_at),
        "lead_time_hours": round(lead, 1), "screening_threshold": round(trigger, 2),
        "confidence": "low_to_moderate_model_screening",
        "message": "A coarse-grid model rise is a reason to watch and verify locally, not proof that a neighbourhood spike will occur." if flagged
                   else "No qualified rise appears in the next six model hours; local events can still be missed by the coarse grid.",
    }


def _model_evidence(payload: dict, pollutant: str, now: datetime) -> dict:
    field = POLLUTANT_FIELDS[pollutant]
    current = payload.get("current") or {}
    units = payload.get("current_units") or {}
    value = _number(current.get(field))
    grid_lat, grid_lon = _number(payload.get("latitude")), _number(payload.get("longitude"))
    return {
        "status": "available" if value is not None else "unavailable",
        "evidence_class": "atmospheric_model_estimate",
        "pollutant": pollutant, "value": value, "unit": normalize_unit(units.get(field)) or units.get(field),
        "valid_at": _iso_utc(current.get("time")),
        "grid_coordinate": {"latitude": grid_lat, "longitude": grid_lon},
        "spatial_resolution_km": 45,
        "temporal_resolution": "CAMS global native 3-hourly; API may interpolate to hourly",
        "model": "Copernicus Atmosphere Monitoring Service global forecast via Open-Meteo",
        "source_url": "https://open-meteo.com/en/docs/air-quality-api",
        "official_aqi": False, "micro_area_measurement": False,
        "forecast_series": [
            {"valid_at": _iso_utc(stamp), "value": _number(value)}
            for stamp, value in zip((payload.get("hourly") or {}).get("time") or [], (payload.get("hourly") or {}).get(field) or [])
            if _number(value) is not None
        ],
        "spike_screen": _spike_screen(payload, pollutant, now),
    }


def _distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat, delta_lon = lat_b - lat_a, math.radians(longitude_b - longitude_a)
    chord = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(chord)))


async def _ground_evidence(client: httpx.AsyncClient, latitude: float, longitude: float,
                           pollutant: str, now: datetime, api_key: str) -> dict:
    base = {"evidence_class": "ground_station_observation", "pollutant": pollutant,
            "search_radius_km": SEARCH_RADIUS_M / 1000, "representativeness_radius_km": None,
            "message": "Search radius finds candidate stations; it is not the distance represented by a monitor."}
    if not api_key:
        return {**base, "status": "not_configured", "reason": "OPENAQ_API_KEY is not configured on the server"}
    headers = {"X-API-Key": api_key}
    try:
        payload = await _json(client, API_BASE + "/locations", {
            "coordinates": f"{latitude},{longitude}", "radius": SEARCH_RADIUS_M, "iso": "IN",
            "limit": 100, "page": 1, "order_by": "id", "sort_order": "asc",
        }, headers)
        locations = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(locations, list):
            raise IndiaSourceError("source_invalid_payload")
        candidates = []
        for location in locations:
            coordinates = location.get("coordinates") or {}
            station_lat, station_lon = _number(coordinates.get("latitude")), _number(coordinates.get("longitude"))
            station_id = location.get("id")
            sensors = [sensor for sensor in location.get("sensors") or [] if (sensor.get("parameter") or {}).get("name") == pollutant]
            if location.get("isMobile") is False and isinstance(station_id, int) and station_lat is not None and station_lon is not None and sensors:
                candidates.append((_distance_km(latitude, longitude, station_lat, station_lon), location, sensors))
        if not candidates:
            return {**base, "status": "not_found", "reason": "No fixed OpenAQ station with this pollutant was returned within the search radius"}
        distance, location, sensors = min(candidates, key=lambda item: item[0])
        latest = await _json(client, f"{API_BASE}/locations/{location['id']}/latest", {"limit": 100, "page": 1}, headers)
        rows = latest.get("results") if isinstance(latest, dict) else None
        if not isinstance(rows, list):
            raise IndiaSourceError("source_invalid_payload")
        sensor_by_id = {sensor.get("id"): sensor for sensor in sensors}
        measurements = []
        for row in rows:
            sensor = sensor_by_id.get(row.get("sensorsId"))
            if sensor:
                parameter = sensor.get("parameter") or {}
                measurements.append(normalize_measurement(
                    row, station_id=location["id"], sensor_id=sensor["id"], pollutant=pollutant,
                    unit=normalize_unit(parameter.get("units")), now=now, source="openaq_v3",
                    source_url=f"{API_BASE}/locations/{location['id']}/latest",
                ))
        accepted = [row for row in measurements if row["quality"]["status"] != "rejected"]
        accepted.sort(key=lambda row: row.get("observed_at") or "", reverse=True)
        if not accepted:
            return {**base, "status": "station_found_reading_unavailable", "station_id": location["id"],
                    "station_name": location.get("name"), "distance_km": round(distance, 2)}
        reading = accepted[0]
        return {**base, "status": "fresh" if reading["fresh"] else "delayed",
                "station_id": location["id"], "station_name": location.get("name") or f"OpenAQ location {location['id']}",
                "latitude": _number((location.get("coordinates") or {}).get("latitude")),
                "longitude": _number((location.get("coordinates") or {}).get("longitude")),
                "distance_km": round(distance, 2), "reading": reading,
                "source_url": f"{API_BASE}/locations/{location['id']}"}
    except IndiaSourceError as exc:
        return {**base, "status": "unavailable", "reason": str(exc)}


async def search_india_places(query: str, limit: int = 8, *, client: httpx.AsyncClient | None = None) -> dict:
    query = " ".join(query.split())
    if not 2 <= len(query) <= 80 or not 1 <= limit <= 20:
        raise ValueError("Search needs 2-80 characters and a limit between 1 and 20")
    own_client = client is None
    client = client or httpx.AsyncClient(limits=httpx.Limits(max_connections=2), trust_env=False)
    try:
        payload = await _json(client, GEOCODING_URL, {"name": query, "count": limit, "language": "en", "countryCode": "IN"})
        rows = payload.get("results") if isinstance(payload, dict) else None
        places = []
        for row in rows or []:
            latitude, longitude = _number(row.get("latitude")), _number(row.get("longitude"))
            if row.get("country_code") == "IN" and latitude is not None and longitude is not None and _inside_india(latitude, longitude):
                places.append({key: row.get(key) for key in ("id", "name", "admin1", "admin2", "admin3", "admin4", "postcodes", "timezone", "population")})
                places[-1].update(latitude=latitude, longitude=longitude,
                                  label=", ".join(part for part in (row.get("name"), row.get("admin1")) if part))
        return {"query": query, "places": places, "source": {"name": "GeoNames via Open-Meteo Geocoding",
                "url": "https://open-meteo.com/en/docs/geocoding-api"},
                "boundary_warning": "Place points and postcodes are search aids, not authoritative municipal boundaries."}
    except IndiaSourceError as exc:
        return {"query": query, "places": [], "status": "unavailable", "reason": str(exc),
                "source": {"name": "GeoNames via Open-Meteo Geocoding", "url": "https://open-meteo.com/en/docs/geocoding-api"}}
    finally:
        if own_client:
            await client.aclose()


async def assess_location(latitude: float, longitude: float, pollutant: str = "pm25", label: str | None = None,
                          *, now: datetime | None = None, client: httpx.AsyncClient | None = None,
                          openaq_key: str | None = None) -> dict:
    latitude, longitude = validate_coordinates(latitude, longitude)
    if pollutant not in POLLUTANT_FIELDS:
        raise ValueError("Unsupported pollutant")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    key = (
        "assessment", round(latitude, 4), round(longitude, 4), pollutant,
        (label or "").strip().casefold(),
        bool(openaq_key if openaq_key is not None else os.getenv("OPENAQ_API_KEY")),
    )
    if client is None and now is None and (cached := _cache_get(key)):
        return cached
    own_client = client is None
    client = client or httpx.AsyncClient(limits=httpx.Limits(max_connections=3), trust_env=False)
    api_key = openaq_key if openaq_key is not None else os.environ.get("OPENAQ_API_KEY", "").strip()
    try:
        field = POLLUTANT_FIELDS[pollutant]
        model_task = _json(client, AIR_QUALITY_URL, {
            "latitude": latitude, "longitude": longitude, "domains": "cams_global", "timezone": "GMT",
            "current": ",".join(POLLUTANT_FIELDS.values()), "hourly": field,
            "past_hours": 12, "forecast_hours": 7, "cell_selection": "land",
        })
        ground_task = _ground_evidence(client, latitude, longitude, pollutant, timestamp, api_key)
        model_payload, ground = await asyncio.gather(model_task, ground_task, return_exceptions=True)
        if isinstance(model_payload, Exception):
            model = {"status": "unavailable", "evidence_class": "atmospheric_model_estimate",
                     "reason": str(model_payload) if isinstance(model_payload, IndiaSourceError) else "source_unavailable"}
        else:
            model = _model_evidence(model_payload, pollutant, timestamp)
        if isinstance(ground, Exception):
            ground = {"status": "unavailable", "evidence_class": "ground_station_observation", "reason": "source_unavailable"}
        has_ground = ground.get("status") in {"fresh", "delayed"}
        result = {
            "schema_version": "2.1", "generated_at": iso(timestamp),
            "location": {"label": (label or "Selected India coordinate")[:120], "latitude": latitude, "longitude": longitude},
            "pollutant": pollutant, "status": "measured_plus_model" if has_ground else "model_estimate_only" if model.get("status") == "available" else "unavailable",
            "ground": ground, "model": model,
            "micro_area": {
                "status": "local_sensor_evidence_required",
                "grid_cell_size_m": 250,
                "message": "Microscopic hotspot screening is enabled only where multiple registered outdoor devices provide fresh, sustained, calibrated and spatially contrasting observations.",
                "authority_route": "/api/v2/authority/micro-candidates",
            },
            "fallback_ladder": [
                {"rank": 1, "source": "Fixed ground monitor", "status": ground.get("status"), "meaning": "Point measurement; representativeness remains unproven."},
                {"rank": 2, "source": "CAMS global atmospheric model", "status": model.get("status"), "meaning": "Approximately 45 km model grid; useful for regional screening, not street-level AQI."},
                {"rank": 3, "source": "Registered local sensor cluster", "status": "operator_setup_required", "meaning": "Required for 250 m inspection planning; at least two local and two background devices are needed."},
            ],
            "limitations": [
                "This response is research decision support, not CPCB's legally recognized AQI.",
                "A coarse model can miss short-lived industrial, traffic, waste-burning or neighbourhood events.",
                "Satellite aerosol and citizen reports are corroborating context, not substitutes for surface concentration monitors.",
                "No pollution source or enforcement action is inferred automatically.",
            ],
        }
        return _cache_put(key, result) if own_client and now is None else result
    finally:
        if own_client:
            await client.aclose()


async def india_overview(pollutant: str = "pm25", *, now: datetime | None = None,
                         client: httpx.AsyncClient | None = None) -> dict:
    if pollutant not in POLLUTANT_FIELDS:
        raise ValueError("Unsupported pollutant")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    key = ("overview", pollutant)
    if client is None and now is None and (cached := _cache_get(key)):
        return cached
    own_client = client is None
    client = client or httpx.AsyncClient(limits=httpx.Limits(max_connections=2), trust_env=False)
    try:
        field = POLLUTANT_FIELDS[pollutant]
        payload = await _json(client, AIR_QUALITY_URL, {
            "latitude": ",".join(str(city[2]) for city in NATIONAL_WATCHLIST),
            "longitude": ",".join(str(city[3]) for city in NATIONAL_WATCHLIST),
            "domains": "cams_global", "timezone": "GMT", "current": field, "hourly": field,
            "past_hours": 12, "forecast_hours": 7, "cell_selection": "land",
        })
        model_rows = payload if isinstance(payload, list) else [payload]
        cities = []
        for city, model_payload in zip(NATIONAL_WATCHLIST, model_rows):
            model = _model_evidence(model_payload, pollutant, timestamp)
            cities.append({"name": city[0], "state": city[1], "latitude": city[2], "longitude": city[3],
                           "model": model, "risk": model.get("spike_screen", {}).get("status")})
        cities.sort(key=lambda city: (city["risk"] != "model_spike_watch", -(city["model"].get("value") or -1)))
        result = {"schema_version": "2.1", "generated_at": iso(timestamp), "pollutant": pollutant,
                  "status": "available", "cities": cities,
                  "coverage": {"mode": "bounded_national_watchlist", "city_count": len(cities),
                               "on_demand_search": True, "all_india_places_preloaded": False,
                               "message": "The watchlist is a bounded national overview. Search can assess other Indian cities, villages and postcodes on demand."},
                  "source": {"name": "CAMS global atmospheric model via Open-Meteo", "url": "https://open-meteo.com/en/docs/air-quality-api",
                             "spatial_resolution_km": 45, "official_aqi": False},
                  "limitations": ["Watchlist values are model estimates, not station readings or official city AQI.",
                                  "National coverage does not imply microscopic resolution."]}
        return _cache_put(key, result) if own_client and now is None else result
    except IndiaSourceError as exc:
        return {"schema_version": "2.1", "generated_at": iso(timestamp), "pollutant": pollutant,
                "status": "unavailable", "cities": [], "reason": str(exc),
                "coverage": {"mode": "bounded_national_watchlist", "on_demand_search": True}}
    finally:
        if own_client:
            await client.aclose()
