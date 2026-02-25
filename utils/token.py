# v1.0 endpoint (based on your token's issuer)
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
import jwt
import requests
from config.settings import AZURE_TENANT_ID, AZURE_CLIENT_SECRET as JWT_SECRET_KEY

JWKS_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/keys"

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 30
_REFRESH_TOKEN_EXPIRE_DAYS = 1
_TOKEN_ISSUER = "bearies-app"
_TOKEN_AUDIENCE = "providend"


# ──────────────────────────────────────────────
# Microsoft token validation (used only by /sso)
# ──────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_jwks():
    response = requests.get(JWKS_URL)
    response.raise_for_status()
    return response.json()


def get_signing_key(token: str):
    """Get the signing key for the token from JWKS."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header"
        )

    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return key

    # Clear cache and retry (keys may have rotated)
    get_jwks.cache_clear()
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find signing key"
    )


def validate_microsoft_token(token: str) -> dict:
    """Validate incoming Microsoft Entra ID token and return its payload."""
    get_signing_key(token)  # ensures kid exists in JWKS

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # For development only
        )

        if payload.get("tid") != AZURE_TENANT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant"
            )

        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )


# ──────────────────────────────────────────────
# App-issued HS256 tokens
# ──────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """Issue a signed HS256 access token that expires in 30 minutes."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": data["user_id"],
        "email": data.get("email"),
        "name": data.get("name"),
        "type": "access",
        "iss": _TOKEN_ISSUER,
        "aud": _TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Issue a signed HS256 refresh token that expires in 1 day."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": data["user_id"],
        "type": "refresh",
        "iss": _TOKEN_ISSUER,
        "aud": _TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=_ALGORITHM)


def validate_app_token(token: str, token_type: str = "access") -> dict:
    """
    Validate an app-issued HS256 token.
    Raises HTTP 401 on expiry, wrong type, or any invalid state.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[_ALGORITHM],
            issuer=_TOKEN_ISSUER,
            audience=_TOKEN_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

    if payload.get("type") != token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type: expected '{token_type}'"
        )

    return payload
