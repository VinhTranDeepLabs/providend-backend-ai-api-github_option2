from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from utils.db_utils import DatabaseUtils


class MeetingService:
    """Service layer for meeting-related operations.
    
    Note: In the new schema, meeting_id is the primary key for meetings table.
    Each meeting is a separate record (not stored as array in client record).
    """

    def create_meeting(self, meeting_id: str, client_id: str, advisor_id: str, 
                      meeting_type: str = "General", status: str = "Started", 
                      conn=None) -> Dict[str, Any]:
        """Create a single meeting record.
        
        Args:
            meeting_id: Unique meeting identifier
            client_id: Client ID (FK)
            advisor_id: Advisor ID (FK)
            meeting_type: Type of meeting (e.g., "Annual Review", "Initial Consultation")
            status: Meeting status (e.g., "Started", "In Progress", "Completed")
            conn: Database connection
        
        Returns:
            Dict with success status and message
        """
        db = DatabaseUtils(conn)
        
        # Create meeting in meetings table
        result = db.create_meeting(
            meeting_id=meeting_id,
            client_id=client_id,
            advisor_id=advisor_id,
            meeting_type=meeting_type,
            status=status
        )
        
        if not result["success"]:
            return result
        
        # Optionally create empty meeting_details record
        # (or wait until there's actual content to store)
        details_result = db.create_meeting_detail(meeting_id=meeting_id)
        
        return {
            "success": True,
            "message": f"Meeting created successfully",
            "meeting_id": meeting_id,
            "client_id": client_id,
            "advisor_id": advisor_id,
            "meeting_type": meeting_type,
            "status": status
        }

    def get_meeting(self, meeting_id: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get meeting record by meeting_id"""
        db = DatabaseUtils(conn)
        return db.get_meeting(meeting_id)

    def get_meeting_detail(self, meeting_id: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get meeting details by meeting_id"""
        db = DatabaseUtils(conn)
        return db.get_meeting_detail(meeting_id)

    def get_meeting_full(self, meeting_id: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get complete meeting information (meeting + details + client info).
        
        Returns:
            Combined dict with meeting, details, and client information
        """
        db = DatabaseUtils(conn)
        
        # Get meeting record
        meeting = db.get_meeting(meeting_id)
        if not meeting:
            return None
        
        # Get meeting details
        details = db.get_meeting_detail(meeting_id) or {}
        
        # Get client info
        client = db.get_client(meeting["client_id"]) or {}
        
        # Get advisor info
        advisor = db.get_advisor(meeting["advisor_id"]) or {}
        
        return {
            "meeting_id": meeting_id,
            "meeting_type": meeting.get("meeting_type"),
            "status": meeting.get("status"),
            "created_datetime": meeting.get("created_datetime"),
            "client_id": meeting.get("client_id"),
            "client_name": client.get("name"),
            "advisor_id": meeting.get("advisor_id"),
            "advisor_name": advisor.get("name"),
            "transcript": details.get("transcript"),
            "summary": details.get("summary"),
            "recommendations": details.get("recommendations"),
            "questions": details.get("questions"),
            "question_tracker": details.get("question_tracker"),
            "advisor_notes": details.get("advisor_notes"),
            "updated_datetime": details.get("updated_datetime")
        }

    def update_meeting_status(self, meeting_id: str, status: str, conn=None) -> Dict[str, Any]:
        """Update meeting status in meetings table.
        
        Args:
            meeting_id: Meeting identifier
            status: New status (e.g., "Started", "In Progress", "Completed", "Cancelled")
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        return db.update_meeting(meeting_id=meeting_id, status=status)

    def update_meeting_type(self, meeting_id: str, meeting_type: str, conn=None) -> Dict[str, Any]:
        """Update meeting type in meetings table"""
        db = DatabaseUtils(conn)
        return db.update_meeting(meeting_id=meeting_id, meeting_type=meeting_type)

    def update_meeting_detail(self, meeting_id: str, conn=None, **updates) -> Dict[str, Any]:
        """Update meeting_details record.
        
        Args:
            meeting_id: Meeting identifier
            **updates: Fields to update (transcript, summary, recommendations, questions, advisor_notes, question_tracker)
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        return db.update_meeting_detail(meeting_id=meeting_id, **updates)

    def create_meeting_detail(self, meeting_id: str, transcript: str = None, 
                             summary: str = None, recommendations: str = None, 
                             questions: str = None, advisor_notes: str = None, 
                             question_tracker: str = None, conn=None) -> Dict[str, Any]:
        """Create or update meeting_details record"""
        db = DatabaseUtils(conn)
        return db.create_meeting_detail(
            meeting_id=meeting_id,
            transcript=transcript,
            summary=summary,
            recommendations=recommendations,
            questions=questions,
            advisor_notes=advisor_notes,
            question_tracker=question_tracker
        )

    def delete_meeting(self, meeting_id: str, conn=None) -> Dict[str, Any]:
        """Delete a meeting and its details (cascades automatically)"""
        db = DatabaseUtils(conn)
        return db.delete_meeting(meeting_id=meeting_id)

    def list_meetings_by_client(self, client_id: str, conn=None) -> List[Dict[str, Any]]:
        """List all meetings for a specific client"""
        db = DatabaseUtils(conn)
        return db.list_meetings(client_id=client_id)

    def list_meetings_by_advisor(self, advisor_id: str, conn=None) -> List[Dict[str, Any]]:
        """List all meetings for a specific advisor"""
        db = DatabaseUtils(conn)
        return db.list_meetings(advisor_id=advisor_id)

    # ==================== QUESTIONS MANAGEMENT ====================
    
    def get_meeting_questions(self, meeting_id: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get questions from meeting_details.
        
        Returns parsed questions object if stored as JSON, or raw string.
        """
        details = self.get_meeting_detail(meeting_id, conn)
        if not details:
            return None
        
        questions_raw = details.get("questions")
        if not questions_raw:
            return None
        
        # Try to parse as JSON
        try:
            questions_obj = json.loads(questions_raw) if isinstance(questions_raw, str) else questions_raw
            return questions_obj
        except Exception:
            return {"raw": questions_raw}

    def update_meeting_questions(self, meeting_id: str, questions: Any, conn=None) -> Dict[str, Any]:
        """Update questions in meeting_details.
        
        Args:
            meeting_id: Meeting identifier
            questions: Questions data (will be JSON-encoded if dict/list)
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        
        # Convert to JSON string if it's a dict or list
        if isinstance(questions, (dict, list)):
            questions_str = json.dumps(questions)
        else:
            questions_str = questions
        
        return db.update_meeting_detail(meeting_id=meeting_id, questions=questions_str)

    def add_question_status_to_meeting(self, meeting_id: str, status: str, conn=None) -> Dict[str, Any]:
        """Add status to questions field in meeting_details.
        
        This merges status into existing questions JSON object.
        """
        # Get existing questions
        questions_obj = self.get_meeting_questions(meeting_id, conn) or {}
        
        # Add status
        questions_obj["status"] = status
        
        # Update
        return self.update_meeting_questions(meeting_id, questions_obj, conn)

    # ==================== TRANSCRIPT MANAGEMENT ====================
    
    def update_meeting_transcript(self, meeting_id: str, transcript: str, conn=None) -> Dict[str, Any]:
        """Update transcript in meeting_details"""
        db = DatabaseUtils(conn)
        return db.update_meeting_detail(meeting_id=meeting_id, transcript=transcript)

    def append_to_transcript(self, meeting_id: str, new_content: str, conn=None) -> Dict[str, Any]:
        """Append content to existing transcript"""
        details = self.get_meeting_detail(meeting_id, conn)
        
        if not details:
            # Create new details with this transcript
            return self.create_meeting_detail(meeting_id=meeting_id, transcript=new_content, conn=conn)
        
        existing_transcript = details.get("transcript") or ""
        updated_transcript = existing_transcript + "\n" + new_content if existing_transcript else new_content
        
        return self.update_meeting_transcript(meeting_id, updated_transcript, conn)

    # ==================== SUMMARY & RECOMMENDATIONS ====================
    
    def update_meeting_summary(self, meeting_id: str, summary: str, conn=None) -> Dict[str, Any]:
        """Update summary in meeting_details"""
        db = DatabaseUtils(conn)
        return db.update_meeting_detail(meeting_id=meeting_id, summary=summary)

    def update_meeting_recommendations(self, meeting_id: str, recommendations: str, conn=None) -> Dict[str, Any]:
        """Update recommendations in meeting_details"""
        db = DatabaseUtils(conn)
        return db.update_meeting_detail(meeting_id=meeting_id, recommendations=recommendations)

    def update_advisor_notes(self, meeting_id: str, notes: str, conn=None) -> Dict[str, Any]:
        """Update advisor notes in meeting_details"""
        db = DatabaseUtils(conn)
        return db.update_meeting_detail(meeting_id=meeting_id, advisor_notes=notes)
    
    # ==================== QUESTION TRACKER METHODS ====================
    
    def get_meeting_tracker(self, meeting_id: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get question_tracker from meeting_details.
        
        Args:
            meeting_id: Meeting identifier
            conn: Database connection
        
        Returns:
            Parsed question_tracker object or None
        """
        details = self.get_meeting_detail(meeting_id, conn)
        if not details:
            return None
        
        tracker_raw = details.get("question_tracker")
        if not tracker_raw:
            return None
        
        # Try to parse as JSON
        try:
            tracker_obj = json.loads(tracker_raw) if isinstance(tracker_raw, str) else tracker_raw
            return tracker_obj
        except Exception:
            return None
    
    def update_meeting_tracker(self, meeting_id: str, tracker_data: Dict[str, Any], conn=None) -> Dict[str, Any]:
        """Update question_tracker in meeting_details.
        
        Args:
            meeting_id: Meeting identifier
            tracker_data: Question tracker data (dict with sections and Q&A status)
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        
        # Convert to JSON string
        tracker_str = json.dumps(tracker_data) if isinstance(tracker_data, dict) else tracker_data
        
        return db.update_meeting_detail(meeting_id=meeting_id, question_tracker=tracker_str)
    
    # ==================== TRANSCRIPT AGGREGATOR METHODS ====================
    
    def add_transcript_segment(self, meeting_id: str, transcript: str, 
                              start_datetime: datetime = None, conn=None) -> Dict[str, Any]:
        """
        Add a transcript segment to the transcript_aggregator table.
        
        Args:
            meeting_id: Meeting identifier
            transcript: Transcript text segment
            start_datetime: When this segment was captured (optional, defaults to NOW)
            conn: Database connection
        
        Returns:
            Dict with success status and segment info
        """
        db = DatabaseUtils(conn)
        return db.add_transcript_segment(
            meeting_id=meeting_id,
            transcript=transcript,
            start_datetime=start_datetime
        )
    
    def get_transcript_segments(self, meeting_id: str, conn=None) -> List[Dict[str, Any]]:
        """
        Get all transcript segments for a meeting, ordered by index.
        
        Args:
            meeting_id: Meeting identifier
            conn: Database connection
        
        Returns:
            List of transcript segments
        """
        db = DatabaseUtils(conn)
        return db.get_transcript_segments(meeting_id)
    
    def get_transcript_segment_by_index(self, meeting_id: str, segment_index: int, 
                                       conn=None) -> Optional[Dict[str, Any]]:
        """
        Get a specific transcript segment by its index.
        
        Args:
            meeting_id: Meeting identifier
            segment_index: Segment index
            conn: Database connection
        
        Returns:
            Transcript segment or None
        """
        db = DatabaseUtils(conn)
        return db.get_transcript_segment_by_index(meeting_id, segment_index)
    
    def get_transcript_segments_by_time(self, meeting_id: str, 
                                       start_time: datetime = None,
                                       end_time: datetime = None, 
                                       conn=None) -> List[Dict[str, Any]]:
        """
        Get transcript segments within a time range.
        
        Args:
            meeting_id: Meeting identifier
            start_time: Start datetime (optional)
            end_time: End datetime (optional)
            conn: Database connection
        
        Returns:
            List of transcript segments within time range
        """
        db = DatabaseUtils(conn)
        return db.get_transcript_segments_by_time(meeting_id, start_time, end_time)
    
    def aggregate_meeting_transcripts(self, meeting_id: str, separator: str = "\n", 
                                     save_to_details: bool = True, 
                                     conn=None) -> Dict[str, Any]:
        """
        Aggregate all transcript segments into a single transcript.
        
        Args:
            meeting_id: Meeting identifier
            separator: String to join segments (default: newline)
            save_to_details: If True, save aggregated transcript to meeting_details
            conn: Database connection
        
        Returns:
            Dict with aggregated transcript and metadata
        """
        db = DatabaseUtils(conn)
        
        # Get aggregated transcript
        full_transcript = db.aggregate_transcripts(meeting_id, separator)
        
        if full_transcript is None:
            return {
                "success": False,
                "message": "No transcript segments found for this meeting",
                "meeting_id": meeting_id
            }
        
        # Optionally save to meeting_details
        if save_to_details:
            update_result = db.update_meeting_detail(
                meeting_id=meeting_id,
                transcript=full_transcript
            )
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to save aggregated transcript: {update_result.get('message')}",
                    "transcript": full_transcript
                }
        
        # Get segment count
        segment_count = db.count_transcript_segments(meeting_id)
        
        return {
            "success": True,
            "message": "Transcripts aggregated successfully",
            "meeting_id": meeting_id,
            "transcript": full_transcript,
            "segment_count": segment_count,
            "saved_to_details": save_to_details
        }
    
    def update_transcript_segment(self, meeting_id: str, segment_index: int,
                                 transcript: str = None, start_datetime: datetime = None,
                                 conn=None) -> Dict[str, Any]:
        """
        Update a specific transcript segment.
        
        Args:
            meeting_id: Meeting identifier
            segment_index: Segment index to update
            transcript: New transcript text (optional)
            start_datetime: New start datetime (optional)
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        return db.update_transcript_segment(
            meeting_id=meeting_id,
            segment_index=segment_index,
            transcript=transcript,
            start_datetime=start_datetime
        )
    
    def delete_transcript_segment(self, meeting_id: str, segment_index: int, 
                                 conn=None) -> Dict[str, Any]:
        """
        Delete a specific transcript segment.
        
        Args:
            meeting_id: Meeting identifier
            segment_index: Segment index to delete
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        return db.delete_transcript_segment(meeting_id, segment_index)
    
    def delete_transcript_segments(self, meeting_id: str, conn=None) -> Dict[str, Any]:
        """
        Delete ALL transcript segments for a meeting.
        
        Args:
            meeting_id: Meeting identifier
            conn: Database connection
        
        Returns:
            Dict with success status and deleted count
        """
        db = DatabaseUtils(conn)
        return db.delete_transcript_segments(meeting_id)
    
    def count_transcript_segments(self, meeting_id: str, conn=None) -> int:
        """
        Count the number of transcript segments for a meeting.
        
        Args:
            meeting_id: Meeting identifier
            conn: Database connection
        
        Returns:
            Number of segments
        """
        db = DatabaseUtils(conn)
        return db.count_transcript_segments(meeting_id)