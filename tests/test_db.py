import os
import sys
import psycopg2
from psycopg2 import OperationalError, Error
from dotenv import load_dotenv
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_utils import DatabaseUtils

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
    
def test_content_versioning(conn):
    """Comprehensive test for content versioning system"""
    
    print("\n" + "="*60)
    print("TESTING CONTENT VERSIONING SYSTEM")
    print("="*60)
    
    db = DatabaseUtils(conn)
    
    # Setup: Create advisor, client, meeting
    test_advisor_id = str(uuid4())
    test_client_id = str(uuid4())
    test_meeting_id = str(uuid4())
    
    print("\n--- Setup: Creating test data ---")
    db.create_advisor(advisor_id=test_advisor_id, name="Dr. Test", email="test@test.com")
    db.create_client(client_id=test_client_id, name="Test Client", advisor_id=test_advisor_id)
    db.create_meeting(meeting_id=test_meeting_id, client_id=test_client_id, advisor_id=test_advisor_id)
    db.create_meeting_detail(meeting_id=test_meeting_id)
    print("✓ Test data created")
    
    # ==================== TEST 1: Create Transcript Versions ====================
    print("\n--- TEST 1: Create Transcript Versions ---")
    
    # Version 1 (initial, clean)
    v1_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='transcript',
        content="Client wants to retire at age 65.",
        created_by=test_advisor_id
    )
    print(f"✓ Created transcript v1: {v1_result['message']}")
    assert v1_result['success'] == True
    assert v1_result['version_number'] == 1
    
    # Version 2 (with edits)
    v2_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='transcript',
        content="Client wants to retire at <del>age 65</del> 60.",
        created_by=test_advisor_id
    )
    print(f"✓ Created transcript v2: {v2_result['message']}")
    assert v2_result['success'] == True
    assert v2_result['version_number'] == 2
    
    # Version 3 (more edits)
    v3_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='transcript',
        content="Client wants to retire at <del>age 65</del> 60 and invest in bonds.",
        created_by=test_advisor_id
    )
    print(f"✓ Created transcript v3: {v3_result['message']}")
    assert v3_result['version_number'] == 3
    
    # ==================== TEST 2: Create Summary Versions ====================
    print("\n--- TEST 2: Create Summary Versions ---")
    
    # Summary v1 (AI-generated)
    s1_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='summary',
        content="Client discussed retirement planning and investment strategy.",
        created_by="AI_PROCESSOR"
    )
    print(f"✓ Created summary v1: {s1_result['message']}")
    assert s1_result['version_number'] == 1
    
    # Summary v2 (advisor edit)
    s2_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='summary',
        content="Client discussed <del>retirement planning</del> early retirement and investment strategy.",
        created_by=test_advisor_id
    )
    print(f"✓ Created summary v2: {s2_result['message']}")
    assert s2_result['version_number'] == 2
    
    # ==================== TEST 3: Retrieve Specific Versions ====================
    print("\n--- TEST 3: Retrieve Specific Versions ---")
    
    transcript_v2 = db.get_content_version(test_meeting_id, 'transcript', 2)
    print(f"✓ Retrieved transcript v2:")
    print(f"  Content: {transcript_v2['content'][:60]}...")
    print(f"  Created by: {transcript_v2['created_by']}")
    print(f"  Is current: {transcript_v2['is_current']}")
    assert transcript_v2 is not None
    assert transcript_v2['version_number'] == 2
    assert "<del>" in transcript_v2['content']
    
    summary_v1 = db.get_content_version(test_meeting_id, 'summary', 1)
    print(f"✓ Retrieved summary v1:")
    print(f"  Content: {summary_v1['content'][:60]}...")
    print(f"  Created by: {summary_v1['created_by']}")
    assert summary_v1['created_by'] == "AI_PROCESSOR"
    
    # ==================== TEST 4: List Version History ====================
    print("\n--- TEST 4: List Version History ---")
    
    transcript_versions = db.list_content_versions(test_meeting_id, 'transcript')
    print(f"✓ Transcript versions: {len(transcript_versions)} found")
    for v in transcript_versions:
        print(f"  v{v['version_number']}: {v['content_length']} chars, "
              f"created by {v['created_by']}, current={v['is_current']}")
    assert len(transcript_versions) == 3
    
    summary_versions = db.list_content_versions(test_meeting_id, 'summary')
    print(f"✓ Summary versions: {len(summary_versions)} found")
    assert len(summary_versions) == 2
    
    # ==================== TEST 5: Get Current Version ====================
    print("\n--- TEST 5: Get Current Version ---")
    
    current_transcript = db.get_current_content_version(test_meeting_id, 'transcript')
    print(f"✓ Current transcript version: v{current_transcript['version_number']}")
    assert current_transcript['version_number'] == 3
    assert current_transcript['is_current'] == True
    
    current_summary = db.get_current_content_version(test_meeting_id, 'summary')
    print(f"✓ Current summary version: v{current_summary['version_number']}")
    assert current_summary['version_number'] == 2
    
    # ==================== TEST 6: Version Count ====================
    print("\n--- TEST 6: Version Count ---")
    
    transcript_count = db.get_content_version_count(test_meeting_id, 'transcript')
    summary_count = db.get_content_version_count(test_meeting_id, 'summary')
    print(f"✓ Transcript versions: {transcript_count}")
    print(f"✓ Summary versions: {summary_count}")
    assert transcript_count == 3
    assert summary_count == 2
    
    # ==================== TEST 7: Unified Timeline ====================
    print("\n--- TEST 7: Unified Timeline ---")
    
    timeline = db.get_unified_timeline(test_meeting_id)
    print(f"✓ Unified timeline: {len(timeline)} total edits")
    print(f"  Chronological order:")
    for entry in timeline:
        print(f"    {entry['created_at']}: {entry['content_type']} v{entry['version_number']} "
              f"by {entry['created_by']}")
    assert len(timeline) == 5  # 3 transcript + 2 summary
    
    # ==================== TEST 8: Rollback Functionality ====================
    print("\n--- TEST 8: Rollback Functionality ---")
    
    # Rollback transcript to v2
    rollback_result = db.rollback_content_to_version(test_meeting_id, 'transcript', 2)
    print(f"✓ Rollback result: {rollback_result['message']}")
    assert rollback_result['success'] == True
    assert rollback_result['version_number'] == 2
    
    # Verify v2 is now current
    current = db.get_current_content_version(test_meeting_id, 'transcript')
    print(f"✓ Current version after rollback: v{current['version_number']}")
    assert current['version_number'] == 2
    assert current['is_current'] == True
    
    # Verify v3 is no longer current
    v3_check = db.get_content_version(test_meeting_id, 'transcript', 3)
    assert v3_check['is_current'] == False
    
    # Verify meeting_details was updated
    meeting_details = db.get_meeting_detail(test_meeting_id)
    print(f"✓ meeting_details.transcript updated: {meeting_details['transcript'][:50]}...")
    assert "<del>age 65</del> 60" in meeting_details['transcript']
    
    # ==================== TEST 9: Set Current Version ====================
    print("\n--- TEST 9: Set Current Version ---")
    
    # Set v1 as current
    set_result = db.set_current_content_version(test_meeting_id, 'transcript', 1)
    print(f"✓ Set v1 as current: {set_result['message']}")
    assert set_result['success'] == True
    
    # Verify
    current = db.get_current_content_version(test_meeting_id, 'transcript')
    assert current['version_number'] == 1
    
    # Verify others are not current
    v2_check = db.get_content_version(test_meeting_id, 'transcript', 2)
    v3_check = db.get_content_version(test_meeting_id, 'transcript', 3)
    assert v2_check['is_current'] == False
    assert v3_check['is_current'] == False
    
    # ==================== TEST 10: Independent Version Numbering ====================
    print("\n--- TEST 10: Independent Version Numbering ---")
    
    # Transcript has v1, v2, v3
    # Summary has v1, v2
    # They should be independent
    
    print(f"✓ Transcript versions: {db.get_content_version_count(test_meeting_id, 'transcript')}")
    print(f"✓ Summary versions: {db.get_content_version_count(test_meeting_id, 'summary')}")
    
    # Create another summary version
    s3_result = db.create_content_version(
        meeting_id=test_meeting_id,
        content_type='summary',
        content="Updated summary v3",
        created_by=test_advisor_id
    )
    assert s3_result['version_number'] == 3  # Should be 3, not affected by transcript versions
    print(f"✓ Created summary v3 (independent numbering)")
    
    # ==================== TEST 11: Error Handling ====================
    print("\n--- TEST 11: Error Handling ---")
    
    # Try to get non-existent version
    non_existent = db.get_content_version(test_meeting_id, 'transcript', 999)
    print(f"✓ Non-existent version returns None: {non_existent is None}")
    assert non_existent is None
    
    # Try to rollback to non-existent version
    bad_rollback = db.rollback_content_to_version(test_meeting_id, 'transcript', 999)
    print(f"✓ Rollback to non-existent version fails: {bad_rollback['success']}")
    assert bad_rollback['success'] == False
    
    # Try to set non-existent version as current
    bad_set = db.set_current_content_version(test_meeting_id, 'transcript', 999)
    print(f"✓ Set non-existent version fails: {bad_set['success']}")
    assert bad_set['success'] == False
    
    # ==================== CLEANUP ====================
    print("\n--- Cleanup ---")
    
    # Note: Deleting meeting will CASCADE delete all versions automatically
    db.delete_meeting(test_meeting_id)
    db.delete_client(test_client_id)
    db.delete_advisor(test_advisor_id)
    print("✓ Test data cleaned up")
    
    print("\n" + "="*60)
    print("CONTENT VERSIONING TESTS COMPLETED SUCCESSFULLY")
    print("="*60)


def test_version_with_meeting_service(conn):
    """Test versioning through MeetingService (integration test)"""
    
    print("\n" + "="*60)
    print("TESTING VERSIONING THROUGH MEETING SERVICE")
    print("="*60)
    
    from services.meeting_service import MeetingService
    
    db = DatabaseUtils(conn)
    meeting_service = MeetingService()
    
    # Setup
    test_advisor_id = str(uuid4())
    test_client_id = str(uuid4())
    test_meeting_id = str(uuid4())
    
    print("\n--- Setup ---")
    db.create_advisor(advisor_id=test_advisor_id, name="Dr. Service Test", email="service@test.com")
    db.create_client(client_id=test_client_id, name="Service Test Client", advisor_id=test_advisor_id)
    db.create_meeting(meeting_id=test_meeting_id, client_id=test_client_id, advisor_id=test_advisor_id)
    db.create_meeting_detail(meeting_id=test_meeting_id)
    print("✓ Test data created")
    
    # ==================== TEST: Update Transcript (Auto-versioning) ====================
    print("\n--- TEST: Update Transcript (Auto-versioning) ---")
    
    # First update (creates v1)
    result1 = meeting_service.update_meeting_transcript(
        meeting_id=test_meeting_id,
        transcript="Initial transcript content.",
        created_by=test_advisor_id,
        conn=conn
    )
    print(f"✓ First update: {result1['message']}")
    
    # Check v1 created
    v1 = db.get_content_version(test_meeting_id, 'transcript', 1)
    assert v1 is not None
    assert v1['content'] == "Initial transcript content."
    assert v1['is_current'] == True
    print(f"✓ Version 1 created: {v1['content']}")
    
    # Second update (creates v2 with diff)
    result2 = meeting_service.update_meeting_transcript(
        meeting_id=test_meeting_id,
        transcript="Updated transcript content.",
        created_by=test_advisor_id,
        conn=conn
    )
    print(f"✓ Second update: {result2['message']}")
    
    # Check v2 created with <del> tags
    v2 = db.get_content_version(test_meeting_id, 'transcript', 2)
    assert v2 is not None
    assert "<del>" in v2['content']  # Should have diff markup
    assert v2['is_current'] == True
    print(f"✓ Version 2 created with diff: {v2['content'][:60]}...")
    
    # ==================== TEST: Update Summary (Auto-versioning) ====================
    print("\n--- TEST: Update Summary (Auto-versioning) ---")
    
    # First update (creates v1)
    result1 = meeting_service.update_meeting_summary(
        meeting_id=test_meeting_id,
        summary="Initial summary.",
        created_by=test_advisor_id,
        conn=conn
    )
    print(f"✓ First summary update")
    
    s1 = db.get_content_version(test_meeting_id, 'summary', 1)
    assert s1 is not None
    print(f"✓ Summary v1 created")
    
    # Second update (creates v2 with diff)
    result2 = meeting_service.update_meeting_summary(
        meeting_id=test_meeting_id,
        summary="Updated summary.",
        created_by=test_advisor_id,
        conn=conn
    )
    print(f"✓ Second summary update")
    
    s2 = db.get_content_version(test_meeting_id, 'summary', 2)
    assert s2 is not None
    assert "<del>" in s2['content']
    print(f"✓ Summary v2 created with diff")
    
    # ==================== TEST: Rollback Through Service ====================
    print("\n--- TEST: Rollback Through Service ---")
    
    rollback_result = meeting_service.rollback_content_to_version(
        meeting_id=test_meeting_id,
        content_type='transcript',
        version_number=1,
        created_by=test_advisor_id,
        conn=conn
    )
    print(f"✓ Rollback: {rollback_result['message']}")
    
    # Verify rollback created a new version (v3)
    v3 = db.get_content_version(test_meeting_id, 'transcript', 3)
    assert v3 is not None
    assert v3['content'] == v1['content']  # Should match v1
    assert v3['is_current'] == True
    print(f"✓ Rollback created v3 (copy of v1)")
    
    # ==================== TEST: Version History ====================
    print("\n--- TEST: Version History Through Service ---")
    
    history = meeting_service.get_content_version_history(
        meeting_id=test_meeting_id,
        content_type='transcript',
        conn=conn
    )
    print(f"✓ Version history retrieved: {history['total_versions']} versions")
    assert history['total_versions'] == 3
    
    # ==================== TEST: Compare Versions ====================
    print("\n--- TEST: Compare Versions Through Service ---")
    
    comparison = meeting_service.compare_content_versions(
        meeting_id=test_meeting_id,
        content_type='transcript',
        v1=1,
        v2=2,
        conn=conn
    )
    print(f"✓ Comparison retrieved")
    print(f"  V1 length: {len(comparison['version_1']['content'])} chars")
    print(f"  V2 length: {len(comparison['version_2']['content'])} chars")
    assert comparison['success'] == True
    
    # ==================== TEST: Unified Timeline ====================
    print("\n--- TEST: Unified Timeline Through Service ---")
    
    timeline = meeting_service.get_unified_edit_timeline(
        meeting_id=test_meeting_id,
        conn=conn
    )
    print(f"✓ Timeline retrieved: {timeline['total_edits']} edits")
    print(f"  Timeline entries:")
    for entry in timeline['timeline']:
        print(f"    {entry['content_type']} v{entry['version_number']} by {entry['created_by']}")
    assert timeline['total_edits'] >= 5  # 3 transcript + 2 summary
    
    # ==================== CLEANUP ====================
    print("\n--- Cleanup ---")
    db.delete_meeting(test_meeting_id)
    db.delete_client(test_client_id)
    db.delete_advisor(test_advisor_id)
    print("✓ Test data cleaned up")
    
    print("\n" + "="*60)
    print("MEETING SERVICE VERSIONING TESTS COMPLETED SUCCESSFULLY")
    print("="*60)

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
        if segment:
            print(f"\nGet Segment by Index (2): {segment['transcript'][:60]}...")
        else:
            print(f"\n✗ Segment index 2 not found for meeting MTG202")
        
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

        # Add new versioning tests
        test_content_versioning(conn)
        test_version_with_meeting_service(conn)
        
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