"""
Migration script to add client_preferences column to existing meeting_details table.
Run this ONCE on your local database before using the ClientPreferenceService.

Usage:
    cd d:\Mastering RAG AI Engineer\providend-backend-ai-api-main\providend-backend-ai-api-main
    python scripts/migrate_add_client_preferences.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "providend_ai")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")


def migrate():
    """Add client_preferences TEXT column to meeting_details if not exists."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode="prefer"
        )
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'meeting_details' 
            AND column_name = 'client_preferences';
        """)
        
        if cursor.fetchone():
            print("Column 'client_preferences' already exists. Nothing to do.")
        else:
            cursor.execute("""
                ALTER TABLE meeting_details 
                ADD COLUMN client_preferences TEXT;
            """)
            conn.commit()
            print("Successfully added 'client_preferences' TEXT column to meeting_details.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()
