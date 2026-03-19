"""
Meeting Processor Service - Background script to process completed meetings

This script:
1. Polls for meetings with status='Completed' and processing_status='pending'
2. Processes each meeting:
   - Autofills questions using QuestionService
   - Generates summary using SummaryService
3. Saves results to meeting_details table
4. Handles retries with exponential backoff (using updated_datetime)

Usage:
    python background_meeting_processor.py

Environment Variables Required:
    - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
    - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, etc.
    - Optional: PROCESSOR_POLL_INTERVAL, PROCESSOR_MAX_RETRIES

Architecture:
    - Polls every 15 seconds (configurable)
    - Uses optimistic locking to prevent duplicate processing
    - Processes tasks in parallel (asyncio)
    - Exponential backoff for retries using updated_datetime field (30s, 60s, 120s)
    - Graceful shutdown on SIGINT/SIGTERM
"""

import os
import time
import psycopg2
import asyncio
import signal
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, List, Optional
import json

# Import existing services
from services.question_service import QuestionService
from services.summay_service import SummaryService
from services.product_service import ProductRecommendationService
from services.client_preference_service import ClientPreferenceService
from services.transcription_service import TranscribeService
from utils.db_utils import DatabaseUtils

from services.transcription_service import has_generic_speaker_labels

# Load environment variables
load_dotenv()

# ==================== CONFIGURATION ====================

# Database configuration
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# Processor configuration
POLL_INTERVAL = int(os.getenv("PROCESSOR_POLL_INTERVAL", "15"))  # seconds
MAX_RETRIES = int(os.getenv("PROCESSOR_MAX_RETRIES", "3"))
BATCH_SIZE = int(os.getenv("PROCESSOR_BATCH_SIZE", "10"))
BACKOFF_BASE = int(os.getenv("PROCESSOR_BACKOFF_BASE", "30"))  # seconds

# Question template for autofill (default)
DEFAULT_QUESTION_TEMPLATE = "Discovery"

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== GLOBAL STATE ====================

running = True

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== DATABASE CONNECTION ====================

def create_db_connection():
    """Create PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode="prefer"
        )
        logger.info("✓ Database connection established")
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

# ==================== PROCESSING FUNCTIONS ====================

def calculate_backoff_delay(retry_count: int) -> int:
    """
    Calculate exponential backoff delay in seconds.
    
    This is used for logging purposes. The actual backoff is implemented
    in the database query using updated_datetime.
    
    Args:
        retry_count: Current retry attempt (0-indexed)
    
    Returns:
        Delay in seconds (30s, 60s, 120s, ...)
    """
    if retry_count == 0:
        return 0  # No delay for first attempt
    
    # Exponential: 30 * 2^(retry_count - 1)
    delay = BACKOFF_BASE * (2 ** (retry_count - 1))
    return int(delay)


async def process_meeting_tasks(meeting_id: str, transcript: str, conn) -> Dict:
    """
    Process a single meeting: autofill questions and generate summary in parallel.
    
    Args:
        meeting_id: The meeting ID
        transcript: Meeting transcript text
        conn: Database connection
    
    Returns:
        Dict with processing results or error
    """
    logger.info(f"[{meeting_id}] Starting processing tasks...")
    
    try:
        # Initialize services
        question_service = QuestionService()
        # summary_service = SummaryService()
        recommendation_service = ProductRecommendationService()
        preference_service = ClientPreferenceService()
        
        # Define async wrapper functions
        async def autofill_task():
            """Autofill questions task"""
            logger.info(f"[{meeting_id}] Running autofill questions...")
            start_time = time.time()
            
            try:
                autofilled_questions = question_service.autofill_questions(
                    template_name=DEFAULT_QUESTION_TEMPLATE,
                    transcript=transcript,
                    meeting_id=meeting_id,
                    conn=conn
                )
                
                # Convert to JSON string for storage
                questions_data = {
                    "questions": [
                        {
                            "question": qa.question,
                            "answer": qa.answer,
                            "confidence": qa.confidence
                        }
                        for qa in autofilled_questions
                    ],
                    "template": DEFAULT_QUESTION_TEMPLATE
                }
                questions_json = json.dumps(questions_data)
                
                duration = time.time() - start_time
                logger.info(f"[{meeting_id}] ✓ Autofill completed in {duration:.2f}s")
                
                return {"success": True, "questions": questions_json}
                
            except Exception as e:
                logger.error(f"[{meeting_id}] ✗ Autofill failed: {e}")
                return {"success": False, "error": str(e)}
        
        # async def summary_task():
        #     """Generate summary task - WITH VERSION CREATION"""
        #     logger.info(f"[{meeting_id}] Running summary generation...")
        #     start_time = time.time()
            
        #     try:
        #         # Pass created_by and conn to enable version creation
        #         summary = summary_service.generate_summary(
        #             transcript=transcript,
        #             meeting_id=meeting_id,
        #             created_by="AI_PROCESSOR",  # <-- ADDED: Track AI-generated summaries
        #             conn=conn
        #         )
                
        #         duration = time.time() - start_time
        #         logger.info(f"[{meeting_id}] ✓ Summary completed in {duration:.2f}s")
                
        #         return {"success": True, "summary": summary}
                
        #     except Exception as e:
        #         logger.error(f"[{meeting_id}] ✗ Summary failed: {e}")
        #         return {"success": False, "error": str(e)}
            
        async def recommendation_task():
            """Generate product recommendations from transcript"""
            logger.info(f"[{meeting_id}] Running product recommendations...")
            start_time = time.time()
            
            try:               
                recommendations = recommendation_service.generate_recommendations(
                    transcript=transcript,
                    meeting_id=meeting_id,
                    conn=conn
                )
                
                # Convert to JSON string for storage
                recommendations_json = json.dumps(recommendations)
                
                duration = time.time() - start_time
                logger.info(f"[{meeting_id}] ✓ Recommendations completed in {duration:.2f}s")
                
                return {"success": True, "recommendations": recommendations_json}
                
            except Exception as e:
                logger.error(f"[{meeting_id}] ✗ Recommendations failed: {e}")
                return {"success": False, "error": str(e)}

        async def preference_task():
            """Extract client preferences from transcript"""
            logger.info(f"[{meeting_id}] Running client preference extraction...")
            start_time = time.time()
            
            try:
                preferences = preference_service.extract_preferences(
                    transcript=transcript,
                    meeting_id=meeting_id,
                    conn=conn
                )
                
                # Convert to JSON string for storage
                preferences_json = json.dumps(preferences)
                
                duration = time.time() - start_time
                logger.info(f"[{meeting_id}] ✓ Preferences extracted in {duration:.2f}s")
                
                return {"success": True, "client_preferences": preferences_json}
                
            except Exception as e:
                logger.error(f"[{meeting_id}] ✗ Preference extraction failed: {e}")
                return {"success": False, "error": str(e)}

        
        # Run core tasks in parallel
        autofill_result, recommendation_result = await asyncio.gather(
            autofill_task(),
            recommendation_task()
        )
        
        # Option 1: Run preference task sequentially AFTER core tasks to prevent Rate Limit
        preference_result = await preference_task()

        # Check if core tasks succeeded (preferences are optional — non-blocking)
        if autofill_result["success"] and recommendation_result["success"]:
            result = {
                "success": True,
                "questions": autofill_result["questions"],
                # "summary": summary_result["summary"],
                "recommendations": recommendation_result["recommendations"]
            }
            # Preferences are optional — add if available, log warning if failed
            if preference_result["success"]:
                result["client_preferences"] = preference_result["client_preferences"]
            else:
                logger.warning(f"[{meeting_id}] Preferences failed but not blocking: {preference_result.get('error', 'unknown')}")
            return result
        else:
            # Collect errors
            errors = []
            if not autofill_result["success"]:
                errors.append(f"Autofill: {autofill_result['error']}")
            # if not summary_result["success"]:
            #     errors.append(f"Summary: {summary_result['error']}")
            if not recommendation_result["success"]:
                errors.append(f"Recommendations: {recommendation_result['error']}")
            
            return {
                "success": False,
                "error": "; ".join(errors)
            }
        
    except Exception as e:
        logger.error(f"[{meeting_id}] Unexpected error in processing: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def process_single_meeting(meeting: Dict, conn) -> bool:
    """
    Process a single meeting end-to-end.
    """
    meeting_id = meeting["meeting_id"]
    transcript = meeting["transcript"]
    retry_count = meeting["processing_retry_count"]
    updated_datetime = meeting["updated_datetime"]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing meeting: {meeting_id}")
    logger.info(f"Retry count: {retry_count}/{MAX_RETRIES}")
    if retry_count > 0:
        time_since_update = (datetime.now(timezone.utc) - updated_datetime).total_seconds()
        expected_backoff = calculate_backoff_delay(retry_count)
        logger.info(f"Time since last attempt: {time_since_update:.0f}s (expected backoff: {expected_backoff}s)")
    logger.info(f"{'='*60}")
    
    db = DatabaseUtils(conn)
    
    # Step 1: Claim the meeting (optimistic lock)
    if not db.claim_meeting_for_processing(meeting_id):
        logger.warning(f"[{meeting_id}] ⚠ Already being processed by another instance")
        return False
    
    # Step 1.5: Identify and replace speaker labels (ONLY if not already done manually)
    try:
        # Check if transcript still has generic labels (Guest-1, Speaker 1, etc.)
        if has_generic_speaker_labels(transcript):
            logger.info(f"[{meeting_id}] Transcript has generic labels, auto-identifying speakers...")
            
            transcribe_service = TranscribeService()
            cleaned_transcript = transcribe_service.identify_and_replace_speakers(
                transcript=transcript,
                meeting_id=meeting_id,
                conn=conn
            )
            
            # Update meeting_details with cleaned transcript
            db.update_meeting_detail(meeting_id=meeting_id, transcript=cleaned_transcript)
            
            # Create transcript version with cleaned transcript
            db.create_content_version(
                meeting_id=meeting_id,
                content_type='transcript',
                content=cleaned_transcript,
                created_by='AI_PROCESSOR'
            )
            
            # Use cleaned transcript for all subsequent processing
            transcript = cleaned_transcript
            logger.info(f"[{meeting_id}] ✓ Transcript updated with identified speakers")
        else:
            logger.info(f"[{meeting_id}] ✓ Transcript already has real names, skipping auto-identification")
        
    except Exception as e:
        logger.error(f"[{meeting_id}] ✗ Failed to identify speakers: {e}")
        logger.warning(f"[{meeting_id}]   Continuing with original transcript")
    
    try:
        # Step 2: Run processing tasks (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            process_meeting_tasks(meeting_id, transcript, conn)
        )
        loop.close()
        
        # Step 3: Save results or mark as failed
        if result["success"]:
            # Success - save results
            save_result = db.save_processing_results(
                meeting_id=meeting_id,
                questions=result["questions"],
                # summary=result["summary"],
                recommendations=result["recommendations"],
                client_preferences=result.get("client_preferences")
            )
            
            if save_result["success"]:
                logger.info(f"[{meeting_id}] ✓ Processing completed successfully")
                return True
            else:
                logger.error(f"[{meeting_id}] ✗ Failed to save results: {save_result['message']}")
                db.mark_processing_failed(
                    meeting_id=meeting_id,
                    error_msg=f"Save failed: {save_result['message']}",
                    retry_count=retry_count,
                    max_retries=MAX_RETRIES
                )
                return False
        else:
            # Failed - mark for retry or give up
            error_msg = result["error"]
            fail_result = db.mark_processing_failed(
                meeting_id=meeting_id,
                error_msg=error_msg,
                retry_count=retry_count,
                max_retries=MAX_RETRIES
            )
            
            if fail_result["will_retry"]:
                next_attempt = retry_count + 2  # +1 for increment, +1 for display
                backoff = calculate_backoff_delay(retry_count + 1)
                logger.warning(
                    f"[{meeting_id}] ⚠ Processing failed, will retry "
                    f"(attempt {next_attempt}/{MAX_RETRIES}) after {backoff}s backoff"
                )
            else:
                logger.error(f"[{meeting_id}] ✗ Processing failed permanently after {MAX_RETRIES} attempts")
            
            return False
    
    except Exception as e:
        # Unexpected error - mark as failed
        logger.error(f"[{meeting_id}] ✗ Unexpected error: {e}")
        logger.exception(e)
        
        db.mark_processing_failed(
            meeting_id=meeting_id,
            error_msg=f"Unexpected error: {str(e)}",
            retry_count=retry_count,
            max_retries=MAX_RETRIES
        )
        return False


# ==================== MAIN PROCESSING LOOP ====================

def process_meetings_batch(conn):
    """Process a batch of meetings ready for processing"""
    db = DatabaseUtils(conn)
    
    # Get meetings ready for processing (with exponential backoff built into query)
    meetings = db.get_meetings_for_processing(limit=BATCH_SIZE)
    
    if not meetings:
        logger.debug("No meetings to process")
        return 0
    
    logger.info(f"Found {len(meetings)} meeting(s) to process")
    
    # Process each meeting
    success_count = 0
    for meeting in meetings:
        if not running:
            logger.info("Shutdown requested, stopping batch processing")
            break
        
        try:
            if process_single_meeting(meeting, conn):
                success_count += 1
        except Exception as e:
            logger.error(f"Error processing meeting {meeting['meeting_id']}: {e}")
            continue
    
    logger.info(f"Batch complete: {success_count}/{len(meetings)} successful")
    return len(meetings)


def monitor_loop():
    """Main monitoring loop"""
    global running
    
    logger.info("\n" + "="*60)
    logger.info("Meeting Processor Service Started")
    logger.info("="*60)
    logger.info(f"Database: {DB_HOST}/{DB_NAME}")
    logger.info(f"Poll Interval: {POLL_INTERVAL} seconds")
    logger.info(f"Max Retries: {MAX_RETRIES}")
    logger.info(f"Batch Size: {BATCH_SIZE}")
    logger.info(f"Backoff Base: {BACKOFF_BASE} seconds (exponential: 30s, 60s, 120s...)")
    logger.info(f"Backoff Implementation: Using updated_datetime field")
    logger.info("="*60 + "\n")
    
    # Create database connection
    try:
        conn = create_db_connection()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return
    
    try:
        while running:
            try:
                logger.info(f"\n[{datetime.now()}] Checking for meetings to process...")
                
                # Process batch of meetings
                processed_count = process_meetings_batch(conn)
                
                # Sleep before next poll
                if running:
                    logger.info(f"Sleeping for {POLL_INTERVAL} seconds...")
                    time.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                logger.exception(e)
                logger.info(f"Retrying in {POLL_INTERVAL} seconds...")
                time.sleep(POLL_INTERVAL)
    
    finally:
        # Cleanup
        conn.close()
        logger.info("\n✓ Database connection closed")
        logger.info("Meeting Processor Service Stopped\n")


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    logger.info("Starting Meeting Processor Service...")
    
    try:
        monitor_loop()
    except KeyboardInterrupt:
        logger.info("\nShutdown initiated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        sys.exit(1)