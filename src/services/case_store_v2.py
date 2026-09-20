"""Durable private reports, withdrawal and versioned authority review.

Production requires PostgreSQL; SQLite is an explicit local development option.
No functions initialize or migrate a store implicitly. Routes must authenticate
before calling the private read/write functions in this module.
"""

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import uuid


MAX_PHOTO_BYTES = 3 * 1024 * 1024
MAX_DESCRIPTION = 4000
MAX_NOTES = 2000
POLLUTANTS = {"pm25", "pm10", "no2", "so2", "o3", "co"}
REVIEW_STATUSES = {"under_review", "needs_verification", "closed"}


class StoreError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _actor_id(actor: dict) -> str:
    user_id = actor.get("user_id") if isinstance(actor, dict) else None
    if not isinstance(user_id, str) or not user_id.startswith("user_") or len(user_id) > 200:
        raise StoreError(403, "A verified identity is required")
    return user_id


def _configuration() -> tuple[str, str]:
    backend = os.environ.get("AIRSENTINEL_STORE", "postgres").strip().lower()
    if backend == "sqlite":
        local = os.environ.get("AIRSENTINEL_ENV") == "local" and not any(
            os.environ.get(name) for name in ("VERCEL", "K_SERVICE", "AWS_LAMBDA_FUNCTION_NAME")
        )
        path = os.environ.get("AIRSENTINEL_SQLITE_PATH", "")
        if not local or not path or path == ":memory:":
            raise StoreError(503, "SQLite requires an explicit local environment and durable file path")
        return backend, str(Path(path).resolve())
    if backend != "postgres":
        raise StoreError(503, "The durable store is not configured")
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn.startswith(("postgresql://", "postgres://")):
        raise StoreError(503, "The durable store is not configured")
    return backend, dsn


class _Transaction:
    def __init__(self, connection, backend):
        self.connection = connection
        self.backend = backend

    def execute(self, query: str, values=()):
        # Statements here are fixed application SQL; only values are supplied by
        # callers. This translation never interpolates user data.
        return self.connection.execute(query.replace("?", "%s") if self.backend == "postgres" else query, values)

    def lock_suffix(self):
        return " FOR UPDATE" if self.backend == "postgres" else ""


@contextmanager
def transaction(*, write=False, initialize=False):
    backend, target = _configuration()
    connection = None
    try:
        if backend == "sqlite":
            if not initialize and not Path(target).is_file():
                raise StoreError(503, "The durable store has not been initialized")
            if initialize:
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(target, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        else:
            import psycopg
            from psycopg.rows import dict_row
            connection = psycopg.connect(target, row_factory=dict_row, connect_timeout=8, sslmode="require")
            connection.execute("SET LOCAL statement_timeout = '10000ms'")
        yield _Transaction(connection, backend)
        connection.commit()
    except StoreError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        raise StoreError(503, "The durable store is temporarily unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


def initialize_store() -> None:
    """Explicit additive v2 schema initialization; never modifies legacy tables."""
    with transaction(write=True, initialize=True) as tx:
        binary = "BYTEA" if tx.backend == "postgres" else "BLOB"
        tx.execute(f"""CREATE TABLE IF NOT EXISTS airv2_reports (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            kind TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL,
            reporter_id TEXT, receipt_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
            photo {binary}, photo_content_type TEXT, photo_sha256 TEXT,
            withdrawn_at TEXT
        )""")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_audit (
            id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES airv2_reports(id),
            created_at TEXT NOT NULL, actor_id TEXT NOT NULL, event_type TEXT NOT NULL,
            from_status TEXT, to_status TEXT NOT NULL, version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL, note_sha256 TEXT
        )""")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_case_notes (
            audit_id TEXT PRIMARY KEY REFERENCES airv2_audit(id), note TEXT NOT NULL
        )""")
        tx.execute("CREATE INDEX IF NOT EXISTS airv2_audit_report ON airv2_audit(report_id, version)")
        tx.execute("CREATE INDEX IF NOT EXISTS airv2_reports_created ON airv2_reports(created_at)")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_rate_limits (
            actor_hash TEXT PRIMARY KEY, window_start TEXT NOT NULL, used INTEGER NOT NULL
        )""")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_models (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            status TEXT NOT NULL, version INTEGER NOT NULL, imported_by TEXT NOT NULL,
            metadata_json TEXT NOT NULL, metadata_checksum_sha256 TEXT NOT NULL
        )""")
        tx.execute("""CREATE TABLE IF NOT EXISTS airv2_model_audit (
            id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES airv2_models(id),
            created_at TEXT NOT NULL, actor_id TEXT NOT NULL, event_type TEXT NOT NULL,
            version INTEGER NOT NULL, note TEXT NOT NULL, metadata_checksum_sha256 TEXT NOT NULL
        )""")


def store_health() -> dict:
    """No paths, DSNs, identities or counts in the public health response."""
    try:
        with transaction() as tx:
            tx.execute("SELECT id FROM airv2_reports LIMIT 1").fetchone()
        return {"available": True, "durable": True}
    except StoreError:
        return {"available": False, "durable": False}


def _number(value, field, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise StoreError(422, f"{field} is outside the supported range")
    return float(value)


def _text(value, field, maximum, *, required=True):
    if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
        raise StoreError(422, f"{field} must contain 1 to {maximum} characters")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
        raise StoreError(422, f"{field} contains unsupported control characters")
    return value.strip()


def _validated_payload(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("consent_to_store") is not True:
        raise StoreError(422, "Explicit consent to store and review the report is required")
    kind = payload.get("kind", "citizen_report")
    if not isinstance(kind, str) or kind not in {"citizen_report", "photo_report", "indoor_sensor", "sensor_reading"}:
        raise StoreError(422, "Unsupported report kind")
    result = {
        "description": _text(payload.get("description", ""), "description", MAX_DESCRIPTION),
        "consent_to_store": True,
        "consent_version": "2026-09-20",
        "kind": kind,
        "evidence_tier": "unverified_citizen_evidence",
        "human_review_required": True,
        "location_precision": "citizen_supplied_private",
    }
    latitude, longitude = payload.get("latitude"), payload.get("longitude")
    if (latitude is None) != (longitude is None):
        raise StoreError(422, "Latitude and longitude must be supplied together")
    result["latitude"] = None if latitude is None else _number(latitude, "latitude", -90, 90)
    result["longitude"] = None if longitude is None else _number(longitude, "longitude", -180, 180)
    if payload.get("locality_id") is not None:
        result["locality_id"] = _text(payload["locality_id"], "locality_id", 100)
    reading = payload.get("reading")
    if reading is not None:
        if not isinstance(reading, dict) or set(reading) - {"pollutant", "value", "unit", "environment", "observed_at", "device_type"}:
            raise StoreError(422, "Reading must contain only supported measurement fields")
        pollutant = reading.get("pollutant")
        if not isinstance(pollutant, str) or pollutant not in POLLUTANTS:
            raise StoreError(422, "Unsupported pollutant")
        unit = reading.get("unit")
        if not isinstance(unit, str) or unit not in {"ug/m3", "mg/m3"} or (pollutant != "co" and unit != "ug/m3"):
            raise StoreError(422, "Use ug/m3 for this pollutant, or mg/m3 for CO")
        environment = reading.get("environment")
        if not isinstance(environment, str) or environment not in {"indoor", "outdoor"}:
            raise StoreError(422, "Reading environment must be indoor or outdoor")
        if reading.get("device_type") != "citizen_device":
            raise StoreError(422, "Citizen evidence requires device_type citizen_device")
        try:
            observed = datetime.fromisoformat(reading.get("observed_at", "").replace("Z", "+00:00"))
            if observed.tzinfo is None or observed > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise StoreError(422, "observed_at must be a valid timestamp with timezone and cannot be in the future")
        result["reading"] = {
            "pollutant": pollutant,
            "value": _number(reading.get("value"), "value", 0, 100 if unit == "mg/m3" else 100000),
            "unit": unit,
            "environment": environment,
            "observed_at": observed.astimezone(timezone.utc).isoformat(),
            "device_type": "citizen_device",
            "verification_status": "unverified",
            "use_for_official_aqi": False,
        }
    elif kind in {"indoor_sensor", "sensor_reading"}:
        raise StoreError(422, "A sensor report requires a reading")
    if kind == "indoor_sensor" and result.get("reading", {}).get("environment") != "indoor":
        raise StoreError(422, "Indoor sensor reports must identify an indoor environment")
    return result


def _consume_report_limit(tx, reporter_id: str) -> None:
    actor_hash = _digest(reporter_id)
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=1)).isoformat()
    tx.execute("INSERT INTO airv2_rate_limits(actor_hash,window_start,used) VALUES(?,?,0) ON CONFLICT(actor_hash) DO NOTHING", (actor_hash, now.isoformat()))
    row = tx.execute("SELECT window_start,used FROM airv2_rate_limits WHERE actor_hash=?" + tx.lock_suffix(), (actor_hash,)).fetchone()
    if row["window_start"] <= cutoff:
        tx.execute("UPDATE airv2_rate_limits SET window_start=?,used=1 WHERE actor_hash=?", (now.isoformat(), actor_hash))
    elif row["used"] >= 10:
        raise StoreError(429, "Report limit reached; try again after one hour")
    else:
        tx.execute("UPDATE airv2_rate_limits SET used=used+1 WHERE actor_hash=?", (actor_hash,))


def _report(row) -> dict:
    payload = json.loads(row["payload_json"])
    return {
        **payload,
        "id": row["id"], "report_id": row["id"], "created_at": row["created_at"],
        "updated_at": row["updated_at"], "kind": row["kind"], "status": row["status"],
        "version": row["version"], "has_photo": bool(row["photo_sha256"]),
        "photo_sha256": row["photo_sha256"], "withdrawn_at": row["withdrawn_at"],
    }


_REPORT_COLUMNS = "id,created_at,updated_at,kind,status,version,payload_json,photo_sha256,withdrawn_at"


def _audit(tx, row, actor_id, event_type, old_status=None, notes=None):
    audit_id = str(uuid.uuid4())
    snapshot = {
        "report_id": row["id"], "kind": row["kind"], "status": row["status"],
        "version": row["version"], "payload_sha256": _digest(row["payload_json"]),
        "photo_sha256": row["photo_sha256"],
    }
    tx.execute("""INSERT INTO airv2_audit
        (id,report_id,created_at,actor_id,event_type,from_status,to_status,version,snapshot_json,note_sha256)
        VALUES(?,?,?,?,?,?,?,?,?,?)""", (
        audit_id, row["id"], _now(), actor_id, event_type, old_status, row["status"],
        row["version"], _json(snapshot), _digest(notes) if notes else None,
    ))
    if notes:
        tx.execute("INSERT INTO airv2_case_notes(audit_id,note) VALUES(?,?)", (audit_id, notes))


def create_report(payload: dict, actor: dict, photo_bytes: bytes | None = None, photo_content_type: str | None = None) -> dict:
    reporter_id = _actor_id(actor)
    validated = _validated_payload(payload)
    if photo_bytes is not None:
        if not isinstance(photo_bytes, bytes) or not 0 < len(photo_bytes) <= MAX_PHOTO_BYTES:
            raise StoreError(413, "The sanitized photo exceeds the 3 MB limit")
        if photo_content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise StoreError(422, "Only sanitized JPEG, PNG and WebP photos are accepted")
    elif validated["kind"] == "photo_report":
        raise StoreError(422, "Photo reports require a photo")
    receipt = secrets.token_urlsafe(32)
    timestamp = _now()
    record_id = "REP-" + uuid.uuid4().hex
    photo_hash = _digest(photo_bytes) if photo_bytes is not None else None
    row = {
        "id": record_id, "created_at": timestamp, "updated_at": timestamp,
        "kind": validated["kind"], "status": "pending_review", "version": 1,
        "payload_json": _json(validated), "photo_sha256": photo_hash, "withdrawn_at": None,
    }
    with transaction(write=True) as tx:
        _consume_report_limit(tx, reporter_id)
        tx.execute("""INSERT INTO airv2_reports
            (id,created_at,updated_at,kind,status,version,reporter_id,receipt_hash,payload_json,photo,photo_content_type,photo_sha256)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
            record_id, timestamp, timestamp, validated["kind"], "pending_review", 1,
            reporter_id, _digest(receipt), row["payload_json"], photo_bytes, photo_content_type, photo_hash,
        ))
        # Citizen identity lives only in the retractable report row. Immutable
        # events deliberately do not contain resident account IDs or raw text.
        _audit(tx, row, "citizen", "submitted")
    return {"report": _report(row), "receipt": receipt}


def list_reports(limit: int = 100) -> list[dict]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise StoreError(422, "Limit must be between 1 and 200")
    with transaction() as tx:
        rows = tx.execute(f"SELECT {_REPORT_COLUMNS} FROM airv2_reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_report(row) for row in rows]


def get_report(report_id: str) -> dict:
    with transaction() as tx:
        row = tx.execute(f"SELECT {_REPORT_COLUMNS} FROM airv2_reports WHERE id=?", (report_id,)).fetchone()
    if row is None:
        raise StoreError(404, "Report not found")
    return _report(row)


def get_photo(report_id: str) -> tuple[bytes, str]:
    with transaction() as tx:
        row = tx.execute("SELECT photo,photo_content_type FROM airv2_reports WHERE id=? AND withdrawn_at IS NULL", (report_id,)).fetchone()
    if row is None or row["photo"] is None:
        raise StoreError(404, "Photo not found")
    return bytes(row["photo"]), row["photo_content_type"]


def transition_report(report_id: str, status: str, notes: str, expected_version: int, actor: dict) -> dict:
    actor_id = _actor_id(actor)
    if not isinstance(status, str) or status not in REVIEW_STATUSES:
        raise StoreError(422, "Unsupported review status")
    notes = _text(notes, "notes", MAX_NOTES)
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
        raise StoreError(422, "A positive expected_version is required")
    with transaction(write=True) as tx:
        row = tx.execute(f"SELECT {_REPORT_COLUMNS} FROM airv2_reports WHERE id=?" + tx.lock_suffix(), (report_id,)).fetchone()
        if row is None:
            raise StoreError(404, "Report not found")
        if row["withdrawn_at"]:
            raise StoreError(409, "Withdrawn evidence cannot be reviewed")
        if row["version"] != expected_version:
            raise StoreError(409, "This case changed; reload it before saving")
        updated = dict(row)
        updated.update(status=status, version=expected_version + 1, updated_at=_now())
        cursor = tx.execute("UPDATE airv2_reports SET status=?,version=?,updated_at=? WHERE id=? AND version=? AND withdrawn_at IS NULL", (status, updated["version"], updated["updated_at"], report_id, expected_version))
        if cursor.rowcount != 1:
            raise StoreError(409, "This case changed; reload it before saving")
        _audit(tx, updated, actor_id, "authority_review", row["status"], notes)
    return _report(updated)


def withdraw_report(report_id: str, receipt: str) -> dict:
    if not isinstance(receipt, str) or not 40 <= len(receipt) <= 100:
        raise StoreError(404, "Report or withdrawal receipt not found")
    with transaction(write=True) as tx:
        row = tx.execute(f"SELECT {_REPORT_COLUMNS},receipt_hash FROM airv2_reports WHERE id=?" + tx.lock_suffix(), (report_id,)).fetchone()
        if row is None or not hmac.compare_digest(row["receipt_hash"], _digest(receipt)):
            raise StoreError(404, "Report or withdrawal receipt not found")
        if row["withdrawn_at"]:
            return {"id": report_id, "status": "withdrawn", "version": row["version"]}
        timestamp = _now()
        tombstone = _json({"redacted": True, "reason": "citizen_withdrawal"})
        tx.execute("""UPDATE airv2_reports SET status='withdrawn',version=version+1,updated_at=?,
            reporter_id=NULL,payload_json=?,photo=NULL,photo_content_type=NULL,photo_sha256=NULL,withdrawn_at=?
            WHERE id=?""", (timestamp, tombstone, timestamp, report_id))
        tx.execute("DELETE FROM airv2_case_notes WHERE audit_id IN (SELECT id FROM airv2_audit WHERE report_id=?)", (report_id,))
        updated = dict(row)
        updated.update(status="withdrawn", version=row["version"] + 1, updated_at=timestamp, withdrawn_at=timestamp, payload_json=tombstone, photo_sha256=None)
        _audit(tx, updated, "receipt_holder", "withdrawn", row["status"])
    return {"id": report_id, "status": "withdrawn", "version": updated["version"]}


def list_audit(report_id: str) -> list[dict]:
    with transaction() as tx:
        exists = tx.execute("SELECT id FROM airv2_reports WHERE id=?", (report_id,)).fetchone()
        if exists is None:
            raise StoreError(404, "Report not found")
        rows = tx.execute("""SELECT a.*,n.note FROM airv2_audit a
            LEFT JOIN airv2_case_notes n ON n.audit_id=a.id
            WHERE a.report_id=? ORDER BY a.version,a.created_at""", (report_id,)).fetchall()
    return [{**{key: row[key] for key in row.keys() if key != "snapshot_json"}, "snapshot": json.loads(row["snapshot_json"])} for row in rows]
