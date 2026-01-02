import os
import psycopg2
from dotenv import load_dotenv
from utils.db_utils import DatabaseUtils
from datetime import date, datetime, timezone
from decimal import Decimal

# Load environment variables
load_dotenv()

def create_connection():
    """Create a database connection to Azure PostgreSQL"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode="require"
        )
        print("✓ Successfully connected to PostgreSQL database")
        return connection
    except Exception as e:
        print(f"✗ Error connecting to PostgreSQL: {e}")
        return None

def main():
    # Create connection
    conn = create_connection()
    
    if not conn:
        return
    
    try:
        # Initialize database utilities
        db = DatabaseUtils(conn)
        
        print("\n" + "="*60)
        print("TESTING DATABASE UTILITIES - NEW SCHEMA")
        print("="*60)
        
        # ==================== ADVISOR OPERATIONS ====================
        print("\n--- ADVISOR OPERATIONS ---")
        
        advisor_id = "41f9f5f9-ce4c-4fef-84f5-631390791464"

        # Create advisor
        result = db.create_advisor(
            advisor_id=advisor_id,
            name="John Tan",
            email="john.tan@providend.com",
            role="Senior Financial Advisor"
        )
        print(f"Create Advisor: {result}")
        
        # Get advisor
        advisor = db.get_advisor(advisor_id)
        print(f"Get Advisor: {advisor}")
        
        # Update advisor
        result = db.update_advisor(
            advisor_id=advisor_id,
            role="Lead Financial Advisor"
        )
        print(f"Update Advisor: {result}")
        
        # List all advisors
        advisors = db.list_advisors()
        print(f"List Advisors: {len(advisors)} advisor(s) found")
        for adv in advisors:
            print(f"  - {adv['advisor_id']}: {adv['name']} ({adv['role']})")
        
        # ==================== CLIENT OPERATIONS ====================
        print("\n--- CLIENT OPERATIONS ---")
        
        # Create client
        result = db.create_client(
            client_id="CLI201",
            name="Sarah Lim",
            advisor_id=advisor_id,
            current_recommendation="Consider increasing equity allocation",
            status="Active"
        )
        print(f"Create Client: {result}")
        
        # Get client
        client = db.get_client("CLI201")
        print(f"Get Client: {client}")
        
        # Update client
        result = db.update_client(
            client_id="CLI201",
            current_recommendation="Diversify portfolio with bonds",
            status="Active"
        )
        print(f"Update Client: {result}")
        
        # List clients by advisor
        clients = db.list_clients(advisor_id=advisor_id)
        print(f"List Clients for ADV201: {len(clients)} client(s) found")
        for cli in clients:
            print(f"  - {cli['client_id']}: {cli['name']} (Status: {cli['status']})")
        
        # ==================== PRODUCT OPERATIONS ====================
        print("\n--- PRODUCT OPERATIONS ---")
        
        # Create products
        result = db.create_product(
            product_id="PROD201",
            name="Equity Growth Fund",
            type="Mutual Fund",
            description="High-growth equity fund with global diversification",
            risk_level="High"
        )
        print(f"Create Product 1: {result}")
        
        result = db.create_product(
            product_id="PROD202",
            name="Bond Income Fund",
            type="Bond Fund",
            description="Conservative bond fund for steady income",
            risk_level="Low"
        )
        print(f"Create Product 2: {result}")
        
        # Get product
        product = db.get_product("PROD201")
        print(f"Get Product: {product}")
        
        # Update product
        result = db.update_product(
            product_id="PROD201",
            description="Updated: High-growth equity fund with Asia-Pacific focus"
        )
        print(f"Update Product: {result}")
        
        # List all products
        products = db.list_products()
        print(f"List Products: {len(products)} product(s) found")
        for prod in products:
            print(f"  - {prod['product_id']}: {prod['name']} (Risk: {prod['risk_level']})")
        
        # ==================== CLIENT_PRODUCTS OPERATIONS ====================
        print("\n--- CLIENT_PRODUCTS OPERATIONS ---")
        
        # Add products to client
        result = db.add_product_to_client(
            client_id="CLI201",
            product_id="PROD201",
            purchase_date=date(2024, 1, 15),
            status="Active",
            investment_amount=Decimal("52020.20")
        )
        print(f"Add Product to Client: {result}")
        
        result = db.add_product_to_client(
            client_id="CLI201",
            product_id="PROD202",
            purchase_date=date(2024, 2, 20),
            status="Active",
            investment_amount=Decimal("32020.20")
        )
        print(f"Add Product to Client: {result}")
        
        # Get client products
        client_products = db.get_client_products("CLI201")
        print(f"Get Client Products: {len(client_products)} product(s) found")
        for cp in client_products:
            print(f"  - {cp['product_name']}: ${cp['investment_amount']} ({cp['status']})")
        
        # Get product clients
        product_clients = db.get_product_clients("PROD201")
        print(f"Get Product Clients: {len(product_clients)} client(s) found")
        for pc in product_clients:
            print(f"  - {pc['client_name']}: ${pc['investment_amount']}")
        
        # ==================== MEETING OPERATIONS ====================
        print("\n--- MEETING OPERATIONS ---")
        
        # Create meeting
        result = db.create_meeting(
            meeting_id="MTG202",
            client_id="CLI201",
            advisor_id=advisor_id,
            meeting_type="Annual Review",
            status="Started"
        )
        print(f"Create Meeting: {result}")
        
        # Get meeting
        meeting = db.get_meeting("MTG202")
        print(f"Get Meeting: {meeting}")
        
        # Update meeting status
        result = db.update_meeting(
            meeting_id="MTG202",
            status="Completed"
        )
        print(f"Update Meeting: {result}")
        
        # List meetings for client
        meetings = db.list_meetings(client_id="CLI201")
        print(f"List Meetings for CLI201: {len(meetings)} meeting(s) found")
        for mtg in meetings:
            print(f"  - {mtg['meeting_id']}: {mtg['meeting_type']} ({mtg['status']})")
        
        # List meetings for advisor
        meetings = db.list_meetings(advisor_id=advisor_id)
        print(f"List Meetings for ADV201: {len(meetings)} meeting(s) found")
        for mtg in meetings:
            print(f"  - {mtg['meeting_id']}: Client {mtg['client_id']} - {mtg['meeting_type']}")
        
        # ==================== MEETING DETAILS OPERATIONS ====================
        print("\n--- MEETING DETAILS OPERATIONS ---")
        
        # Create meeting details
        result = db.create_meeting_detail(
            meeting_id="MTG202",
            transcript="Client: I want to discuss my retirement plans...\nAdvisor: Let's review your portfolio...",
            summary="Discussed retirement planning and portfolio rebalancing",
            recommendations="1. Increase bond allocation\n2. Consider annuity products",
            questions="What is your target retirement age?",
            advisor_notes="Client seems concerned about market volatility"
        )
        print(f"Create Meeting Details: {result}")
        
        # Get meeting details
        details = db.get_meeting_detail("MTG202")
        print(f"Get Meeting Details: {details}")
        
        # Update meeting details
        result = db.update_meeting_detail(
            meeting_id="MTG202",
            summary="Updated: Comprehensive retirement planning session completed",
            advisor_notes="Follow-up scheduled in 3 months"
        )
        print(f"Update Meeting Details: {result}")
        
        # List meeting details for specific IDs
        all_details = db.list_meeting_details(meeting_ids=["MTG202"])
        print(f"List Meeting Details: {len(all_details)} detail(s) found")
        for det in all_details:
            print(f"  - {det['meeting_id']}: {det['summary'][:50]}...")
        
        # ==================== TEST RELATIONSHIPS ====================
        print("\n--- TESTING RELATIONSHIPS ---")
        
        # Create second client for the same advisor
        db.create_client(
            client_id="CLI202",
            name="Michael Wong",
            advisor_id=advisor_id,
            status="Active"
        )
        
        # Create meeting for second client
        db.create_meeting(
            meeting_id="MTG202",
            client_id="CLI202",
            advisor_id=advisor_id,
            meeting_type="Initial Consultation",
            status="Scheduled"
        )
        
        # List all clients for advisor
        advisor_clients = db.list_clients(advisor_id=advisor_id)
        print(f"\nAdvisor ADV201 has {len(advisor_clients)} clients:")
        for cli in advisor_clients:
            print(f"  - {cli['name']} ({cli['client_id']})")
        
        # List all meetings for advisor
        advisor_meetings = db.list_meetings(advisor_id=advisor_id)
        print(f"\nAdvisor ADV201 has {len(advisor_meetings)} meetings:")
        for mtg in advisor_meetings:
            print(f"  - {mtg['meeting_id']}: {mtg['meeting_type']} with {mtg['client_id']}")
        
        # ==================== TRANSCRIPT AGGREGATOR OPERATIONS ====================
        print("\n--- TRANSCRIPT AGGREGATOR OPERATIONS ---")
        
        # Add transcript segments
        result = db.add_transcript_segment(
            meeting_id="MTG202",
            transcript="Advisor: Good morning! Thank you for coming in today.",
            start_datetime=datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc)
        )
        print(f"Add Transcript Segment 1: {result}")
        
        result = db.add_transcript_segment(
            meeting_id="MTG202",
            transcript="Client: Thank you for having me. I wanted to discuss my retirement plans.",
            start_datetime=datetime(2024, 1, 15, 20, 0, 30, tzinfo=timezone.utc)
        )
        print(f"Add Transcript Segment 2: {result}")
        
        result = db.add_transcript_segment(
            meeting_id="MTG202",
            transcript="Advisor: Great! Let's start by reviewing your current portfolio allocation.",
            start_datetime=datetime(2024, 1, 15, 20, 1, 30, tzinfo=timezone.utc)
        )
        print(f"Add Transcript Segment 3: {result}")
        
        # Add segment without explicit datetime (uses NOW)
        result = db.add_transcript_segment(
            meeting_id="MTG202",
            transcript="Client: I'm particularly concerned about market volatility."
        )
        print(f"Add Transcript Segment 4 (auto-timestamp): {result}")
        
        # Get all segments
        segments = db.get_transcript_segments("MTG202")
        print(f"\nGet Transcript Segments: {len(segments)} segment(s) found")
        for seg in segments:
            print(f"  - Segment {seg['index']}: {seg['transcript'][:50]}... (at {seg['start_datetime']})")
        
        # Get segment by index
        segment = db.get_transcript_segment_by_index("MTG202", 2)
        print(f"\nGet Segment by Index (2): {segment['transcript'][:60]}...")
        
        # Get segments by time range
        segments_filtered = db.get_transcript_segments_by_time(
            meeting_id="MTG202",
            start_time=datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 20, 1, 0, tzinfo=timezone.utc)
        )
        print(f"\nGet Segments by Time Range: {len(segments_filtered)} segment(s) found")
        for seg in segments_filtered:
            print(f"  - Segment {seg['index']}: {seg['transcript'][:50]}...")
        
        # Aggregate transcripts
        full_transcript = db.aggregate_transcripts("MTG202")
        print(f"\nAggregate Transcripts: {len(full_transcript)} characters")
        print(f"Preview: {full_transcript[:150]}...")
        
        # Update segment
        result = db.update_transcript_segment(
            meeting_id="MTG202",
            segment_index=1,
            transcript="Advisor: Good morning! Welcome to our meeting today."
        )
        print(f"\nUpdate Transcript Segment: {result}")
        
        # Count segments
        count = db.count_transcript_segments("MTG202")
        print(f"Count Transcript Segments: {count} segment(s)")
        
        # Delete single segment
        result = db.delete_transcript_segment("MTG202", 4)
        print(f"Delete Transcript Segment 4: {result}")
        
        # Count after deletion
        count = db.count_transcript_segments("MTG202")
        print(f"Count After Deletion: {count} segment(s)")
        
        # ==================== CLEANUP (Optional) ====================
        print("\n--- CLEANUP ---")
        print("Cleanup commented out. Uncomment to delete test data.")
        
        # Uncomment below to delete test data
        # db.remove_product_from_client("CLI201", "PROD201")
        # db.remove_product_from_client("CLI201", "PROD202")
        # db.delete_transcript_segments("MTG202")  # Delete transcript segments
        # db.delete_meeting_detail("MTG202")
        # db.delete_meeting_detail("MTG202")
        # db.delete_meeting("MTG202")
        # db.delete_meeting("MTG202")
        # db.delete_client("CLI201")
        # db.delete_client("CLI202")
        # db.delete_product("PROD201")
        # db.delete_product("PROD202")
        # db.delete_advisor(advisor_id)
        # print("✓ Test data cleaned up")
        
        print("\n" + "="*60)
        print("DATABASE UTILITIES TEST COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    main()