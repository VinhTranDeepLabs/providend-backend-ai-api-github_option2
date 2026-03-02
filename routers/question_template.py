from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from services.question_template_service import QuestionTemplateService
from typing import Optional, Dict, List
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

router = APIRouter()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


# ==================== REQUEST / RESPONSE MODELS ====================

class TemplateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "template_name": "Total Client Profile",
        "template_owner": "advisor-001",
        "template_type": "with-section",
        "questions": {
            "Personal Values": [
                "What are your core values around money?",
                "What does financial security mean to you?"
            ],
            "Goals & Objectives": [
                "What are your short-term financial goals?",
                "What are your long-term financial goals?"
            ]
        }
    }})

    template_name: str = Field(..., description="Template name", examples=["Total Client Profile"])
    template_owner: Optional[str] = Field(None, description="Template owner", examples=["advisor-001"])
    template_type: Optional[str] = Field("with-section", description="Template type: 'with-section' or 'without-section'", examples=["with-section"])
    questions: Dict[str, List[str]] = Field(
        ...,
        description="Dict of section names to question lists. For 'without-section', use names like 'section-a', 'section-b', 'uncategorized'."
    )


class TemplateContentList(BaseModel):
    template_id: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    template_name: str = Field(..., examples=["Total Client Profile"])
    template_owner: Optional[str] = Field(None, examples=["advisor-001"])
    template_type: str = Field(..., description="'with-section' or 'without-section'", examples=["with-section"])
    last_modified: Optional[str] = Field(None, examples=["2025-06-15T10:30:00"])
    number_of_questions: int = Field(..., examples=[12])


class TemplateListResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "templates": [
            {
                "template_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "template_name": "Total Client Profile",
                "template_owner": "advisor-001",
                "template_type": "with-section",
                "last_modified": "2025-06-15T10:30:00",
                "number_of_questions": 12
            },
            {
                "template_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "template_name": "Pre Discovery",
                "template_owner": "advisor-001",
                "template_type": "without-section",
                "last_modified": "2025-06-14T08:00:00",
                "number_of_questions": 5
            }
        ],
        "item_total": 8,
        "page": 1,
        "rows_per_page": 2,
        "item_start": 1,
        "item_end": 2,
        "last_page": 4
    }})

    templates: List[TemplateContentList] = Field(..., description="List of templates for the current page")
    item_total: int = Field(..., description="Total number of templates matching the filter across all pages", examples=[8])
    page: int = Field(..., description="Current page number (1-based)", examples=[1])
    rows_per_page: int = Field(..., description="Number of rows displayed per page", examples=[2])
    item_start: int = Field(..., description="1-based index of the first item on the current page (e.g. 1 in '1-2 of 8')", examples=[1])
    item_end: int = Field(..., description="1-based index of the last item on the current page (e.g. 2 in '1-2 of 8')", examples=[2])
    last_page: int = Field(..., description="Total number of pages available (e.g. 4 when item_total=8 and rows_per_page=2)", examples=[4])


class TemplateDetailResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "template_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "template_name": "Total Client Profile",
        "template_owner": "advisor-001",
        "template_type": "with-section",
        "created_at": "2025-06-15T10:30:00",
        "updated_at": "2025-06-15T10:30:00",
        "questions": {
            "Personal Values": [
                "What are your core values around money?",
                "What does financial security mean to you?"
            ],
            "Goals & Objectives": [
                "What are your short-term financial goals?",
                "What are your long-term financial goals?"
            ]
        }
    }})

    template_id: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    template_name: str = Field(..., examples=["Total Client Profile"])
    template_owner: Optional[str] = Field(None, examples=["advisor-001"])
    template_type: str = Field(..., examples=["with-section"])
    created_at: Optional[str] = Field(None, examples=["2025-06-15T10:30:00"])
    updated_at: Optional[str] = Field(None, examples=["2025-06-15T10:30:00"])
    questions: Dict[str, List[str]] = Field(
        ...,
        description="Dict of section names to question lists."
    )


class TemplateCreateResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Template created successfully",
        "template_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }})

    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Template created successfully"])
    template_id: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])


class TemplateSaveResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Template saved successfully",
        "template_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }})

    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Template saved successfully"])
    template_id: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])


class DeleteResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Deleted successfully"
    }})

    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Deleted successfully"])


class ErrorResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "detail": "Resource not found"
    }})

    detail: str


def _to_utc(d: date, end_of_day: bool, tz: ZoneInfo) -> datetime:
    """Convert a date to a UTC-aware datetime in the given timezone.
    start_of_day → 00:00:00, end_of_day → 23:59:59.999999."""
    if end_of_day:
        local_dt = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=tz)
    else:
        local_dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


# ==================== TEMPLATE ENDPOINTS ====================

@router.get("/all", response_model=TemplateListResponse)
async def get_all_templates(
    page: int = Query(1, ge=1, description="Page number (1-based). Determines which page of results to return."),
    rows_per_page: int = Query(10, ge=1, le=100, description="Number of rows per page. Controls how many templates are returned in a single response."),
    template_name: Optional[str] = Query(None, description="Filter by template name using case-insensitive partial match. Example: 'client' matches 'Total Client Profile'."),
    template_owner: Optional[str] = Query(None, description="Filter by template owner using case-insensitive partial match. Example: 'advisor-001'."),
    template_type: Optional[str] = Query(None, description="Filter by template type. Accepted values: 'with-section' or 'without-section'."),
    date_from: Optional[date] = Query(None, description="Filter templates last modified on or after this date. Format: YYYY-MM-DD."),
    date_to: Optional[date] = Query(None, description="Filter templates last modified on or before this date. Format: YYYY-MM-DD."),
    client_timezone: Optional[str] = Query("UTC", description="IANA timezone of the caller used to interpret date_from/date_to. Example: 'Asia/Singapore', 'America/New_York'. Defaults to UTC."),
    conn=Depends(get_conn),
):
    """List all question templates with pagination and optional filters.

    Returns a paginated list of templates along with pagination metadata
    (item_total, item_start, item_end) to support UI pagination controls
    like 'item_start - item_end of item_total'.

    Date filters are interpreted in client_timezone then converted to UTC before
    querying the database (which stores timestamps in UTC)."""
    try:
        tz = ZoneInfo(client_timezone)
    except ZoneInfoNotFoundError:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=422, detail=f"Unknown timezone: '{client_timezone}'. Use an IANA timezone name, e.g. 'Asia/Singapore'.")

    dt_from = _to_utc(date_from, end_of_day=False, tz=tz) if date_from else None
    dt_to   = _to_utc(date_to,   end_of_day=True,  tz=tz) if date_to   else None

    service = QuestionTemplateService(conn)
    result = service.get_all_templates(
        page=page,
        rows_per_page=rows_per_page,
        template_name=template_name,
        template_owner=template_owner,
        template_type=template_type,
        date_from=dt_from,
        date_to=dt_to,
    )
    return result


@router.get("/{template_id}", response_model=TemplateDetailResponse, responses={
    404: {"model": ErrorResponse, "description": "Template not found"}
})
async def get_detailed_template(template_id: str, conn=Depends(get_conn)):
    """Get a complete template with all sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.get_detailed_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/", response_model=TemplateCreateResponse, responses={
    400: {"model": ErrorResponse, "description": "Creation failed"}
})
async def create_template(request: TemplateRequest, conn=Depends(get_conn)):
    """Create a new template with all sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.create_detailed_template(request.template_name, request.questions, request.template_owner, request.template_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result


@router.put("/{template_id}", response_model=TemplateSaveResponse, responses={
    400: {"model": ErrorResponse, "description": "Save failed (e.g. template not found)"}
})
async def save_template(template_id: str, request: TemplateRequest, conn=Depends(get_conn)):
    """Save button — full replace of sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.save_detailed_template(template_id, request.template_name, request.questions, request.template_owner, request.template_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result


@router.delete("/{template_id}", response_model=DeleteResponse, responses={
    400: {"model": ErrorResponse, "description": "Deletion failed"}
})
async def delete_template(template_id: str, conn=Depends(get_conn)):
    """Delete a template (cascades to all sections and questions)"""
    service = QuestionTemplateService(conn)
    result = service.delete_template(template_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result
