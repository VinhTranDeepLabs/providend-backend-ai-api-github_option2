from fastapi import APIRouter, Response, status
from backup.network_service import network_service

router = APIRouter()

@router.get("/connection")
async def check_connection(response: Response):
    """
    Check internet connection status
    
    Returns:
        - **Status 200**: Online - Internet connection is available
        - **Status 408**: Offline - No internet connection (Request Timeout)
    """
    is_online, status_message = network_service.check_internet_connection()
    
    if is_online:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "Online",
            "message": "Internet connection is available"
        }
    else:
        response.status_code = status.HTTP_408_REQUEST_TIMEOUT
        return {
            "status": "Offline",
            "message": "No internet connection detected"
        }