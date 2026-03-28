"""
Audio Monitor Service - Background script to process new audio files from Azure Blob Storage

This script:
1. Polls Azure Blob Storage for new audio files
2. Transcribes audio using Azure Speech Services Batch API (via transcription_service)
3. Parses filename: <meeting_id>_<YYYY-MM-DD HH-MM-SS+00>.extension
4. Saves transcript to transcript_aggregator table
5. Tracks processed files in processed_audio_files table
6. Automatically retries failed transcriptions

Usage:
    python audio_monitor.py

Environment Variables Required:
    - BLOB_ACCOUNT_NAME
    - BLOB_CONTAINER_NAME
    - BLOB_ACCOUNT_KEY
    - AZURE_SPEECH_KEY
    - AZURE_SPEECH_REGION
    - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
"""

import os
import time
import re
import psycopg2
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import signal
import sys
import logging

# Import services
from services.transcription_service import TranscribeService
from utils.blob_utils import blob_storage_service

# Load environment variables
load_dotenv()

# ==================== CONFIGURATION ====================

BLOB_ACCOUNT_NAME = os.getenv("BLOB_ACCOUNT_NAME")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
BLOB_ACCOUNT_KEY = os.getenv("BLOB_ACCOUNT_KEY")

# Database configuration
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# Monitor configuration
POLL_INTERVAL = int(os.getenv("AUDIO_MONITOR_INTERVAL", "5"))  # seconds
SUPPORTED_EXTENSIONS = [".wav", ".webm"]

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_monitor.log', encoding='utf-8'),
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

# ==================== UTILITY FUNCTIONS ====================

def parse_filename(filename: str):
    """
    Parse audio filename to extract meeting_id and start_datetime
    
    Expected format: <meeting_id>_<YYYY-MM-DD HH-MM-SS+00>.extension
    Example: MTG001_2024-12-29 14-30-00+00.wav
    
    Returns:
        tuple: (meeting_id, start_datetime) or (None, None) if invalid
    """
    try:
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Pattern: meeting_id_YYYY-MM-DD HH-MM-SS+00
        pattern = r'^(.+?)_(\d{4}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})\+(\d{2})$'
        match = re.match(pattern, name_without_ext)
        
        if not match:
            logger.warning(f"Filename does not match expected format: {filename}")
            return None, None
        
        meeting_id = match.group(1)
        date_part = match.group(2)  # YYYY-MM-DD
        time_part = match.group(3)  # HH-MM-SS
        tz_offset = match.group(4)  # 00
        
        # Convert to datetime
        datetime_str = f"{date_part} {time_part.replace('-', ':')}"
        start_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        
        # Add timezone (assuming +00 is UTC)
        start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        
        logger.info(f"Parsed: {filename} → meeting_id={meeting_id}, datetime={start_datetime}")
        return meeting_id, start_datetime
        
    except Exception as e:
        logger.error(f"Error parsing filename {filename}: {e}")
        return None, None

def create_db_connection():
    """Create PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode="require"
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def build_blob_url(blob_name: str) -> str:
    """Build public blob URL"""
    return f"https://{BLOB_ACCOUNT_NAME}.blob.core.windows.net/{BLOB_CONTAINER_NAME}/{blob_name}"

# ==================== BLOB STORAGE FUNCTIONS ====================

def get_blob_service_client():
    """Create Azure Blob Service Client"""
    connection_string = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={BLOB_ACCOUNT_NAME};"
        f"AccountKey={BLOB_ACCOUNT_KEY};"
        f"EndpointSuffix=core.windows.net"
    )
    return BlobServiceClient.from_connection_string(connection_string)

def list_blob_audio_files():
    """List all audio files in blob storage container"""
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
        
        blobs = []
        for blob in container_client.list_blobs():
            # Filter by supported extensions
            if any(blob.name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                blobs.append({
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified
                })
        
        logger.info(f"Found {len(blobs)} audio files in blob storage")
        return blobs
        
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        return []

# ==================== DATABASE FUNCTIONS ====================

def get_processed_blobs(conn):
    """Get list of blob names that have been completed or are currently processing (excludes failed)"""
    try:
        cursor = conn.cursor()
        # Only return blobs with 'completed' or 'processing' status
        # This allows 'failed' blobs to be retried in the next loop
        cursor.execute("SELECT blob_name FROM processed_audio_files WHERE status IN ('completed', 'processing');")
        results = cursor.fetchall()
        cursor.close()
        return set(row[0] for row in results)
    except Exception as e:
        logger.error(f"Error fetching processed blobs: {e}")
        return set()

def mark_as_processing(conn, blob_name: str, meeting_id: str, file_size: int):
    """Mark blob file as being processed"""
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO processed_audio_files (blob_name, meeting_id, status, processed_datetime, file_size_bytes)
            VALUES (%s, %s, 'processing', NOW(), %s)
            ON CONFLICT (blob_name) DO UPDATE
            SET status = 'processing', processed_datetime = NOW();
        """
        cursor.execute(query, (blob_name, meeting_id, file_size))
        conn.commit()
        cursor.close()
        logger.info(f"Marked as processing: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error marking as processing: {e}")
        conn.rollback()
        return False

def mark_as_completed(conn, blob_name: str):
    """Mark blob file as completed"""
    try:
        cursor = conn.cursor()
        query = """
            UPDATE processed_audio_files
            SET status = 'completed', processed_datetime = NOW()
            WHERE blob_name = %s;
        """
        cursor.execute(query, (blob_name,))
        conn.commit()
        cursor.close()
        logger.info(f"Marked as completed: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Error marking as completed: {e}")
        conn.rollback()
        return False

def mark_as_failed(conn, blob_name: str, error_message: str):
    """Mark blob file as failed with error message"""
    try:
        cursor = conn.cursor()
        query = """
            UPDATE processed_audio_files
            SET status = 'failed', processed_datetime = NOW(), error_message = %s
            WHERE blob_name = %s;
        """
        cursor.execute(query, (error_message, blob_name))
        conn.commit()
        cursor.close()
        logger.error(f"Marked as failed: {blob_name} - {error_message}")
        return True
    except Exception as e:
        logger.error(f"Error marking as failed: {e}")
        conn.rollback()
        return False

def save_transcript_to_db(conn, meeting_id: str, transcript: str, start_datetime: datetime):
    """Save transcript to transcript_aggregator table"""
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO transcript_aggregator (meeting_id, transcript, start_datetime)
            VALUES (%s, %s, %s)
            RETURNING index;
        """
        cursor.execute(query, (meeting_id, transcript, start_datetime))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        segment_index = result[0] if result else None
        logger.info(f"✓ Saved transcript to DB: meeting_id={meeting_id}, segment={segment_index}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving transcript to DB: {e}")
        conn.rollback()
        return False

# ==================== MAIN PROCESSING LOGIC ====================

def process_new_audio_file(blob_info: dict, conn):
    """
    Process a single new audio file
    
    Steps:
    1. Parse filename
    2. Mark as processing
    3. Build blob URL
    4. Transcribe using batch API
    5. Save to DB
    6. Mark as completed
    """
    blob_name = blob_info['name']
    file_size = blob_info['size']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {blob_name}")
    logger.info(f"{'='*60}")
    
    # Parse filename
    meeting_id, start_datetime = parse_filename(blob_name)
    if not meeting_id or not start_datetime:
        mark_as_failed(conn, blob_name, "Invalid filename format")
        return False
    
    # Mark as processing
    if not mark_as_processing(conn, blob_name, meeting_id, file_size):
        return False
    
    try:
        # Build public Blob URL (URL-encoded, no SAS token required)
        blob_url = blob_storage_service.get_blob_url(blob_name)
        logger.info(f"Generated Blob URL: {blob_url}")
        
        # Transcribe using batch API
        logger.info("Starting batch transcription...")
        transcribe_service = TranscribeService()
        results = transcribe_service.batch_transcribe_urls(
            audio_urls=[blob_url],
            language='auto'  # Auto-detect language
        )
        
        if not results or len(results) == 0:
            mark_as_failed(conn, blob_name, "Batch transcription returned no results")
            return False
        
        # Extract transcript from first result
        transcription_result = results[0]
        transcript = transcription_result.transcript
        
        if not transcript or not transcript.strip():
            mark_as_failed(conn, blob_name, "Transcription returned empty result")
            return False
        
        logger.info(f"✓ Transcription complete: {len(transcript)} characters")
        
        # Save to database
        if not save_transcript_to_db(conn, meeting_id, transcript, start_datetime):
            mark_as_failed(conn, blob_name, "Failed to save to database")
            return False
        
        # Mark as completed
        mark_as_completed(conn, blob_name)
        
        logger.info(f"✓ Successfully processed: {blob_name}")
        return True
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        mark_as_failed(conn, blob_name, error_msg)
        return False

def monitor_loop():
    """Main monitoring loop"""
    global running
    
    logger.info("\n" + "="*60)
    logger.info("Audio Monitor Service Started")
    logger.info("="*60)
    logger.info(f"Blob Storage: {BLOB_ACCOUNT_NAME}/{BLOB_CONTAINER_NAME}")
    logger.info(f"Poll Interval: {POLL_INTERVAL} seconds")
    logger.info(f"Supported Extensions: {', '.join(SUPPORTED_EXTENSIONS)}")
    logger.info("="*60 + "\n")
    
    # Create database connection
    try:
        conn = create_db_connection()
        logger.info("✓ Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return
    
    try:
        while running:
            try:
                logger.info(f"\n[{datetime.now()}] Checking for new audio files...")
                
                # Get list of blobs in storage
                blob_files = list_blob_audio_files()
                
                # Get list of already processed blobs (excludes failed)
                processed_blobs = get_processed_blobs(conn)
                
                # Find new files (includes failed files for retry)
                new_files = [
                    blob for blob in blob_files
                    if blob['name'] not in processed_blobs
                ]
                
                if new_files:
                    logger.info(f"Found {len(new_files)} new file(s) to process")
                    
                    for blob in new_files:
                        if not running:
                            logger.info("Shutdown requested, stopping processing")
                            break
                        
                        process_new_audio_file(blob, conn)
                else:
                    logger.info("No new files found")
                
                # Wait before next poll
                if running:
                    logger.info(f"Sleeping for {POLL_INTERVAL} seconds...")
                    time.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                logger.info(f"Retrying in {POLL_INTERVAL} seconds...")
                time.sleep(POLL_INTERVAL)
    
    finally:
        # Cleanup
        conn.close()
        logger.info("\n✓ Database connection closed")
        logger.info("Audio Monitor Service Stopped\n")

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        monitor_loop()
    except KeyboardInterrupt:
        logger.info("\nShutdown initiated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)