from fastapi import APIRouter, Request, Depends, status, HTTPException
from typing import Dict, Any

from services.chat_service import ChatService
from services.meeting_service import MeetingService
from models.schemas import (
    SendMessageRequest,
    CreateChatResponse,
    SendMessageResponse,
    ChatHistoryResponse
)


router = APIRouter(prefix="/chat", tags=["Chat"])
chat_service = ChatService()


def get_conn(request: Request):
    """Return the shared DB connection stored on app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post("/meeting/{meeting_id}/new")
async def start_new_chat(
    meeting_id: str,
    conn=Depends(get_conn)
):
    """
    Start a new chat for a meeting (soft-deletes previous chat if exists).
    
    Called when user clicks "new_chat" button.
    Gets advisor_id from meeting record.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        New chat details
    """
    # Get meeting to extract advisor_id
    meeting_service = MeetingService()
    meeting = meeting_service.get_meeting(meeting_id, conn)
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    advisor_id = meeting["advisor_id"]
    
    try:
        # Reset chat (soft delete old, create new)
        result = chat_service.reset_chat(
            meeting_id=meeting_id,
            user_id=advisor_id,
            conn=conn
        )
        
        return {
            "success": True,
            "message": "New chat started successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start new chat: {str(e)}"
        )


@router.post("/meeting/{meeting_id}/message")
async def send_message(
    meeting_id: str,
    request: SendMessageRequest,
    conn=Depends(get_conn)
):
    """
    Send a message and get AI response.
    
    Auto-creates chat if none exists for this meeting.
    Fetches fresh transcript + summary from meeting_details on every call.
    Gets advisor_id from meeting record.
    
    Args:
        meeting_id: The meeting ID
        request: Message request with text and optional chart_data
    
    Returns:
        AI response with message IDs
    """
    # Get meeting to extract advisor_id
    meeting_service = MeetingService()
    meeting = meeting_service.get_meeting(meeting_id, conn)
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    advisor_id = meeting["advisor_id"]
    
    try:
        # Generate chat response
        result = chat_service.generate_chat_response(
            meeting_id=meeting_id,
            user_id=advisor_id,
            message_text=request.message,
            chart_data=request.chart_data,
            conn=conn
        )
        
        return {
            "success": True,
            "message": "Message sent successfully",
            "data": {
                "chat_id": result["chat_id"],
                "user_message_id": result["user_message_id"],
                "bot_message_id": result["bot_message_id"],
                "bot_response": result["bot_response"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.get("/meeting/{meeting_id}/messages")
async def get_chat_history(
    meeting_id: str,
    conn=Depends(get_conn)
):
    """
    Get conversation history for the meeting's active chat.
    
    Gets advisor_id from meeting record.
    
    Args:
        meeting_id: The meeting ID
    
    Returns:
        Chat history with all messages
    """
    # Get meeting to extract advisor_id
    meeting_service = MeetingService()
    meeting = meeting_service.get_meeting(meeting_id, conn)
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting not found: {meeting_id}"
        )
    
    advisor_id = meeting["advisor_id"]
    
    try:
        # Get chat history
        result = chat_service.get_chat_history(
            meeting_id=meeting_id,
            user_id=advisor_id,
            conn=conn
        )
        
        return {
            "success": True,
            "message": "Chat history retrieved successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )