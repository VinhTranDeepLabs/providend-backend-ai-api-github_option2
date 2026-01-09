from fastapi import APIRouter, HTTPException, Path, Request, Depends
from models.schemas import (
    GenerateSummaryRequest,
    GenerateSummaryResponse,
    ErrorResponse
)
from services.summay_service import SummaryService

router = APIRouter()
summary_service = SummaryService()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post(
    "/{meeting_id}/summary",
    response_model=GenerateSummaryResponse,
    responses={500: {"model": ErrorResponse}}
)
async def generate_meeting_summary(
    meeting_id: str = Path(..., description="The meeting ID"),
    request: GenerateSummaryRequest = None,
    conn=Depends(get_conn)
):
    """
    Generate a structured 3-paragraph summary from meeting transcript
    
    Creates a summary with three sections:
    - Meeting Objective: Purpose and context of the meeting
    - Client Situation: Current circumstances and financial status
    - Goals: What the client wants to achieve
    
    - **meeting_id**: The ID of the meeting (used to fetch participant names)
    - **transcript**: The conversation transcript to summarize
    
    Returns formatted summary with actual participant names instead of Speaker 1/Speaker 2
    """
    try:
        summary = summary_service.generate_summary(
            transcript=request.transcript,
            meeting_id=meeting_id,
            conn=conn
        )
        
        return GenerateSummaryResponse(
            summary=summary,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )