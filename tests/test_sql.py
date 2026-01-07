import os
import psycopg2
from psycopg2 import OperationalError, Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_connection():
    """
    Create a database connection to Azure PostgreSQL
    Returns connection object or None
    """
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),  # e.g., yourserver.postgres.database.azure.com
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode="require"  # Azure requires SSL
        )
        print("✓ Successfully connected to PostgreSQL database")
        return connection
    
    except OperationalError as e:
        print(f"✗ Error connecting to PostgreSQL: {e}")
        return None

def execute_query(connection, query):
    """
    Execute a SELECT query and return results
    """
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        cursor.close()
        return columns, results
    
    except Error as e:
        print(f"✗ Error executing query: {e}")
        return None, None

def execute_command(connection, command):
    """
    Execute a command that doesn't return results (CREATE, INSERT, UPDATE, DELETE)
    """
    try:
        cursor = connection.cursor()
        cursor.execute(command)
        connection.commit()
        cursor.close()
        print("✓ Command executed successfully")
        return True
    
    except Error as e:
        print(f"✗ Error executing command: {e}")
        connection.rollback()
        return False

def create_database_tables(connection):
    """
    Create the 6 main tables: advisors, clients, meetings, meeting_details, products, client_products
    """
    # Table 1: Advisors
    create_advisors_table = """
        CREATE TABLE IF NOT EXISTS advisors (
            advisor_id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            role VARCHAR(50),
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    
    # Table 2: Clients
    create_clients_table = """
        CREATE TABLE IF NOT EXISTS clients (
            client_id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100),
            advisor_id VARCHAR(100) REFERENCES advisors(advisor_id) ON DELETE SET NULL,
            current_recommendation TEXT,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status VARCHAR(50)
        );
    """
    
    # Table 3: Meetings
    create_meetings_table = """
        CREATE TABLE IF NOT EXISTS meetings (
            meeting_id VARCHAR(100) PRIMARY KEY,
            client_id VARCHAR(100) REFERENCES clients(client_id) ON DELETE CASCADE,
            advisor_id VARCHAR(100) REFERENCES advisors(advisor_id) ON DELETE SET NULL,
            meeting_name VARCHAR(200) DEFAULT 'Scheduled meeting',
            meeting_type VARCHAR(50),
            created_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status VARCHAR(50)
        );
    """
    
    # Table 4: Meeting Details
    create_meeting_details_table = """
        CREATE TABLE IF NOT EXISTS meeting_details (
            meeting_id VARCHAR(100) PRIMARY KEY REFERENCES meetings(meeting_id) ON DELETE CASCADE,
            transcript TEXT,
            summary TEXT,
            recommendations TEXT,
            questions TEXT,
            question_tracker TEXT,
            advisor_notes TEXT,
            updated_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    
    # Table 5: Products
    create_products_table = """
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100),
            type VARCHAR(50),
            description TEXT,
            risk_level VARCHAR(50),
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    
    # Table 6: Client_Products (Junction table)
    create_client_products_table = """
        CREATE TABLE IF NOT EXISTS client_products (
            client_id VARCHAR(100) REFERENCES clients(client_id) ON DELETE CASCADE,
            product_id VARCHAR(100) REFERENCES products(product_id) ON DELETE CASCADE,
            purchase_date DATE,
            status VARCHAR(50),
            investment_amount DECIMAL(15, 2),
            PRIMARY KEY (client_id, product_id)
        );
    """
    
    # Table 7: Transcript_Aggregator
    create_transcript_aggregator_table = """
        CREATE TABLE IF NOT EXISTS transcript_aggregator (
            index SERIAL PRIMARY KEY,
            meeting_id VARCHAR(100) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
            transcript TEXT,
            start_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """

    # Table 8: Processed_audio_files
    create_processed_audio_files = """
        CREATE TABLE IF NOT EXISTS processed_audio_files (
            blob_name VARCHAR(255) PRIMARY KEY,
            meeting_id VARCHAR(100),
            status VARCHAR(50),  -- 'processing', 'completed', 'failed'
            processed_datetime TIMESTAMPTZ,
            error_message TEXT,
            file_size_bytes BIGINT
        );
    """

    # Table 9: Feedback
    create_feedback_table = """
        CREATE TABLE IF NOT EXISTS feedback (
            index SERIAL PRIMARY KEY,
            meeting_id VARCHAR(100) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
            feedback TEXT,
            feedback_on VARCHAR(50),
            edit_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """
    
    print("\nCreating tables...")
    if execute_command(connection, create_advisors_table):
        print("✓ 'advisors' table created")
    
    if execute_command(connection, create_clients_table):
        print("✓ 'clients' table created")
    
    if execute_command(connection, create_meetings_table):
        print("✓ 'meetings' table created")
    
    if execute_command(connection, create_meeting_details_table):
        print("✓ 'meeting_details' table created")
    
    if execute_command(connection, create_products_table):
        print("✓ 'products' table created")
    
    if execute_command(connection, create_client_products_table):
        print("✓ 'client_products' table created")
    
    if execute_command(connection, create_transcript_aggregator_table):
        print("✓ 'transcript_aggregator' table created")

    if execute_command(connection, create_processed_audio_files):
        print("✓ 'transcript_aggregator' table created")

    if execute_command(connection, create_feedback_table):
        print("✓ 'feedback' table created")

    # ==================== ADD PROCESSING COLUMNS TO MEETING_DETAILS ====================
    print("\n--- Adding Processing Columns to meeting_details ---")
    
    # Check if columns already exist before adding them
    add_processing_status = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='meeting_details' AND column_name='processing_status') THEN
                ALTER TABLE meeting_details ADD COLUMN processing_status VARCHAR(50) DEFAULT 'pending';
            END IF;
        END $$;
    """
    
    add_processing_retry_count = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='meeting_details' AND column_name='processing_retry_count') THEN
                ALTER TABLE meeting_details ADD COLUMN processing_retry_count INTEGER DEFAULT 0;
            END IF;
        END $$;
    """
    
    add_processing_error = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='meeting_details' AND column_name='processing_error') THEN
                ALTER TABLE meeting_details ADD COLUMN processing_error TEXT;
            END IF;
        END $$;
    """

    add_question_tracker = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='meeting_details' AND column_name='question_tracker') THEN
                ALTER TABLE meeting_details ADD COLUMN question_tracker TEXT;
            END IF;
        END $$;
    """

    add_meeting_name = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='meetings' AND column_name='meeting_name') THEN
                ALTER TABLE meetings ADD COLUMN meeting_name TEXT DEFAULT 'Scheduled meeting';
            END IF;
        END $$;
    """

    alter_meetings_client_id = """
        DO $$ 
        BEGIN
            -- Check if client_id is NOT NULL and alter if necessary
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'meetings' 
                AND column_name = 'client_id' 
                AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE meetings ALTER COLUMN client_id DROP NOT NULL;
            END IF;
        END $$;
    """

    # add_feedback_on_column = """
    #     DO $$ 
    #     BEGIN
    #         IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
    #                     WHERE table_name='feedback' AND column_name='feedback_on') THEN
    #             ALTER TABLE feedback ADD COLUMN feedback_on VARCHAR(50);
    #         END IF;
    #     END $$;
    # """
    
    if execute_command(connection, add_question_tracker):
        print("✓ 'question_tracker' column added")
    
    if execute_command(connection, add_processing_status):
        print("✓ 'processing_status' column added")
    
    if execute_command(connection, add_processing_retry_count):
        print("✓ 'processing_retry_count' column added")
    
    if execute_command(connection, add_processing_error):
        print("✓ 'processing_error' column added")

    if execute_command(connection, add_question_tracker):
        print("✓ 'question_tracker' column added")

    if execute_command(connection, add_meeting_name):
        print("✓ 'question_tracker' column added")

    if execute_command(connection, alter_meetings_client_id):
        print("✓ 'client_id' column in meetings is now nullable")

    # if execute_command(connection, add_feedback_on_column):
    #     print("✓ 'feedback_on' column added")


def drop_database_tables(connection):
    """
    Drop the seven main tables created by `create_database_tables`.

    Drops in order that respects foreign-key dependencies:
    1) transcript_aggregator (references meetings)
    2) client_products (references clients, products)
    3) meeting_details (references meetings)
    4) meetings (references clients, advisors)
    5) clients (references advisors)
    6) products (standalone)
    7) advisors (standalone)
    """
    drop_feedback = "DROP TABLE IF EXISTS feedback CASCADE;"
    drop_transcript_aggregator = "DROP TABLE IF EXISTS transcript_aggregator CASCADE;"
    drop_client_products = "DROP TABLE IF EXISTS client_products CASCADE;"
    drop_meeting_details = "DROP TABLE IF EXISTS meeting_details CASCADE;"
    drop_meetings = "DROP TABLE IF EXISTS meetings CASCADE;"
    drop_clients = "DROP TABLE IF EXISTS clients CASCADE;"
    drop_products = "DROP TABLE IF EXISTS products CASCADE;"
    drop_advisors = "DROP TABLE IF EXISTS advisors CASCADE;"

    print("\nDropping tables (if they exist)...")
    if execute_command(connection, drop_feedback):
        print("✓ 'feedback' dropped (if existed)")
    # if execute_command(connection, drop_transcript_aggregator):
    #     print("✓ 'transcript_aggregator' dropped (if existed)")
    # if execute_command(connection, drop_client_products):
    #     print("✓ 'client_products' dropped (if existed)")
    # if execute_command(connection, drop_meeting_details):
    #     print("✓ 'meeting_details' dropped (if existed)")
    # if execute_command(connection, drop_meetings):
    #     print("✓ 'meetings' dropped (if existed)")
    # if execute_command(connection, drop_clients):
    #     print("✓ 'clients' dropped (if existed)")
    # if execute_command(connection, drop_products):
    #     print("✓ 'products' dropped (if existed)")
    # if execute_command(connection, drop_advisors):
    #     print("✓ 'advisors' dropped (if existed)")

def view_table_columns(connection, table_name):
    """
    View column headers and data types for a specific table
    """
    query = """
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position;
    """
    try:
        cursor = connection.cursor()
        cursor.execute(query, (table_name,))
        results = cursor.fetchall()
        cursor.close()
        
        if results:
            print(f"\n--- Columns in '{table_name}' table ---")
            for row in results:
                col_name = row[0]
                data_type = row[1]
                max_length = row[2] if row[2] else "N/A"
                print(f"  • {col_name}: {data_type}({max_length})")
        else:
            print(f"\n✗ Table '{table_name}' not found")
    
    except Error as e:
        print(f"✗ Error viewing columns: {e}")

def main():
    # Create connection
    conn = create_connection()
    
    if conn:
        try:
            # Example: Get database version
            columns, results = execute_query(conn, "SELECT version();")
            
            if results:
                print(f"\nDatabase version:")
                print(results[0][0][:80] + "...")  # Truncate for readability
            
            # Create database tables
            create_database_tables(conn)
            
            # List all tables in public schema
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
            columns, results = execute_query(conn, query)
            
            if results:
                print(f"\n{'='*50}")
                print(f"Tables in database:")
                print(f"{'='*50}")
                for row in results:
                    print(f"  - {row[0]}")
            
            # View column headers for each table
            print(f"\n{'='*50}")
            print(f"Table Column Details:")
            print(f"{'='*50}")
            view_table_columns(conn, "advisors")
            view_table_columns(conn, "clients")
            view_table_columns(conn, "meetings")
            view_table_columns(conn, "meeting_details")
            view_table_columns(conn, "products")
            view_table_columns(conn, "client_products")
            view_table_columns(conn, "transcript_aggregator")
            view_table_columns(conn, "feedback")

            # # # Delete all tables (uncomment to drop)
            # drop_database_tables(conn)
        
        finally:
            # Always close connection
            conn.close()
            print(f"\n{'='*50}")
            print("✓ Database connection closed")
            print(f"{'='*50}")

if __name__ == "__main__":
    main()