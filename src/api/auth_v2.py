"""Fail-closed Clerk session authentication for the private pilot APIs.

Identity and the verified primary email are always fetched from Clerk. Headers,
request JSON and editable user metadata never grant an authority role.
"""

import ipaddress
import math
import os
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def configured_origins() -> list[str]:
    """Return only explicitly configured exact origins, with no wildcard hosts."""
    raw = os.environ.get("CLERK_AUTHORIZED_PARTIES", "")
    origins = list(dict.fromkeys(item.strip().rstrip("/") for item in raw.split(",") if item.strip()))
    local = os.environ.get("AIRSENTINEL_ENV") == "local" and not any(
        os.environ.get(name) for name in ("VERCEL", "K_SERVICE", "AWS_LAMBDA_FUNCTION_NAME")
    )
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            hostname = parsed.hostname or ""
            loopback = hostname.lower() == "localhost"
            try:
                loopback = loopback or ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                pass
            valid = (
                parsed.scheme in ({"https", "http"} if local else {"https"})
                and bool(hostname)
                and "*" not in origin
                and not parsed.username
                and not parsed.password
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
                and (local or not loopback)
            )
            _ = parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise HTTPException(503, "Authentication origins are not configured safely")
    return origins


def _field(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _verify_identity(request: Request, secret: str, origins: list[str]) -> dict:
    # Lazy import lets public read-only data endpoints run if auth is unconfigured.
    try:
        from clerk_backend_api import AuthenticateRequestOptions, Clerk, authenticate_request
    except ImportError as exc:
        raise HTTPException(503, "Authentication service is unavailable") from exc

    try:
        state = authenticate_request(
            request,
            AuthenticateRequestOptions(
                secret_key=secret,
                jwt_key=os.environ.get("CLERK_JWT_KEY") or None,
                authorized_parties=origins,
                accepts_token=["session_token"],
            ),
        )
        if not state.is_signed_in:
            raise HTTPException(401, "A valid signed-in session is required")
        claims = state.payload or {}
        user_id = claims.get("sub")
        session_id = claims.get("sid")
        expires = claims.get("exp")
        if (
            not isinstance(user_id, str)
            or not user_id.startswith("user_")
            or not isinstance(session_id, str)
            or not session_id.startswith("sess_")
            or not isinstance(expires, (float, int))
            or isinstance(expires, bool)
            or not math.isfinite(expires)
            or expires <= time.time()
            or claims.get("azp") not in origins
        ):
            raise HTTPException(401, "A valid signed-in session is required")
        with Clerk(bearer_auth=secret, timeout_ms=8000) as client:
            # No identity cache: revocation and allowlist removals apply on the
            # next request, even while a previously issued JWT has time left.
            session = client.sessions.get(session_id=session_id, retries=None)
            user = client.users.get(user_id=user_id, retries=None)
        if (
            _field(session, "status") != "active"
            or _field(session, "user_id") != user_id
            or _field(user, "id") != user_id
            or _field(user, "banned", False)
            or _field(user, "locked", False)
            or _field(user, "deprovisioned", False)
        ):
            raise HTTPException(401, "This session is no longer active")
        primary_id = _field(user, "primary_email_address_id")
        primary = next(
            (email for email in (_field(user, "email_addresses", []) or []) if _field(email, "id") == primary_id),
            None,
        )
        if not primary or _field(_field(primary, "verification", {}), "status") != "verified":
            raise HTTPException(403, "Verify your primary email before using this feature")
        email = _field(primary, "email_address", "")
        if not isinstance(email, str) or "@" not in email:
            raise HTTPException(403, "A verified primary email is required")
        return {"user_id": user_id, "email": email.strip().casefold()}
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose SDK exceptions: these can contain tokens/remote payloads.
        raise HTTPException(503, "Authentication verification is temporarily unavailable") from exc


def require_user(request: Request) -> dict:
    authorization = request.headers.get("authorization", "")
    # Require explicit bearer credentials. This avoids ambient session-cookie
    # authentication on mutation endpoints and does not trust x-user-* headers.
    if not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"})
    if len(authorization) > 16384:
        raise HTTPException(401, "Invalid credentials")
    secret = os.environ.get("CLERK_SECRET_KEY", "").strip()
    origins = configured_origins()
    if not secret or not origins:
        raise HTTPException(503, "Authentication has not been configured")
    origin = request.headers.get("origin")
    if origin and origin not in origins:
        raise HTTPException(403, "Request origin is not authorized")
    return _verify_identity(request, secret, origins)


def require_authority(request: Request) -> dict:
    identity = require_user(request)
    allowed = {
        value.strip().casefold()
        for value in os.environ.get("AUTHORITY_ALLOWED_EMAILS", "").split(",")
        if value.strip()
    }
    if not allowed or identity["email"] not in allowed:
        raise HTTPException(403, "Authority access has not been granted to this account")
    return identity
