from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi import status as http_status
from models.schemas import (
    TranscriptRequest,
    UnansweredQuestionsResponse,
    ErrorResponse,
    RecommendQuestions,
    RecommendQuestionsResponse,
    AutofillQuestionsRequest,
    AutofillQuestionsResponse,
    QuestionTrackerRequest,
    QuestionTrackerResponse
)
from services.question_service import QuestionService

router = APIRouter()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post(
    "/recommend",
    response_model=RecommendQuestionsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_recommended_questions(request: RecommendQuestions, conn=Depends(get_conn)):
    """
    Identify which preset questions were not answered in the transcript
    
    - **question_template_name**: The template to use
    - **transcript**: The conversation transcript to analyze (leave empty to fetch from meeting_id)
    - **meeting_id**: Optional meeting ID to fetch transcript from
    - **num_of_recommendations**: Number of questions to recommend
    
    Returns list of questions that were not answered or discussed
    """
    try:
        question_template_name = request.question_template_name
        num_of_recommendations = request.num_of_recommendations or 5
        transcript = request.transcript
        meeting_id = getattr(request, 'meeting_id', None)

        unanswered = QuestionService().get_unanswered_questions(
            question_template_name, 
            transcript, 
            num_of_recommendations,
            meeting_id=meeting_id,
            conn=conn
        )
        
        return RecommendQuestionsResponse(
            recommended_questions=unanswered,
            total_recommended=len(unanswered),
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to identify unanswered questions: {str(e)}"
        )
    
    
@router.post(
    "/autofill",
    response_model=AutofillQuestionsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def autofill_questions(request: AutofillQuestionsRequest, conn=Depends(get_conn)):
    """
    Analyze transcript and extract answers for preset questions
    
    - **template_name**: The question template to use
    - **transcript**: The conversation transcript to analyze (leave empty to fetch from meeting_id)
    - **meeting_id**: Optional meeting ID to fetch transcript from
    
    Returns preset questions with extracted answers and confidence levels
    """
    try:
        autofilled_questions = QuestionService().autofill_questions(
            request.template_name, 
            request.transcript, 
            request.meeting_id,
            conn=conn
        )
        
        return AutofillQuestionsResponse(
            message="Questions autofilled successfully",
            autofilled_questions=autofilled_questions,
            filled_template=request.template_name,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to autofill questions: {str(e)}"
        )
    

@router.post(
    "/tracker",
    response_model=QuestionTrackerResponse,
    responses={500: {"model": ErrorResponse}}
)
async def track_questions(request: QuestionTrackerRequest, conn=Depends(get_conn)):
    """
    Track which questions were answered in the transcript, organized by sections
    
    - **question_template**: The question template name to use for tracking
    - **transcript**: The conversation transcript to analyze
    
    Returns questions organized by section with boolean indicating if answered
    """
    try:
        sections = QuestionService().track_questions(
            template_name=request.question_template,
            transcript=request.transcript,
            conn=conn
        )
        
        return QuestionTrackerResponse(
            sections=sections,
            success=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track questions: {str(e)}"
        )