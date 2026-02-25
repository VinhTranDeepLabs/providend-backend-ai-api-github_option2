from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.token import validate_app_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency — validates the app-issued Bearer token.

    Raises HTTP 403 if the Authorization header is missing.
    Raises HTTP 401 if the token is expired or invalid.
    Returns the decoded payload on success.
    """
    token = credentials.credentials
    # validate_app_token raises HTTPException(401) on any failure
    payload = validate_app_token(token, token_type="access")
    return payload
