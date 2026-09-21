"""Six-hour India-wide *regional* pollution-rise screening, not certified prediction.

CAMS global forecasts have ~45 km / native 3-hour resolution. The API interpolates
hourly values: neither its past values nor its current values are observations.
This module keeps those facts in its output instead of inventing ground evidence,
an ensemble, trained AI, neighbourhood precision, probabilities, or official AQI.
"""
from __future__ import annotations

import asyncio
import copy
import math
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx

from .forecast_v2 import iso, parse_time
from .india_intelligence_v2 import (
    AIR_QUALITY_URL, POLLUTANT_FIELDS, SPIKE_FLOORS, IndiaSourceError,
    _distance_km, _json, validate_coordinates,
)
from .monitoring_v2 import WEATHER_URL, normalize_unit

UTC = timezone.utc
HORIZON_HOURS = 6
BASELINE_HOURS = 12
MIN_BASELINE_POINTS = 8
CACHE_TTL_SECONDS = 300
MAX_CACHE_ENTRIES = 48
MAX_CONCURRENT_REQUESTS = 4
WEATHER_FIELDS = ("wind_speed_10m", "wind_direction_10m", "relative_humidity_2m", "precipitation")

# One representative per state/UT. These points are NOT exhaustive city coverage,
# administrative boundaries, or all sensors. Other coordinates are on demand.
NATIONAL_REPRESENTATIVES = (
    ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    ("Itanagar", "Arunachal Pradesh", 27.0844, 93.6053),
    ("Guwahati", "Assam", 26.1445, 91.7362),
    ("Patna", "Bihar", 25.5941, 85.1376),
    ("Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("Panaji", "Goa", 15.4909, 73.8278),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Gurugram", "Haryana", 28.4595, 77.0266),
    ("Shimla", "Himachal Pradesh", 31.1048, 77.1734),
    ("Ranchi", "Jharkhand", 23.3441, 85.3096),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Imphal", "Manipur", 24.8170, 93.9368),
    ("Shillong", "Meghalaya", 25.5788, 91.8933),
    ("Aizawl", "Mizoram", 23.7271, 92.7176),
    ("Kohima", "Nagaland", 25.6751, 94.1086),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("Ludhiana", "Punjab", 30.9010, 75.8573),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Gangtok", "Sikkim", 27.3314, 88.6138),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Agartala", "Tripura", 23.8315, 91.2868),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Dehradun", "Uttarakhand", 30.3165, 78.0322),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Sri Vijaya Puram", "Andaman and Nicobar Islands", 11.6234, 92.7265),
    ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("Daman", "Dadra and Nagar Haveli and Daman and Diu", 20.3974, 72.8328),
    ("Delhi", "Delhi", 28.6139, 77.2090),
    ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
    ("Leh", "Ladakh", 34.1526, 77.5771),
    ("Kavaratti", "Lakshadweep", 10.5593, 72.6358),
    ("Puducherry", "Puducherry", 11.9416, 79.8083),
)

_CACHE: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
_INFLIGHT: dict[tuple, asyncio.Task] = {}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _stamp(value: Any) -> datetime | None:
    """Naive API timestamps are UTC only because both requests specify GMT."""
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _series(payload: dict, field: str, now: datetime) -> tuple[list[tuple], dict]:
    hourly, units = _dict(payload.get("hourly")), _dict(payload.get("hourly_units"))
    times, values = _list(hourly.get("time")), _list(hourly.get(field))
    quality = {"rejected_points": 0, "conflicting_timestamps": 0,
               "unit_valid": normalize_unit(units.get(field)) == "µg/m³",
               "returned_unit": units.get(field), "model_run_at": None,
               "model_run_freshness": "not_exposed_by_provider"}
    if not quality["unit_valid"]:
        return [], quality
    if payload.get("utc_offset_seconds", 0) != 0:
        quality["reason"] = "unexpected_timezone"
        return [], quality
    grouped: dict[datetime, list[float]] = {}
    hour = now.replace(minute=0, second=0, microsecond=0)
    for index, raw_time in enumerate(times):
        stamp = _stamp(raw_time)
        value = _number(values[index]) if index < len(values) else None
        if stamp is None or value is None or value < 0 or stamp.minute or stamp.second or stamp.microsecond:
            quality["rejected_points"] += 1
            continue
        if hour - timedelta(hours=BASELINE_HOURS) <= stamp <= hour + timedelta(hours=HORIZON_HOURS):
            grouped.setdefault(stamp, []).append(value)
    points = []
    for stamp, duplicates in grouped.items():
        if len(set(duplicates)) != 1:
            quality["conflicting_timestamps"] += 1
            continue
        points.append((stamp, duplicates[0]))
    return sorted(points), quality


def screen_pollutant(payload: dict, pollutant: str, now: datetime) -> dict:
    """Deterministic robust-change screen; not an evaluated event probability.

    Require a recent model reference, >=8/12 baseline hours with no >2h gaps,
    and all six future hours. Missing data must not become a no-risk conclusion.
    A current exceedance is ongoing *modelled* risk, never a before-event warning.
    """
    field = POLLUTANT_FIELDS[pollutant]
    hour = now.replace(minute=0, second=0, microsecond=0)
    points, quality = _series(payload, field, now)
    lookup = dict(points)
    baseline_rows = [(stamp, value) for stamp, value in points if stamp < hour]
    future = [(hour + timedelta(hours=h), lookup.get(hour + timedelta(hours=h)))
              for h in range(1, HORIZON_HOURS + 1)]
    current = lookup.get(hour)
    quality.update(baseline_points=len(baseline_rows), expected_baseline_points=BASELINE_HOURS,
                   future_points=sum(value is not None for _, value in future), expected_future_points=HORIZON_HOURS,
                   current_valid_at=iso(hour) if current is not None else None)
    result = {
        "pollutant": pollutant, "unit": "ug/m3", "status": "insufficient_data",
        "current": current, "baseline": None, "threshold": None,
        "first_crossing_at": None, "lead_time_hours": None, "peak_value": None, "peak_at": None,
        "evidence_class": "atmospheric_model_forecast", "confidence": "unvalidated_screening",
        "trained_model": False, "operationally_validated": False, "official_aqi": False,
        "quality": quality,
        "series": [{"valid_at": iso(stamp), "value": value,
                    "phase": "forecast" if stamp > now else "past_model"} for stamp, value in points],
        "message": "Insufficient quality-controlled model points; risk is unknown, not clear.",
    }
    if not quality["unit_valid"]:
        quality["reason"] = "missing_or_incompatible_unit"
        return result
    if current is None:
        quality.setdefault("reason", "current_model_hour_missing_or_stale")
        return result
    if len(baseline_rows) < MIN_BASELINE_POINTS:
        quality["reason"] = "insufficient_baseline"
        return result
    times = [stamp for stamp, _ in baseline_rows] + [hour]
    if any((b - a).total_seconds() > 7200 for a, b in zip(times, times[1:])):
        quality["reason"] = "baseline_gap"
        return result
    baseline_values = [value for _, value in baseline_rows]
    baseline = median(baseline_values)
    mad = median(abs(value - baseline) for value in baseline_values)
    increment = max(SPIKE_FLOORS[pollutant], baseline * 0.35, 3 * 1.4826 * mad)
    threshold = baseline + increment
    result.update(baseline=round(baseline, 3), threshold=round(threshold, 3),
                  baseline_deviation=round(mad, 3), minimum_rise=round(increment, 3))
    # Report ongoing modelled rise even when later forecast points are missing.
    # This is a model diagnostic, not a sensor observation or advance prediction.
    if current > threshold:
        result.update(status="model_current_rise",
                      message="The model already exceeds its recent baseline. This is an ongoing modelled rise, not an advance warning or ground detection.")
        quality["reason"] = "current_model_rise"
        return result
    if any(value is None for _, value in future):
        quality["reason"] = "incomplete_future_horizon"
        return result
    peak_at, peak = max(future, key=lambda item: item[1])
    result.update(peak_value=peak, peak_at=iso(peak_at))
    # Find earliest crossing, not peak time. Strictly later than request time.
    first = next(((stamp, value) for stamp, value in future if value > threshold and value > current), None)
    if first:
        crossing_at, _ = first
        result.update(status="forecast_watch", first_crossing_at=iso(crossing_at),
                      lead_time_hours=round((crossing_at - now).total_seconds() / 3600, 3),
                      message="A regional-model rise is forecast within six hours. Verify locally; this is not a guaranteed event or a calibrated event probability.")
    else:
        result.update(status="no_model_spike_signal",
                      message="No qualifying rise in the next six model hours. This is not a safety assessment; local sudden events can be missed.")
    quality["reason"] = "passed_screening_checks"
    return result


def _weather(payload: dict, now: datetime) -> dict:
    current, units = _dict(payload.get("current")), _dict(payload.get("current_units"))
    stamp = _stamp(current.get("time"))
    result = {"status": "unavailable", "valid_at": iso(stamp) if stamp else None,
              "evidence_class": "weather_model_context", "used_in_spike_threshold": False,
              "message": "Weather is corroborating context, not a proven pollution cause."}
    expected = {"wind_speed_10m": "m/s", "wind_direction_10m": "°",
                "relative_humidity_2m": "%", "precipitation": "mm"}
    if stamp is None or not 0 <= (now - stamp).total_seconds() <= 5400 or payload.get("utc_offset_seconds", 0) != 0:
        return {**result, "reason": "weather_time_missing_or_stale"}
    for field in WEATHER_FIELDS:
        value = _number(current.get(field))
        valid = value is not None and value >= 0 and units.get(field) == expected[field]
        if field == "relative_humidity_2m" and value is not None and value > 100:
            valid = False
        if field == "wind_direction_10m" and value is not None and value > 360:
            valid = False
        result[field] = value if valid else None
    count = sum(result.get(field) is not None for field in WEATHER_FIELDS)
    result.update(status="available" if count == len(WEATHER_FIELDS) else "partial" if count else "unavailable",
                  units=expected)
    return result


def _matching_rows(payload: Any, places: list[dict]) -> list[dict]:
    rows = payload if isinstance(payload, list) else [payload]
    if len(rows) != len(places):
        return [{} for _ in places]  # Never zip a truncated response into the wrong cities.
    matched = []
    for place, raw in zip(places, rows):
        row = _dict(raw)
        lat, lon = _number(row.get("latitude")), _number(row.get("longitude"))
        if (lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180
                or _distance_km(place["latitude"], place["longitude"], lat, lon) > 200):
            matched.append({})
        else:
            matched.append(row)
    return matched


def _places(latitude: Any, longitude: Any, label: Any) -> list[dict]:
    if latitude is None and longitude is None:
        return [{"id": f"state-{index + 1}", "name": name, "state": state, "latitude": lat, "longitude": lon}
                for index, (name, state, lat, lon) in enumerate(NATIONAL_REPRESENTATIVES)]
    lat, lon = validate_coordinates(latitude, longitude)
    return [{"id": f"point-{lat:.4f}-{lon:.4f}", "name": str(label or "Selected India coordinate")[:120],
             "state": None, "latitude": lat, "longitude": lon}]


async def _build(places: list[dict], now: datetime, client: httpx.AsyncClient) -> dict:
    coordinates = {"latitude": ",".join(str(p["latitude"]) for p in places),
                   "longitude": ",".join(str(p["longitude"]) for p in places), "timezone": "GMT"}
    model_result, weather_result = await asyncio.gather(
        _json(client, AIR_QUALITY_URL, {**coordinates, "domains": "cams_global",
              "hourly": ",".join(POLLUTANT_FIELDS.values()), "past_hours": BASELINE_HOURS,
              "forecast_hours": HORIZON_HOURS + 1, "cell_selection": "land"}),
        _json(client, WEATHER_URL, {**coordinates, "current": ",".join(WEATHER_FIELDS),
              "wind_speed_unit": "ms", "forecast_days": 1}), return_exceptions=True,
    )
    model_rows = _matching_rows(model_result, places)
    weather_rows = _matching_rows(weather_result, places)
    alerts, locations = [], []
    for place, model, weather in zip(places, model_rows, weather_rows):
        pollutants = {name: screen_pollutant(model, name, now) for name in POLLUTANT_FIELDS}
        eligible = sum(row["status"] != "insufficient_data" for row in pollutants.values())
        location = {**place, "status": "available" if eligible == 6 else "partial" if eligible else "unavailable",
                    "weather": _weather(weather, now), "pollutants": pollutants,
                    "grid_coordinate": {"latitude": model.get("latitude"), "longitude": model.get("longitude")},
                    "spatial_resolution_km": 45, "micro_area_measurement": False}
        locations.append(location)
        for pollutant, signal in pollutants.items():
            if signal["status"] not in {"forecast_watch", "model_current_rise"}:
                continue
            alerts.append({**place, "id": f"{place['id']}-{pollutant}-{signal['status']}", "location_id": place["id"],
                           "kind": signal["status"], "pollutant": pollutant,
                           **{key: signal[key] for key in ("unit", "current", "baseline", "threshold", "first_crossing_at",
                              "lead_time_hours", "peak_value", "peak_at", "evidence_class", "confidence", "message")}})
    alerts.sort(key=lambda a: (a["kind"] != "forecast_watch", a["lead_time_hours"] if a["lead_time_hours"] is not None else 0,
                               a["name"], a["pollutant"]))
    eligible_count = sum(location["status"] != "unavailable" for location in locations)
    complete_count = sum(location["status"] == "available" for location in locations)
    return {
        "schema_version": "2.2", "generated_at": iso(now),
        "status": "available" if complete_count == len(places) else "partial" if eligible_count else "unavailable",
        "horizon_hours": HORIZON_HOURS, "baseline_hours": BASELINE_HOURS,
        "method": {"name": "CAMS regional robust-rise screening", "trained_here": False, "ensemble": False,
                   "threshold": "past-12h median + max(35% of median, 3 x 1.4826 x MAD, pollutant absolute-rise floor)",
                   "absolute_rise_floors_ug_m3": SPIKE_FLOORS.copy(), "operationally_validated": False,
                   "event_probability_available": False},
        "coverage": {"mode": "state_ut_representatives" if len(places) > 1 else "on_demand_coordinate",
                     "requested_locations": len(places), "assessed_locations": eligible_count,
                     "forecast_locations": sum(any(p["status"] in {"forecast_watch", "no_model_spike_signal"}
                         for p in location["pollutants"].values()) for location in locations),
                     "states_uts_represented": len({p["state"] for p in places if p["state"]}),
                     "on_demand_india_coordinates": True, "all_india_places_preloaded": False,
                     "continuously_monitored_all_india": False, "spatial_resolution_km": 45,
                     "message": "36 state/UT representative points refresh on request; other India coordinates are assessed on demand. Not every city or neighbourhood is continuously watched."},
        "summary": {"forecast_watch_count": sum(a["kind"] == "forecast_watch" for a in alerts),
                    "model_current_rise_count": sum(a["kind"] == "model_current_rise" for a in alerts),
                    "observed_rise_count": None, "observation_status": "not_assessed_by_model_screen",
                    "insufficient_count": sum(p["status"] == "insufficient_data" for loc in locations for p in loc["pollutants"].values())},
        "alerts": alerts, "locations": locations,
        "sources": [
            {"id": "cams_global", "name": "Copernicus CAMS global via Open-Meteo", "url": "https://open-meteo.com/en/docs/air-quality-api",
             "status": "available" if complete_count == len(places) else "partial" if eligible_count else "unavailable",
             "reason": str(model_result) if isinstance(model_result, IndiaSourceError) else None,
             "evidence_class": "atmospheric_model_forecast", "spatial_resolution_km": 45,
             "native_time_step_hours": 3, "api_time_step_hours": 1, "model_update_interval_hours": 12,
             "retrieved_at": iso(now), "model_run_at": None, "freshness": "valid_times_checked_run_time_not_exposed"},
            {"id": "open_meteo_weather", "name": "Open-Meteo weather model context", "url": "https://open-meteo.com/en/docs",
             "status": "available" if all(loc["weather"]["status"] == "available" for loc in locations) else "partial" if any(loc["weather"]["status"] != "unavailable" for loc in locations) else "unavailable",
             "reason": str(weather_result) if isinstance(weather_result, IndiaSourceError) else None,
             "evidence_class": "weather_model_context", "retrieved_at": iso(now)},
        ],
        "limitations": [
            "Research screening, not a trained or validated local sudden-pollution prediction model; event accuracy and probability are not established.",
            "CAMS is about 45 km with native 3-hour output interpolated to hourly. It can miss rapid industrial, road, fire or neighbourhood events.",
            "Past/current CAMS values are model estimates, not measurements. Sensor detections, government observations and satellite context must remain separate evidence.",
            "A valid forecast time does not prove a fresh model run: the provider does not expose run-init time in this response.",
            "No spike signal does not mean clean air or safety. Missing, stale, conflicting or incompatible data suppress screening, never imply low risk.",
            "Point bounds are operating bounds, not an authoritative India boundary. No official CPCB AQI, source attribution or automatic enforcement decision is produced.",
        ],
    }


def _cache_get(key: tuple, now: datetime) -> dict | None:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    inserted, payload = entry
    age = time.monotonic() - inserted
    generated = parse_time(payload["generated_at"])
    expired_crossing = any(parse_time(a.get("first_crossing_at")) <= now
                           for a in payload["alerts"] if a.get("first_crossing_at"))
    if (age >= CACHE_TTL_SECONDS or generated is None or (now - generated).total_seconds() >= CACHE_TTL_SECONDS
            or generated.replace(minute=0, second=0, microsecond=0) != now.replace(minute=0, second=0, microsecond=0)
            or expired_crossing):
        _CACHE.pop(key, None)
        return None
    _CACHE.move_to_end(key)
    result = copy.deepcopy(payload)
    result["cache"] = {"hit": True, "age_seconds": round(age, 2), "ttl_seconds": CACHE_TTL_SECONDS}
    # Recompute lead time for this request; keep generated_at as original fetch time.
    for alert in result["alerts"]:
        if alert["first_crossing_at"]:
            alert["lead_time_hours"] = round((parse_time(alert["first_crossing_at"]) - now).total_seconds() / 3600, 3)
    for location in result["locations"]:
        for signal in location["pollutants"].values():
            if signal["first_crossing_at"]:
                signal["lead_time_hours"] = round((parse_time(signal["first_crossing_at"]) - now).total_seconds() / 3600, 3)
    return result


async def build_early_warning(latitude=None, longitude=None, label=None, *, now=None, client=None) -> dict:
    """Two batched upstream requests, shared cache and in-flight coalescing.

    Explicit clients/times bypass shared cache for deterministic tests and callers.
    No sensor history fan-out or unauthenticated background process is started.
    """
    places = _places(latitude, longitude, label)
    timestamp = now or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    timestamp = timestamp.astimezone(UTC)
    use_cache = client is None and now is None
    key = tuple((p["latitude"], p["longitude"], p["name"]) for p in places)
    if use_cache and (cached := _cache_get(key, timestamp)):
        return cached

    async def perform():
        owned = client is None
        connection = client or httpx.AsyncClient(limits=httpx.Limits(max_connections=2), trust_env=False)
        try:
            result = await _build(places, timestamp, connection)
            result["cache"] = {"hit": False, "age_seconds": 0, "ttl_seconds": CACHE_TTL_SECONDS}
            if use_cache:
                _CACHE[key] = (time.monotonic(), copy.deepcopy(result))
                _CACHE.move_to_end(key)
                while len(_CACHE) > MAX_CACHE_ENTRIES:
                    _CACHE.popitem(last=False)
            return result
        finally:
            if owned:
                await connection.aclose()

    if not use_cache:
        return await perform()
    inflight_key = (id(asyncio.get_running_loop()), key)
    task = _INFLIGHT.get(inflight_key)
    if task is None:
        if len(_INFLIGHT) >= MAX_CONCURRENT_REQUESTS:
            raise IndiaSourceError("screening_capacity_reached")
        task = asyncio.create_task(perform())
        _INFLIGHT[inflight_key] = task
        task.add_done_callback(lambda finished: _INFLIGHT.pop(inflight_key, None))
    return copy.deepcopy(await asyncio.shield(task))
