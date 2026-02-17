from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, ConfigDict
from services.question_template_service import QuestionTemplateService
from typing import Optional, Dict, List

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
        ]
    }})

    templates: List[TemplateContentList]


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


# ==================== TEMPLATE ENDPOINTS ====================

@router.get("/all", response_model=TemplateListResponse)
async def get_all_templates(conn=Depends(get_conn)):
    """List all question templates"""
    service = QuestionTemplateService(conn)
    return {"templates": service.get_all_templates()}


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
