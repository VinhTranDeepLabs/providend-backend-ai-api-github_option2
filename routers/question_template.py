from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, model_validator
from services.question_template_service import QuestionTemplateService
from typing import Optional, Dict, List

router = APIRouter()

DEFAULT_SECTION = "uncategorized"


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


# ==================== REQUEST MODELS ====================

class TemplateRequest(BaseModel):
    template_name: str = Field(..., description="Template name")
    template_owner: Optional[str] = Field(None, description="Template owner")
    template_type: Optional[str] = Field("with-section", description="Template type: 'with-section' or 'without-section'")
    sections: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Sections with questions. Required for 'with-section'. e.g. {'Section 1': ['Q1', 'Q2']}"
    )
    questions: Optional[List[str]] = Field(
        None,
        description="Flat list of questions. Required for 'without-section'. e.g. ['Q1', 'Q2']"
    )

    @model_validator(mode="after")
    def validate_sections_or_questions(self):
        if self.template_type == "without-section":
            if not self.questions:
                raise ValueError("'questions' is required when template_type is 'without-section'")
        else:
            if not self.sections:
                raise ValueError("'sections' is required when template_type is 'with-section'")
        return self

    def get_sections(self) -> Dict[str, List[str]]:
        """Return sections dict — wraps flat questions under a default key for without-section."""
        if self.template_type == "without-section":
            return {DEFAULT_SECTION: self.questions}
        return self.sections


# ==================== TEMPLATE ENDPOINTS ====================

@router.get("/all")
async def get_all_templates(conn=Depends(get_conn)):
    """List all question templates"""
    service = QuestionTemplateService(conn)
    return {"templates": service.get_all_templates()}


@router.get("/{template_id}")
async def get_detailed_template(template_id: str, conn=Depends(get_conn)):
    """Get a complete template with all sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.get_detailed_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/")
async def create_template(request: TemplateRequest, conn=Depends(get_conn)):
    """Create a new template with all sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.create_detailed_template(request.template_name, request.get_sections(), request.template_owner, request.template_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result


@router.put("/{template_id}")
async def save_template(template_id: str, request: TemplateRequest, conn=Depends(get_conn)):
    """Save button — full replace of sections and questions"""
    service = QuestionTemplateService(conn)
    result = service.save_detailed_template(template_id, request.template_name, request.get_sections(), request.template_owner, request.template_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result


@router.delete("/{template_id}")
async def delete_template(template_id: str, conn=Depends(get_conn)):
    """Delete a template (cascades to all sections and questions)"""
    service = QuestionTemplateService(conn)
    result = service.delete_template(template_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    service.refresh_categorized_questions()
    return result
