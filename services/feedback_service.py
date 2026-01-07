from typing import Dict, List, Optional, Any
from utils.db_utils import DatabaseUtils


class FeedbackService:
    """Service layer for feedback-related operations"""
    
    def __init__(self):
        pass
    
    def create_feedback(self, meeting_id: str, feedback: str, feedback_on: str = None, 
                    conn=None) -> Dict[str, Any]:
        """
        Create a new feedback entry for a meeting.
        
        Args:
            meeting_id: The meeting ID
            feedback: Feedback text content
            feedback_on: What the feedback is about (e.g., "Summary", "Transcript", etc.)
            conn: Database connection
        
        Returns:
            Dict with success status and feedback details
        """
        db = DatabaseUtils(conn)
        
        # Verify meeting exists
        meeting = db.get_meeting(meeting_id)
        if not meeting:
            return {
                "success": False,
                "message": f"Meeting not found: {meeting_id}"
            }
        
        # Create feedback
        result = db.create_feedback(meeting_id=meeting_id, feedback=feedback, 
                                    feedback_on=feedback_on)
        
        return result
    
    def get_feedback(self, feedback_index: int, conn=None) -> Dict[str, Any]:
        """
        Get a single feedback entry by index.
        
        Args:
            feedback_index: The feedback index
            conn: Database connection
        
        Returns:
            Dict with feedback details or error
        """
        db = DatabaseUtils(conn)
        feedback = db.get_feedback(feedback_index)
        
        if not feedback:
            return {
                "success": False,
                "message": "Feedback not found"
            }
        
        return {
            "success": True,
            "feedback": feedback
        }
    
    def get_meeting_feedbacks(self, meeting_id: str, conn=None) -> Dict[str, Any]:
        """
        Get all feedback entries for a specific meeting.
        
        Args:
            meeting_id: The meeting ID
            conn: Database connection
        
        Returns:
            Dict with list of feedbacks
        """
        db = DatabaseUtils(conn)
        
        # Verify meeting exists
        meeting = db.get_meeting(meeting_id)
        if not meeting:
            return {
                "success": False,
                "message": f"Meeting not found: {meeting_id}",
                "feedbacks": []
            }
        
        feedbacks = db.list_feedbacks(meeting_id=meeting_id)
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "total_feedbacks": len(feedbacks),
            "feedbacks": feedbacks
        }
    
    def update_feedback(self, feedback_index: int, feedback: str = None, 
                    feedback_on: str = None, conn=None) -> Dict[str, Any]:
        """
        Update feedback text and/or feedback_on field.
        
        Args:
            feedback_index: The feedback index
            feedback: New feedback text (optional)
            feedback_on: What the feedback is about (optional)
            conn: Database connection
        
        Returns:
            Dict with success status and updated feedback
        """
        db = DatabaseUtils(conn)
        
        # Check if feedback exists
        existing = db.get_feedback(feedback_index)
        if not existing:
            return {
                "success": False,
                "message": "Feedback not found"
            }
        
        # Update feedback
        result = db.update_feedback(feedback_index=feedback_index, feedback=feedback,
                                feedback_on=feedback_on)
        
        return result
    
    def delete_feedback(self, feedback_index: int, conn=None) -> Dict[str, Any]:
        """
        Delete a feedback entry.
        
        Args:
            feedback_index: The feedback index
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        
        # Check if feedback exists
        existing = db.get_feedback(feedback_index)
        if not existing:
            return {
                "success": False,
                "message": "Feedback not found"
            }
        
        # Delete feedback
        result = db.delete_feedback(feedback_index=feedback_index)
        
        return result