import re
from difflib import SequenceMatcher
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
                  meeting_name: str = None, meeting_type: str = "General", 
                  status: str = "Started", conn=None) -> Dict[str, Any]:
        """Create a single meeting record.
        
        Args:
            meeting_id: Unique meeting identifier
            client_id: Client ID (FK)
            advisor_id: Advisor ID (FK)
            meeting_name: Name/title of the meeting (defaults to "Scheduled meeting" in DB)
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
            meeting_name=meeting_name,
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
            "meeting_name": meeting_name or "Scheduled meeting",
            "meeting_type": meeting_type,
            "status": status
        }
    
    def create_quick_meeting(self, meeting_id: str, advisor_id: str, 
                            meeting_name: str = None, meeting_type: str = "General", 
                            status: str = "Started", conn=None) -> Dict[str, Any]:
        """Create a quick meeting without client_id (can be assigned later).
        
        Args:
            meeting_id: Unique meeting identifier
            advisor_id: Advisor ID (FK)
            meeting_name: Name/title of the meeting (defaults to "Scheduled meeting" in DB)
            meeting_type: Type of meeting (e.g., "Annual Review", "Initial Consultation")
            status: Meeting status (e.g., "Started", "In Progress", "Completed")
            conn: Database connection
        
        Returns:
            Dict with success status and message
        """
        db = DatabaseUtils(conn)
        
        # Create quick meeting in meetings table (no client_id)
        result = db.create_quick_meeting(
            meeting_id=meeting_id,
            advisor_id=advisor_id,
            meeting_name=meeting_name,
            meeting_type=meeting_type,
            status=status
        )
        
        if not result["success"]:
            return result
        
        # Optionally create empty meeting_details record
        details_result = db.create_meeting_detail(meeting_id=meeting_id)
        
        return {
            "success": True,
            "message": f"Quick meeting created successfully",
            "meeting_id": meeting_id,
            "client_id": None,
            "advisor_id": advisor_id,
            "meeting_name": meeting_name or "Quick meeting",
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
        
        # Get client info (handle NULL client_id for quick meetings)
        client_id = meeting.get("client_id")
        if client_id:
            client = db.get_client(client_id) or {}
            client_name = client.get("name")
        else:
            client_name = None
        
        # Get advisor info
        advisor = db.get_advisor(meeting["advisor_id"]) or {}

        print(meeting)
        
        return {
            "meeting_id": meeting_id,
            "meeting_name": meeting.get("meeting_name"),
            "meeting_type": meeting.get("meeting_type"),
            "status": meeting.get("status"),
            "created_datetime": meeting.get("created_datetime"),
            "client_id": client_id,
            "client_name": client_name,
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
    
    def update_meeting_name(self, meeting_id: str, meeting_name: str, conn=None) -> Dict[str, Any]:
        """Update meeting name in meetings table"""
        db = DatabaseUtils(conn)
        return db.update_meeting(meeting_id=meeting_id, meeting_name=meeting_name)
    
    def assign_client_to_meeting(self, meeting_id: str, client_id: str, conn=None) -> Dict[str, Any]:
        """Assign a client to a meeting (typically used for quick meetings)"""
        db = DatabaseUtils(conn)
        return db.update_meeting(meeting_id=meeting_id, client_id=client_id)

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
    
    def _extract_original_text(self, marked_up_text: str) -> str:
        """
        Extract original text by removing all <del> tags.
        
        Args:
            marked_up_text: Text with HTML markup
        
        Returns:
            Clean text without <del> tags
        """
        if not marked_up_text:
            return ""
        
        # Remove <del>...</del> tags but keep the content inside
        clean_text = re.sub(r'<del>(.*?)</del>', r'\1', marked_up_text, flags=re.DOTALL)
        
        # Ensure we're not double-escaping
        # The text should remain as-is without additional escaping
        return clean_text


    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace for consistent comparison.
        Preserves newlines but normalizes other whitespace.
        
        Args:
            text: Input text
        
        Returns:
            Text with normalized whitespace
        """
        # Split by newlines to preserve them
        lines = text.split('\n')
        # Normalize spaces within each line
        normalized_lines = [' '.join(line.split()) for line in lines]
        # Rejoin with newlines
        return '\n'.join(normalized_lines)


    def _generate_diff_markup(self, original_text: str, new_text: str) -> str:
        """
        Generate word-level diff markup with <del> tags for deletions.
        Combines consecutive deleted words into a single <del> tag.
        
        Args:
            original_text: The original transcript (clean, no markup)
            new_text: The new incoming transcript
        
        Returns:
            Marked-up text with <del> tags for deleted words
        """
        # Normalize whitespace to prevent issues with extra spaces
        original_text = self._normalize_whitespace(original_text)
        new_text = self._normalize_whitespace(new_text)
        
        # Split into words, preserving newlines as separate tokens
        def tokenize(text):
            """Split text into words and newlines."""
            tokens = []
            for line in text.split('\n'):
                words = line.split()
                tokens.extend(words)
                tokens.append('\n')  # Add newline as a token
            # Remove trailing newline if present
            if tokens and tokens[-1] == '\n':
                tokens.pop()
            return tokens
        
        original_tokens = tokenize(original_text)
        new_tokens = tokenize(new_text)
        
        # Use SequenceMatcher for token-level diff
        matcher = SequenceMatcher(None, original_tokens, new_tokens)
        
        result = []
        deleted_buffer = []  # Buffer to accumulate consecutive deleted tokens
        
        def flush_deleted_buffer():
            """Helper to flush accumulated deleted tokens."""
            if deleted_buffer:
                # Join tokens, handling newlines properly
                deleted_text = []
                for token in deleted_buffer:
                    if token == '\n':
                        deleted_text.append('\n')
                    else:
                        deleted_text.append(token)
                
                # Join with spaces, but preserve newlines
                text_parts = []
                current_line = []
                for token in deleted_buffer:
                    if token == '\n':
                        if current_line:
                            text_parts.append(' '.join(current_line))
                        text_parts.append('\n')
                        current_line = []
                    else:
                        current_line.append(token)
                if current_line:
                    text_parts.append(' '.join(current_line))
                
                deleted_str = ''.join(text_parts)
                result.append(f'<del>{deleted_str}</del>')
                deleted_buffer.clear()
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Flush any pending deletions first
                flush_deleted_buffer()
                # Tokens are the same, add them normally
                result.extend(new_tokens[j1:j2])
            
            elif tag == 'replace':
                # Tokens were replaced
                # Add original tokens to deletion buffer
                deleted_buffer.extend(original_tokens[i1:i2])
                # Flush deletions
                flush_deleted_buffer()
                # Add new tokens normally
                result.extend(new_tokens[j1:j2])
            
            elif tag == 'delete':
                # Tokens were deleted from original
                # Add to deletion buffer
                deleted_buffer.extend(original_tokens[i1:i2])
            
            elif tag == 'insert':
                # Flush any pending deletions first
                flush_deleted_buffer()
                # Tokens were added (not in original)
                # Add new tokens normally (no markup)
                result.extend(new_tokens[j1:j2])
        
        # Flush any remaining deletions at the end
        flush_deleted_buffer()
        
        # Reconstruct text from tokens, preserving newlines
        output_parts = []
        current_line = []
        for token in result:
            if token == '\n':
                if current_line:
                    output_parts.append(' '.join(current_line))
                output_parts.append('\n')
                current_line = []
            elif token.startswith('<del>'):
                # Add deletion marker as-is
                if current_line:
                    output_parts.append(' '.join(current_line))
                    current_line = []
                output_parts.append(token)
            else:
                current_line.append(token)
        
        if current_line:
            output_parts.append(' '.join(current_line))
        
        return ''.join(output_parts)


    def update_meeting_transcript(self, meeting_id: str, transcript: str, 
                                created_by: str = "SYSTEM", conn=None) -> Dict[str, Any]:
        """
        Update transcript in meeting_details with diff tracking AND create version.
        
        Args:
            meeting_id: Meeting identifier
            transcript: New transcript content (unescaped, raw string)
            created_by: advisor_id who made the change
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        
        # Get existing meeting details to check if first version
        details = db.get_meeting_detail(meeting_id)
        
        if not details or not details.get("transcript"):
            # First time saving transcript - save as-is and create v1
            result = db.update_meeting_detail(meeting_id=meeting_id, transcript=transcript)
            
            if result.get("success"):
                # Create version 1 (clean, no markup)
                db.create_content_version(
                    meeting_id=meeting_id,
                    content_type='transcript',
                    content=transcript,
                    created_by=created_by
                )
            
            return result
        
        # Not first version - save new clean transcript and reset processing status
        result = db.update_meeting_detail(
            meeting_id=meeting_id, 
            transcript=transcript,
            processing_status='pending',
            processing_retry_count=0,
            processing_error=None
        )
        
        # Create new version with clean transcript
        if result.get("success"):
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='transcript',
                content=transcript,
                created_by=created_by
            )
        
        return result
        

    def store_transcript(self, meeting_id: str, transcript: str, created_by: str = "SYSTEM", conn=None) -> Dict[str, Any]:
        """Store transcript and create a version entry."""
        db = DatabaseUtils(conn)
        result = db.update_meeting_detail(meeting_id=meeting_id, transcript=transcript)
        if result.get("success"):
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='transcript',
                content=transcript,
                created_by=created_by
            )
        return result

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
    
    def update_meeting_summary(self, meeting_id: str, summary: str, 
                            created_by: str = "SYSTEM", conn=None) -> Dict[str, Any]:
        """
        Update summary in meeting_details with diff tracking AND create version.
        
        Args:
            meeting_id: Meeting identifier
            summary: New summary content
            created_by: advisor_id who made the change
            conn: Database connection
        
        Returns:
            Dict with success status
        """
        db = DatabaseUtils(conn)
        
        # Get existing meeting details to check if first version
        details = db.get_meeting_detail(meeting_id)
        
        if not details or not details.get("summary"):
            # First time saving summary - save as-is and create v1
            result = db.update_meeting_detail(meeting_id=meeting_id, summary=summary)
            
            if result.get("success"):
                # Create version 1 (clean, no markup)
                db.create_content_version(
                    meeting_id=meeting_id,
                    content_type='summary',
                    content=summary,
                    created_by=created_by
                )
            
            return result
        
        # Not first version - save new clean summary
        result = db.update_meeting_detail(meeting_id=meeting_id, summary=summary)
        
        # Create new version with clean summary
        if result.get("success"):
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='summary',
                content=summary,
                created_by=created_by
            )
        
        return result

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
                                     created_by: str = "SYSTEM",
                                     conn=None) -> Dict[str, Any]:
        """
        Aggregate all transcript segments into a single transcript AND create v1.
        
        Args:
            meeting_id: Meeting identifier
            separator: String to join segments (default: newline)
            save_to_details: If True, save to meeting_details
            created_by: Who triggered the aggregation
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
            
            # Create version 1 (initial aggregation, clean text)
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='transcript',
                content=full_transcript,
                created_by=created_by
            )
        
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
    

     # ==================== NEW VERSION-RELATED METHODS ====================
    
    def get_content_version_history(self, meeting_id: str, content_type: str, 
                                   conn=None) -> Dict[str, Any]:
        """
        Get version history for a specific content type
        
        Args:
            meeting_id: Meeting identifier
            content_type: 'transcript' or 'summary'
            conn: Database connection
        
        Returns:
            Dict with version list
        """
        db = DatabaseUtils(conn)
        versions = db.list_content_versions(meeting_id, content_type)
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "content_type": content_type,
            "total_versions": len(versions),
            "versions": versions
        }
    
    def get_content_version(self, meeting_id: str, content_type: str, 
                           version_number: int, conn=None) -> Dict[str, Any]:
        """
        Get a specific content version
        
        Args:
            meeting_id: Meeting identifier
            content_type: 'transcript' or 'summary'
            version_number: Version number to retrieve
            conn: Database connection
        
        Returns:
            Dict with version details
        """
        db = DatabaseUtils(conn)
        version = db.get_content_version(meeting_id, content_type, version_number)
        
        if not version:
            return {
                "success": False,
                "message": f"{content_type.capitalize()} version {version_number} not found"
            }
        
        return {
            "success": True,
            "version": version
        }
    
    def compare_content_versions(self, meeting_id: str, content_type: str, 
                                v1: int, v2: int, conn=None) -> Dict[str, Any]:
        """
        Compare two versions of content
        
        Args:
            meeting_id: Meeting identifier
            content_type: 'transcript' or 'summary'
            v1: First version number
            v2: Second version number
            conn: Database connection
        
        Returns:
            Dict with both versions for comparison
        """
        db = DatabaseUtils(conn)
        
        version1 = db.get_content_version(meeting_id, content_type, v1)
        version2 = db.get_content_version(meeting_id, content_type, v2)
        
        if not version1 or not version2:
            return {
                "success": False,
                "message": "One or both versions not found"
            }
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "content_type": content_type,
            "version_1": {
                "version_number": version1["version_number"],
                "content": version1["content"],
                "created_by": version1["created_by"],
                "created_at": version1["created_at"],
                "is_current": version1["is_current"]
            },
            "version_2": {
                "version_number": version2["version_number"],
                "content": version2["content"],
                "created_by": version2["created_by"],
                "created_at": version2["created_at"],
                "is_current": version2["is_current"]
            }
        }
    
    def rollback_content_to_version(self, meeting_id: str, content_type: str, 
                                   version_number: int, created_by: str = "SYSTEM",
                                   conn=None) -> Dict[str, Any]:
        """
        Rollback content to a previous version
        
        Args:
            meeting_id: Meeting identifier
            content_type: 'transcript' or 'summary'
            version_number: Version to rollback to
            created_by: Who triggered the rollback
            conn: Database connection
        
        Returns:
            Dict with success status and restored content
        """
        db = DatabaseUtils(conn)
        
        # Perform rollback (updates meeting_details and sets is_current)
        result = db.rollback_content_to_version(meeting_id, content_type, version_number)
        
        if not result.get("success"):
            return result
        
        # Create a new version to track the rollback action
        # This preserves the fact that a rollback happened
        content = result.get("content")
        db.create_content_version(
            meeting_id=meeting_id,
            content_type=content_type,
            content=content,
            created_by=created_by
        )
        
        return result
    
    def get_unified_edit_timeline(self, meeting_id: str, conn=None) -> Dict[str, Any]:
        """
        Get unified timeline of all edits (transcript + summary + others)
        
        Args:
            meeting_id: Meeting identifier
            conn: Database connection
        
        Returns:
            Dict with chronological timeline of all edits
        """
        db = DatabaseUtils(conn)
        timeline = db.get_unified_timeline(meeting_id)
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "total_edits": len(timeline),
            "timeline": timeline
        }