"""Bounded OpenAQ evidence service. No synthetic measurements or spatial radius.

The discovery box includes Delhi/NCR and is not an administrative boundary or
an inventory of every physical monitor. OpenAQ observations remain third-party
aggregated, provisional evidence; this module neither certifies AQI nor infers
pollution causes. Credentials are used only on api.openaq.org requests.
"""
from __future__ import annotations

import asyncio
import copy
import csv
import gzip
import hashlib
import io
import json
import math
import os
import time
from collections import Counter, OrderedDict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx

from .forecast_v2 import accepted_series, build_forecast, iso, parse_time

UTC = timezone.utc
DELHI_BBOX = (76.8, 28.3, 77.6, 29.0)
API_BASE = "https://api.openaq.org/v3"
ARCHIVE_BASE = "https://openaq-data-archive.s3.amazonaws.com/records/csv.gz"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
POLLUTANTS = {"pm25", "pm10", "no2", "so2", "o3", "co", "no", "nox", "bc"}
MAX_LOCATION_PAGES = 4
PAGE_SIZE = 500
MAX_HISTORY_PAGES = 2
HISTORY_HOURS = 168
MAX_PEERS = 2
MAX_COMPRESSED_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 6_000_000
MAX_ARCHIVE_ROWS = 25_000
CACHE_TTL_SECONDS = 60
MAX_SNAPSHOT_CACHE_ENTRIES = 24
MAX_DISCOVERY_CACHE_ENTRIES = 4
MAX_CONCURRENT_SNAPSHOTS = 2
_CACHE: OrderedDict = OrderedDict()
_INFLIGHT: dict[tuple, asyncio.Task] = {}
_DISCOVERY_CACHE: OrderedDict = OrderedDict()
_DISCOVERY_INFLIGHT: dict[str, asyncio.Task] = {}


class SourceError(Exception):
    """Sanitized source failure: never return arbitrary upstream text or headers."""


def normalize_unit(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip().lower().replace("μ", "u").replace("µ", "u").replace("³", "3").replace("^", "").replace(" ", "")
    return {"ug/m3": "µg/m³", "mg/m3": "mg/m³", "ppb": "ppb", "ppm": "ppm"}.get(key)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _positive_id(value: Any) -> int | None:
    try:
        parsed = int(value)
        return parsed if parsed > 0 and str(value).strip() == str(parsed) else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_measurement(raw: dict, *, station_id: int, sensor_id: int, pollutant: str,
                          unit: str | None, now: datetime, source: str,
                          source_url: str, hourly: bool = False) -> dict:
    """Retain rejected records with explicit flags; never impute or convert gases."""
    raw_parameter = raw.get("parameter")
    parameter = raw_parameter if isinstance(raw_parameter, dict) else {}
    supplied_unit = parameter.get("units", raw.get("units", unit))
    actual_unit = normalize_unit(supplied_unit)
    expected_unit = normalize_unit(unit)
    actual_pollutant = parameter.get("name", raw_parameter if isinstance(raw_parameter, str) else raw.get("parameter_name", pollutant))
    period = raw.get("period") or {}
    stamp = parse_time(period.get("datetimeTo") if hourly else raw.get("datetime", raw.get("observed_at")))
    value = _number(raw.get("value"))
    reasons = []
    if value is None or value < 0:
        reasons.append("invalid_or_negative_value")
    if actual_unit is None or (pollutant in {"pm25", "pm10", "bc"} and actual_unit not in {"µg/m³", "mg/m³"}):
        reasons.append("unsupported_unit")
    if expected_unit is not None and actual_unit != expected_unit:
        reasons.append("unit_mismatch")
    if actual_pollutant != pollutant:
        reasons.append("pollutant_mismatch")
    if stamp is None:
        reasons.append("missing_or_timezone_naive_timestamp")
    elif stamp > now:
        reasons.append("future_observation")
    flags = (raw.get("flagInfo") or {}).get("hasFlags")
    if flags is True:
        reasons.append("upstream_quality_flag")
    if hourly:
        start = parse_time(period.get("datetimeFrom"))
        if start is None or stamp is None or stamp - start != timedelta(hours=1):
            reasons.append("invalid_hourly_period")
        coverage = (raw.get("coverage") or {}).get("percentCoverage")
        if coverage is not None and (_number(coverage) is None or not 75 <= float(coverage) <= 100):
            reasons.append("low_or_invalid_hourly_coverage")
    age_hours = (now - stamp).total_seconds() / 3600 if stamp else None
    fresh = stamp is not None and 0 <= age_hours <= 3 and source != "openaq_archive"
    status = "rejected" if reasons else ("valid" if flags is False else "provisional")
    return {
        "station_id": station_id, "sensor_id": sensor_id, "pollutant": pollutant,
        "value": value, "unit": actual_unit, "original_unit": supplied_unit,
        "observed_at": iso(stamp) if stamp else None, "collected_at": iso(now),
        "age_hours": round(age_hours, 3) if age_hours is not None else None,
        "fresh": fresh, "usable_for_current_analysis": fresh and status == "valid",
        "quality": {"status": status, "reasons": reasons,
                    "upstream_flags": "present" if flags is True else "none" if flags is False else "unknown"},
        "averaging_period": "hour" if hourly else "source_reported",
        "source": source, "source_url": source_url,
        "regulatory_use": "prohibited; human-reviewed research only",
    }


def deduplicate_measurements(points: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for point in points:
        key = tuple(point.get(k) for k in ("station_id", "sensor_id", "pollutant", "unit", "observed_at"))
        grouped.setdefault(key, []).append(point)
    output = []
    for group in grouped.values():
        point = copy.deepcopy(group[0])
        if len({p.get("value") for p in group}) > 1:
            point["quality"] = {"status": "rejected", "reasons": ["conflicting_duplicate"], "upstream_flags": "unknown"}
            point["usable_for_current_analysis"] = False
        elif any(p.get("quality", {}).get("status") == "rejected" for p in group):
            point = copy.deepcopy(next(p for p in group if p.get("quality", {}).get("status") == "rejected"))
        point["duplicate_count"] = len(group) - 1
        output.append(point)
    return sorted(output, key=lambda p: p.get("observed_at") or "")


def station_from_location(raw: dict, *, source: str = "openaq_v3") -> dict | None:
    coordinates = raw.get("coordinates") or {}
    lat, lon = _number(coordinates.get("latitude")), _number(coordinates.get("longitude"))
    station_id = _positive_id(raw.get("id"))
    if (station_id is None or lat is None or lon is None
            or not DELHI_BBOX[0] <= lon <= DELHI_BBOX[2] or not DELHI_BBOX[1] <= lat <= DELHI_BBOX[3]):
        return None
    sensors = []
    for sensor in raw.get("sensors") or []:
        parameter = sensor.get("parameter") or {}
        sensor_id = _positive_id(sensor.get("id"))
        if sensor_id is not None and parameter.get("name") in POLLUTANTS:
            sensors.append({"id": sensor_id, "pollutant": parameter["name"],
                            "unit": normalize_unit(parameter.get("units")), "original_unit": parameter.get("units")})
    return {"id": station_id, "name": raw.get("name") or f"OpenAQ location {station_id}",
            "latitude": lat, "longitude": lon, "provider": (raw.get("provider") or {}).get("name"),
            "owner": (raw.get("owner") or {}).get("name"), "licenses": raw.get("licenses") or [],
            "source": source, "source_url": f"{API_BASE}/locations/{station_id}",
            "latest_at": iso(stamp) if (stamp := parse_time(raw.get("datetimeLast"))) else None,
            "is_mobile": raw.get("isMobile"), "is_reference_monitor": raw.get("isMonitor"),
            "sensors": sensors, "measurements": [], "latest_status": "not_requested",
            "location_precision": "mobile_initial_point" if raw.get("isMobile") is True else "station_point" if raw.get("isMobile") is False else "mobility_unknown_point",
            "search_distance_km": None,
            "representativeness_radius_km": None,
            "representativeness_status": "unknown; no calibration or dispersion evidence supplied"}


def _haversine(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    dlat, dlon = lat2 - lat1, math.radians(b["longitude"] - a["longitude"])
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)))


class _Fetcher:
    def __init__(self, client: httpx.AsyncClient, api_key: str | None, *, shared_discovery: bool = False):
        self.client, self.api_key = client, api_key
        self.shared_discovery = shared_discovery
        self.semaphore = asyncio.Semaphore(3)
        self.requests = 0

    async def content(self, url: str, params: dict | None = None, *, archive: bool = False) -> bytes:
        headers = {"X-API-Key": self.api_key} if url.startswith(API_BASE + "/") and self.api_key else {}
        maximum = MAX_COMPRESSED_BYTES if archive else MAX_RESPONSE_BYTES
        async with self.semaphore:
            self.requests += 1
            try:
                async with self.client.stream("GET", url, params=params, headers=headers, timeout=6.0, follow_redirects=False) as response:
                    if response.status_code != 200:
                        raise SourceError(f"source_http_{response.status_code}")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > maximum:
                            raise SourceError("source_response_too_large")
                    return bytes(body)
            except httpx.HTTPError:
                raise SourceError("source_network_unavailable") from None

    async def json(self, path: str, params: dict | None = None) -> dict:
        try:
            payload = json.loads(await self.content(API_BASE + path, params))
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise SourceError("source_invalid_payload")
            return payload
        except (ValueError, UnicodeError):
            raise SourceError("source_invalid_json") from None

    async def pages(self, path: str, params: dict, max_pages: int) -> tuple[list[dict], dict]:
        rows, total, complete, reason, pages = [], None, False, "page_limit", 0
        reported = None
        seen = set()
        for page in range(1, max_pages + 1):
            try:
                payload = await self.json(path, {**params, "limit": PAGE_SIZE, "page": page})
            except SourceError as exc:
                reason = str(exc)
                break
            pages += 1
            batch = payload["results"]
            reported = (payload.get("meta") or {}).get("found")
            if isinstance(reported, int) and not isinstance(reported, bool):
                total = reported
            fingerprint = hashlib.sha256(json.dumps(batch, sort_keys=True).encode()).hexdigest()
            if batch and fingerprint in seen:
                reason = "repeated_page"
                break
            seen.add(fingerprint)
            rows.extend(r for r in batch[:PAGE_SIZE] if isinstance(r, dict))
            if len(batch) > PAGE_SIZE:
                reason = "source_ignored_page_size"
                break
            if len(batch) < PAGE_SIZE or (total is not None and len(rows) >= total):
                complete, reason = True, None
                break
        return rows, {"complete": complete, "returned": len(rows), "total_reported": total, "total_reported_raw": reported,
                      "pages_fetched": pages, "page_limit": max_pages, "page_size": PAGE_SIZE,
                      "incomplete_reason": reason}


def _forget_task(mapping: dict, key, task: asyncio.Task) -> None:
    if mapping.get(key) is task:
        mapping.pop(key, None)
    # Observe exceptions even when every waiting HTTP request disconnected.
    if not task.cancelled():
        task.exception()


async def _discover_locations(fetcher: _Fetcher) -> tuple[list[dict], dict]:
    params = {"bbox": ",".join(map(str, DELHI_BBOX)), "iso": "IN", "order_by": "id", "sort_order": "asc"}
    if not fetcher.shared_discovery:
        return await fetcher.pages("/locations", params, MAX_LOCATION_PAGES)
    key = hashlib.sha256((fetcher.api_key or "").encode()).hexdigest()
    cached = _DISCOVERY_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        rows, metadata = copy.deepcopy(cached[1])
        metadata["discovery_cache"] = {"hit": True, "age_seconds": round(time.monotonic() - cached[0], 2)}
        return rows, metadata

    async def collect():
        try:
            result = await asyncio.wait_for(fetcher.pages("/locations", params, MAX_LOCATION_PAGES), timeout=25)
        except asyncio.TimeoutError:
            result = ([], {"complete": False, "returned": 0, "total_reported": None,
                           "incomplete_reason": "discovery_deadline", "pages_fetched": 0})
        _DISCOVERY_CACHE[key] = (time.monotonic(), copy.deepcopy(result))
        while len(_DISCOVERY_CACHE) > MAX_DISCOVERY_CACHE_ENTRIES:
            _DISCOVERY_CACHE.popitem(last=False)
        return result

    task = _DISCOVERY_INFLIGHT.get(key)
    coalesced = task is not None
    if task is None:
        task = asyncio.create_task(collect())
        _DISCOVERY_INFLIGHT[key] = task
        task.add_done_callback(lambda finished: _forget_task(_DISCOVERY_INFLIGHT, key, finished))
    rows, metadata = copy.deepcopy(await asyncio.shield(task))
    metadata["discovery_cache"] = {"hit": False, "coalesced": coalesced}
    return rows, metadata


async def _weather(fetcher: _Fetcher, station: dict | None) -> dict:
    lat, lon = (station["latitude"], station["longitude"]) if station else (28.6139, 77.2090)
    base = {"source": "Open-Meteo", "source_url": "https://open-meteo.com/en/docs",
            "kind": "weather_model_estimate", "latitude": lat, "longitude": lon,
            "message": "Gridded model weather context, not a local weather-station measurement or pollutant reading."}
    try:
        payload = json.loads(await fetcher.content(WEATHER_URL, {
            "latitude": lat, "longitude": lon, "timezone": "GMT", "forecast_days": 1,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
            "wind_speed_unit": "ms"}))
        current = payload.get("current") or {}
        if not current.get("time"):
            raise SourceError("weather_missing_timestamp")
        return {**base, "status": "available", "current": current, "units": payload.get("current_units") or {},
                "valid_at": current["time"] + "Z"}
    except (SourceError, ValueError, TypeError, AttributeError) as exc:
        return {**base, "status": "unavailable", "current": None,
                "error": str(exc) if isinstance(exc, SourceError) else "weather_invalid_payload"}


def _history(points: list[dict], station_id: int | None, pollutant: str, metadata: dict, mode: str) -> dict:
    selected_points = [p for p in points if p["pollutant"] == pollutant]
    eligible = [p for p in selected_points if p["quality"]["status"] != "rejected"]
    # Select one sensor/unit series; never splice instruments or gas units.
    groups = Counter((p["sensor_id"], p["unit"]) for p in eligible)
    sensor_id, unit = groups.most_common(1)[0][0] if groups else (None, None)
    series = [p for p in eligible if (p["sensor_id"], p["unit"]) == (sensor_id, unit)]
    return {"status": ("delayed" if mode == "archive" else "available") if series else "unavailable",
            "station_id": station_id, "sensor_id": sensor_id, "pollutant": pollutant, "unit": unit,
            "points": series, "completeness": metadata, "rejected_rows": len(selected_points) - len(eligible),
            "other_sensor_unit_rows": len(eligible) - len(series),
            "from": series[0]["observed_at"] if series else None, "to": series[-1]["observed_at"] if series else None}


async def _load_station(fetcher: _Fetcher, station: dict, pollutant: str, now: datetime) -> tuple[dict, dict]:
    station = copy.deepcopy(station)
    latest_rows, latest_meta = await fetcher.pages(f"/locations/{station['id']}/latest", {}, 1)
    measurements = []
    sensor_lookup = {s["id"]: s for s in station["sensors"]}
    for raw in latest_rows:
        sensor = sensor_lookup.get(raw.get("sensorsId"))
        if sensor is not None and raw.get("locationsId", station["id"]) == station["id"]:
            measurements.append(normalize_measurement(raw, station_id=station["id"], sensor_id=sensor["id"],
                pollutant=sensor["pollutant"], unit=sensor["unit"], now=now, source="openaq_v3",
                source_url=f"{API_BASE}/locations/{station['id']}/latest"))
    station["measurements"] = deduplicate_measurements(measurements)
    station["latest_status"] = "available" if measurements else "unavailable"
    station["latest_completeness"] = latest_meta
    # Prefer a sensor with a recent latest record, then metadata order, without
    # treating any other station or instrument as an interchangeable series.
    matching = [s for s in station["sensors"] if s["pollutant"] == pollutant and s["unit"]]
    matching.sort(key=lambda s: max((p["observed_at"] or "" for p in measurements if p["sensor_id"] == s["id"]), default=""), reverse=True)
    if not matching:
        return station, _history([], station["id"], pollutant, {"complete": False, "incomplete_reason": "pollutant_sensor_unavailable"}, "live")
    sensor = matching[0]
    url = f"/sensors/{sensor['id']}/hours"
    raw_hours, history_meta = await fetcher.pages(url, {
        "datetime_from": iso(now - timedelta(hours=HISTORY_HOURS)), "datetime_to": iso(now)}, MAX_HISTORY_PAGES)
    points = deduplicate_measurements([normalize_measurement(raw, station_id=station["id"], sensor_id=sensor["id"],
        pollutant=pollutant, unit=sensor["unit"], now=now, source="openaq_v3", source_url=API_BASE + url,
        hourly=True) for raw in raw_hours])
    history_meta["requested_hours"] = HISTORY_HOURS
    history_meta["valid_hourly_rows"] = sum(p["quality"]["status"] == "valid" for p in points)
    history_meta["hourly_completeness"] = min(1, history_meta["valid_hourly_rows"] / HISTORY_HOURS)
    return station, _history(points, station["id"], pollutant, history_meta, "live")


def build_candidates(histories: list[dict], stations: list[dict], *, now: datetime) -> tuple[list[dict], dict]:
    """Only corroborated, fresh station anomalies become human review candidates."""
    anomalies = []
    indexed = {s["id"]: s for s in stations}
    mobility_excluded = 0
    for history in histories:
        clean = accepted_series(history["points"], now)
        if len(clean) < 25:
            continue
        latest = clean[-1]
        if indexed.get(latest["station_id"], {}).get("is_mobile") is not False:
            mobility_excluded += 1
            continue
        stamp = parse_time(latest["observed_at"])
        if now - stamp > timedelta(hours=3):
            continue
        previous = [p for p in clean[:-1] if stamp - timedelta(hours=30) <= parse_time(p["observed_at"]) < stamp][-24:]
        if len(previous) < 24:
            continue
        baseline = median(p["value"] for p in previous)
        mad = median(abs(p["value"] - baseline) for p in previous)
        # Relative and robust spread gates are screening criteria, not legal
        # limits or health thresholds; all terms stay in the measured unit.
        excess = latest["value"] - baseline
        threshold = max(3 * 1.4826 * mad, abs(baseline) * 0.5)
        if excess <= threshold or latest["value"] <= 0:
            continue
        anomalies.append({"latest": latest, "baseline": baseline, "excess": excess, "threshold": threshold})
    candidates = []
    for anomaly in anomalies:
        latest = anomaly["latest"]
        peers = [a for a in anomalies if a["latest"]["station_id"] != latest["station_id"]
                 and a["latest"]["pollutant"] == latest["pollutant"] and a["latest"]["unit"] == latest["unit"]
                 and abs((parse_time(a["latest"]["observed_at"]) - parse_time(latest["observed_at"])).total_seconds()) <= 3600]
        if not peers:
            continue
        station = indexed.get(latest["station_id"], {})
        candidates.append({"id": f"review-{latest['station_id']}-{latest['pollutant']}-{latest['observed_at']}",
            "station_id": latest["station_id"], "name": station.get("name"),
            "latitude": station.get("latitude"), "longitude": station.get("longitude"),
            "pollutant": latest["pollutant"], "unit": latest["unit"], "observed_at": latest["observed_at"],
            "value": latest["value"], "baseline": anomaly["baseline"], "excess": anomaly["excess"],
            "screening_threshold": anomaly["threshold"], "status": "human_review_required",
            "cause": "unverified", "source_attribution": None, "enforcement_allowed": False,
            "locality_geometry_status": "unverified; candidate is attached to a station point only",
            "corroboration": [{"station_id": p["latest"]["station_id"], "observed_at": p["latest"]["observed_at"],
                "value": p["latest"]["value"], "baseline": p["baseline"],
                "station_distance_km": round(_haversine(station, indexed[p["latest"]["station_id"]]), 2)
                    if station and p["latest"]["station_id"] in indexed else None} for p in peers],
            "representativeness_radius_km": None,
            "message": "Concurrent elevation at distinct stations is supporting context, not proof of a shared local source. Verify locality geometry and independent local evidence."})
    return candidates, {"status": "review_candidates" if candidates else "insufficient_evidence" if anomalies else "no_qualified_candidate",
        "mobile_or_unknown_stations_excluded": mobility_excluded,
        "stations_evaluated": len(histories), "uncorroborated_anomalies": sum(not any(c["station_id"] == a["latest"]["station_id"] for c in candidates) for a in anomalies),
        "message": "Requires 24 prior valid hourly samples, a fresh anomaly, and a separate station's same-unit anomaly within one hour. No source attribution or automatic enforcement."}


async def _archive_station(fetcher: _Fetcher, station_id: int, now: datetime, pollutant: str) -> tuple[dict | None, dict]:
    local_day = now.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
    days = [local_day - timedelta(days=offset) for offset in (4, 5, 6)]

    async def one_day(day):
        url = f"{ARCHIVE_BASE}/locationid={station_id}/year={day.year}/month={day.month:02d}/location-{station_id}-{day:%Y%m%d}.csv.gz"
        try:
            compressed = await fetcher.content(url, archive=True)
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as archive:
                content = archive.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise SourceError("archive_decompressed_limit")
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            rows = []
            for index, row in enumerate(reader):
                if index >= MAX_ARCHIVE_ROWS:
                    raise SourceError("archive_row_limit")
                if _positive_id(row.get("location_id")) == station_id and row.get("parameter") in POLLUTANTS:
                    row["source_url"] = url
                    rows.append(row)
            return rows, {"date": str(day), "status": "available", "source_url": url}
        except (SourceError, OSError, EOFError, UnicodeError, csv.Error) as exc:
            return [], {"date": str(day), "status": "unavailable", "error": str(exc) if isinstance(exc, SourceError) else "archive_invalid_payload", "source_url": url}

    fetched = await asyncio.gather(*(one_day(day) for day in days))
    rows = [row for batch, _ in fetched for row in batch]
    files = [meta for _, meta in fetched]
    metadata = {"complete": all(m["status"] == "available" for m in files), "files": files,
                "scope": "Three archive days for two known OpenAQ locations; not Delhi-wide station discovery",
                "minimum_publication_delay_hours": 72, "quality_flags_available": False}
    if not rows:
        return None, _history([], station_id, pollutant, metadata, "archive")
    first = rows[0]
    sensors = {}
    for row in rows:
        sensor_id = _positive_id(row.get("sensors_id"))
        if sensor_id:
            sensors[sensor_id] = {"id": sensor_id, "parameter": {"name": row["parameter"], "units": row.get("units")}}
    station = station_from_location({"id": station_id, "name": first.get("location"),
        "coordinates": {"latitude": first.get("lat"), "longitude": first.get("lon")},
        "sensors": list(sensors.values())}, source="openaq_archive")
    if station is None:
        return None, _history([], station_id, pollutant, metadata, "archive")
    points = []
    for row in rows:
        sensor_id = _positive_id(row.get("sensors_id"))
        if sensor_id is None:
            continue
        points.append(normalize_measurement(row, station_id=station_id, sensor_id=sensor_id,
            pollutant=row["parameter"], unit=row.get("units"), now=now, source="openaq_archive", source_url=row["source_url"]))
    points = deduplicate_measurements(points)
    latest = {}
    for point in points:
        if point["quality"]["status"] != "rejected":
            latest[(point["sensor_id"], point["unit"])] = point
    station["measurements"] = list(latest.values())
    station["latest_at"] = max((p["observed_at"] for p in latest.values()), default=None)
    station["latest_status"] = "delayed"
    station["source_url"] = files[0]["source_url"]
    station["archive_completeness"] = metadata
    return station, _history(points, station_id, pollutant, metadata, "archive")


def _base_snapshot(now: datetime, pollutant: str, mode: str) -> dict:
    return {"schema_version": "2.0", "generated_at": iso(now), "requested_mode": mode,
        "status": "unavailable", "message": "No measurements available.", "selected_station_id": None,
        "selected_pollutant": pollutant, "stations": [],
        "history": _history([], None, pollutant, {"complete": False}, mode),
        "forecast": build_forecast([], now=now), "candidates": [],
        "candidate_status": {"status": "insufficient_evidence", "message": "Fresh quality-checked measurements and independent corroboration are required."},
        "weather": {"status": "unavailable", "kind": "weather_model_estimate"},
        "coverage": {"bbox": list(DELHI_BBOX), "scope": "OpenAQ locations within a Delhi/NCR discovery bounding box",
                     "complete": False, "returned": 0, "total_reported": None, "pages_fetched": 0,
                     "all_physical_sensors": False, "administrative_boundary": False,
                     "representativeness_radius_km": None},
        "sources": [], "limitations": ["OpenAQ is a third-party aggregator; these values are not certified official AQI.",
            "Station points have no assumed 5 km or other sensing radius. Search distance is not spatial representativeness.",
            "Discovery completeness covers the API query only, not every monitor in Delhi or physical hardware.",
            "Predictions and candidates support human investigation; neither identifies a pollution source nor authorizes enforcement."]}


async def _build(fetcher: _Fetcher, station_id: int | None, pollutant: str, mode: str, now: datetime) -> dict:
    snapshot = _base_snapshot(now, pollutant, mode)
    use_archive = mode == "archive" or not fetcher.api_key
    if use_archive:
        results = await asyncio.gather(*(_archive_station(fetcher, sid, now, pollutant) for sid in (17, 235)))
        stations = [station for station, _ in results if station]
        histories = {h["station_id"]: h for _, h in results}
        selected = next((s for s in stations if s["id"] == station_id), None) if station_id else next(iter(stations), None)
        snapshot["stations"] = stations
        snapshot["coverage"].update(returned=len(stations), complete=False,
            scope="Two known archive locations (17, 235), not Delhi-wide live discovery", incomplete_reason="live_api_key_unavailable" if not fetcher.api_key else "archive_subset")
        snapshot["sources"].append({"id": "openaq_archive", "status": "delayed" if stations else "unavailable",
            "label": "OpenAQ public archive — 72+ hours delayed", "url": "https://docs.openaq.org/aws/about",
            "minimum_publication_delay_hours": 72, "live": False})
        if not fetcher.api_key:
            snapshot["sources"].append({"id": "openaq_v3", "status": "unavailable", "reason": "OPENAQ_API_KEY is not configured on the server", "live": False})
        if selected:
            snapshot.update(status="delayed", selected_station_id=selected["id"], history=histories[selected["id"]],
                message="Showing real archived observations, published at least 72 hours after each day ends. Live monitoring is unavailable." if not fetcher.api_key else "Showing real delayed OpenAQ archive observations.")
        elif station_id:
            snapshot["message"] = "Requested station is not available in the bounded archive subset. Configure live OpenAQ access for station discovery."
        snapshot["forecast"].update(status="stale_input", message="Current forecasts withheld: archive observations are delayed and upstream quality flags are unavailable.")
        snapshot["weather"] = await _weather(fetcher, selected)
        return snapshot
    raw_locations, coverage = await _discover_locations(fetcher)
    stations_by_id = {}
    for raw in raw_locations:
        station = station_from_location(raw)
        if station is not None:
            stations_by_id[station["id"]] = station
    stations = list(stations_by_id.values())
    snapshot["coverage"].update(coverage, returned=len(stations), rejected_or_duplicate_metadata_rows=len(raw_locations) - len(stations))
    available = [s for s in stations if s["is_mobile"] is False and any(p["pollutant"] == pollutant for p in s["sensors"])]
    available.sort(key=lambda s: s["latest_at"] or "", reverse=True)
    selected = stations_by_id.get(station_id) if station_id else next(iter(available), next(iter(stations), None))
    if selected:
        peers = sorted([s for s in available if s["id"] != selected["id"]], key=lambda s: _haversine(selected, s))[:MAX_PEERS]
        results = await asyncio.gather(*(_load_station(fetcher, s, pollutant, now) for s in [selected, *peers]))
        histories = []
        for station, history in results:
            stations_by_id[station["id"]] = station
            histories.append(history)
        selected = stations_by_id[selected["id"]]
        snapshot.update(selected_station_id=selected["id"], history=histories[0],
                        forecast=build_forecast(histories[0]["points"], now=now))
        snapshot["candidates"], snapshot["candidate_status"] = build_candidates(histories, list(stations_by_id.values()), now=now)
        has_current = any(p["fresh"] and p["quality"]["status"] != "rejected" for p in selected["measurements"] if p["pollutant"] == pollutant)
        has_history = bool(histories[0]["points"])
        snapshot["status"] = ("live" if coverage["complete"] else "partial") if has_current else "delayed" if has_history else "unavailable"
        snapshot["message"] = "Fresh station observations received; source quality remains provisional." if has_current else "No fresh observation for the selected pollutant. Available history retains its original timestamps."
        if selected["is_mobile"] is not False:
            snapshot["forecast"] = build_forecast([], now=now)
            snapshot["forecast"].update(status="mobile_station" if selected["is_mobile"] else "mobility_unknown",
                message="Station forecast withheld: a stationary location has not been confirmed.")
        snapshot["coverage"]["latest_stations_requested"] = len(results)
        snapshot["coverage"]["latest_stations_total"] = len(stations)
    elif station_id:
        snapshot["message"] = "Requested station was not found within the returned Delhi/NCR discovery results."
    else:
        snapshot["message"] = "OpenAQ station discovery is unavailable or returned no Delhi/NCR locations."
    snapshot["stations"] = list(stations_by_id.values())
    snapshot["weather"] = await _weather(fetcher, selected)
    snapshot["sources"].append({"id": "openaq_v3", "status": snapshot["status"], "label": "OpenAQ v3 station observations",
        "url": "https://docs.openaq.org", "live": snapshot["status"] in {"live", "partial"}, "discovery": coverage})
    return snapshot


async def _collect_snapshot(station_id: int | None, pollutant: str, mode: str, timestamp: datetime,
                            client: httpx.AsyncClient | None, key: str, cache_key: tuple, use_cache: bool) -> dict:
    own_client = client is None
    client = client or httpx.AsyncClient(limits=httpx.Limits(max_connections=3), trust_env=False)
    fetcher = _Fetcher(client, key, shared_discovery=use_cache)
    try:
        result = await asyncio.wait_for(_build(fetcher, station_id, pollutant, mode, timestamp), timeout=45)
    except asyncio.TimeoutError:
        result = _base_snapshot(timestamp, pollutant, mode)
        result["message"] = "Source collection exceeded the bounded 45-second deadline. Retry after a minute."
        result["coverage"]["incomplete_reason"] = "collection_deadline"
    finally:
        if own_client:
            await client.aclose()
    result["network_requests"] = fetcher.requests
    result["cache"] = {"hit": False, "ttl_seconds": CACHE_TTL_SECONDS}
    result["request_protection"] = {"scope": "per_process", "max_unique_inflight_snapshots": MAX_CONCURRENT_SNAPSHOTS,
        "distributed_rate_limit": False, "message": "Per-process bounds do not prevent shared upstream quota exhaustion across instances; deployment edge rate limiting is required."}
    if use_cache:
        _CACHE[cache_key] = (time.monotonic(), copy.deepcopy(result))
        while len(_CACHE) > MAX_SNAPSHOT_CACHE_ENTRIES:
            _CACHE.popitem(last=False)
    return result


async def build_snapshot(station_id: int | None = None, pollutant: str = "pm25", mode: str = "live",
                         *, now: datetime | None = None, client: httpx.AsyncClient | None = None,
                         api_key: str | None = None) -> dict:
    """Public entry point. `client` and `now` allow deterministic, offline tests.

    Supported modes: live (keyed API, or explicitly delayed public archive when
    no key is configured) and archive. Each response has a 45-second deadline,
    6-second request timeout, at most three concurrent requests, bounded pages
    and response bytes. At most two unique snapshots run per process; identical
    requests share work. One-minute caches retain 24 snapshots and four discovery
    results. These process-local bounds are not distributed quota protection.
    """
    if pollutant not in POLLUTANTS:
        raise ValueError("Unsupported pollutant")
    if mode not in {"live", "archive"}:
        raise ValueError("mode must be live or archive")
    if station_id is not None and _positive_id(station_id) is None:
        raise ValueError("station_id must be a positive integer")
    station_id = int(station_id) if station_id is not None else None
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    key = api_key if api_key is not None else os.environ.get("OPENAQ_API_KEY", "").strip()
    cache_key = (station_id, pollutant, mode, hashlib.sha256(key.encode()).hexdigest())
    use_cache = client is None and now is None
    if use_cache and cache_key in _CACHE:
        inserted, cached = _CACHE[cache_key]
        if time.monotonic() - inserted < CACHE_TTL_SECONDS:
            result = copy.deepcopy(cached)
            result["cache"] = {"hit": True, "ttl_seconds": CACHE_TTL_SECONDS, "snapshot_age_seconds": round(time.monotonic() - inserted, 2)}
            return result
        del _CACHE[cache_key]
    if not use_cache:
        return await _collect_snapshot(station_id, pollutant, mode, timestamp, client, key, cache_key, False)
    task = _INFLIGHT.get(cache_key)
    coalesced = task is not None
    if task is None and len(_INFLIGHT) >= MAX_CONCURRENT_SNAPSHOTS:
        result = _base_snapshot(timestamp, pollutant, mode)
        result.update(status="overloaded", error_code="snapshot_capacity", retry_after_seconds=15,
            message="This process is collecting its maximum of two distinct snapshots. Retry in 15 seconds.",
            network_requests=0, request_protection={"scope": "per_process", "distributed_rate_limit": False})
        return result
    if task is None:
        task = asyncio.create_task(_collect_snapshot(station_id, pollutant, mode, timestamp, None, key, cache_key, True))
        _INFLIGHT[cache_key] = task
        task.add_done_callback(lambda finished: _forget_task(_INFLIGHT, cache_key, finished))
    result = copy.deepcopy(await asyncio.shield(task))
    result["cache"]["coalesced"] = coalesced
    return result
