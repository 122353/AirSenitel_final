"""Station-specific persistence/ridge research forecasts with chronological QA.

Persistence repeats the last accepted hourly observation. With sufficient data,
a small autoregressive ridge model is actually fitted and compared on an earlier
validation split. Calibration and held-out evaluation remain later, separate
periods; no model promotion or operational validation is implied.
"""
from __future__ import annotations

import math
import hashlib
import json
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

UTC = timezone.utc
FRESH_HOURS = 3
MIN_POINTS = 48
HORIZONS = (1, 3, 4)
RIDGE_MIN_POINTS = 120
LAGS = (1, 2, 3, 6, 24)
RIDGE_PENALTY = 1.0


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("utc") or value.get("local")
    if not isinstance(value, (str, datetime)):
        return None
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(UTC) if result.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _quantile(values: list[float], q: float) -> float:
    """Conservative finite-sample absolute-residual order statistic."""
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((len(ordered) + 1) * q) - 1))
    return ordered[index]


def accepted_series(points: list[dict], now: datetime) -> list[dict]:
    """Reject invalid/flagged/future rows and conflicting duplicate timestamps."""
    grouped: dict[tuple, list[dict]] = {}
    for point in points:
        stamp = parse_time(point.get("observed_at"))
        value = point.get("value")
        if (stamp is None or stamp > now or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
                or point.get("quality", {}).get("status") != "valid"
                or point.get("averaging_period") != "hour"):
            continue
        key = (point.get("station_id"), point.get("sensor_id"), point.get("pollutant"), point.get("unit"), stamp)
        if any(part is None for part in key):
            continue
        grouped.setdefault(key, []).append(point)
    deduplicated = [rows[0] for rows in grouped.values() if len({r["value"] for r in rows}) == 1]
    return sorted(deduplicated, key=lambda p: parse_time(p["observed_at"]))


def _persistence_forecast(points: list[dict], *, now: datetime | None = None, mode: str = "live") -> dict:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    result = {
        "status": "insufficient_data", "model": "persistence", "model_label": "Persistence baseline",
        "trained_model": False, "operational": False, "unit": None, "station_id": None,
        "pollutant": None, "sensor_id": None, "origin_at": None, "points": [],
        "evaluation": {"status": "insufficient_data", "method": "chronological_rolling_origin"},
        "interval_method": "90% absolute-residual interval; calibration precedes held-out evaluation",
        "message": "At least 48 valid hourly observations from one station, sensor, pollutant and unit are required.",
    }
    clean = accepted_series(points, now)
    identities = {(p["station_id"], p["sensor_id"], p["pollutant"], p["unit"]) for p in clean}
    if len(identities) > 1:
        result.update(status="mixed_series", message="Forecast blocked: station, sensor, pollutant or units differ.")
        return result
    if not clean:
        return result
    latest = clean[-1]
    result.update({k: latest[k] for k in ("station_id", "sensor_id", "pollutant", "unit")})
    result["origin_at"] = latest["observed_at"]
    if len(clean) < MIN_POINTS:
        return result
    times = [parse_time(p["observed_at"]) for p in clean]
    # Count temporal completeness, not merely the number of rows supplied.
    expected = int((times[-1] - times[0]).total_seconds() // 3600) + 1
    completeness = min(1.0, len(clean) / max(expected, 1))
    if completeness < 0.75:
        result.update(status="insufficient_coverage", message="Forecast blocked: valid hourly coverage is below 75%.")
        result["evaluation"]["hourly_completeness"] = round(completeness, 4)
        return result
    lookup = dict(zip(times, clean))
    calibration_start = times[len(clean) // 2]
    holdout_start = times[len(clean) * 3 // 4]
    horizon_metrics = []
    forecast_points = []
    for horizon in HORIZONS:
        delta = timedelta(hours=horizon)
        calibration = []
        heldout = []
        for target_at, target in lookup.items():
            origin_at = target_at - delta
            origin = lookup.get(origin_at)
            if origin is None:
                continue
            residual = target["value"] - origin["value"]
            if calibration_start <= target_at < holdout_start:
                calibration.append(abs(residual))
            elif target_at >= holdout_start:
                heldout.append({"origin_at": iso(origin_at), "target_at": iso(target_at),
                                "prediction": origin["value"], "actual": target["value"], "residual": residual})
        if len(calibration) < 8 or len(heldout) < 8:
            continue
        width = _quantile(calibration, 0.9)
        mae = mean(abs(p["residual"]) for p in heldout)
        rmse = math.sqrt(mean(p["residual"] ** 2 for p in heldout))
        coverage = mean(abs(p["residual"]) <= width for p in heldout)
        horizon_metrics.append({
            "horizon_hours": horizon, "mae": round(mae, 4), "rmse": round(rmse, 4),
            "calibration_rows": len(calibration), "test_rows": len(heldout),
            "interval_half_width": round(width, 4), "empirical_coverage": round(coverage, 4),
            "test_predictions": heldout,
        })
        forecast_points.append({"observed_at": iso(times[-1] + delta), "horizon_hours": horizon,
                                "value": latest["value"], "lower": max(0.0, latest["value"] - width),
                                "upper": latest["value"] + width, "unit": latest["unit"]})
    result["evaluation"] = {
        "status": "evaluated" if horizon_metrics else "insufficient_data",
        "method": "chronological_rolling_origin", "model_selection": "Fixed persistence baseline; no tuning on holdout",
        "calibration_start": iso(calibration_start), "calibration_end_exclusive": iso(holdout_start),
        "holdout_start": iso(holdout_start), "holdout_end": iso(times[-1]),
        "hourly_completeness": round(completeness, 4), "input_rows": len(clean), "horizons": horizon_metrics,
    }
    if not forecast_points:
        return result
    if mode != "live" or now - times[-1] > timedelta(hours=FRESH_HOURS):
        result.update(status="stale_input", message="Historical evaluation is available; current forecast withheld because inputs are delayed or older than 3 hours.")
        return result
    # A 3-hour-old origin must never publish a 1-hour forecast as a future point.
    future_points = [p for p in forecast_points if parse_time(p["observed_at"]) > now]
    result.update(status="research_forecast", points=future_points,
                  message="Untrained persistence research baseline. Intervals are empirical and may under-cover changing conditions; not official AQI.")
    return result


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Partial-pivot Gaussian elimination for the bounded 6 x 6 ridge system."""
    size = len(vector)
    augmented = [list(row) + [target] for row, target in zip(matrix, vector)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular_model")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    coefficients = [row[-1] for row in augmented]
    if not all(math.isfinite(value) for value in coefficients):
        raise ValueError("nonfinite_model")
    return coefficients


def _fit_ridge(examples: list[dict]) -> dict:
    """All centering/scaling and coefficients use only the supplied fit rows."""
    centers = [mean(row["features"][column] for row in examples) for column in range(len(LAGS))]
    scales = [math.sqrt(mean((row["features"][column] - centers[column]) ** 2 for row in examples)) or 1.0
              for column in range(len(LAGS))]
    design = [[1.0, *[(value - center) / scale for value, center, scale in zip(row["features"], centers, scales)]]
              for row in examples]
    size = len(LAGS) + 1
    matrix = [[sum(row[i] * row[j] for row in design) + (RIDGE_PENALTY if i == j and i > 0 else 0.0)
               for j in range(size)] for i in range(size)]
    vector = [sum(row[column] * example["actual"] for row, example in zip(design, examples)) for column in range(size)]
    coefficients = _solve(matrix, vector)
    signature_data = [[row["origin_at"], row["target_at"], row["features"], row["actual"]] for row in examples]
    return {"coefficients": coefficients, "centers": centers, "scales": scales,
            "training_rows": len(examples), "training_target_from": examples[0]["target_at"],
            "training_target_to": examples[-1]["target_at"],
            "training_signature": hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()[:20]}


def _ridge_predict(model: dict, features: list[float]) -> float:
    normalized = [(value - center) / scale for value, center, scale in zip(features, model["centers"], model["scales"])]
    prediction = model["coefficients"][0] + sum(coef * value for coef, value in zip(model["coefficients"][1:], normalized))
    if not math.isfinite(prediction):
        raise ValueError("nonfinite_prediction")
    # A fixed nonnegative constraint applies identically in validation,
    # calibration, holdout and deployment; no test-driven clipping threshold.
    return max(0.0, prediction)


def _features(lookup: dict, origin: datetime) -> list[float] | None:
    # Lag 1 is the most recent value available at forecast origin; lag 24 is
    # 23 hours before it. Every input is <= origin and strictly < target.
    rows = [lookup.get(origin - timedelta(hours=lag - 1)) for lag in LAGS]
    return [row["value"] for row in rows] if all(row is not None for row in rows) else None


def _predict_examples(examples: list[dict], model: dict | None) -> list[dict]:
    rows = []
    for example in examples:
        prediction = _ridge_predict(model, example["features"]) if model else example["persistence"]
        rows.append({"origin_at": example["origin_at"], "target_at": example["target_at"],
                     "prediction": prediction, "actual": example["actual"],
                     "residual": example["actual"] - prediction})
    return rows


def _metrics(rows: list[dict], width: float) -> dict:
    return {"mae": round(mean(abs(row["residual"]) for row in rows), 4),
            "rmse": round(math.sqrt(mean(row["residual"] ** 2 for row in rows)), 4),
            "test_rows": len(rows), "interval_half_width": round(width, 4),
            "empirical_coverage": round(mean(abs(row["residual"]) <= width for row in rows), 4)}


def _ridge_comparison(clean: list[dict], result: dict, now: datetime, mode: str) -> dict:
    times = [parse_time(point["observed_at"]) for point in clean]
    lookup = dict(zip(times, clean))
    train_end = times[len(clean) * 50 // 100]
    calibration_start = times[len(clean) * 65 // 100]
    holdout_start = times[len(clean) * 80 // 100]
    horizon_metrics, forecast_points, selected_models = [], [], []
    current_features = _features(lookup, times[-1])
    for horizon in HORIZONS:
        examples = []
        for target_at, target in lookup.items():
            origin = target_at - timedelta(hours=horizon)
            features = _features(lookup, origin)
            if features is not None:
                examples.append({"origin_at": iso(origin), "target_at": iso(target_at),
                    "features": features, "actual": target["value"], "persistence": lookup[origin]["value"]})
        train = [row for row in examples if row["target_at"] < iso(train_end)]
        validation_pool = [row for row in examples if iso(train_end) <= row["target_at"] < iso(calibration_start)]
        calibration_pool = [row for row in examples if iso(calibration_start) <= row["target_at"] < iso(holdout_start)]
        test = [row for row in examples if row["target_at"] >= iso(holdout_start)]
        # Multi-hour targets immediately after a split can have origins before
        # the final fitted target. Purge them: all observations used in a fit
        # must already be known at every evaluated forecast origin.
        validation = [row for row in validation_pool if train and row["origin_at"] >= train[-1]["target_at"]]
        refit_examples = train + validation_pool
        calibration = [row for row in calibration_pool if refit_examples and row["origin_at"] >= refit_examples[-1]["target_at"]]
        test = [row for row in test if refit_examples and row["origin_at"] >= refit_examples[-1]["target_at"]]
        if len(train) < 24 or min(len(validation), len(calibration), len(test)) < 8:
            result["evaluation"]["trained_candidate"] = {
                "status": "insufficient_lag_coverage", "minimum_input_rows": RIDGE_MIN_POINTS,
                "horizon_hours": horizon, "training_rows": len(train), "validation_rows": len(validation),
                "calibration_rows": len(calibration), "holdout_rows": len(test),
                "minimum_training_rows": 24, "minimum_rows_per_evaluation_split": 8,
                "message": "Ridge comparison declined: exact hourly lag/target pairs after forecast-origin purging are insufficient in one or more chronological splits."}
            return result
        initial_fit = _fit_ridge(train)
        validation_predictions = {"persistence": _predict_examples(validation, None),
                                  "ridge_autoregression": _predict_examples(validation, initial_fit)}
        validation_mae = {name: mean(abs(row["residual"]) for row in rows) for name, rows in validation_predictions.items()}
        selected = "ridge_autoregression" if validation_mae["ridge_autoregression"] < validation_mae["persistence"] else "persistence"
        # Selection is frozen first; only earlier train+validation targets are
        # used for refitting. Calibration and holdout never enter coefficients.
        fitted = _fit_ridge(refit_examples)
        candidate_metrics = []
        chosen_rows, chosen_width = [], None
        for name, fitted_model in (("persistence", None), ("ridge_autoregression", fitted)):
            calibration_predictions = _predict_examples(calibration, fitted_model)
            width = _quantile([abs(row["residual"]) for row in calibration_predictions], 0.9)
            test_predictions = _predict_examples(test, fitted_model)
            candidate_metrics.append({"model": name, "selected": name == selected,
                "validation_mae": round(validation_mae[name], 4), "validation_rows": len(validation),
                "calibration_rows": len(calibration), **_metrics(test_predictions, width)})
            if name == selected:
                chosen_rows, chosen_width = test_predictions, width
        selected_models.append(selected)
        horizon_metrics.append({"horizon_hours": horizon, "selected_model": selected,
            "calibration_rows": len(calibration), **_metrics(chosen_rows, chosen_width),
            "test_predictions": chosen_rows, "candidates": candidate_metrics,
            "fit": {key: fitted[key] for key in ("training_rows", "training_target_from", "training_target_to", "training_signature")},
            "initial_training_rows": len(train), "initial_training_target_to": initial_fit["training_target_to"],
            "validation_origin_from": validation[0]["origin_at"], "calibration_origin_from": calibration[0]["origin_at"],
            "validation_purged_rows": len(validation_pool) - len(validation),
            "calibration_purged_rows": len(calibration_pool) - len(calibration),
            "selection_reason": "Lowest MAE on earlier validation period; persistence wins ties"})
        if selected == "ridge_autoregression" and current_features is None:
            horizon_metrics[-1]["current_forecast_status"] = "required_current_lags_missing"
            continue
        prediction = _ridge_predict(fitted, current_features) if selected == "ridge_autoregression" else clean[-1]["value"]
        forecast_points.append({"observed_at": iso(times[-1] + timedelta(hours=horizon)),
            "horizon_hours": horizon, "value": prediction, "lower": max(0.0, prediction - chosen_width),
            "upper": prediction + chosen_width, "unit": clean[-1]["unit"], "model": selected})
    trained_selected = "ridge_autoregression" in selected_models
    model = selected_models[0] if len(set(selected_models)) == 1 else "horizon_selected"
    labels = {"persistence": "Persistence baseline", "ridge_autoregression": "Trained autoregressive ridge",
              "horizon_selected": "Ridge / persistence selected by horizon"}
    result.update(model=model, model_label=labels[model], trained_model=trained_selected, points=[])
    completeness = result["evaluation"].get("hourly_completeness")
    result["evaluation"] = {"status": "evaluated", "method": "chronological_rolling_origin",
        "model_selection": "Fixed ridge penalty; train first 50%, select on next 15%; refit train+validation before calibration",
        "training_start": iso(times[0]), "training_end_exclusive": iso(train_end),
        "validation_start": iso(train_end), "validation_end_exclusive": iso(calibration_start),
        "calibration_start": iso(calibration_start), "calibration_end_exclusive": iso(holdout_start),
        "holdout_start": iso(holdout_start), "holdout_end": iso(times[-1]),
        "hourly_completeness": completeness, "input_rows": len(clean), "horizons": horizon_metrics,
        "trained_candidate": {"status": "fitted_and_compared", "model": "ridge_autoregression",
            "trained": True, "selected_for_any_horizon": trained_selected, "lags": list(LAGS),
            "lag_definition": "Lag 1 is observation at origin; lag k is k-1 hours before origin",
            "ridge_penalty": RIDGE_PENALTY, "minimum_input_rows": RIDGE_MIN_POINTS,
            "fit_scope": "Same station, sensor, pollutant and unit; no artifact loading or persistence"}}
    if mode != "live" or now - times[-1] > timedelta(hours=FRESH_HOURS):
        result.update(status="stale_input", message="Trained-candidate historical evaluation is available; current predictions withheld because inputs are delayed or stale.")
    else:
        future = [point for point in forecast_points if parse_time(point["observed_at"]) > now]
        result.update(status="research_forecast" if future else "missing_current_lags", points=future,
            message="Research forecast selected by earlier validation MAE. Ridge was fitted and compared with persistence; empirical intervals and holdout metrics do not establish operational validation.")
    return result


def build_forecast(points: list[dict], *, now: datetime | None = None, mode: str = "live") -> dict:
    """Train/compare a bounded ridge candidate when enough valid history exists."""
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    result = _persistence_forecast(points, now=timestamp, mode=mode)
    clean = accepted_series(points, timestamp)
    if result["status"] in {"mixed_series", "insufficient_coverage"}:
        return result
    if len(clean) < RIDGE_MIN_POINTS:
        result["evaluation"]["trained_candidate"] = {"status": "insufficient_data",
            "minimum_input_rows": RIDGE_MIN_POINTS, "valid_input_rows": len(clean),
            "message": "At least 120 valid hourly observations are required to train and chronologically compare ridge with persistence."}
        return result
    try:
        return _ridge_comparison(clean, result, timestamp, mode)
    except (ValueError, OverflowError, ZeroDivisionError):
        # Do not invent a trained result when the bounded linear solve fails.
        result["evaluation"]["trained_candidate"] = {"status": "fit_unavailable", "message": "Numerical fitting was unavailable; evaluated persistence remains the baseline."}
        return result
