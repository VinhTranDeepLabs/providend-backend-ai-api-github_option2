from fastapi import APIRouter, Request, Depends, Response, status, HTTPException, Query
from services.advisor_service import AdvisorService
from typing import Optional, List
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

router = APIRouter()
advisor_service = AdvisorService()


def _to_utc(d: date, end_of_day: bool, tz: ZoneInfo) -> datetime:
    """Convert a date to a UTC-aware datetime in the given timezone.
    start_of_day → 00:00:00, end_of_day → 23:59:59.999999."""
    if end_of_day:
        local_dt = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=tz)
    else:
        local_dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


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
async def get_advisor_clients(
    advisor_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based). Determines which page of results to return."),
    rows_per_page: int = Query(10, ge=1, le=100, description="Number of rows per page. Controls how many clients are returned in a single response."),
    client_name: Optional[str] = Query(None, description="Filter by client name using case-insensitive partial match. Example: 'john' matches 'John Smith'."),
    date_from: Optional[date] = Query(None, description="Filter clients whose last meeting is on or after this date. Format: YYYY-MM-DD."),
    date_to: Optional[date] = Query(None, description="Filter clients whose last meeting is on or before this date. Format: YYYY-MM-DD."),
    client_timezone: Optional[str] = Query("UTC", description="IANA timezone of the caller used to interpret date_from/date_to. Example: 'Asia/Singapore', 'America/New_York'. Defaults to UTC."),
    conn=Depends(get_conn)
):
    """Get paginated clients for an advisor with optional name and date filters.

    Returns a paginated list of clients along with pagination metadata
    (item_total, item_start, item_end) to support UI pagination controls.

    Date filters are interpreted in client_timezone then converted to UTC before
    querying the database (which stores timestamps in UTC)."""
    try:
        tz = ZoneInfo(client_timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=422, detail=f"Unknown timezone: '{client_timezone}'. Use an IANA timezone name, e.g. 'Asia/Singapore'.")

    dt_from = _to_utc(date_from, end_of_day=False, tz=tz) if date_from else None
    dt_to   = _to_utc(date_to,   end_of_day=True,  tz=tz) if date_to   else None

    result = advisor_service.get_advisor_clients(
        advisor_id,
        page=page,
        rows_per_page=rows_per_page,
        client_name=client_name,
        date_from=dt_from,
        date_to=dt_to,
        conn=conn
    )

    return {
        "success": True,
        "advisor_id": advisor_id,
        **result
    }


@router.get("/{advisor_id}/meetings")
async def get_advisor_meetings(
    advisor_id: str,
    search: Optional[str] = Query(None, description="Search in client name, meeting name, or meeting type"),
    meeting_type: Optional[str] = Query(None, description="Filter by meeting types (comma-separated for multiple)"),
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format: YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format: YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    sort_by: str = Query("date", description="Sort by field", regex="^(date|client_name|meeting_type)$"),
    sort_order: str = Query("desc", description="Sort order", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Records per page"),
    conn=Depends(get_conn)
):
    """
    Get paginated meetings for an advisor with search, filtering, and sorting.
    
    Args:
        advisor_id: The advisor ID
        search: Search term (searches client name, meeting name, meeting type)
        meeting_type: Filter by meeting type(s) - comma-separated for multiple (e.g., "General,Annual Review")
        date_from: Start date (ISO format: YYYY-MM-DD)
        date_to: End date (ISO format: YYYY-MM-DD)
        sort_by: Sort field - 'date' or 'client_name'
        sort_order: Sort order - 'asc' or 'desc'
        page: Page number (starts at 1)
        per_page: Number of records per page (max 100)
    
    Returns:
        Paginated list of meetings with metadata
    """
    # Parse meeting_types from comma-separated string
    meeting_types = None
    if meeting_type:
        meeting_types = [mt.strip() for mt in meeting_type.split(",") if mt.strip()]
    
    # Validate date range
    if date_from and date_to:
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from must be before or equal to date_to"
            )
    
    result = advisor_service.get_advisor_meetings(
        advisor_id=advisor_id,
        search=search,
        meeting_types=meeting_types,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to fetch meetings")
        )
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "data": result["data"],
        "pagination": result["pagination"]
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