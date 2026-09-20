"""Private operator-attested device ingestion and conservative inspection hints.

All routes calling this service must require authority authentication. Device
registration is an operator attestation, not platform verification of hardware,
calibration or physical independence. Inspection cells do not imply sensor range.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from statistics import median
import unicodedata
import uuid

from src.services.case_store_v2 import (
    POLLUTANTS, StoreError, _actor_id, _digest, _json, _now, _number, _text, transaction,
)


# Matches the public monitoring discovery scope; not an administrative boundary.
DELHI_NCR_BBOX = (76.8, 28.3, 77.6, 29.0)
MAX_SAMPLES = 100
MAX_QUERY_ROWS = 10000
MAX_QUERY_HOURS = 72
CELL_SIZE_M = 250
FRESHNESS_HOURS = 2
MIN_SAMPLE_SPAN_MINUTES = 20
MATCH_TOLERANCE_MINUTES = 20
BACKGROUND_DISTANCE_M = 3000
PM25_SCREENING_THRESHOLD = 75
MIN_BACKGROUND_RATIO = 1.5
MIN_BACKGROUND_EXCESS = 20
_METERS_PER_DEGREE = 111320.0
_GRID_LATITUDE = 28.3
_GRID_LONGITUDE = 76.8
_LONGITUDE_SCALE = _METERS_PER_DEGREE * math.cos(math.radians(28.65))


def _timestamp(value, field):
    try:
        if not isinstance(value, str):
            raise ValueError()
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise StoreError(422, f"{field} must be a timestamp with timezone")


def _channel(pollutant, unit):
    if not isinstance(pollutant, str) or pollutant not in POLLUTANTS:
        raise StoreError(422, "Unsupported pollutant")
    if not isinstance(unit, str) or unit not in {"ug/m3", "mg/m3"} or (pollutant != "co" and unit != "ug/m3"):
        raise StoreError(422, "Use ug/m3 for this pollutant, or ug/m3 or mg/m3 for CO")
    return {"pollutant": pollutant, "unit": unit}


def initialize_devices() -> None:
    """Explicit additive initialization in the already configured durable store."""
    with transaction(write=True, initialize=True) as tx:
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_devices (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, registered_by TEXT NOT NULL,
            physical_fingerprint TEXT NOT NULL UNIQUE, metadata_json TEXT NOT NULL
        )""")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_device_observations (
            id TEXT PRIMARY KEY, device_id TEXT NOT NULL REFERENCES airv2_devices(id),
            received_at TEXT NOT NULL, observed_at TEXT NOT NULL, pollutant TEXT NOT NULL,
            unit TEXT NOT NULL, value DOUBLE PRECISION NOT NULL, actor_id TEXT NOT NULL,
            device_snapshot_json TEXT NOT NULL,
            UNIQUE(device_id,pollutant,observed_at)
        )""")
        tx.execute("CREATE INDEX IF NOT EXISTS airv2_device_observed ON airv2_device_observations(observed_at,device_id)")


def _device(row):
    return {
        **json.loads(row["metadata_json"]), "id": row["id"], "created_at": row["created_at"],
        "physical_device_fingerprint": row["physical_fingerprint"],
        "verification_status": "operator_attested_not_independently_verified",
    }


def register_device(payload: dict, actor: dict) -> dict:
    actor_id = _actor_id(actor)
    required = {"physical_device_id", "name", "latitude", "longitude", "location_accuracy_m", "environment", "calibration_reference", "calibration_valid_until", "supported_channels"}
    if not isinstance(payload, dict) or required - set(payload) or set(payload) - (required | {"representativeness_radius_m"}):
        raise StoreError(422, "Provide the documented device fields, with no credentials or extra fields")
    physical_id = _text(payload["physical_device_id"], "physical_device_id", 128)
    physical_id = " ".join(unicodedata.normalize("NFKC", physical_id).casefold().split())
    fingerprint = _digest(physical_id)
    west, south, east, north = DELHI_NCR_BBOX
    latitude = _number(payload["latitude"], "latitude in Delhi/NCR pilot bounds", south, north)
    longitude = _number(payload["longitude"], "longitude in Delhi/NCR pilot bounds", west, east)
    accuracy = _number(payload["location_accuracy_m"], "location_accuracy_m", 0.01, 1000)
    environment = payload["environment"]
    if not isinstance(environment, str) or environment not in {"indoor", "outdoor"}:
        raise StoreError(422, "environment must be indoor or outdoor")
    valid_until = _timestamp(payload["calibration_valid_until"], "calibration_valid_until")
    if valid_until <= datetime.now(timezone.utc):
        raise StoreError(422, "Operator-attested calibration must have a future valid-until timestamp")
    channels = payload["supported_channels"]
    if not isinstance(channels, list) or not 1 <= len(channels) <= 6:
        raise StoreError(422, "Provide one to six supported channels")
    validated_channels = []
    seen = set()
    for channel in channels:
        if not isinstance(channel, dict) or set(channel) != {"pollutant", "unit"}:
            raise StoreError(422, "Channels require only pollutant and unit")
        checked = _channel(channel["pollutant"], channel["unit"])
        if checked["pollutant"] in seen:
            raise StoreError(422, "Register one measurement unit per pollutant")
        seen.add(checked["pollutant"])
        validated_channels.append(checked)
    radius = payload.get("representativeness_radius_m")
    if radius is not None:
        radius = _number(radius, "representativeness_radius_m", 0.01, 10000)
    metadata = {
        "name": _text(payload["name"], "name", 120), "latitude": latitude, "longitude": longitude,
        "location_accuracy_m": accuracy, "environment": environment,
        "calibration_reference": _text(payload["calibration_reference"], "calibration_reference", 500),
        "calibration_valid_until": valid_until.isoformat(),
        "calibration_status": "operator_attestation_only",
        "representativeness_radius_m": radius,
        "representativeness_status": "unknown" if radius is None else "operator_attested_not_platform_verified",
        "supported_channels": validated_channels,
        "physical_independence": "operator_attested_identifier_not_independently_verified",
    }
    row = {"id": str(uuid.uuid4()), "created_at": _now(), "physical_fingerprint": fingerprint, "metadata_json": _json(metadata)}
    with transaction(write=True) as tx:
        inserted = tx.execute("""INSERT INTO airv2_devices
            (id,created_at,registered_by,physical_fingerprint,metadata_json) VALUES(?,?,?,?,?)
            ON CONFLICT(physical_fingerprint) DO NOTHING""", (
            row["id"], row["created_at"], actor_id, fingerprint, row["metadata_json"],
        ))
        if inserted.rowcount != 1:
            raise StoreError(409, "This physical device identifier is already registered")
    return _device(row)


def list_devices(limit: int = 200) -> list[dict]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise StoreError(422, "Device limit must be between 1 and 1000")
    with transaction() as tx:
        rows = tx.execute("SELECT id,created_at,physical_fingerprint,metadata_json FROM airv2_devices ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_device(row) for row in rows]


def ingest_observations(device_id: str, payload: dict, actor: dict) -> dict:
    actor_id = _actor_id(actor)
    if not isinstance(payload, dict) or set(payload) != {"samples"}:
        raise StoreError(422, "Observation ingestion expects a samples array")
    samples = payload["samples"]
    if not isinstance(samples, list) or not 1 <= len(samples) <= MAX_SAMPLES:
        raise StoreError(422, "Ingest between 1 and 100 samples at a time")
    now = datetime.now(timezone.utc)
    checked = []
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {"pollutant", "value", "unit", "observed_at"}:
            raise StoreError(422, "Each sample requires pollutant, value, unit and observed_at only")
        channel = _channel(sample["pollutant"], sample["unit"])
        observed = _timestamp(sample["observed_at"], "observed_at")
        if observed > now + timedelta(minutes=5) or observed < now - timedelta(days=7):
            raise StoreError(422, "Samples must be no older than seven days and no more than five minutes in the future")
        upper = 100 if channel["unit"] == "mg/m3" else (5000 if channel["pollutant"] in {"pm25", "pm10"} else 100000)
        value = _number(sample["value"], "value", 0, upper)
        identity = (channel["pollutant"], observed.isoformat())
        if identity in seen:
            raise StoreError(409, "Duplicate pollutant timestamp in the submitted batch")
        seen.add(identity)
        checked.append({**channel, "value": value, "observed_at": observed.isoformat(), "id": str(uuid.uuid4())})
    with transaction(write=True) as tx:
        row = tx.execute("SELECT id,created_at,physical_fingerprint,metadata_json FROM airv2_devices WHERE id=?", (device_id,)).fetchone()
        if row is None:
            raise StoreError(404, "Registered device not found")
        device = _device(row)
        channels = {(channel["pollutant"], channel["unit"]) for channel in device["supported_channels"]}
        snapshot = _json(device)
        for sample in checked:
            if (sample["pollutant"], sample["unit"]) not in channels:
                raise StoreError(422, "Sample channel does not match this registered device")
            inserted = tx.execute("""INSERT INTO airv2_device_observations
                (id,device_id,received_at,observed_at,pollutant,unit,value,actor_id,device_snapshot_json)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(device_id,pollutant,observed_at) DO NOTHING""", (
                sample["id"], device_id, now.isoformat(), sample["observed_at"], sample["pollutant"],
                sample["unit"], sample["value"], actor_id, snapshot,
            ))
            if inserted.rowcount != 1:
                raise StoreError(409, "A sample for this device, pollutant and timestamp already exists; no samples were changed")
    return {"device_id": device_id, "accepted": len(checked), "observation_ids": [sample["id"] for sample in checked], "verification_status": "operator_attested_not_independently_verified"}


def recent_observations(hours: int = 24, limit: int = 2000) -> dict:
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= MAX_QUERY_HOURS:
        raise StoreError(422, "Query window must be between 1 and 72 hours")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_QUERY_ROWS:
        raise StoreError(422, "Observation limit must be between 1 and 10000")
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=hours)).isoformat()
    with transaction() as tx:
        rows = tx.execute("""SELECT id,device_id,received_at,observed_at,pollutant,unit,value,device_snapshot_json
            FROM airv2_device_observations WHERE observed_at>=? AND observed_at<=?
            ORDER BY observed_at DESC,id LIMIT ?""", (cutoff, now.isoformat(), limit + 1)).fetchall()
        device_rows = tx.execute("SELECT id,created_at,physical_fingerprint,metadata_json FROM airv2_devices ORDER BY created_at DESC LIMIT 1001").fetchall()
    observations = [{
        **{key: row[key] for key in row.keys() if key != "device_snapshot_json"},
        "device_snapshot": json.loads(row["device_snapshot_json"]),
    } for row in rows[:limit]]
    return {
        "devices": [_device(row) for row in device_rows[:1000]], "observations": observations,
        "truncated": len(rows) > limit or len(device_rows) > 1000,
        "window_start": cutoff, "window_end": now.isoformat(),
        "query_window_hours": hours,
        "privacy": "authority_only_device_evidence",
    }


def _cell(latitude, longitude):
    return (
        math.floor((longitude - _GRID_LONGITUDE) * _LONGITUDE_SCALE / CELL_SIZE_M),
        math.floor((latitude - _GRID_LATITUDE) * _METERS_PER_DEGREE / CELL_SIZE_M),
    )


def _cell_center(cell):
    return (
        _GRID_LATITUDE + (cell[1] + 0.5) * CELL_SIZE_M / _METERS_PER_DEGREE,
        _GRID_LONGITUDE + (cell[0] + 0.5) * CELL_SIZE_M / _LONGITUDE_SCALE,
    )


def _distance(latitude_a, longitude_a, latitude_b, longitude_b):
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)
    chord = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(chord)))


def _series_window(series, anchor, *, background=False):
    # Compare device medians, so a high-rate device cannot dominate the cell.
    lower = anchor - timedelta(minutes=60 if not background else 40)
    upper = anchor + timedelta(minutes=20 if background else 0)
    subset = [(timestamp, value) for timestamp, value in series if lower <= timestamp <= upper]
    if len(subset) < 3:
        return None
    if (subset[-1][0] - subset[0][0]).total_seconds() < MIN_SAMPLE_SPAN_MINUTES * 60:
        return None
    if abs((subset[-1][0] - anchor).total_seconds()) > MATCH_TOLERANCE_MINUTES * 60:
        return None
    return {"median": median(value for _, value in subset), "count": len(subset), "start": subset[0][0], "end": subset[-1][0]}


def micro_candidates(data: dict, now: datetime | None = None) -> dict:
    """Pure derivation from private query results; no database or network writes.

    These are research screening heuristics for choosing an inspection location.
    They are not legal AQI limits, causal attribution, a validated spatial model,
    or evidence of complete Delhi coverage.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise StoreError(422, "Analysis time must include a timezone")
    now = now.astimezone(timezone.utc)
    if not isinstance(data, dict) or not isinstance(data.get("devices"), list) or not isinstance(data.get("observations"), list):
        raise StoreError(422, "Analysis requires a bounded device and observation snapshot")
    methodology = {
        "status": "research_screening_heuristics_not_validated", "parameter": "pm25", "unit": "ug/m3",
        "cell_size_m": CELL_SIZE_M, "freshness_hours": FRESHNESS_HOURS,
        "max_location_accuracy_m": 50, "minimum_samples_per_device": 3,
        "minimum_span_minutes": MIN_SAMPLE_SPAN_MINUTES, "minimum_cell_devices": 2,
        "minimum_background_devices": 2, "background_distance_m": BACKGROUND_DISTANCE_M,
        "contemporaneous_tolerance_minutes": MATCH_TOLERANCE_MINUTES,
        "cell_median_threshold": PM25_SCREENING_THRESHOLD, "background_ratio_threshold": MIN_BACKGROUND_RATIO,
        "background_excess_threshold": MIN_BACKGROUND_EXCESS,
        "spatial_meaning": "250 m inspection planning grid; not measurement resolution or sensor range",
        "physical_independence": "distinct operator-attested identifiers; not independently verified",
    }
    result = {"candidates": [], "coverage": {"registered_devices": len(data["devices"]), "eligible_devices": 0, "sampled_cells": 0, "candidate_cells": 0, "complete_area_coverage": False}, "reasons": [], "methodology": methodology}
    if data.get("truncated") or len(data["devices"]) > 1000 or len(data["observations"]) > MAX_QUERY_ROWS:
        result["reasons"] = ["Input is truncated; no inspection candidates are inferred from incomplete evidence."]
        return result
    excluded = Counter()
    devices = {}
    fingerprints = Counter()
    for device in data["devices"]:
        if isinstance(device, dict) and isinstance(device.get("physical_device_fingerprint"), str):
            fingerprints[device["physical_device_fingerprint"]] += 1
    for device in data["devices"]:
        try:
            if not isinstance(device, dict):
                raise ValueError()
            fingerprint = device.get("physical_device_fingerprint")
            if not isinstance(fingerprint, str) or len(fingerprint) != 64 or fingerprints[fingerprint] != 1:
                excluded["missing_or_repeated_physical_identifier"] += 1
                continue
            if device.get("verification_status") != "operator_attested_not_independently_verified" or device.get("calibration_status") != "operator_attestation_only" or not device.get("calibration_reference"):
                excluded["missing_operator_attestation"] += 1
                continue
            if device.get("environment") != "outdoor":
                excluded["indoor_or_unknown_environment"] += 1
                continue
            if _timestamp(device.get("calibration_valid_until"), "calibration_valid_until") <= now:
                excluded["expired_calibration_attestation"] += 1
                continue
            accuracy = _number(device.get("location_accuracy_m"), "location_accuracy_m", 0.01, 1000)
            if accuracy > 50:
                excluded["location_accuracy_above_50m"] += 1
                continue
            if {"pollutant": "pm25", "unit": "ug/m3"} not in device.get("supported_channels", []):
                excluded["no_pm25_channel"] += 1
                continue
            west, south, east, north = DELHI_NCR_BBOX
            lat = _number(device.get("latitude"), "latitude", south, north)
            lon = _number(device.get("longitude"), "longitude", west, east)
            if not isinstance(device.get("id"), str):
                raise ValueError()
            devices[device["id"]] = {**device, "_cell": _cell(lat, lon)}
        except (StoreError, ValueError, TypeError):
            excluded["invalid_device_metadata"] += 1
    raw_series = defaultdict(dict)
    conflicting = set()
    cutoff = now - timedelta(hours=FRESHNESS_HOURS)
    for observation in data["observations"]:
        try:
            device_id = observation.get("device_id")
            if device_id not in devices or observation.get("pollutant") != "pm25" or observation.get("unit") != "ug/m3":
                continue
            timestamp = _timestamp(observation.get("observed_at"), "observed_at")
            if not cutoff < timestamp <= now:
                continue
            value = _number(observation.get("value"), "value", 0, 5000)
            snapshot = observation.get("device_snapshot")
            if not isinstance(snapshot, dict) or any(snapshot.get(key) != devices[device_id].get(key) for key in ("id", "physical_device_fingerprint", "latitude", "longitude", "environment", "location_accuracy_m", "calibration_reference", "calibration_valid_until")):
                conflicting.add(device_id)
                continue
            if timestamp in raw_series[device_id] and raw_series[device_id][timestamp] != value:
                conflicting.add(device_id)
            raw_series[device_id][timestamp] = value
        except (AttributeError, StoreError, TypeError):
            excluded["invalid_observation"] += 1
    series = {}
    for device_id, samples in raw_series.items():
        ordered = sorted(samples.items())
        if device_id in conflicting:
            excluded["inconsistent_immutable_evidence"] += 1
        elif len(ordered) < 3 or (ordered[-1][0] - ordered[0][0]).total_seconds() < MIN_SAMPLE_SPAN_MINUTES * 60:
            excluded["insufficient_sustained_samples"] += 1
        else:
            series[device_id] = ordered
    excluded["no_fresh_pm25_samples"] += len(set(devices) - set(raw_series))
    cells = defaultdict(list)
    for device_id in series:
        cells[devices[device_id]["_cell"]].append(device_id)
    result["coverage"].update(eligible_devices=len(series), sampled_cells=len(cells), excluded=dict(excluded))
    failure_counts = Counter()
    for cell, identifiers in sorted(cells.items()):
        if len(identifiers) < 2:
            failure_counts["fewer_than_two_devices_in_cell"] += 1
            continue
        anchor = max(series[device_id][-1][0] for device_id in identifiers)
        matching = {device_id: _series_window(series[device_id], anchor) for device_id in identifiers}
        matching = {device_id: stats for device_id, stats in matching.items() if stats}
        elevated_count = sum(stats["median"] > PM25_SCREENING_THRESHOLD for stats in matching.values())
        if elevated_count < 2 or median(stats["median"] for stats in matching.values()) <= PM25_SCREENING_THRESHOLD:
            failure_counts["insufficient_contemporaneous_elevated_devices"] += 1
            continue
        latitude, longitude = _cell_center(cell)
        background = {}
        for device_id, observations in series.items():
            device = devices[device_id]
            if device["_cell"] == cell or _distance(latitude, longitude, device["latitude"], device["longitude"]) > BACKGROUND_DISTANCE_M:
                continue
            stats = _series_window(observations, anchor, background=True)
            if stats:
                background[device_id] = stats
        if len(background) < 2:
            failure_counts["fewer_than_two_contemporaneous_background_devices"] += 1
            continue
        cell_median = median(stats["median"] for stats in matching.values())
        background_median = median(stats["median"] for stats in background.values())
        excess = cell_median - background_median
        if excess < MIN_BACKGROUND_EXCESS or cell_median < MIN_BACKGROUND_RATIO * background_median:
            failure_counts["not_distinct_from_nearby_background"] += 1
            continue
        result["candidates"].append({
            "id": f"INSPECT-250-{cell[0]}-{cell[1]}", "latitude": latitude, "longitude": longitude,
            "cell_size_m": CELL_SIZE_M, "device_count": len(matching), "background_count": len(background),
            "elevated_device_count": elevated_count,
            "device_ids": sorted(matching), "background_device_ids": sorted(background),
            "observed_at": anchor.isoformat(), "cell_median_pm25": round(cell_median, 2),
            "background_median_pm25": round(background_median, 2), "excess_pm25": round(excess, 2),
            "background_ratio": round(cell_median / background_median, 2) if background_median > 0 else None,
            "evidence_summary": f"{elevated_count} of {len(matching)} outdoor devices with distinct operator-attested identifiers show sustained PM2.5 elevation; {len(background)} nearby background devices provide a contemporaneous comparison. Calibration and physical independence are operator attestations. The 250 m cell is an inspection planning unit, not validated measurement resolution.",
            "confidence": "screening_only", "cause": "unverified",
            "recommended_actions": [
                "Review calibration records, installation photos and distinct physical-device identities.",
                "Inspect the area and compare with a reference instrument before any attribution.",
                "Check weather, nearby activity and instrument faults; record the human review outcome.",
            ],
        })
    result["coverage"]["candidate_cells"] = len(result["candidates"])
    result["coverage"]["screening_failures"] = dict(failure_counts)
    if not data["devices"]:
        result["reasons"].append("No authority-registered physical devices are present.")
    if not series:
        result["reasons"].append("No outdoor PM2.5 device meets the location, attestation, freshness and sustained-sample requirements.")
    if not result["candidates"]:
        result["reasons"].append("Evidence does not meet the multi-device and nearby-background screening conditions; no inspection candidate is inferred.")
    result["reasons"].append("Coverage is limited to registered devices with usable observations; no complete Delhi sensor network or source attribution is claimed.")
    return result
