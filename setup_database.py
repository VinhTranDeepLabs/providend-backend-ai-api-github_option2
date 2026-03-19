import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")
TARGET_DB_NAME = os.getenv("DB_NAME", "providend_ai")

def get_connection(dbname=None):
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        dbname=dbname if dbname else "postgres"
    )

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to default 'postgres' db to create new db
        conn = get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if db exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (TARGET_DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{TARGET_DB_NAME}'...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(TARGET_DB_NAME)
            ))
            print("Database created successfully.")
        else:
            print(f"Database '{TARGET_DB_NAME}' already exists.")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def create_tables():
    """Create tables in the target database"""
    try:
        conn = get_connection(TARGET_DB_NAME)
        cursor = conn.cursor()
        
        print("Creating tables...")
        
        commands = [
            """
            CREATE TABLE IF NOT EXISTS advisors (
                advisor_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                role VARCHAR(50),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS clients (
                client_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                advisor_id VARCHAR(50),
                current_recommendation TEXT,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id VARCHAR(50) PRIMARY KEY,
                client_id VARCHAR(50),
                advisor_id VARCHAR(50),
                meeting_name VARCHAR(200),
                meeting_type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Started',
                created_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS meeting_details (
                meeting_id VARCHAR(50) PRIMARY KEY REFERENCES meetings(meeting_id) ON DELETE CASCADE,
                transcript TEXT,
                summary TEXT,
                recommendations TEXT,
                questions TEXT,
                advisor_notes TEXT,
                question_tracker TEXT,
                client_preferences TEXT,
                updated_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_status VARCHAR(50) DEFAULT 'pending',
                processing_retry_count INT DEFAULT 0,
                processing_error TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id VARCHAR(50) PRIMARY KEY,
                meeting_id VARCHAR(50) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
                user_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id VARCHAR(50) PRIMARY KEY,
                chat_id VARCHAR(50) REFERENCES chats(chat_id) ON DELETE CASCADE,
                content TEXT,
                sender_type VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100),
                type VARCHAR(50),
                description TEXT,
                risk_level VARCHAR(20),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # ADD TRANSCRIPT SEGMENT TABLE (Found in MeetingService code but missed in previous DDL)
            """
            CREATE TABLE IF NOT EXISTS transcript_aggregator (
                id SERIAL PRIMARY KEY,
                meeting_id VARCHAR(50) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
                transcript TEXT,
                start_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                segment_index INT
            )
            """
        ]
        
        for command in commands:
            cursor.execute(command)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("All tables created successfully.")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    if create_database():
        create_tables()
