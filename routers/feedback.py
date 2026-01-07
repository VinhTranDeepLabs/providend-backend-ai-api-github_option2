from fastapi import APIRouter, Request, Depends, status, HTTPException
from typing import Optional
from services.feedback_service import FeedbackService

router = APIRouter()
feedback_service = FeedbackService()


def get_conn(request: Request):
    """Return the shared DB connection stored on app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


# ==================== POST METHODS ====================

@router.post("/")
async def create_feedback(
    meeting_id: str,
    feedback: str,
    feedback_on: str = None,  # Add this parameter
    conn=Depends(get_conn)
):
    """
    Create a new feedback entry for a meeting.
    
    Args:
        meeting_id: The meeting ID
        feedback: Feedback text content
        feedback_on: What the feedback is about (e.g., "Summary", "Transcript", etc.)
    
    Returns:
        Created feedback details
    """
    result = feedback_service.create_feedback(
        meeting_id=meeting_id,
        feedback=feedback,
        feedback_on=feedback_on,  # Add this
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create feedback")
        )
    
    return {
        "success": True,
        "message": "Feedback created successfully",
        "feedback_index": result.get("feedback_index"),
        "meeting_id": result.get("meeting_id"),
        "feedback": result.get("feedback"),
        "feedback_on": result.get("feedback_on"),  # Add this
        "edit_datetime": result.get("edit_datetime")
    }


# ==================== GET METHODS ====================

@router.get("/{feedback_index}")
async def get_feedback(
    feedback_index: int,
    conn=Depends(get_conn)
):
    """
    Get a single feedback entry by index.
    
    Args:
        feedback_index: The feedback index
    
    Returns:
        Feedback details
    """
    result = feedback_service.get_feedback(feedback_index, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "Feedback not found")
        )
    
    return {
        "success": True,
        "feedback": result.get("feedback")
    }


@router.get("/meeting/{meeting_id}")
async def get_meeting_feedbacks(
    meeting_id: str,
    conn=Depends(get_conn)
):
    """
    Get all feedback entries for a specific meeting.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        List of feedbacks for the meeting
    """
    result = feedback_service.get_meeting_feedbacks(meeting_id, conn=conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "Meeting not found")
        )
    
    return {
        "success": True,
        "meeting_id": result.get("meeting_id"),
        "total_feedbacks": result.get("total_feedbacks"),
        "feedbacks": result.get("feedbacks")
    }


# ==================== PATCH METHODS ====================

@router.patch("/{feedback_index}")
async def update_feedback(
    feedback_index: int,
    feedback: str = None,
    feedback_on: str = None,  # Add this parameter
    conn=Depends(get_conn)
):
    """
    Update feedback text and/or feedback_on field.
    
    Args:
        feedback_index: The feedback index
        feedback: New feedback text (optional)
        feedback_on: What the feedback is about (optional)
    
    Returns:
        Updated feedback details
    """
    result = feedback_service.update_feedback(
        feedback_index=feedback_index,
        feedback=feedback,
        feedback_on=feedback_on,  # Add this
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update feedback")
        )
    
    return {
        "success": True,
        "message": "Feedback updated successfully",
        "feedback_index": result.get("feedback_index"),
        "meeting_id": result.get("meeting_id"),
        "feedback": result.get("feedback"),
        "feedback_on": result.get("feedback_on"),  # Add this
        "edit_datetime": result.get("edit_datetime")
    }


# ==================== DELETE METHODS ====================

@router.delete("/{feedback_index}")
async def delete_feedback(
    feedback_index: int,
    conn=Depends(get_conn)
):
    """
    Delete a feedback entry.
    
    Args:
        feedback_index: The feedback index
    
    Returns:
        Deletion confirmation
    """
    result = feedback_service.delete_feedback(
        feedback_index=feedback_index,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to delete feedback")
        )
    
    return {
        "success": True,
        "message": "Feedback deleted successfully",
        "feedback_index": feedback_index
    }