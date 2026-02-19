"""
Standalone test script for ChatService.generate_chat_response.
Connects to real DB and Azure OpenAI using .env credentials.

Usage:
    python tests/test_chat_service.py
"""

import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

# Allow imports from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MEETING_ID = "3d598281-ca29-4a77-9b01-4f1591f90ac5"   # <-- paste your meeting_id
USER_ID    = "test-user"
MESSAGE    = "what is client's favorite shows to watch?"
# MESSAGE    = "what is the client's goal"
CHART_DATA = None                      # set to a dict to test chart context
DRY_RUN    = False                      # True = print prompt only, no AI call, no DB writes
# ─────────────────────────────────────────────────────────────────────────────


def create_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
        sslmode="require"
    )
    print("✓ Connected to database")
    return conn


def build_prompt(meeting_id, user_id, message_text, chart_data, conn):
    """Mirrors the prompt-building logic in ChatService.generate_chat_response."""
    from utils.db_utils import DatabaseUtils

    db = DatabaseUtils(conn)

    meeting_details = db.get_meeting_detail(meeting_id)
    if not meeting_details:
        raise Exception(f"Meeting details not found for meeting_id: {meeting_id}")

    meeting = db.get_meeting(meeting_id)
    if not meeting:
        raise Exception(f"Meeting not found for meeting_id: {meeting_id}")

    transcript    = meeting_details.get("transcript", "")
    summary       = meeting_details.get("summary", "")
    meeting_name  = meeting.get("meeting_name", "Meeting")

    # Fetch real chat history from the active chat for this meeting
    # active_chat = db.get_active_chat_for_meeting(meeting_id)
    chat_history_text = ""
    # if active_chat:
    #     chat_messages = db.get_chat_messages(active_chat["chat_id"])
    #     if chat_messages:
    #         chat_history_text = "\n\nPrevious Conversation:\n"
    #         for msg in chat_messages:
    #             role = "Advisor" if msg["sender_type"] == "user" else "Assistant"
    #             chat_history_text += f"{role}: {msg['content']}\n"
    #     print(f"✓ Loaded {len(chat_messages) if active_chat else 0} messages from chat {active_chat['chat_id']}")
    # else:
    #     print("  No active chat found — history will be empty")
    
    

    enhanced_message = message_text
    if chart_data:
        enhanced_message += f"\n\n[Chart Data Attached]\n{json.dumps(chart_data, ensure_ascii=False)}"

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
4. Be concise and professional, respond in POINT form whereever appropriate unless asked otherwise.
5. Avoid offering guidance on next steps unless specifically asked.
6. Only add a follow-up elaboration question when the advisor's question is broad or general (e.g. goals, concerns, financial situation) — not for specific factual questions (e.g. hobbies, age). If not needed, end the response immediately without any closing remark.

If chart data is provided, analyze it in the context of the meeting discussion."""

    user_prompt = f"Advisor's Question: {enhanced_message}"

    return system_prompt, user_prompt


def main():
    conn = create_connection()
    try:
        system_prompt, user_prompt = build_prompt(
            MEETING_ID, USER_ID, MESSAGE, CHART_DATA, conn
        )

        print("\n" + "=" * 60)
        print("SYSTEM PROMPT")
        print("=" * 60)
        print(system_prompt)

        print("\n" + "=" * 60)
        print("USER PROMPT")
        print("=" * 60)
        print(user_prompt)

        rough_tokens = (len(system_prompt) + len(user_prompt)) // 4
        print(f"\n~ Estimated tokens: {rough_tokens}")

        if DRY_RUN:
            print("\n[DRY_RUN=True] Skipping Azure OpenAI call and DB writes.")
            return

        # Live call — set DRY_RUN = False to reach here
        from services.azure_openai_service import azure_openai_service

        print("\n" + "=" * 60)
        print("CALLING AZURE OPENAI...")
        print("=" * 60)

        response = azure_openai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1000
        )

        print("\nBOT RESPONSE:")
        print(response)

    finally:
        conn.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    main()
