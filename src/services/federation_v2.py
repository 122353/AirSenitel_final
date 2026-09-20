"""Versioned, non-executable model-card interchange for a future governed pilot.

This registry exchanges metadata only. A checksum proves payload integrity, not
partner identity, model validity, deployed capability or federated training.
"""

from datetime import date
import hmac
import json
import re
import uuid

from src.services.case_store_v2 import (
    MAX_NOTES, POLLUTANTS, StoreError, _actor_id, _digest, _json, _now,
    _number, _text, transaction,
)


SCHEMA_VERSION = "1.0"
MAX_METADATA_BYTES = 24000
_REQUIRED = {
    "schema_version", "name", "version", "country_code", "region", "parameter", "unit",
    "horizon_hours", "metrics", "holdout_start", "holdout_end", "license", "privacy_notes",
    "training_data_summary", "model_family",
}
_OPTIONAL = {"artifact_sha256"}


def validate_metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict) or set(metadata) - (_REQUIRED | _OPTIONAL) or _REQUIRED - set(metadata):
        raise StoreError(422, "Metadata must contain the documented schema fields and no executable payloads")
    try:
        if len(_json(metadata).encode("utf-8")) > MAX_METADATA_BYTES:
            raise StoreError(413, "Metadata exceeds the 24 KB limit")
    except (TypeError, ValueError, OverflowError) as exc:
        raise StoreError(422, "Metadata must be finite JSON data") from exc
    if metadata["schema_version"] != SCHEMA_VERSION:
        raise StoreError(422, "Unsupported metadata schema_version")
    result = {"schema_version": SCHEMA_VERSION}
    for key, maximum in {
        "name": 160, "version": 80, "region": 200, "license": 200,
        "privacy_notes": 3000, "training_data_summary": 3000, "model_family": 120,
    }.items():
        result[key] = _text(metadata[key], key, maximum)
    country = metadata["country_code"]
    if not isinstance(country, str) or not re.fullmatch(r"[A-Z]{2}", country):
        raise StoreError(422, "country_code must be a two-letter uppercase country code")
    result["country_code"] = country
    parameter = metadata["parameter"]
    if not isinstance(parameter, str) or parameter not in POLLUTANTS:
        raise StoreError(422, "Unsupported model parameter")
    unit = metadata["unit"]
    if not isinstance(unit, str) or unit not in {"ug/m3", "mg/m3"} or (parameter != "co" and unit != "ug/m3"):
        raise StoreError(422, "Incompatible parameter and unit")
    result.update(parameter=parameter, unit=unit)
    horizon = metadata["horizon_hours"]
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 168:
        raise StoreError(422, "horizon_hours must be an integer between 1 and 168")
    result["horizon_hours"] = horizon
    metrics = metadata["metrics"]
    if not isinstance(metrics, dict) or {"mae", "rmse"} - set(metrics) or set(metrics) - {"mae", "rmse", "r2"}:
        raise StoreError(422, "metrics requires mae and rmse, with optional r2")
    result["metrics"] = {
        "mae": _number(metrics["mae"], "mae", 0, 1000000),
        "rmse": _number(metrics["rmse"], "rmse", 0, 1000000),
    }
    if result["metrics"]["rmse"] + 1e-9 < result["metrics"]["mae"]:
        raise StoreError(422, "RMSE cannot be smaller than MAE on the same holdout")
    if "r2" in metrics:
        result["metrics"]["r2"] = _number(metrics["r2"], "r2", -1000000, 1)
    try:
        start = date.fromisoformat(metadata["holdout_start"])
        end = date.fromisoformat(metadata["holdout_end"])
        if start >= end or end > date.today():
            raise ValueError()
    except (TypeError, ValueError):
        raise StoreError(422, "Holdout dates must be YYYY-MM-DD, end after start and no later than today")
    result.update(holdout_start=start.isoformat(), holdout_end=end.isoformat())
    artifact_hash = metadata.get("artifact_sha256")
    if artifact_hash is not None:
        if not isinstance(artifact_hash, str) or not re.fullmatch("[0-9a-fA-F]{64}", artifact_hash):
            raise StoreError(422, "artifact_sha256 must be a SHA-256 hex digest")
        result["artifact_sha256"] = artifact_hash.lower()
    return result


def _model(row) -> dict:
    return {
        "id": row["id"], "model_id": row["id"], "created_at": row["created_at"],
        "updated_at": row["updated_at"], "status": row["status"], "version": row["version"],
        "metadata": json.loads(row["metadata_json"]),
        "metadata_checksum_sha256": row["metadata_checksum_sha256"],
        "interchange_type": "model_metadata_only",
        "partner_connection": False, "federated_training": False,
    }


_MODEL_COLUMNS = "id,created_at,updated_at,status,version,metadata_json,metadata_checksum_sha256"


def _audit(tx, row, actor_id, event_type, notes):
    tx.execute("""INSERT INTO airv2_model_audit
        (id,model_id,created_at,actor_id,event_type,version,note,metadata_checksum_sha256)
        VALUES(?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), row["id"], _now(), actor_id, event_type,
        row["version"], notes, row["metadata_checksum_sha256"],
    ))


def import_metadata(payload: dict, actor: dict) -> dict:
    actor_id = _actor_id(actor)
    if not isinstance(payload, dict):
        raise StoreError(422, "Metadata must be a JSON object")
    claimed_checksum = None
    if "metadata" in payload:
        if set(payload) - {"schema_version", "metadata", "metadata_checksum_sha256"}:
            raise StoreError(422, "Unsupported interchange envelope fields")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise StoreError(422, "Unsupported interchange schema_version")
        claimed_checksum = payload.get("metadata_checksum_sha256")
        metadata = validate_metadata(payload["metadata"])
    else:
        metadata = validate_metadata(payload)
    metadata_json = _json(metadata)
    checksum = _digest(metadata_json)
    if claimed_checksum is not None and (
        not isinstance(claimed_checksum, str)
        or not re.fullmatch("[0-9a-f]{64}", claimed_checksum)
        or not hmac.compare_digest(claimed_checksum, checksum)
    ):
        raise StoreError(422, "Metadata checksum does not match canonical content")
    timestamp = _now()
    row = {
        "id": "MODEL-" + uuid.uuid4().hex, "created_at": timestamp, "updated_at": timestamp,
        "status": "pending_review", "version": 1, "metadata_json": metadata_json,
        "metadata_checksum_sha256": checksum,
    }
    with transaction(write=True) as tx:
        tx.execute("""INSERT INTO airv2_models
            (id,created_at,updated_at,status,version,imported_by,metadata_json,metadata_checksum_sha256)
            VALUES(?,?,?,?,?,?,?,?)""", (
            row["id"], timestamp, timestamp, "pending_review", 1, actor_id, metadata_json, checksum,
        ))
        _audit(tx, row, actor_id, "imported_to_quarantine", "Awaiting authority review of provenance, evaluation and privacy")
    return _model(row)


def list_models(include_pending: bool = False, limit: int = 100) -> list[dict]:
    if not isinstance(include_pending, bool) or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise StoreError(422, "Invalid model listing options")
    with transaction() as tx:
        condition = "" if include_pending else " WHERE status='approved'"
        rows = tx.execute(f"SELECT {_MODEL_COLUMNS} FROM airv2_models{condition} ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_model(row) for row in rows]


def export_metadata(model_id: str) -> dict:
    with transaction() as tx:
        row = tx.execute(f"SELECT {_MODEL_COLUMNS} FROM airv2_models WHERE id=? AND status='approved'", (model_id,)).fetchone()
    if row is None:
        raise StoreError(404, "Approved model metadata not found")
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": json.loads(row["metadata_json"]),
        "metadata_checksum_sha256": row["metadata_checksum_sha256"],
    }


def review_model(model_id: str, approve: bool, notes: str, expected_version: int, actor: dict) -> dict:
    actor_id = _actor_id(actor)
    if not isinstance(approve, bool):
        raise StoreError(422, "approve must be true or false")
    notes = _text(notes, "notes", MAX_NOTES)
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
        raise StoreError(422, "A positive expected_version is required")
    with transaction(write=True) as tx:
        row = tx.execute(f"SELECT {_MODEL_COLUMNS} FROM airv2_models WHERE id=?" + tx.lock_suffix(), (model_id,)).fetchone()
        if row is None:
            raise StoreError(404, "Model metadata not found")
        if row["version"] != expected_version:
            raise StoreError(409, "This model card changed; reload it before saving")
        updated = dict(row)
        updated.update(status="approved" if approve else "rejected", version=expected_version + 1, updated_at=_now())
        cursor = tx.execute("UPDATE airv2_models SET status=?,version=?,updated_at=? WHERE id=? AND version=?", (updated["status"], updated["version"], updated["updated_at"], model_id, expected_version))
        if cursor.rowcount != 1:
            raise StoreError(409, "This model card changed; reload it before saving")
        _audit(tx, updated, actor_id, updated["status"], notes)
    return _model(updated)


def list_model_audit(model_id: str) -> list[dict]:
    with transaction() as tx:
        exists = tx.execute("SELECT id FROM airv2_models WHERE id=?", (model_id,)).fetchone()
        if exists is None:
            raise StoreError(404, "Model metadata not found")
        rows = tx.execute("SELECT * FROM airv2_model_audit WHERE model_id=? ORDER BY version", (model_id,)).fetchall()
    return [dict(row) for row in rows]
