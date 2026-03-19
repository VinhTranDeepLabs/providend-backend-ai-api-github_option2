import os
import sys

# Add root folder to python path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

import json
from services.client_preference_service import ClientPreferenceService

RICH_TRANSCRIPT = """
Advisor: How's your weekend been?
Client: Great! Played golf on Saturday as usual at Sentosa Golf Club. 
Then we went to this amazing omakase place in town - I love Japanese food.
My wife and I are planning a trip to Hokkaido next month for our anniversary.
We just adopted a labrador, his name is Charlie.
I've been watching that new Netflix series "The Bear" - have you seen it?
Oh and you know me, die-hard Liverpool fan. What a season!
"""

FINANCE_ONLY_TRANSCRIPT = """
Advisor: Let's review your portfolio.
Client: Yes, I want to increase my equity allocation.
The market looks good and I'm comfortable with moderate risk.
My CPF is growing well too. Let's discuss retirement timeline.
I want to put some funds into a Singapore REITs ETF and some into fixed deposits.
"""

def run_tests():
    print("Initializing ClientPreferenceService...")
    service = ClientPreferenceService()
    
    print("\n" + "="*50)
    print("TEST 1: RICH TRANSCRIPT EXTRACT")
    print("="*50)
    
    try:
        # We pass None for conn as the extraction logic doesn't insert directly, 
        # it just uses LLM to generate the dict.
        rich_results = service.extract_preferences(
            transcript=RICH_TRANSCRIPT, 
            meeting_id="TEST-RICH-001",
            conn=None
        )
        print("\nSUMMARY STATS:")
        print(json.dumps(rich_results.get("extraction_summary", {}), indent=2))
        
        # Verify specific findings
        prefs = rich_results.get("client_preferences", {})
        
        found_hobbies = prefs.get("hobbies_and_activities", {}).get("found")
        found_sports = prefs.get("favorite_sports_teams", {}).get("found")
        found_pets = prefs.get("pet_ownership", {}).get("found")
        found_travel = prefs.get("travel_preferences", {}).get("found")
        
        print("\nEXPECTED FINDINGS:")
        print(f"- Hobbies (Golf): {'PASS ✅' if found_hobbies else 'FAIL ❌'}")
        print(f"- Sports Team (Liverpool): {'PASS ✅' if found_sports else 'FAIL ❌'}")
        print(f"- Pets (Labrador): {'PASS ✅' if found_pets else 'FAIL ❌'}")
        print(f"- Travel (Hokkaido): {'PASS ✅' if found_travel else 'FAIL ❌'}")
        
    except Exception as e:
        print(f"Error in Test 1: {e}")
        
        
    print("\n" + "="*50)
    print("TEST 2: FINANCE ONLY (ANTI-HALLUCINATION)")
    print("="*50)
    
    try:
        finance_results = service.extract_preferences(
            transcript=FINANCE_ONLY_TRANSCRIPT, 
            meeting_id="TEST-FINANCE-001",
            conn=None
        )
        
        print("\nSUMMARY STATS (Expected 0 found):")
        summary = finance_results.get("extraction_summary", {})
        print(json.dumps(summary, indent=2))
        
        if summary.get("total_categories_found", -1) == 0:
            print("\nANTI-HALLUCINATION TEST: PASS ✅ (No personal facts hallucinated from finance data)")
        else:
            print("\nANTI-HALLUCINATION TEST: FAIL ❌ (AI hallucinated facts)")
            
    except Exception as e:
        print(f"Error in Test 2: {e}")

if __name__ == "__main__":
    run_tests()
