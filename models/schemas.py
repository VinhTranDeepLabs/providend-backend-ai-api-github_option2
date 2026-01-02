from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request Models
class TranscriptRequest(BaseModel):
    transcript: str = Field(..., description="The transcript text to process")

class BatchTranscribeRequest(BaseModel):
    audio_urls: List[str] = Field(..., description="List of audio file URLs for batch transcription")
    language: Optional[str] = Field("en-US", description="Language code for transcription")

class RecommendQuestions(BaseModel):
    question_template_name: str = Field(..., description="The question template to analyze for recommending questions")
    transcript: str = Field(..., description="The transcript text to process")
    num_of_recommendations: Optional[int] = Field(5, description="Number of recommended questions to return")

class AutofillQuestionsRequest(BaseModel):
    template_name: str = Field(..., description="The question template name to use for autofill")
    transcript: str = Field(..., description="The transcript text to process")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID associated with the transcript")


# Response Models
class SummaryResponse(BaseModel):
    summary: str
    key_points: List[str]
    success: bool = True

class QuestionAnswer(BaseModel):
    question: str
    question_answered: bool
    answer: Optional[str]
    confidence: Optional[str] = Field(None, description="Confidence level: high, medium, low")

class AutofillQuestionsResponse(BaseModel):
    message: str
    autofilled_questions: List[QuestionAnswer]
    filled_template: str

class UnansweredQuestionsResponse(BaseModel):
    unanswered_questions: List[str]
    total_unanswered: int
    success: bool = True

class RecommendQuestionsResponse(BaseModel):
    recommended_questions: List[str]
    total_recommended: int
    success: bool = True

class SpeakerSegment(BaseModel):
    speaker: str
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class TranscriptionResult(BaseModel):
    audio_url: str
    transcript: str
    speaker_segments: List[SpeakerSegment]
    language: str
    duration: Optional[float] = None

class BatchTranscribeResponse(BaseModel):
    results: List[TranscriptionResult]
    total_files: int
    success: bool = True
    errors: Optional[List[Dict[str, str]]] = None

# Error Response
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


####### client profile related schemas ########
class ClientCreateResponse(BaseModel):
    """Response for create_client_profile"""
    name: str
    role: str
    email: str


class MeetingItem(BaseModel):
    meeting_id: str
    date: str  # keep as ISO date string; change to date / datetime if desired


class ClientProfileResponse(BaseModel):
    """Response for get_client_profile"""
    meetings: List[MeetingItem]


class UpdateClientResponse(BaseModel):
    """Response for update_client_profile"""
    message: str
    update: Optional[Dict[str, Any]] = None


class ClientMeetingHistoryResponse(BaseModel):
    """Response for get_client_meeting_history (same shape as ClientProfileResponse)"""
    meetings: List[MeetingItem]


class RecommendationItem(BaseModel):
    meeting_id: str
    recommendation: str


class ClientRecommendationResponse(BaseModel):
    """Response for get_client_recommendation"""
    recommendations: List[RecommendationItem]


######

class QuestionTrackerRequest(BaseModel):
    question_template: str = Field(..., description="The question template name to use for tracking")
    transcript: str = Field(..., description="The conversation transcript to analyze")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID to save tracker data")

class QuestionTrackerResponse(BaseModel):
    sections: Dict[str, Dict[str, bool]] = Field(
        ..., 
        description="Questions organized by section with boolean indicating if answered"
    )
    success: bool = True

class GetQuestionTrackerResponse(BaseModel):
    """Response for GET /meeting/{meeting_id}/tracker endpoint"""
    success: bool = True
    meeting_id: str = Field(..., description="The meeting ID")
    tracker: Dict[str, Dict[str, bool]] = Field(
        ..., 
        description="Question tracker data organized by sections"
    )

class GenerateSummaryRequest(BaseModel):
    transcript: str = Field(..., description="The meeting transcript to summarize")

class GenerateSummaryResponse(BaseModel):
    summary: str = Field(..., description="The generated 3-paragraph summary")
    success: bool = True

####### Transcript Aggregator Schemas ########

class TranscriptSegment(BaseModel):
    """Individual transcript segment"""
    index: int = Field(..., description="Auto-incrementing segment index")
    meeting_id: str = Field(..., description="Meeting ID this segment belongs to")
    transcript: str = Field(..., description="Transcript text content")
    start_datetime: datetime = Field(..., description="When this segment was captured")


class AddTranscriptSegmentRequest(BaseModel):
    """Request to add a transcript segment"""
    transcript: str = Field(..., description="Transcript text segment")
    start_datetime: Optional[datetime] = Field(None, description="When segment was captured (defaults to NOW)")


class AddTranscriptSegmentResponse(BaseModel):
    """Response for adding a transcript segment"""
    success: bool = True
    message: str
    meeting_id: str
    segment_index: int
    start_datetime: datetime


class TranscriptSegmentsResponse(BaseModel):
    """Response with list of transcript segments"""
    success: bool = True
    meeting_id: str
    total_segments: int
    segments: List[TranscriptSegment]


class TranscriptSegmentByIndexResponse(BaseModel):
    """Response for getting a single segment"""
    success: bool = True
    segment: TranscriptSegment


class AggregateTranscriptsRequest(BaseModel):
    """Request to aggregate transcript segments"""
    separator: str = Field("\n", description="String to join segments")
    save_to_details: bool = Field(True, description="Save aggregated transcript to meeting_details")


class AggregateTranscriptsResponse(BaseModel):
    """Response for aggregating transcripts"""
    success: bool = True
    message: str
    meeting_id: str
    transcript: str = Field(..., description="Aggregated transcript text")
    segment_count: int = Field(..., description="Number of segments aggregated")
    saved_to_details: bool = Field(..., description="Whether saved to meeting_details")


class UpdateTranscriptSegmentRequest(BaseModel):
    """Request to update a transcript segment"""
    transcript: Optional[str] = Field(None, description="New transcript text")
    start_datetime: Optional[datetime] = Field(None, description="New start datetime")


class DeleteTranscriptSegmentsResponse(BaseModel):
    """Response for deleting transcript segments"""
    success: bool = True
    message: str
    meeting_id: str
    deleted_count: int = Field(..., description="Number of segments deleted")


class TranscriptSegmentCountResponse(BaseModel):
    """Response for counting transcript segments"""
    success: bool = True
    meeting_id: str
    segment_count: int


# ==================== SSO SCHEMAS ====================

class SSORequest(BaseModel):
    """Request model for SSO endpoint"""
    access_token: str = Field(..., description="Microsoft Entra ID access token")


class SSOResponse(BaseModel):
    """Response model for SSO endpoint"""
    valid: bool = Field(..., description="Whether the token is valid")
    user: Dict[str, Any] = Field(..., description="User information from database")
    access_token: str = Field(..., description="The validated access token")