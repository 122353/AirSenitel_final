"""Opt-in official evidence feeds; never substitute fire pixels for surface AQI.

Only documented public API hosts are called. Credentials stay on the server and
are deliberately absent from exceptions, returned provenance and cache keys.
"""
from __future__ import annotations

import asyncio
import copy
import csv
import hashlib
import io
import math
import os
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from .forecast_v2 import iso, parse_time

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))
INDIA_BOUNDS = (68.0, 6.0, 98.5, 38.5)
CPCB_RESOURCE = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
CPCB_URL = "https://www.data.gov.in/catalog/real-time-air-quality-index"
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/"
FIRMS_PRODUCT = "VIIRS_NOAA20_NRT"
CACHE_TTL_SECONDS = 900
FAILURE_CACHE_SECONDS = 60
MAX_RESPONSE_BYTES = 6_000_000
MAX_CPCB_PAGES = 6
CPCB_PAGE_SIZE = 1000
MAX_FIRE_ROWS = 20_000
MAX_RETURNED_RECORDS = 300
CONTEXT_RADIUS_KM = 100
_CACHE: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
_SOURCE_LOCKS: dict[tuple, list] = {}


class SourceUnavailable(Exception):
    """A fixed, credential-free error that is safe to expose."""


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _nonnegative(value: Any) -> float | None:
    value = _number(value)
    return value if value is not None and value >= 0 else None


def _coordinates(latitude: Any, longitude: Any) -> tuple[float, float] | None:
    lat, lon = _number(latitude), _number(longitude)
    west, south, east, north = INDIA_BOUNDS
    if lat is None or lon is None or not (south <= lat <= north and west <= lon <= east):
        return None
    return lat, lon


def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, a))))


def _stamp_fields(stamp: datetime | None, now: datetime, fresh_hours: float) -> dict:
    age = (now - stamp).total_seconds() / 3600 if stamp else None
    freshness = "unknown" if age is None else "future_timestamp" if age < 0 else "fresh" if age <= fresh_hours else "stale"
    return {"observed_at": iso(stamp) if stamp else None, "age_hours": round(age, 2) if age is not None else None,
            "freshness": freshness}


def _source(source_id: str) -> dict:
    nasa = source_id == "nasa_firms"
    return {"id": source_id, "label": "NASA FIRMS / NOAA-20 VIIRS" if nasa else "CPCB via data.gov.in",
            "source_url": FIRMS_URL if nasa else CPCB_URL, "status": "unavailable", "records": [],
            "official_aqi": False, "usable_for_concentration_forecast": False,
            "evidence_type": "satellite_fire_context" if nasa else "government_published_snapshot",
            "coverage": {"records_received": 0, "records_returned": 0, "partial": False},
            "freshness": {"latest_observed_at": None, "fresh_records": 0, "stale_records": 0,
                          "unknown_time_records": 0}}


async def _request(client: httpx.AsyncClient, url: str, *, params: dict | None = None) -> bytes:
    """Bound reads before buffering. Never return upstream messages or request URLs."""
    try:
        async with client.stream("GET", url, params=params, timeout=8, follow_redirects=False) as response:
            if response.status_code == 429:
                raise SourceUnavailable("Provider rate limit reached; retry after the cache window")
            if response.status_code in (401, 403):
                raise SourceUnavailable("Provider rejected the configured credential")
            if response.status_code != 200:
                raise SourceUnavailable("Provider returned an unsuccessful response")
            output = bytearray()
            async for chunk in response.aiter_bytes():
                output.extend(chunk)
                if len(output) > MAX_RESPONSE_BYTES:
                    raise SourceUnavailable("Provider response exceeded the safe size limit")
            return bytes(output)
    except (httpx.HTTPError, OSError) as exc:
        raise SourceUnavailable("Provider request failed or timed out") from None


def _cpcb_time(value: Any) -> datetime | None:
    parsed = parse_time(value)
    if parsed:
        return parsed
    if not isinstance(value, str):
        return None
    for pattern in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            # The Indian current snapshot publishes local Indian time when no offset exists.
            return datetime.strptime(value, pattern).replace(tzinfo=IST).astimezone(UTC)
        except ValueError:
            pass
    return None


def _cpcb_record(row: Any) -> dict | None:
    if not isinstance(row, dict) or str(row.get("country", "India")).casefold() not in ("india", "in"):
        return None
    coordinates = _coordinates(row.get("latitude"), row.get("longitude"))
    if not coordinates or not row.get("station") or not row.get("pollutant_id"):
        return None
    values = {name: _nonnegative(row.get(key)) for name, key in
              (("min", "pollutant_min"), ("max", "pollutant_max"), ("average", "pollutant_avg"))}
    flags = ["units_unverified"]
    if any(value is None for value in values.values()):
        flags.append("missing_or_invalid_published_value")
    if values["min"] is not None and values["max"] is not None and values["min"] > values["max"]:
        flags.append("inconsistent_range")
    if (all(value is not None for value in values.values())
            and not values["min"] <= values["average"] <= values["max"]):
        flags.append("average_outside_published_range")
    stamp = _cpcb_time(row.get("last_update"))
    return {"station": str(row["station"])[:240], "city": str(row.get("city", ""))[:120],
            "state": str(row.get("state", ""))[:120], "latitude": coordinates[0], "longitude": coordinates[1],
            "pollutant": str(row["pollutant_id"])[:20], "published_values": values,
            "observed_at": iso(stamp) if stamp else None, "unit": None, "units_verified": False,
            "evidence_type": "government_published_snapshot", "quality_flags": flags,
            "timestamp_assumption": "Asia/Kolkata when upstream time has no offset"}


async def _fetch_cpcb(client: httpx.AsyncClient, key: str, resource: str) -> dict:
    import json

    result = _source("cpcb_data_gov")
    result["freshness_window_hours"] = 3
    result["reason"] = "Published values are preserved; units and index semantics are not verified, so these are not concentration forecasts"
    if not re.fullmatch(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", resource):
        result["reason"] = "CPCB_DATA_GOV_RESOURCE_ID must be a valid resource UUID"
        return result
    received, rejected, total, offset, pages, seen = 0, 0, None, 0, 0, {}
    for page in range(MAX_CPCB_PAGES):
        try:
            body = await _request(client, f"https://api.data.gov.in/resource/{resource}", params={
                "api-key": key, "format": "json", "limit": CPCB_PAGE_SIZE, "offset": offset})
            payload = json.loads(body)
            rows = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise SourceUnavailable("Provider response did not contain a station snapshot")
            total_value = _nonnegative(payload.get("total"))
            total = int(total_value) if total_value is not None else None
            pages += 1
            # Page limits are checked even if the upstream ignores our requested limit.
            if len(rows) > CPCB_PAGE_SIZE:
                rows = rows[:CPCB_PAGE_SIZE]
                result["coverage"]["partial"] = True
            received += len(rows)
            new_records = 0
            for row in rows:
                record = _cpcb_record(row)
                if record is None:
                    rejected += 1
                    continue
                identity = (record["station"], record["city"], record["state"], record["pollutant"], record["observed_at"])
                if identity in seen:
                    first = seen[identity]
                    if (first["published_values"] != record["published_values"]
                            or first["latitude"] != record["latitude"] or first["longitude"] != record["longitude"]):
                        if "conflicting_duplicate" not in first["quality_flags"]:
                            first["quality_flags"].append("conflicting_duplicate")
                    continue
                seen[identity] = record
                result["records"].append(record)
                new_records += 1
            offset += len(rows)
            if not rows or (total is not None and offset >= total):
                break
            if new_records == 0 or (total is None and len(rows) < CPCB_PAGE_SIZE):
                result["coverage"]["partial"] = total is None or offset < total
                break
        except (SourceUnavailable, ValueError, TypeError):
            result["coverage"]["partial"] = True
            result["reason"] = "Government snapshot unavailable or incomplete; previously parsed pages are retained without inventing readings"
            break
    result["coverage"].update({"records_received": received, "records_validated": len(result["records"]),
                               "records_rejected": rejected, "upstream_total": total, "pages_loaded": pages,
                               "partial": result["coverage"]["partial"] or (total is None and pages >= MAX_CPCB_PAGES)
                               or (total is not None and offset < total)})
    result["status"] = "partial" if result["coverage"]["partial"] and pages else "available" if pages else "unavailable"
    return result


async def _fetch_firms(client: httpx.AsyncClient, key: str) -> dict:
    result = _source("nasa_firms")
    result.update({"product": FIRMS_PRODUCT, "spatial_resolution_m": 375, "freshness_window_hours": 24,
                   "lookback_days": 2, "reason": "Thermal detections are context after satellite overpass, not AQI, smoke concentration or proof of a pollution source"})
    try:
        # One India country request is reused for national and local views for 15 minutes.
        body = await _request(client, f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{quote(key, safe='')}/{FIRMS_PRODUCT}/IND/2")
        reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
        if not reader.fieldnames or not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(reader.fieldnames):
            raise SourceUnavailable("Provider response did not contain the expected fire-detection fields")
        rejected, received, seen = 0, 0, set()
        for index, row in enumerate(reader):
            if index >= MAX_FIRE_ROWS:
                result["coverage"]["partial"] = True
                break
            received += 1
            coordinates = _coordinates(row.get("latitude"), row.get("longitude"))
            try:
                stamp = datetime.strptime(f"{row['acq_date']} {row['acq_time'].zfill(4)}", "%Y-%m-%d %H%M").replace(tzinfo=UTC)
            except (ValueError, KeyError, AttributeError):
                stamp = None
            if coordinates is None or stamp is None or row.get("country_id", "IND") != "IND":
                rejected += 1
                continue
            identity = (*coordinates, iso(stamp))
            if identity in seen:
                continue
            seen.add(identity)
            confidence = str(row.get("confidence", "")).lower()
            result["records"].append({"latitude": coordinates[0], "longitude": coordinates[1],
                "observed_at": iso(stamp), "frp_mw": _nonnegative(row.get("frp")),
                "confidence": {"h": "high", "n": "nominal", "l": "low"}.get(confidence, "unknown"),
                "evidence_type": "satellite_fire_context", "quality_flags": ["context_only"] +
                (["low_or_unknown_confidence"] if confidence not in ("h", "n") else [])})
        result["coverage"].update({"records_received": received, "records_validated": len(result["records"]),
                                   "records_rejected": rejected, "country_code": "IND"})
        result["status"] = "partial" if result["coverage"]["partial"] else "available"
    except (SourceUnavailable, UnicodeError, csv.Error) as exc:
        result["reason"] = str(exc) if isinstance(exc, SourceUnavailable) else "Provider fire data could not be parsed"
    return result


async def _load_source(source_id: str, key: str, resource: str, client: httpx.AsyncClient, use_cache: bool) -> dict:
    if not key:
        result = _source(source_id)
        result.update({"status": "not_configured", "reason": "NASA_FIRMS_MAP_KEY is not configured on the server" if source_id == "nasa_firms" else "CPCB_DATA_GOV_API_KEY is not configured on the server"})
        return result
    cache_key = (source_id, hashlib.sha256(key.encode()).hexdigest(), resource)
    cached = _CACHE.get(cache_key) if use_cache else None
    if cached:
        inserted, payload = cached
        ttl = FAILURE_CACHE_SECONDS if payload["status"] == "unavailable" else CACHE_TTL_SECONDS
        if time.monotonic() - inserted < ttl:
            result = copy.deepcopy(payload)
            result["cache"] = {"hit": True, "age_seconds": round(time.monotonic() - inserted, 1), "ttl_seconds": ttl}
            return result
    try:
        result = await asyncio.wait_for(_fetch_firms(client, key) if source_id == "nasa_firms" else _fetch_cpcb(client, key, resource), timeout=18)
    except asyncio.TimeoutError:
        result = _source(source_id)
        result["reason"] = "Provider exceeded the total request time budget"
    result["fetched_at"] = iso(datetime.now(UTC))
    if use_cache:
        _CACHE[cache_key] = (time.monotonic(), copy.deepcopy(result))
        _CACHE.move_to_end(cache_key)
        while len(_CACHE) > 8:
            _CACHE.popitem(last=False)
    result["cache"] = {"hit": False, "ttl_seconds": FAILURE_CACHE_SECONDS if result["status"] == "unavailable" else CACHE_TTL_SECONDS}
    return result


async def _cached_source(source_id: str, key: str, resource: str, client: httpx.AsyncClient, use_cache: bool) -> dict:
    """Serialize equal cold fetches without sharing a caller-owned HTTP client.

    The second waiter checks the cache after acquiring the lock. Cancellation of
    one requester cannot close another requester's client or cached payload.
    Bounds are per process, not a distributed national ingestion guarantee.
    """
    if not use_cache or not key:
        return await _load_source(source_id, key, resource, client, use_cache)
    lock_key = (id(asyncio.get_running_loop()), source_id, hashlib.sha256(key.encode()).hexdigest(), resource)
    entry = _SOURCE_LOCKS.get(lock_key)
    if entry is None:
        if len(_SOURCE_LOCKS) >= 4:
            result = _source(source_id)
            result["reason"] = "Source request capacity reached; retry shortly"
            return result
        entry = [asyncio.Lock(), 0]
        _SOURCE_LOCKS[lock_key] = entry
    entry[1] += 1
    try:
        async with entry[0]:
            return await _load_source(source_id, key, resource, client, use_cache)
    finally:
        entry[1] -= 1
        if not entry[1]:
            _SOURCE_LOCKS.pop(lock_key, None)


def _scope_and_age(result: dict, coordinates: tuple | None, now: datetime) -> dict:
    records = result["records"]
    if coordinates:
        scoped = []
        for row in records:
            distance = _distance(*coordinates, row["latitude"], row["longitude"])
            if distance <= CONTEXT_RADIUS_KM:
                row["distance_km"] = round(distance, 2)
                scoped.append(row)
        records = scoped
    for row in records:
        row.update(_stamp_fields(parse_time(row.get("observed_at")), now, result.get("freshness_window_hours", 3)))
        if row["freshness"] in ("unknown", "future_timestamp"):
            row["quality_flags"].append("invalid_observation_time")
    valid_times = [row["observed_at"] for row in records if row["freshness"] not in ("unknown", "future_timestamp")]
    result["freshness"] = {"latest_observed_at": max(valid_times) if valid_times else None,
                           "fresh_records": sum(row["freshness"] == "fresh" for row in records),
                           "stale_records": sum(row["freshness"] == "stale" for row in records),
                           "unknown_time_records": sum(row["freshness"] in ("unknown", "future_timestamp") for row in records)}
    records.sort(key=lambda row: row.get("observed_at") or "", reverse=True)
    result["records"] = records[:MAX_RETURNED_RECORDS]
    result["coverage"].update({"records_in_scope": len(records), "records_returned": len(result["records"]),
                               "display_truncated": len(records) > MAX_RETURNED_RECORDS})
    if result["status"] == "available" and records and not result["freshness"]["fresh_records"]:
        result["status"] = "delayed"
    result["empty_does_not_mean_clean_air"] = True
    return result


async def get_source_context(latitude=None, longitude=None, *, now=None, client=None) -> dict:
    """Return optional NASA/government evidence, independent of forecast generation.

    A selected location limits displayed evidence to a 100-km context radius; it
    does not assert that a monitor/fire represents every point in that radius.
    National snapshots use a bounded 15-minute warm-process cache, not a durable
    background collector. Injected clients bypass that cache for deterministic QA.
    """
    coordinates = None
    if latitude is not None or longitude is not None:
        coordinates = _coordinates(latitude, longitude)
        if coordinates is None:
            raise ValueError("Provide finite latitude and longitude within India operating bounds")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must include a timezone")
    current = current.astimezone(UTC)
    owned_client = client is None
    if owned_client:
        client = httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False)
    try:
        sources = await asyncio.gather(
            _cached_source("nasa_firms", (os.getenv("NASA_FIRMS_MAP_KEY") or os.getenv("FIRMS_MAP_KEY") or "").strip(), "", client, owned_client),
            _cached_source("cpcb_data_gov", os.getenv("CPCB_DATA_GOV_API_KEY", "").strip(),
                           os.getenv("CPCB_DATA_GOV_RESOURCE_ID", CPCB_RESOURCE).strip(), client, owned_client))
    finally:
        if owned_client:
            await client.aclose()
    scope = {"type": "india"} if coordinates is None else {"type": "nearby_context", "latitude": coordinates[0],
             "longitude": coordinates[1], "radius_km": CONTEXT_RADIUS_KM}
    return {"generated_at": iso(current), "scope": scope,
            "sources": [_scope_and_age(source, coordinates, current) for source in sources],
            "limitations": ["These optional feeds provide separate evidence, not a trained sensor-satellite fusion forecast.",
                "Fire detections occur after overpass; missing detections do not rule out burning or pollution.",
                "Government snapshot units require verification before concentration modelling or AQI conversion.",
                "National fetching is on demand with a warm-process cache; no continuous all-station collector is implied."]}
