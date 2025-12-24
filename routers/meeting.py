from fastapi import APIRouter, Request, Depends, status, HTTPException
from typing import Optional
from datetime import datetime
from uuid import uuid4
from services.meeting_service import MeetingService

router = APIRouter()
meeting_service = MeetingService()


def get_conn(request: Request):
    """Return the shared DB connection stored on app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post("/create")
async def create_meeting(
    client_id: str,
    advisor_id: str,
    meeting_type: str = "General",
    meeting_status: str = "Started",
    meeting_id: Optional[str] = None,
    conn=Depends(get_conn)
):
    """
    Create a new meeting.
    
    Args:
        client_id: The client ID
        advisor_id: The advisor ID
        meeting_type: Type of meeting (default: "General")
        meeting_status: Initial status (default: "Started")
        meeting_id: Optional custom meeting ID (auto-generated if not provided)
    
    Returns:
        Created meeting details
    """
    # Generate meeting_id if not provided
    if not meeting_id:
        meeting_id = str(uuid4())
    
    result = meeting_service.create_meeting(
        meeting_id=meeting_id,
        client_id=client_id,
        advisor_id=advisor_id,
        meeting_type=meeting_type,
        status=meeting_status,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create meeting")
        )
    
    return {
        "success": True,
        "message": "Meeting created successfully",
        "meeting_id": meeting_id,
        "client_id": client_id,
        "advisor_id": advisor_id,
        "meeting_type": meeting_type,
        "status": meeting_status
    }


@router.get("/{meeting_id}")
async def get_meeting_details(meeting_id: str, conn=Depends(get_conn)):
    """
    Get complete meeting details (meeting + details + client/advisor info).
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Complete meeting information
    """
    result = meeting_service.get_meeting_full(meeting_id, conn=conn)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    return {
        "success": True,
        "meeting": result
    }


@router.get("/{meeting_id}/basic")
async def get_meeting_basic(meeting_id: str, conn=Depends(get_conn)):
    """
    Get basic meeting information (from meetings table only).
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Basic meeting record
    """
    meeting = meeting_service.get_meeting(meeting_id, conn=conn)
    
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    return {
        "success": True,
        "meeting": meeting
    }


@router.patch("/{meeting_id}/status")
async def update_meeting_status(
    meeting_id: str,
    new_status: str,
    conn=Depends(get_conn)
):
    """
    Update meeting status.
    
    Args:
        meeting_id: The meeting ID
        new_status: The new status (e.g., "Started", "In Progress", "Completed", "Cancelled")
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_meeting_status(meeting_id, new_status, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update meeting status")
        )
    
    return {
        "success": True,
        "message": f"Meeting status updated to '{new_status}'",
        "meeting_id": meeting_id,
        "status": new_status
    }


@router.patch("/{meeting_id}/type")
async def update_meeting_type(
    meeting_id: str,
    meeting_type: str,
    conn=Depends(get_conn)
):
    """
    Update meeting type.
    
    Args:
        meeting_id: The meeting ID
        meeting_type: The new meeting type
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_meeting_type(meeting_id, meeting_type, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update meeting type")
        )
    
    return {
        "success": True,
        "message": "Meeting type updated successfully",
        "meeting_id": meeting_id,
        "meeting_type": meeting_type
    }


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str, conn=Depends(get_conn)):
    """
    Delete a meeting (and its details via cascade).
    
    Args:
        meeting_id: The meeting ID to delete
    
    Returns:
        Deletion confirmation
    """
    result = meeting_service.delete_meeting(meeting_id, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete meeting")
        )
    
    return {
        "success": True,
        "message": "Meeting deleted successfully",
        "meeting_id": meeting_id
    }


# ==================== MEETING DETAILS ENDPOINTS ====================

@router.patch("/{meeting_id}/details")
async def update_meeting_details(
    meeting_id: str,
    transcript: Optional[str] = None,
    summary: Optional[str] = None,
    recommendations: Optional[str] = None,
    questions: Optional[str] = None,
    advisor_notes: Optional[str] = None,
    conn=Depends(get_conn)
):
    """
    Update meeting details.
    
    Args:
        meeting_id: The meeting ID
        transcript: Meeting transcript (optional)
        summary: Meeting summary (optional)
        recommendations: Recommendations (optional)
        questions: Questions (optional)
        advisor_notes: Advisor notes (optional)
    
    Returns:
        Update confirmation
    """
    updates = {}
    if transcript is not None:
        updates["transcript"] = transcript
    if summary is not None:
        updates["summary"] = summary
    if recommendations is not None:
        updates["recommendations"] = recommendations
    if questions is not None:
        updates["questions"] = questions
    if advisor_notes is not None:
        updates["advisor_notes"] = advisor_notes
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    result = meeting_service.update_meeting_detail(meeting_id=meeting_id, conn=conn, **updates)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update meeting details")
        )
    
    return {
        "success": True,
        "message": "Meeting details updated successfully",
        "meeting_id": meeting_id,
        "updated_fields": list(updates.keys())
    }


@router.patch("/{meeting_id}/transcript")
async def update_meeting_transcript(
    meeting_id: str,
    transcript: str,
    append: bool = False,
    conn=Depends(get_conn)
):
    """
    Update or append to meeting transcript.
    
    Args:
        meeting_id: The meeting ID
        transcript: Transcript content
        append: If True, append to existing transcript; if False, replace (default: False)
    
    Returns:
        Update confirmation
    """
    if append:
        result = meeting_service.append_to_transcript(meeting_id, transcript, conn=conn)
    else:
        result = meeting_service.update_meeting_transcript(meeting_id, transcript, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update transcript")
        )
    
    return {
        "success": True,
        "message": "Transcript updated successfully" if not append else "Transcript appended successfully",
        "meeting_id": meeting_id
    }


@router.patch("/{meeting_id}/summary")
async def update_meeting_summary(
    meeting_id: str,
    summary: str,
    conn=Depends(get_conn)
):
    """
    Update meeting summary.
    
    Args:
        meeting_id: The meeting ID
        summary: Summary content
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_meeting_summary(meeting_id, summary, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update summary")
        )
    
    return {
        "success": True,
        "message": "Summary updated successfully",
        "meeting_id": meeting_id
    }


@router.patch("/{meeting_id}/recommendations")
async def update_meeting_recommendations(
    meeting_id: str,
    recommendations: str,
    conn=Depends(get_conn)
):
    """
    Update meeting recommendations.
    
    Args:
        meeting_id: The meeting ID
        recommendations: Recommendations content
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_meeting_recommendations(meeting_id, recommendations, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update recommendations")
        )
    
    return {
        "success": True,
        "message": "Recommendations updated successfully",
        "meeting_id": meeting_id
    }


@router.patch("/{meeting_id}/notes")
async def update_advisor_notes(
    meeting_id: str,
    notes: str,
    conn=Depends(get_conn)
):
    """
    Update advisor notes for a meeting.
    
    Args:
        meeting_id: The meeting ID
        notes: Advisor notes
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_advisor_notes(meeting_id, notes, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update advisor notes")
        )
    
    return {
        "success": True,
        "message": "Advisor notes updated successfully",
        "meeting_id": meeting_id
    }


# ==================== QUESTIONS MANAGEMENT ====================

@router.get("/{meeting_id}/questions")
async def get_meeting_questions(meeting_id: str, conn=Depends(get_conn)):
    """
    Get questions for a meeting.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Questions data
    """
    questions = meeting_service.get_meeting_questions(meeting_id, conn=conn)
    
    if questions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for this meeting"
        )
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "questions": questions
    }


@router.patch("/{meeting_id}/questions")
async def update_meeting_questions(
    meeting_id: str,
    questions: dict,
    conn=Depends(get_conn)
):
    """
    Update questions for a meeting.
    
    Args:
        meeting_id: The meeting ID
        questions: Questions data (as JSON object)
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_meeting_questions(meeting_id, questions, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update questions")
        )
    
    return {
        "success": True,
        "message": "Questions updated successfully",
        "meeting_id": meeting_id
    }


@router.patch("/{meeting_id}/questions/status")
async def update_question_status(
    meeting_id: str,
    question_status: str,
    conn=Depends(get_conn)
):
    """
    Update status in questions field.
    
    Args:
        meeting_id: The meeting ID
        question_status: Status to set in questions object
    
    Returns:
        Update confirmation
    """
    result = meeting_service.add_question_status_to_meeting(meeting_id, question_status, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update question status")
        )
    
    return {
        "success": True,
        "message": "Question status updated successfully",
        "meeting_id": meeting_id,
        "status": question_status
    }


# ==================== LIST ENDPOINTS ====================

@router.get("/client/{client_id}/list")
async def list_client_meetings(client_id: str, conn=Depends(get_conn)):
    """
    List all meetings for a specific client.
    
    Args:
        client_id: The client ID
    
    Returns:
        List of meetings for the client
    """
    meetings = meeting_service.list_meetings_by_client(client_id, conn=conn)
    
    return {
        "success": True,
        "client_id": client_id,
        "total_meetings": len(meetings),
        "meetings": meetings
    }


@router.get("/advisor/{advisor_id}/list")
async def list_advisor_meetings(advisor_id: str, conn=Depends(get_conn)):
    """
    List all meetings for a specific advisor.
    
    Args:
        advisor_id: The advisor ID
    
    Returns:
        List of meetings for the advisor
    """
    meetings = meeting_service.list_meetings_by_advisor(advisor_id, conn=conn)
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "total_meetings": len(meetings),
        "meetings": meetings
    }


# ==================== TRANSCRIPT AGGREGATOR ENDPOINTS ====================

@router.post("/{meeting_id}/transcript/segment")
async def add_transcript_segment(
    meeting_id: str,
    transcript: str,
    start_datetime: Optional[datetime] = None,
    conn=Depends(get_conn)
):
    """
    Add a transcript segment to the meeting.
    
    Args:
        meeting_id: The meeting ID
        transcript: Transcript text segment
        start_datetime: When this segment was captured (optional, defaults to NOW)
    
    Returns:
        Confirmation with segment index
    """
    result = meeting_service.add_transcript_segment(
        meeting_id=meeting_id,
        transcript=transcript,
        start_datetime=start_datetime,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to add transcript segment")
        )
    
    return {
        "success": True,
        "message": "Transcript segment added successfully",
        "meeting_id": meeting_id,
        "segment_index": result.get("segment_index"),
        "start_datetime": result.get("start_datetime")
    }


@router.get("/{meeting_id}/transcript/segments")
async def get_transcript_segments(meeting_id: str, conn=Depends(get_conn)):
    """
    Get all transcript segments for a meeting.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        List of transcript segments ordered by index
    """
    segments = meeting_service.get_transcript_segments(meeting_id, conn=conn)
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "total_segments": len(segments),
        "segments": segments
    }


@router.get("/{meeting_id}/transcript/segments/{segment_index}")
async def get_transcript_segment_by_index(
    meeting_id: str,
    segment_index: int,
    conn=Depends(get_conn)
):
    """
    Get a specific transcript segment by its index.
    
    Args:
        meeting_id: The meeting ID
        segment_index: The segment index
    
    Returns:
        Transcript segment
    """
    segment = meeting_service.get_transcript_segment_by_index(
        meeting_id=meeting_id,
        segment_index=segment_index,
        conn=conn
    )
    
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript segment not found"
        )
    
    return {
        "success": True,
        "segment": segment
    }


@router.get("/{meeting_id}/transcript/segments/range")
async def get_transcript_segments_by_time(
    meeting_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    conn=Depends(get_conn)
):
    """
    Get transcript segments within a time range.
    
    Args:
        meeting_id: The meeting ID
        start_time: Start datetime (optional)
        end_time: End datetime (optional)
    
    Returns:
        List of transcript segments within time range
    """
    segments = meeting_service.get_transcript_segments_by_time(
        meeting_id=meeting_id,
        start_time=start_time,
        end_time=end_time,
        conn=conn
    )
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "start_time": start_time,
        "end_time": end_time,
        "total_segments": len(segments),
        "segments": segments
    }


@router.post("/{meeting_id}/transcript/aggregate")
async def aggregate_meeting_transcripts(
    meeting_id: str,
    separator: str = "\n",
    save_to_details: bool = True,
    conn=Depends(get_conn)
):
    """
    Aggregate all transcript segments into a single transcript.
    
    Args:
        meeting_id: The meeting ID
        separator: String to join segments (default: newline)
        save_to_details: If True, save to meeting_details.transcript (default: True)
    
    Returns:
        Aggregated transcript
    """
    result = meeting_service.aggregate_meeting_transcripts(
        meeting_id=meeting_id,
        separator=separator,
        save_to_details=save_to_details,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to aggregate transcripts")
        )
    
    return result


@router.patch("/{meeting_id}/transcript/segments/{segment_index}")
async def update_transcript_segment(
    meeting_id: str,
    segment_index: int,
    transcript: Optional[str] = None,
    start_datetime: Optional[datetime] = None,
    conn=Depends(get_conn)
):
    """
    Update a specific transcript segment.
    
    Args:
        meeting_id: The meeting ID
        segment_index: The segment index to update
        transcript: New transcript text (optional)
        start_datetime: New start datetime (optional)
    
    Returns:
        Update confirmation
    """
    result = meeting_service.update_transcript_segment(
        meeting_id=meeting_id,
        segment_index=segment_index,
        transcript=transcript,
        start_datetime=start_datetime,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update transcript segment")
        )
    
    return {
        "success": True,
        "message": "Transcript segment updated successfully",
        "meeting_id": meeting_id,
        "segment_index": segment_index
    }


@router.delete("/{meeting_id}/transcript/segments/{segment_index}")
async def delete_transcript_segment(
    meeting_id: str,
    segment_index: int,
    conn=Depends(get_conn)
):
    """
    Delete a specific transcript segment.
    
    Args:
        meeting_id: The meeting ID
        segment_index: The segment index to delete
    
    Returns:
        Deletion confirmation
    """
    result = meeting_service.delete_transcript_segment(
        meeting_id=meeting_id,
        segment_index=segment_index,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete transcript segment")
        )
    
    return {
        "success": True,
        "message": "Transcript segment deleted successfully",
        "meeting_id": meeting_id,
        "segment_index": segment_index
    }


@router.delete("/{meeting_id}/transcript/segments")
async def delete_all_transcript_segments(meeting_id: str, conn=Depends(get_conn)):
    """
    Delete ALL transcript segments for a meeting.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Deletion confirmation with count
    """
    result = meeting_service.delete_transcript_segments(meeting_id, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete transcript segments")
        )
    
    return {
        "success": True,
        "message": result.get("message"),
        "meeting_id": meeting_id,
        "deleted_count": result.get("deleted_count", 0)
    }


@router.get("/{meeting_id}/transcript/count")
async def count_transcript_segments(meeting_id: str, conn=Depends(get_conn)):
    """
    Count the number of transcript segments for a meeting.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Segment count
    """
    count = meeting_service.count_transcript_segments(meeting_id, conn=conn)
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "segment_count": count
    }