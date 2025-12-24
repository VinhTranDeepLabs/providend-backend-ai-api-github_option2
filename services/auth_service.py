import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status
from config.settings import (
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_REDIRECT_URI,
    FRONTEND_URL
)

# Microsoft identity platform endpoints
AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
AUTHORIZE_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

# Scopes for Microsoft Graph API
SCOPES = ["openid", "profile", "email", "User.Read"]


class AuthService:
    def __init__(self):
        self.tenant_id = AZURE_TENANT_ID
        self.client_id = AZURE_CLIENT_ID
        self.client_secret = AZURE_CLIENT_SECRET
        self.redirect_uri = AZURE_REDIRECT_URI
        
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate the Microsoft login URL"""
        auth_url = (
            f"{AUTHORIZE_ENDPOINT}"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={'+'.join(SCOPES)}"
            f"&response_mode=query"
        )
        
        if state:
            auth_url += f"&state={state}"
            
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": " ".join(SCOPES)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TOKEN_ENDPOINT, data=token_data)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to obtain access token: {response.text}"
                )
            
            return response.json()
    
    async def get_user_profile(self, access_token: str) -> Dict:
        """Fetch user profile from Microsoft Graph API"""
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(GRAPH_API_ENDPOINT, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to fetch user profile"
                )
            
            return response.json()
    
    def validate_token(self, token: str) -> Dict:
        """Validate JWT token (basic validation, for production use proper validation)"""
        try:
            # For production, validate with Microsoft's public keys
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # For development only
            )
            return decoded
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def extract_user_from_token(self, decoded_token: Dict) -> Dict:
        """Extract user information from decoded token"""
        return {
            "id": decoded_token.get("oid") or decoded_token.get("sub"),
            "email": decoded_token.get("email") or decoded_token.get("preferred_username"),
            "name": decoded_token.get("name"),
            "roles": decoded_token.get("roles", [])
        }
    
    def get_logout_url(self, post_logout_redirect: str = None) -> str:
        """Generate Microsoft logout URL"""
        redirect = post_logout_redirect or FRONTEND_URL
        return f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={redirect}"


# Singleton instance
auth_service = AuthService()