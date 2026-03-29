"""Supabase GitHub OAuth (PKCE flow) + HMAC-signed session cookies."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

_COOKIE_NAME = "shelter_session"
_PKCE_COOKIE = "pkce_verifier"
_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


# ── PKCE helpers ──────────────────────────────────────────────────────

def _generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ── Supabase Auth API ─────────────────────────────────────────────────

def get_login_url(redirect_to: str) -> tuple[str, str]:
    """Return (authorize_url, code_verifier). Store verifier in a cookie."""
    verifier, challenge = _generate_pkce()
    params = urllib.parse.urlencode({
        "provider": "github",
        "redirect_to": redirect_to,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return f"{SUPABASE_URL}/auth/v1/authorize?{params}", verifier


def exchange_code(auth_code: str, code_verifier: str) -> dict:
    """Exchange authorization code for a Supabase session.

    Returns dict with ``access_token``, ``refresh_token``, and ``user``.
    """
    data = json.dumps({
        "auth_code": auth_code,
        "code_verifier": code_verifier,
    }).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=pkce",
        data=data,
        headers={
            "Content-Type": "application/json",
            "apikey": SUPABASE_ANON_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def extract_user_info(session: dict) -> dict:
    """Pull GitHub login, avatar, and provider token from a Supabase session."""
    user = session.get("user", {})
    meta = user.get("user_metadata", {})
    return {
        "id": user.get("id", ""),
        "github_login": meta.get("user_name", meta.get("preferred_username", "")),
        "avatar_url": meta.get("avatar_url", ""),
        "provider_token": session.get("provider_token", ""),
    }


# ── Session cookies (HMAC-signed) ────────────────────────────────────

def _sign(payload: str) -> str:
    sig = hmac.new(
        SESSION_SECRET.encode(), payload.encode(), hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify(cookie: str) -> str | None:
    parts = cookie.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    expected = hmac.new(
        SESSION_SECRET.encode(), payload.encode(), hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return payload


def create_session_cookie(
    user_id: str, github_login: str, avatar_url: str,
    provider_token: str = "",
) -> tuple[str, str, int]:
    """Return (cookie_name, cookie_value, max_age)."""
    payload = json.dumps({
        "uid": user_id,
        "login": github_login,
        "avatar": avatar_url,
        "gh_token": provider_token,
        "iat": int(time.time()),
    })
    return _COOKIE_NAME, _sign(payload), _COOKIE_MAX_AGE


def read_session_cookie(cookie_value: str) -> dict | None:
    """Return user dict from a signed cookie, or None if invalid/expired.

    Returns ``{"uid": str, "login": str, "avatar": str}`` or None.
    """
    payload = _verify(cookie_value)
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, KeyError):
        return None
    issued = data.get("iat", 0)
    if time.time() - issued > _COOKIE_MAX_AGE:
        return None
    return data
