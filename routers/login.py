from fastapi import APIRouter, Query, HTTPException, status, Depends, Request
from fastapi.responses import RedirectResponse
from typing import Optional
from services.auth_service import auth_service
from models.schemas import SSORequest, SSOResponse
from services.advisor_service import AdvisorService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_conn(request: Request):
    """Return the shared DB connection stored on app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn

@router.post("/sso", response_model=SSOResponse)
async def sso_login(
    request: SSORequest,
    conn=Depends(get_conn)
):
    """
    Single Sign-On endpoint - Validates Microsoft Entra ID token
    
    - Validates token against Microsoft's JWKS
    - Creates or retrieves user from advisors table
    - Returns user information
    """
    try:
        # Import and validate token
        from utils.token import validate_token
        
        # Validate token with JWKS (raises HTTPException if invalid)
        token_payload = validate_token(request.access_token)
        
        # Extract user info from token
        user_oid = token_payload.get("oid") or token_payload.get("sub")
        user_email = token_payload.get("email") or token_payload.get("preferred_username") or token_payload.get("upn")
        user_name = token_payload.get("name")
        
        if not user_email or not user_oid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token missing required user information (email or oid)"
            )
        
        # Get or create user in database
        advisor_service = AdvisorService()
        user = advisor_service.get_or_create_user_from_token(
            oid=user_oid,
            email=user_email,
            name=user_name or user_email.split("@")[0],  # Fallback to email prefix
            conn=conn
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve or create user"
            )
        
        logger.info(f"SSO successful for user: {user_email}")
        
        return SSOResponse(
            valid=True,
            user=user,
            access_token=request.access_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSO error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
    

# @router.get("/login")
# async def login(redirect_to: Optional[str] = Query(None, description="Optional redirect URL after login")):
#     """
#     Initiate OAuth2 login flow with Azure Entra ID
    
#     Automatically redirects to Microsoft login page
#     """
#     # Build authorization URL
#     auth_url = auth_service.get_authorization_url(state=redirect_to)
    
#     logger.info("Initiating OAuth2 login flow")
#     return RedirectResponse(url=auth_url)


# @router.get("/callback")
# async def auth_callback(
#     code: str = Query(..., description="Authorization code from Azure AD"),
#     state: Optional[str] = Query(None, description="State parameter for redirect")
# ):
#     """
#     Handle OAuth2 callback from Azure Entra ID
    
#     Exchange authorization code for access token and redirect to frontend with token
#     """
#     try:
#         # Exchange authorization code for tokens
#         token_data = await auth_service.exchange_code_for_token(code)
        
#         # Get user profile from Microsoft Graph
#         user_profile = await auth_service.get_user_profile(token_data["access_token"])
        
#         # Build user object
#         user = {
#             "id": user_profile.get("id"),
#             "email": user_profile.get("mail") or user_profile.get("userPrincipalName"),
#             "name": user_profile.get("displayName"),
#             "access_token": token_data["access_token"],
#             "refresh_token": token_data.get("refresh_token"),
#             "expires_in": token_data.get("expires_in")
#         }
        
#         # Redirect to frontend with token (in production, use HTTP-only cookies)
#         from config.settings import FRONTEND_URL
#         redirect_url = state or f"{FRONTEND_URL}/auth/success"
        
#         # Pass tokens as URL parameters (for development)
#         # In production, set HTTP-only cookies instead
#         full_redirect = (
#             f"{redirect_url}"
#             f"?access_token={token_data['access_token']}"
#             f"&email={user['email']}"
#             f"&name={user['name']}"
#         )
        
#         logger.info(f"Authentication successful for user: {user['email']}")
#         return RedirectResponse(url=full_redirect)
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Authentication callback error: {str(e)}")
#         from config.settings import FRONTEND_URL
#         error_redirect = f"{FRONTEND_URL}/auth/error?message=authentication_failed"
#         return RedirectResponse(url=error_redirect)


@router.get("/verify")
async def verify_token(
    access_token: str = Query(..., description="Access token to verify")
):
    """
    Verify if access token is valid
    
    Returns user info if token is valid, 401 if not
    """
    try:
        # Validate token
        decoded = auth_service.validate_token(access_token)
        user = auth_service.extract_user_from_token(decoded)
        
        return {
            "valid": True,
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# @router.get("/logout")
# async def logout(
#     post_logout_redirect: Optional[str] = Query(None, description="URL to redirect after logout")
# ):
#     """
#     Logout user from Azure AD
    
#     Redirects to Azure AD logout endpoint
#     """
#     logout_url = auth_service.get_logout_url(post_logout_redirect)
    
#     logger.info("User logout initiated")
#     return RedirectResponse(url=logout_url)


# @router.get("/check")
# async def check_auth():
#     """
#     Check if auth configuration is valid
#     """
#     from config.settings import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_REDIRECT_URI
    
#     return {
#         "configured": True,
#         "tenant_id": AZURE_TENANT_ID[:8] + "...",  # Partial for security
#         "client_id": AZURE_CLIENT_ID[:8] + "...",
#         "redirect_uri": AZURE_REDIRECT_URI
#     }