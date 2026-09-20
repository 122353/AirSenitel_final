# Private evidence and metadata interchange

This is a proposed pilot for human review, not an approved government deployment.
The v2 services do not dispatch enforcement, publish resident evidence, connect
partner countries or execute federated training.

## Authentication and authorization

Protected routes require an explicit `Authorization: Bearer <Clerk session JWT>`.
The official `clerk-backend-api` verifies the signature and time claims and accepts
only session tokens. The service additionally checks the exact authorized party
and retrieves the current session and user from Clerk. Revoked sessions, banned,
locked or deprovisioned users, and unverified primary email addresses are denied.
Authority access requires that verified primary email to appear in the server's
`AUTHORITY_ALLOWED_EMAILS` configuration. Client headers, token email claims,
submitted actor names and editable user metadata cannot grant authority access.
Passwords and session tokens are not stored in the application database.

Required server configuration:

| Variable | Purpose |
| --- | --- |
| `CLERK_SECRET_KEY` | Server-only Clerk key; never expose in the frontend |
| `CLERK_AUTHORIZED_PARTIES` | Comma-separated exact trusted origins, without paths or wildcards |
| `AUTHORITY_ALLOWED_EMAILS` | Comma-separated verified primary emails approved for authority access |
| `CLERK_JWT_KEY` | Optional Clerk public verification key to avoid JWKS network lookups |
| `AIRSENTINEL_STORE=postgres` | Production durable store |
| `DATABASE_URL` | PostgreSQL connection URL; connections require TLS |

Missing configuration or failed provider verification blocks protected actions.
HTTP/loopback origins and SQLite are accepted only with explicit
`AIRSENTINEL_ENV=local` and no serverless/cloud service environment markers.
Local SQLite also requires `AIRSENTINEL_STORE=sqlite` and an explicit
`AIRSENTINEL_SQLITE_PATH`. There is no automatic serverless filesystem fallback.

## Storage and review

Call `case_store_v2.initialize_store()` explicitly after configuring the target
database. It creates only additive `airv2_` tables. Importing modules and serving
requests do not initialize or migrate a database. The application database role
should be confined to the pilot database; schema initialization can use a
separate deployment role. Runtime access does not require schema creation rights.

Reports, sanitized photo bytes, review changes and audit events are transactional.
Reports begin `pending_review`. Authority actions require notes and the currently
displayed `expected_version`; concurrent edits permit one winner and return a
conflict for stale edits. PostgreSQL uses row locks and conditional updates; local
SQLite uses a write transaction and conditional updates. A durable per-user quota
allows ten report submissions in a one-hour window and is not reset by withdrawal.

Precise citizen coordinates, report text, device readings and photos are private.
No public report listing or public photo retrieval is provided. Sanitization of
uploaded images belongs to the API boundary: decode and re-encode the pixels,
drop EXIF and other metadata, and enforce byte/pixel limits before storage.
Indoor and outdoor citizen-device readings both retain an unverified evidence
label and cannot substitute for official outdoor AQI. The six supported
parameters are PM2.5, PM10, NO2, SO2, O3 and CO; raw device identifiers are rejected.

Report receipts contain 32 random bytes and are returned once. Only their SHA-256
digest is stored. Withdrawal must send the receipt in a POST body, never in a URL
or logs. The receipt authorizes withdrawal only, not reading private evidence.
Withdrawal atomically removes report text, location, reading, photo, reporter ID
and review-note text. A redacted tombstone and append-only audit events remain.
Audit snapshots contain status/version and content hashes, not citizen text or
account IDs. Authority actors are recorded from authenticated identities. Notes
are stored separately so withdrawal can remove them without rewriting events.

Deletion covers the active application records. Provider backup, WAL and recovery
retention must be configured and documented by the database operator before a
resident-facing deployment; the application cannot promise immediate erasure from
backups. Quota pseudonyms should be included in the operator retention schedule.
SQLite enables secure deletion of vacated cells for local development.

## Model-card interchange

Only the explicit `schema_version: "1.0"` JSON model-card fields are accepted:
name, version, country code, region, pollutant parameter and unit, forecast
horizon, MAE/RMSE and optional R2, holdout dates, license, privacy notes, training
data summary, model family and optional artifact SHA-256. Unknown fields,
non-finite values, incompatible units and executable/model download fields are
rejected. No pickle files, weights, executable code or external model URLs are
loaded.

Imports are quarantined as `pending_review`. A separate authorized review action
with notes and optimistic version checking approves or rejects them. Only
approved metadata can be listed publicly or exported. Approval must include a
human check that the public text contains no personal data and that provenance,
evaluation and license claims are supportable. No sample country models are
silently seeded as real partnerships.

Exports contain `schema_version`, `metadata` and
`metadata_checksum_sha256`. The digest is SHA-256 over UTF-8 JSON with sorted keys,
no indentation or spaces, Unicode preserved, and finite numbers only. Validation
normalizes MAE/RMSE/R2 to floating-point values before canonical serialization.
Checksum matching checks integrity, not partner identity or scientific validity.
Partner signatures, bilateral governance and actual distributed training are
future work and are not represented as connected capabilities.

## Verification

`python -m unittest tests.test_security_v2 -v` covers real Clerk SDK verification
using ephemeral RSA keys, forged/expired/wrong-party credentials, server lookup
and revoked/banned accounts; private durable report storage; transactional audit
rollback; concurrent case reviews and rate limits; withdrawal and redaction;
metadata quarantine, validation, checksum round-trip and approval revocation.
Tests use temporary local SQLite files and mock only Clerk's remote user/session
lookups, never the JWT verifier. Production PostgreSQL connectivity/migration and
real Clerk account configuration require separate environment verification.

Reference: [Clerk's official Python authentication guide](https://clerk.com/articles/how-to-add-authentication-to-a-python-backend).
