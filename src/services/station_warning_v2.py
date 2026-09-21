"""Selected-station observed-rise and future-rise screens, never official AQI.

The pre-event baseline excludes the two most recent hourly samples. Detection
requires both of those hours to exceed it. Forecast watches use only eligible
future predictions from the existing chronologically evaluated station model.
These engineering gates have not been calibrated as a national warning system.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from statistics import median

from .forecast_v2 import accepted_series, iso, parse_time
from .monitoring_v2 import normalize_unit

MASS_FLOORS = {"pm25": 10.0, "pm10": 20.0, "no2": 15.0, "so2": 15.0, "o3": 20.0, "co": 200.0}


def screen_station(snapshot: dict, *, now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    # These names are part of monitoring_v2.build_snapshot's public contract.
    # Avoid silently screening a different pollutant or bypassing archive mode.
    pollutant = snapshot.get("selected_pollutant")
    selected = next((s for s in snapshot.get("stations", [])
                     if s.get("id") == snapshot.get("selected_station_id")), {})
    result = {"status": "insufficient_data", "scope": "selected_station_only",
              "station_id": selected.get("id"), "name": selected.get("name"),
              "pollutant": pollutant, "unit": None,
              "observed_at": None, "first_crossing_at": None, "lead_time_hours": None,
              "confidence": "research_unvalidated", "official_aqi": False,
              "operationally_validated": False, "source_attribution": None,
              "message": "Need 12 valid baseline hours and two consecutive recent hours from one fixed sensor."}
    if snapshot.get("requested_mode") == "archive":
        return {**result, "status": "archive", "message": "Archive data cannot issue current warnings."}
    if selected.get("is_mobile") is not False:
        return {**result, "status": "station_not_fixed", "message": "A fixed station must be confirmed before screening."}
    rows = accepted_series((snapshot.get("history") or {}).get("points", []), now)
    if not rows:
        return result
    identities = {(p["station_id"], p["sensor_id"], p["pollutant"], p["unit"]) for p in rows}
    if len(identities) != 1 or rows[-1]["station_id"] != selected.get("id") or rows[-1]["pollutant"] != pollutant:
        return {**result, "message": "Mixed sensor, pollutant or unit series cannot be screened."}
    latest = rows[-1]
    stamp = parse_time(latest["observed_at"])
    result.update(current=latest["value"], observed_at=latest["observed_at"], unit=latest["unit"])
    if now - stamp > timedelta(hours=3):
        return {**result, "status": "stale_input", "message": "Latest quality-accepted hour is over three hours old. Current warnings withheld."}
    unit = normalize_unit(latest["unit"])
    floor = MASS_FLOORS.get(latest["pollutant"])
    if unit not in {"µg/m³", "mg/m³"} or floor is None:
        return {**result, "status": "unsupported_unit", "message": "This screen requires known mass-concentration units; gas volume units are not silently converted."}
    floor = floor / 1000 if unit == "mg/m³" else floor
    lookup = {parse_time(p["observed_at"]): p for p in rows}
    previous = lookup.get(stamp - timedelta(hours=1))
    baseline_rows = [lookup.get(stamp - timedelta(hours=i)) for i in range(2, 14)]
    if previous is None or any(p is None for p in baseline_rows):
        return result
    values = [p["value"] for p in baseline_rows]
    baseline = median(values)
    mad = median(abs(value - baseline) for value in values)
    threshold = baseline + max(3 * 1.4826 * mad, abs(baseline) * .35, floor)
    result.update(baseline=round(baseline, 3), threshold=round(threshold, 3),
                  baseline_hours=12, required_sustained_hours=2)
    if latest["value"] > threshold and previous["value"] > threshold:
        return {**result, "status": "observed_rise", "evidence_class": "ground_station_observation",
                "detected_at": iso(now), "rise_observed_since": previous["observed_at"],
                "message": "Two quality-accepted hours exceed the pre-event baseline screen. This is an observed station rise, not a prediction, local source attribution or certified emergency."}
    forecast = snapshot.get("forecast") or {}
    result.update(model_label=forecast.get("model_label"), trained_model=forecast.get("trained_model", False),
                  forecast_status=forecast.get("status"))
    # Do not reinterpret a model for a different instrument or a stale origin.
    identity_matches = all(forecast.get(k) == latest[k] for k in ("station_id", "sensor_id", "pollutant", "unit"))
    eligible = (forecast.get("status") == "research_forecast" and identity_matches
                and parse_time(forecast.get("origin_at")) == stamp
                and (forecast.get("evaluation") or {}).get("status") == "evaluated")
    future = []
    for point in forecast.get("points", []) if eligible else []:
        at, value = parse_time(point.get("observed_at")), point.get("value")
        if (at and now < at <= now + timedelta(hours=6) and isinstance(value, (int, float))
                and not isinstance(value, bool) and math.isfinite(value) and value >= 0
                and normalize_unit(point.get("unit")) == unit):
            future.append((at, value))
    future.sort()
    crossings = [(at, value) for at, value in future if value > threshold]
    if latest["value"] <= threshold and crossings:
        first_at, _ = crossings[0]
        return {**result, "status": "forecast_watch", "evidence_class": "station_research_forecast",
                "first_crossing_at": iso(first_at), "lead_time_hours": round((first_at-now).total_seconds()/3600, 2),
                "peak_value": max(value for _, value in future),
                "message": "The station research model first crosses the rise screen at this future time. Verify locally; held-out concentration error does not establish event-warning accuracy."}
    return {**result, "status": "no_qualified_signal", "forecast_eligible": bool(future),
            "message": "No sustained observed rise or eligible new forecast crossing in this selected series. This is not an all-clear and does not describe unmonitored areas."}
