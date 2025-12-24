from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi import status as http_status
from models.schemas import (
    BatchTranscribeRequest,
    BatchTranscribeResponse,
    TranscriptRequest, 
    SummaryResponse,
    ErrorResponse
)
from services.transcription_service import TranscribeService
from services.azure_openai_service import azure_openai_service
import json

router = APIRouter()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post(
    "/batch-transcribe",
    response_model=BatchTranscribeResponse,
    responses={500: {"model": ErrorResponse}}
)
async def batch_transcribe(request: BatchTranscribeRequest):
    """
    Perform batch speech-to-text transcription with speaker diarization
    
    - **audio_urls**: List of publicly accessible audio file URLs (Azure Blob Storage, etc.)
    - **language**: Language code for transcription (default: en-US)
    
    Supports audio formats: WAV, MP3, OGG, FLAC
    
    Returns transcriptions with speaker identification and timestamps
    """
    try:
        if not request.audio_urls:
            raise HTTPException(
                status_code=400,
                detail="At least one audio URL is required"
            )
        
        # Validate URLs (basic check)
        for url in request.audio_urls:
            if not url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid URL format: {url}"
                )
        
        # Perform batch transcription
        results = TranscribeService().batch_transcribe_urls(
            audio_urls=request.audio_urls,
            language=request.language
        )
        
        return BatchTranscribeResponse(
            results=results,
            total_files=len(results),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@router.post("/aggregate/{meeting_id}")
async def aggregate_transcript(meeting_id: str, conn=Depends(get_conn)):
    """
    Aggregate transcript segments for a meeting into a single transcript.
    
    - **meeting_id**: The ID of the meeting to aggregate transcripts for
    """
    try:
        aggregated_transcript = TranscribeService().aggregate_transcript(meeting_id, conn=conn)
        return {
            "meeting_id": meeting_id, 
            "transcript": aggregated_transcript, 
            "success": True
        }
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate transcript: {str(e)}"
        )


@router.get("/{meeting_id}")
async def get_transcript(meeting_id: str, conn=Depends(get_conn)):
    """
    Retrieve the transcript for a specific meeting.
    
    - **meeting_id**: The ID of the meeting to retrieve the transcript for
    """
    try:
        transcript = TranscribeService().get_transcript(meeting_id, conn=conn)
        
        if transcript is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No transcript found for meeting_id: {meeting_id}"
            )
        
        return {
            "meeting_id": meeting_id, 
            "transcript": transcript, 
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )