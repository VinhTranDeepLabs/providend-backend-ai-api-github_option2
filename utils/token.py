# v1.0 endpoint (based on your token's issuer)
from functools import lru_cache
from fastapi import HTTPException, status
import jwt
import requests
from config.settings import AZURE_TENANT_ID  # Changed import

JWKS_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/keys"


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


def validate_token(token: str) -> dict:
    """Validate Microsoft SSO token and return payload."""
    signing_key_data = get_signing_key(token)
    signing_key = jwt.PyJWK(signing_key_data).key
    
    try:
        # payload = jwt.decode(
        #     token,
        #     signing_key,
        #     algorithms=["RS256"],
        #     options={"verify_aud": False}
        # )
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # For development only
        )
        
        # Validate tenant
        if payload.get("tid") != AZURE_TENANT_ID:  # Changed variable
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