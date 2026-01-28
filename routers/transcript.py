from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi import status as http_status
from fastapi import UploadFile, File, Query
from typing import Optional
from datetime import datetime
from models.schemas import (
    BatchTranscribeRequest,
    BatchTranscribeResponse,
    TranscriptRequest, 
    SummaryResponse,
    ErrorResponse,
    ApplySpeakerMappingRequest,
    IdentifySpeakersResponse,
    ApplySpeakerMappingResponse
)
from services.meeting_service import MeetingService
from utils.db_utils import DatabaseUtils
from services.transcription_service import TranscribeService
from services.azure_openai_service import azure_openai_service
import json
import logging

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post("/upload-audio/{meeting_id}")
async def upload_audio_file(
    meeting_id: str,
    audio_file: UploadFile = File(..., description="Audio file (WebM or WAV, max 300MB)"),
    start_datetime: Optional[datetime] = Query(None, description="Audio start timestamp (ISO format, defaults to NOW)"),
    conn=Depends(get_conn)  # ✨ ADD THIS LINE
):
    """
    Upload audio file to Azure Blob Storage for background transcription
    
    The file will be uploaded with a name format that the background processor expects:
    <meeting_id>_<YYYY-MM-DD HH-MM-SS+00>.extension
    
    - **meeting_id**: Meeting identifier
    - **audio_file**: Audio file (WebM or WAV format, max 300MB)
    - **start_datetime**: Optional timestamp for the audio (defaults to current time)
    
    Returns upload confirmation with blob URL and metadata.
    The background processor (background_batch_transcribe.py) will automatically:
    1. Detect the new file
    2. Transcribe it using Azure Speech Services
    3. Save transcript to database
    """
    try:
        result = await TranscribeService().upload_audio_to_blob(
            meeting_id=meeting_id,
            audio_file=audio_file,
            start_datetime=start_datetime,
            conn=conn  # ✨ ADD THIS LINE
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


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
    

@router.get("/batch-transcribe/status/{meeting_id}")
async def check_transcription_status(
    meeting_id: str,
    conn=Depends(get_conn)
):
    """
    Check if all audio files for a meeting have been processed.
    
    Returns completion status and counts for each processing stage.
    Use this endpoint to poll for transcription completion after upload.
    
    - **queued**: Files uploaded but not yet picked up by background processor
    - **processing**: Files currently being transcribed
    - **completed**: Successfully transcribed and saved to database
    - **failed**: Transcription failed (will be retried)
    - **all_completed**: True when no files are queued or processing
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Transcription status summary
    """
    try:
        db = DatabaseUtils(conn)
        result = db.check_meeting_transcription_status(meeting_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to check status")
            )
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "all_completed": result["all_completed"],
            "total_files": result["total_files"],
            "queued": result["queued"],
            "processing": result["processing"],
            "completed": result["completed"],
            "failed": result["failed"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check transcription status: {str(e)}"
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
    
# ==================== SPEAKER IDENTIFICATION ENDPOINTS ====================

@router.post("/{meeting_id}/identify-speakers", response_model=IdentifySpeakersResponse)
async def identify_speakers(
    meeting_id: str,
    conn=Depends(get_conn)
):
    """
    Identify who each speaker is in the transcript.
    
    Returns suggested speaker mappings without modifying transcript.
    User can review/edit these suggestions before applying.
    """
    try:
        meeting_service = MeetingService()
        details = meeting_service.get_meeting_detail(meeting_id, conn=conn)
        
        if not details:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Meeting details not found for meeting_id: {meeting_id}"
            )
        
        transcript = details.get("transcript")
        
        if not transcript or not transcript.strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No transcript found for this meeting"
            )
        
        from services.transcription_service import has_generic_speaker_labels
        
        if not has_generic_speaker_labels(transcript):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Transcript already has identified speakers"
            )
        
        transcribe_service = TranscribeService()
        result = transcribe_service.identify_speakers(
            transcript=transcript,
            meeting_id=meeting_id,
            conn=conn
        )
        
        return IdentifySpeakersResponse(
            success=True,
            meeting_id=meeting_id,
            speaker_mapping=result["speaker_mapping"],
            num_speakers=result["num_speakers"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error identifying speakers for meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to identify speakers: {str(e)}"
        )


@router.post("/{meeting_id}/apply-speaker-mapping", response_model=ApplySpeakerMappingResponse)
async def apply_speaker_mapping(
    meeting_id: str,
    request: ApplySpeakerMappingRequest,
    created_by: str = Query("MANUAL_SPEAKER_ID", description="Advisor ID who confirmed the mapping"),
    conn=Depends(get_conn)
):
    """
    Apply user-confirmed speaker name mapping to transcript.
    
    Replaces all speaker labels and creates a new version.
    """
    try:
        if not request.speaker_mapping:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="speaker_mapping cannot be empty"
            )
        
        meeting_service = MeetingService()
        details = meeting_service.get_meeting_detail(meeting_id, conn=conn)
        
        if not details:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Meeting details not found for meeting_id: {meeting_id}"
            )
        
        transcript = details.get("transcript")
        
        if not transcript or not transcript.strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No transcript found for this meeting"
            )
        
        transcribe_service = TranscribeService()
        updated_transcript = transcribe_service.apply_speaker_mapping(
            transcript=transcript,
            speaker_mapping=request.speaker_mapping
        )
        
        speakers_replaced = len(request.speaker_mapping)
        
        db = DatabaseUtils(conn)
        update_result = db.update_meeting_detail(
            meeting_id=meeting_id,
            transcript=updated_transcript
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update transcript: {update_result.get('message')}"
            )
        
        version_created = False
        try:
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='transcript',
                content=updated_transcript,
                created_by=created_by
            )
            version_created = True
            logger.info(f"Created transcript version for meeting {meeting_id}")
        except Exception as e:
            logger.error(f"Failed to create version for meeting {meeting_id}: {e}")
        
        preview = updated_transcript[:200] + "..." if len(updated_transcript) > 200 else updated_transcript
        
        logger.info(f"✓ Applied speaker mapping to meeting {meeting_id}: {speakers_replaced} speakers")
        
        return ApplySpeakerMappingResponse(
            success=True,
            message="Speaker mapping applied successfully",
            meeting_id=meeting_id,
            speakers_replaced=speakers_replaced,
            version_created=version_created,
            updated_transcript_preview=preview
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying speaker mapping for meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply speaker mapping: {str(e)}"
        )