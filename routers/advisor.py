from fastapi import APIRouter, Request, Depends, Response, status, HTTPException
from services.advisor_service import AdvisorService

router = APIRouter()
advisor_service = AdvisorService()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post("/{advisor_id}/create")
async def create_advisor(
    advisor_id: str, 
    name: str, 
    email: str = None, 
    role: str = "Advisor",
    conn=Depends(get_conn)
):
    """
    Create a new advisor profile.
    
    Args:
        advisor_id: Unique advisor identifier
        name: Full name of the advisor
        email: Email address (optional)
        role: Role/title (default: "Advisor")
    
    Returns:
        Created advisor details
    """
    result = advisor_service.create_advisor(
        advisor_id=advisor_id,
        name=name,
        email=email,
        role=role,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create advisor")
        )
    
    return {
        "success": True,
        "message": "Advisor created successfully",
        "advisor_id": advisor_id,
        "name": name,
        "email": email,
        "role": role
    }


@router.get("/{advisor_id}")
async def get_advisor_profile(advisor_id: str, conn=Depends(get_conn)):
    """
    Get advisor profile by ID.
    
    Args:
        advisor_id: The advisor ID
    
    Returns:
        Advisor profile information
    """
    result = advisor_service.get_advisor_profile(advisor_id, conn=conn)
    
    if not result.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advisor not found"
        )
    
    advisor = result.get("advisor")
    return {
        "success": True,
        "advisor_id": advisor["advisor_id"],
        "name": advisor["name"],
        "email": advisor.get("email"),
        "role": advisor.get("role"),
        "date_created": advisor.get("date_created")
    }


@router.patch("/{advisor_id}")
async def update_advisor_profile(
    advisor_id: str,
    name: str = None,
    email: str = None,
    role: str = None,
    conn=Depends(get_conn)
):
    """
    Update advisor profile.
    
    Args:
        advisor_id: The advisor ID
        name: New name (optional)
        email: New email (optional)
        role: New role (optional)
    
    Returns:
        Update confirmation
    """
    result = advisor_service.update_advisor(
        advisor_id=advisor_id,
        name=name,
        email=email,
        role=role,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update advisor")
        )
    
    return {
        "success": True,
        "message": "Advisor updated successfully",
        "advisor_id": advisor_id
    }


@router.delete("/{advisor_id}")
async def delete_advisor(advisor_id: str, conn=Depends(get_conn)):
    """
    Delete an advisor.
    
    Args:
        advisor_id: The advisor ID to delete
    
    Returns:
        Deletion confirmation
    """
    result = advisor_service.delete_advisor(advisor_id, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete advisor")
        )
    
    return {
        "success": True,
        "message": "Advisor deleted successfully",
        "advisor_id": advisor_id
    }


@router.get("/")
async def list_all_advisors(conn=Depends(get_conn)):
    """
    List all advisors.
    
    Returns:
        List of all advisors
    """
    advisors = advisor_service.list_advisors(conn=conn)
    
    return {
        "success": True,
        "total_advisors": len(advisors),
        "advisors": advisors
    }


@router.get("/{advisor_id}/clients")
async def get_advisor_clients(advisor_id: str, conn=Depends(get_conn)):
    """
    Get all clients for an advisor.
    
    Args:
        advisor_id: The advisor ID
    
    Returns:
        List of clients assigned to this advisor
    """
    result = advisor_service.get_advisor_clients(advisor_id, conn=conn)
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "total_clients": result.get("total_clients", 0),
        "clients": result.get("clients", [])
    }


@router.get("/{advisor_id}/meetings")
async def get_advisor_meetings(advisor_id: str, conn=Depends(get_conn)):
    """
    Get all meetings for an advisor.
    
    Args:
        advisor_id: The advisor ID
    
    Returns:
        List of meetings conducted by this advisor
    """
    result = advisor_service.get_advisor_meetings(advisor_id, conn=conn)
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "total_meetings": result.get("total_meetings", 0),
        "meetings": result.get("meetings", [])
    }


@router.get("/{advisor_id}/statistics")
async def get_advisor_statistics(advisor_id: str, conn=Depends(get_conn)):
    """
    Get statistics for an advisor (clients, meetings, status breakdowns).
    
    Args:
        advisor_id: The advisor ID
    
    Returns:
        Statistics summary for the advisor
    """
    result = advisor_service.get_advisor_statistics(advisor_id, conn=conn)
    
    return {
        "success": True,
        **result
    }