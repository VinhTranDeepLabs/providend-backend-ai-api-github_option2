from typing import Dict, Optional, List, Any
from uuid import uuid4
from datetime import datetime, timezone
import json

from utils.db_utils import DatabaseUtils
from services.azure_openai_service import azure_openai_service


class ChatService:
    """Service layer for chat operations"""
    
    def __init__(self):
        pass
    
    def get_or_create_active_chat(self, meeting_id: str, user_id: str, conn) -> str:
        """
        Get active chat for a meeting or create a new one.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user (advisor) ID
            conn: Database connection
        
        Returns:
            chat_id: The active chat ID
        """
        db = DatabaseUtils(conn)
        
        # Check for active chat
        active_chat = db.get_active_chat_for_meeting(meeting_id)
        
        if active_chat:
            return active_chat["chat_id"]
        
        # Create new chat if none exists
        chat_id = str(uuid4())
        result = db.create_chat(
            chat_id=chat_id,
            meeting_id=meeting_id,
            user_id=user_id
        )
        
        if result.get("success"):
            return chat_id
        else:
            raise Exception(f"Failed to create chat: {result.get('message')}")
    
    def reset_chat(self, meeting_id: str, user_id: str, conn) -> Dict:
        """
        Soft delete existing chat and create a new one (called when 'new_chat' button is pressed).
        
        Args:
            meeting_id: The meeting ID
            user_id: The user (advisor) ID
            conn: Database connection
        
        Returns:
            Dict with new chat details
        """
        db = DatabaseUtils(conn)
        
        # Soft delete existing active chat (if any)
        existing_chat = db.get_active_chat_for_meeting(meeting_id)
        if existing_chat:
            db.soft_delete_chat(existing_chat["chat_id"])
        
        # Create new chat
        chat_id = str(uuid4())
        result = db.create_chat(
            chat_id=chat_id,
            meeting_id=meeting_id,
            user_id=user_id
        )
        
        if not result.get("success"):
            raise Exception(f"Failed to create new chat: {result.get('message')}")
        
        return {
            "chat_id": chat_id,
            "meeting_id": meeting_id,
            "created_at": result.get("created_at")
        }
    
    def generate_chat_response(
        self,
        meeting_id: str,
        user_id: str,
        message_text: str,
        chart_data: Optional[Dict[str, Any]],
        conn
    ) -> Dict:
        """
        Generate AI response for a chat message.
        
        Flow:
        1. Get or create active chat
        2. Fetch meeting context (transcript + summary) - FRESH on every call
        3. Get chat history
        4. Build enhanced prompt with context
        5. Call Azure OpenAI for response
        6. Store user message and bot response
        7. Return response
        
        Args:
            meeting_id: The meeting ID
            user_id: The user (advisor) ID
            message_text: User's message
            chart_data: Optional chart data for context
            conn: Database connection
        
        Returns:
            Dict with response details
        """
        db = DatabaseUtils(conn)
        
        # 1. Get or create active chat
        chat_id = self.get_or_create_active_chat(meeting_id, user_id, conn)
        
        # 2. Fetch meeting context (FRESH - not stored in chat)
        meeting_details = db.get_meeting_detail(meeting_id)
        if not meeting_details:
            raise Exception(f"Meeting details not found for meeting_id: {meeting_id}")
        
        meeting = db.get_meeting(meeting_id)
        if not meeting:
            raise Exception(f"Meeting not found for meeting_id: {meeting_id}")
        
        transcript = meeting_details.get("transcript", "")
        summary = meeting_details.get("summary", "")
        meeting_name = meeting.get("meeting_name", "Meeting")
        
        # 3. Get chat history for context
        chat_messages = db.get_chat_messages(chat_id)
        
        # Format chat history
        chat_history_text = ""
        if chat_messages:
            chat_history_text = "\n\nPrevious Conversation:\n"
            for msg in chat_messages:
                role = "Advisor" if msg["sender_type"] == "user" else "Assistant"
                chat_history_text += f"{role}: {msg['content']}\n"
        
        # 4. Build enhanced prompt with all context
        enhanced_message = message_text
        
        # Add chart data if provided
        if chart_data:
            chart_context = f"\n\n[Chart Data Attached]\n{json.dumps(chart_data, ensure_ascii=False)}"
            enhanced_message += chart_context
        
        # Build system prompt with meeting context
        system_prompt = f"""You are an AI assistant helping a financial advisor analyze meeting data.

Meeting Context:
- Meeting: {meeting_name}
- Meeting ID: {meeting_id}

Meeting Transcript:
{transcript if transcript else "No transcript available"}

Meeting Summary:
{summary if summary else "No summary available"}

{chat_history_text}

Your role is to:
1. Answer questions about this specific meeting
2. Reference information from the transcript and summary
3. Provide insights based on the meeting content
4. Be concise and professional, respond in point form whereever appropriate unless asked otherwise.
5. Avoid offering guidance on next steps unless specifically asked.
6. Only add a follow-up elaboration question when the advisor's question is broad or general (e.g. goals, concerns, financial situation) — not for specific factual questions (e.g. hobbies, age). If not needed, end the response immediately without any closing remark.

If chart data is provided, analyze it in the context of the meeting discussion."""

        user_prompt = f"Advisor's Question: {enhanced_message}"
        
        # 5. Call Azure OpenAI for response
        try:
            bot_response = azure_openai_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1000
            )
        except Exception as e:
            raise Exception(f"AI service error: {str(e)}")
        
        # 6. Store user message
        user_message_id = str(uuid4())
        user_msg_result = db.create_message(
            message_id=user_message_id,
            chat_id=chat_id,
            content=message_text,  # Store original message (without chart data)
            sender_type="user"
        )
        
        if not user_msg_result.get("success"):
            raise Exception(f"Failed to store user message: {user_msg_result.get('message')}")
        
        # 7. Store bot response
        bot_message_id = str(uuid4())
        bot_msg_result = db.create_message(
            message_id=bot_message_id,
            chat_id=chat_id,
            content=bot_response,
            sender_type="bot"
        )
        
        if not bot_msg_result.get("success"):
            raise Exception(f"Failed to store bot message: {bot_msg_result.get('message')}")
        
        return {
            "success": True,
            "chat_id": chat_id,
            "user_message_id": user_message_id,
            "bot_message_id": bot_message_id,
            "bot_response": bot_response
        }
    
    def get_chat_history(self, meeting_id: str, user_id: str, conn) -> Dict:
        """
        Get conversation history for the meeting's active chat.
        
        Args:
            meeting_id: The meeting ID
            user_id: The user (advisor) ID
            conn: Database connection
        
        Returns:
            Dict with chat history
        """
        db = DatabaseUtils(conn)
        
        # Get active chat for meeting
        active_chat = db.get_active_chat_for_meeting(meeting_id)
        
        if not active_chat:
            return {
                "success": True,
                "chat_id": None,
                "meeting_id": meeting_id,
                "total_messages": 0,
                "messages": []
            }
        
        chat_id = active_chat["chat_id"]
        
        # Get all messages
        messages = db.get_chat_messages(chat_id)
        
        return {
            "success": True,
            "chat_id": chat_id,
            "meeting_id": meeting_id,
            "total_messages": len(messages),
            "messages": messages
        }