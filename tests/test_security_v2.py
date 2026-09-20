"""Security regression tests; no provider credentials or external services used."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.services import case_store_v2 as store
from src.services import federation_v2 as federation


ACTOR = {"user_id": "user_test_citizen", "email": "citizen@example.test"}
AUTHORITY = {"user_id": "user_test_authority", "email": "authority@example.test"}
ORIGIN = "https://pilot.example.test"


def report_payload(**overrides):
    return {
        "description": "Citizen observed smoke near a public road.", "kind": "citizen_report",
        "latitude": 28.61, "longitude": 77.22, "consent_to_store": True, **overrides,
    }


def metadata_payload(**overrides):
    return {
        "schema_version": "1.0", "name": "Test model card", "version": "1.2.0",
        "country_code": "IN", "region": "Test region", "parameter": "pm25", "unit": "ug/m3",
        "horizon_hours": 3, "metrics": {"mae": 8.2, "rmse": 11.4, "r2": 0.5},
        "holdout_start": "2025-01-01", "holdout_end": "2025-02-01",
        "license": "CC-BY-4.0", "privacy_notes": "Only aggregate public station data.",
        "training_data_summary": "Test fixture, not a production model.", "model_family": "HistGradientBoosting",
        **overrides,
    }


class LocalStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "test.sqlite3")
        self.env = patch.dict(os.environ, {
            "AIRSENTINEL_ENV": "local", "AIRSENTINEL_STORE": "sqlite", "AIRSENTINEL_SQLITE_PATH": self.path,
            "VERCEL": "", "K_SERVICE": "", "AWS_LAMBDA_FUNCTION_NAME": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        store.initialize_store()

    def assert_store_error(self, status, fn, *args, **kwargs):
        with self.assertRaises(store.StoreError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(status, caught.exception.status_code)

    def test_fail_closed_without_postgres_and_no_sqlite_fallback(self):
        with patch.dict(os.environ, {"AIRSENTINEL_ENV": "production", "AIRSENTINEL_STORE": "postgres", "DATABASE_URL": ""}):
            self.assert_store_error(503, store.list_reports)
        with patch.dict(os.environ, {"AIRSENTINEL_ENV": "production"}):
            self.assert_store_error(503, store.list_reports)
        with patch.dict(os.environ, {"VERCEL": "1"}):
            self.assert_store_error(503, store.list_reports)
        with patch.dict(os.environ, {"AIRSENTINEL_SQLITE_PATH": str(Path(self.tmp.name) / "missing.sqlite3")}):
            self.assert_store_error(503, store.list_reports)
            self.assertFalse((Path(self.tmp.name) / "missing.sqlite3").exists())

    def test_report_is_durable_private_and_receipt_is_not_stored(self):
        created = store.create_report(report_payload(actor_id="forged_actor"), ACTOR)
        record, receipt = created["report"], created["receipt"]
        self.assertEqual("pending_review", record["status"])
        self.assertGreaterEqual(len(receipt), 40)
        self.assertNotIn("reporter_id", record)
        self.assertNotIn("actor_id", record)
        self.assertNotIn("receipt", store.get_report(record["id"]))
        self.assertEqual(record["id"], store.list_reports()[0]["id"])
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute("SELECT reporter_id,receipt_hash FROM airv2_reports").fetchone()
        self.assertEqual(ACTOR["user_id"], row[0])
        self.assertNotEqual(receipt, row[1])
        self.assertNotIn(receipt, Path(self.path).read_bytes().decode("latin1"))

    def test_consent_size_location_and_sensor_validation(self):
        for payload in [report_payload(consent_to_store=False), report_payload(latitude=float("nan")), report_payload(longitude=181), report_payload(description="x" * 4001), report_payload(latitude=None)]:
            self.assert_store_error(422, store.create_report, payload, ACTOR)
        self.assert_store_error(413, store.create_report, report_payload(), ACTOR, b"x" * (store.MAX_PHOTO_BYTES + 1), "image/jpeg")
        self.assert_store_error(422, store.create_report, report_payload(kind="photo_report"), ACTOR)
        self.assert_store_error(403, store.create_report, report_payload(), {"user_id": "forged"})
        for pollutant in sorted(store.POLLUTANTS):
            reading = {
                "pollutant": pollutant, "value": 12.5, "unit": "mg/m3" if pollutant == "co" else "ug/m3",
                "environment": "indoor", "observed_at": datetime.now(timezone.utc).isoformat(), "device_type": "citizen_device",
            }
            record = store.create_report(report_payload(kind="indoor_sensor", reading=reading), ACTOR)["report"]
            self.assertFalse(record["reading"]["use_for_official_aqi"])
            self.assertEqual("unverified", record["reading"]["verification_status"])
        self.assert_store_error(422, store.create_report, report_payload(kind="sensor_reading", reading={**reading, "raw_device_id": "secret"}), ACTOR)

    def test_concurrent_case_edits_allow_exactly_one_version(self):
        record = store.create_report(report_payload(), ACTOR)["report"]
        def review(status):
            try:
                return store.transition_report(record["id"], status, "Independent authority review.", 1, AUTHORITY)["version"]
            except store.StoreError as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(review, ["under_review", "needs_verification"]))
        self.assertCountEqual([2, 409], results)
        history = store.list_audit(record["id"])
        self.assertEqual(2, len(history))
        self.assertEqual(AUTHORITY["user_id"], history[-1]["actor_id"])
        self.assertEqual(1, history[0]["snapshot"]["version"])
        self.assert_store_error(422, store.transition_report, record["id"], "closed", " ", 2, AUTHORITY)
        self.assert_store_error(422, store.transition_report, record["id"], "enforced", "Not a valid review status", 2, AUTHORITY)

    def test_withdrawal_removes_personal_data_photo_and_notes_atomically(self):
        created = store.create_report(report_payload(kind="photo_report"), ACTOR, b"sanitized-test-jpeg", "image/jpeg")
        record_id = created["report"]["id"]
        self.assertEqual(b"sanitized-test-jpeg", store.get_photo(record_id)[0])
        store.transition_report(record_id, "under_review", "Resident details to remove on withdrawal", 1, AUTHORITY)
        self.assert_store_error(404, store.withdraw_report, record_id, secrets.token_urlsafe(32))
        self.assertEqual("withdrawn", store.withdraw_report(record_id, created["receipt"])["status"])
        self.assertEqual(3, store.withdraw_report(record_id, created["receipt"])["version"])
        record = store.get_report(record_id)
        for private_field in ("description", "latitude", "longitude", "reading", "reporter_id"):
            self.assertNotIn(private_field, record)
        self.assertFalse(record["has_photo"])
        self.assert_store_error(404, store.get_photo, record_id)
        self.assert_store_error(409, store.transition_report, record_id, "closed", "Cannot review withdrawn evidence", 3, AUTHORITY)
        history = store.list_audit(record_id)
        self.assertEqual([1, 2, 3], [item["version"] for item in history])
        self.assertTrue(all(item["note"] is None for item in history))
        self.assertNotIn(ACTOR["user_id"], json.dumps(history))
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute("SELECT reporter_id,photo,payload_json FROM airv2_reports WHERE id=?", (record_id,)).fetchone()
        self.assertIsNone(row[0])
        self.assertIsNone(row[1])
        self.assertEqual({"redacted": True, "reason": "citizen_withdrawal"}, json.loads(row[2]))

    def test_rate_limit_is_durable_and_withdrawal_cannot_reset_it(self):
        for _ in range(10):
            created = store.create_report(report_payload(), ACTOR)
            store.withdraw_report(created["report"]["id"], created["receipt"])
        self.assert_store_error(429, store.create_report, report_payload(), ACTOR)
        # A different authenticated person has a separate quota.
        store.create_report(report_payload(), {"user_id": "user_other"})

    def test_concurrent_rate_limit_is_atomic(self):
        def submit(index):
            try:
                store.create_report(report_payload(description=f"Concurrent report {index}"), ACTOR)
                return 201
            except store.StoreError as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(submit, range(12)))
        self.assertEqual(10, results.count(201))
        self.assertEqual(2, results.count(429))

    def test_transaction_rolls_back_on_audit_failure(self):
        with patch.object(store, "_audit", side_effect=RuntimeError("simulated failure")):
            self.assert_store_error(503, store.create_report, report_payload(), ACTOR)
        self.assertEqual([], store.list_reports())
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM airv2_rate_limits").fetchone()[0])

    def test_metadata_quarantine_approval_checksum_and_safe_export(self):
        imported = federation.import_metadata(metadata_payload(), AUTHORITY)
        self.assertEqual("pending_review", imported["status"])
        self.assertEqual([], federation.list_models())
        self.assertEqual(1, len(federation.list_models(include_pending=True)))
        self.assert_store_error(404, federation.export_metadata, imported["id"])
        approved = federation.review_model(imported["id"], True, "Reviewed aggregate-only fields and documented holdout.", 1, AUTHORITY)
        self.assertEqual("approved", approved["status"])
        self.assert_store_error(409, federation.review_model, imported["id"], False, "Stale review", 1, AUTHORITY)
        exported = federation.export_metadata(imported["id"])
        self.assertEqual({"schema_version", "metadata", "metadata_checksum_sha256"}, set(exported))
        self.assertNotIn(AUTHORITY["user_id"], json.dumps(exported))
        reimported = federation.import_metadata(exported, AUTHORITY)
        self.assertEqual("pending_review", reimported["status"])
        self.assertEqual(exported["metadata_checksum_sha256"], reimported["metadata_checksum_sha256"])
        exported["metadata"]["region"] = "Tampered"
        self.assert_store_error(422, federation.import_metadata, exported, AUTHORITY)
        federation.review_model(imported["id"], False, "Approval revoked pending evidence", 2, AUTHORITY)
        self.assert_store_error(404, federation.export_metadata, imported["id"])
        self.assertEqual(3, len(federation.list_model_audit(imported["id"])))

    def test_metadata_rejects_executable_unknown_and_invalid_values(self):
        invalid = [
            metadata_payload(pickle="gASV..."), metadata_payload(artifact_url="https://evil.invalid/model.pkl"),
            metadata_payload(schema_version="2.0"), metadata_payload(metrics={"mae": float("nan"), "rmse": 12}),
            metadata_payload(metrics={"mae": 20, "rmse": 10}), metadata_payload(horizon_hours=True),
            metadata_payload(holdout_end="2999-01-01"), metadata_payload(artifact_sha256="not-a-checksum"),
            metadata_payload(unit="ppm"), metadata_payload(parameter="unknown"),
        ]
        for payload in invalid:
            self.assert_store_error(422, federation.import_metadata, payload, AUTHORITY)
        self.assertEqual([], federation.list_models(include_pending=True))


AUTH_DEPS = all(importlib.util.find_spec(name) for name in ("fastapi", "clerk_backend_api", "jwt", "cryptography"))


@unittest.skipUnless(AUTH_DEPS, "Install API dependencies to run real Clerk JWT verification tests")
class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def setUp(self):
        from src.api import auth_v2
        self.auth = auth_v2
        self.env = patch.dict(os.environ, {
            "AIRSENTINEL_ENV": "production", "CLERK_SECRET_KEY": "sk_test_fixture_only",
            "CLERK_JWT_KEY": self.public_key, "CLERK_AUTHORIZED_PARTIES": ORIGIN,
            "AUTHORITY_ALLOWED_EMAILS": AUTHORITY["email"],
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.user = SimpleNamespace(id=AUTHORITY["user_id"], banned=False, locked=False, deprovisioned=False,
            primary_email_address_id="email_primary", email_addresses=[SimpleNamespace(
                id="email_primary", email_address=AUTHORITY["email"], verification=SimpleNamespace(status="verified"))])
        self.session = SimpleNamespace(status="active", user_id=AUTHORITY["user_id"])
        self.client_patch = patch("clerk_backend_api.Clerk")
        self.client = self.client_patch.start().return_value.__enter__.return_value
        self.client.users.get.return_value = self.user
        self.client.sessions.get.return_value = self.session
        self.addCleanup(self.client_patch.stop)

    def token(self, *, key=None, **claims):
        import jwt
        now = int(time.time())
        return jwt.encode({"sub": AUTHORITY["user_id"], "sid": "sess_test", "azp": ORIGIN,
            "exp": now + 120, "iat": now - 5, "nbf": now - 5, **claims}, key or self.key, algorithm="RS256", headers={"kid": "fixture"})

    def request(self, token=None, extra=None):
        from starlette.requests import Request
        headers = {"origin": ORIGIN, **(extra or {})}
        if token is not None:
            headers["authorization"] = "Bearer " + token
        return Request({"type": "http", "method": "POST", "path": "/api/v2/private", "headers": [(key.encode(), value.encode()) for key, value in headers.items()]})

    def assert_auth_error(self, status, fn, *args):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            fn(*args)
        self.assertEqual(status, caught.exception.status_code)

    def test_real_sdk_accepts_signature_and_server_verified_allowlist(self):
        self.assertEqual(AUTHORITY, self.auth.require_authority(self.request(self.token())))
        self.client.users.get.assert_called_once_with(user_id=AUTHORITY["user_id"], retries=None)
        self.client.sessions.get.assert_called_once_with(session_id="sess_test", retries=None)

    def test_missing_forged_expired_and_wrong_origin_tokens_fail(self):
        self.assert_auth_error(401, self.auth.require_authority, self.request(extra={"x-user-email": AUTHORITY["email"]}))
        for token in (self.token(key=self.other_key), self.token(exp=int(time.time()) - 600), self.token(azp="https://untrusted.example.test")):
            self.assert_auth_error(401, self.auth.require_authority, self.request(token))
        self.assert_auth_error(403, self.auth.require_authority, self.request(self.token(), {"origin": "https://untrusted.example.test"}))
        self.client.users.get.assert_not_called()

    def test_verified_primary_email_required_and_user_metadata_never_grants_authority(self):
        self.user.email_addresses[0].email_address = "outsider@example.test"
        self.assert_auth_error(403, self.auth.require_authority, self.request(self.token(email=AUTHORITY["email"], role="admin"), {"x-user-email": AUTHORITY["email"]}))
        self.user.email_addresses[0].email_address = AUTHORITY["email"]
        self.user.email_addresses[0].verification.status = "unverified"
        self.assert_auth_error(403, self.auth.require_authority, self.request(self.token()))

    def test_revoked_session_and_banned_user_fail_closed(self):
        self.session.status = "revoked"
        self.assert_auth_error(401, self.auth.require_user, self.request(self.token()))
        self.session.status = "active"
        self.user.banned = True
        self.assert_auth_error(401, self.auth.require_user, self.request(self.token()))
        self.user.banned = False
        self.client.users.get.side_effect = RuntimeError("provider offline with secret details")
        self.assert_auth_error(503, self.auth.require_user, self.request(self.token()))

    def test_missing_configuration_or_production_localhost_fails_closed(self):
        with patch.dict(os.environ, {"CLERK_SECRET_KEY": ""}):
            self.assert_auth_error(503, self.auth.require_user, self.request(self.token()))
        for origin in ("http://localhost:5173", "https://localhost:5173", "https://*.example.test", "https://example.test/path"):
            with patch.dict(os.environ, {"CLERK_AUTHORIZED_PARTIES": origin}):
                self.assert_auth_error(503, self.auth.require_user, self.request(self.token()))


if __name__ == "__main__":
    unittest.main()
