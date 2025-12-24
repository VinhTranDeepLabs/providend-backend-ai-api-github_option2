from fastapi import APIRouter, HTTPException, Path
from models.schemas import (
    GenerateSummaryRequest,
    GenerateSummaryResponse,
    ErrorResponse
)
from services.summay_service import SummaryService

router = APIRouter()
meeting_service = SummaryService()

@router.post(
    "/{meeting_id}/summary",
    response_model=GenerateSummaryResponse,
    responses={500: {"model": ErrorResponse}}
)
async def generate_meeting_summary(
    meeting_id: str = Path(..., description="The meeting ID"),
    request: GenerateSummaryRequest = None
):
    """
    Generate a structured 3-paragraph summary from meeting transcript
    
    Creates a summary with three sections:
    - Meeting Objective: Purpose and context of the meeting
    - Client Situation: Current circumstances and financial status
    - Goals: What the client wants to achieve
    
    - **meeting_id**: The ID of the meeting (for reference/logging)
    - **transcript**: The conversation transcript to summarize
    
    Returns formatted summary without saving to database
    """
    try:
        summary = meeting_service.generate_summary(request.transcript)
        
        return GenerateSummaryResponse(
            summary=summary,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )