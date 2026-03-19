from services.azure_openai_service import azure_openai_service
from utils.db_utils import DatabaseUtils
from typing import Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

# 19 preference categories with descriptions and examples for the LLM prompt
PREFERENCE_CATEGORIES_GUIDE = """
=== 19 CLIENT PREFERENCE CATEGORIES ===

1. hobbies_and_activities
   What to look for: Sports, hobbies, leisure activities, clubs, regular pastimes
   Examples: "I play golf every Saturday", "I joined a book club", "I do pottery on weekends"
   Schema: {"activities": ["golf", "reading"], "frequency": "weekly/monthly/etc"}

2. favorite_sports_teams
   What to look for: Teams or leagues the client follows, fan references
   Examples: "I'm a huge Liverpool fan", "We watched the Lakers game last night"
   Schema: [{"team": "Liverpool FC", "sport": "Football"}]

3. food_and_dietary_preferences
   What to look for: Favorite foods, restaurants, dietary restrictions, allergies
   Examples: "I'm vegetarian", "We always go to Crystal Jade", "My daughter is allergic to nuts"
   Schema: {"favorites": [], "dietary_restrictions": [], "favorite_restaurants": [], "allergies": []}

4. beverage_preferences
   What to look for: Preferred drinks, coffee/tea habits, wine/whisky preferences
   Examples: "I only drink black coffee", "I'm into Japanese whisky lately"
   Schema: {"preferred_drinks": [], "favorites": ""}

5. travel_preferences
   What to look for: Travel style, favorite destinations, upcoming trips, frequency
   Examples: "We go to Japan every year", "I prefer beach vacations"
   Schema: {"style": "beach/adventure/cultural", "frequent_destinations": [], "frequency": ""}

6. pet_ownership
   What to look for: Pets mentioned, names, breeds, care concerns
   Examples: "Our golden retriever Max needs surgery", "My cat is 12 years old"
   Schema: [{"type": "dog", "breed": "Golden Retriever", "name": "Max"}]

7. favorite_media
   What to look for: TV shows, movies, books, podcasts, music preferences
   Examples: "I've been watching Succession", "I just finished reading Sapiens"
   Schema: {"tv_shows": [], "movies": [], "books": [], "podcasts": [], "music": []}

8. real_estate_status
   What to look for: Property ownership, housing preferences, renovation plans
   Examples: "We just bought a condo in Bukit Timah", "Looking to downsize after kids leave"
   Schema: {"properties_owned": null, "types": [], "preference": "", "plans": ""}

9. vehicle_preferences
   What to look for: Car ownership, car enthusiasm, EV interest
   Examples: "Just got a Tesla Model 3", "I'm thinking about getting an EV"
   Schema: {"current_vehicles": [], "interests": ""}

10. upcoming_milestones
    What to look for: Birthdays, anniversaries, graduations, weddings, retirements
    Examples: "My daughter graduates in June", "Our 25th anniversary is next month"
    Schema: [{"event": "daughter's graduation", "timeline": "June 2026"}]

11. charitable_causes
    What to look for: Donations, volunteering, causes they care about
    Examples: "I donate to the Red Cross annually", "We volunteer at the animal shelter"
    Schema: {"causes": [], "organizations": [], "involvement": ""}

12. communication_style
    What to look for: Preferred contact method, meeting preferences, availability
    Examples: "I prefer WhatsApp over email", "Don't call me after 6pm"
    Schema: {"preferred_method": "", "availability_notes": "", "meeting_preference": ""}

13. tech_savviness
    What to look for: Comfort with technology, app usage, digital vs paper preference
    Examples: "I do everything on my phone", "I still prefer printed statements"
    Schema: {"level": "low/medium/high", "notes": ""}

14. weekend_routines
    What to look for: Regular weekend activities, family routines
    Examples: "Every Sunday we go to church then brunch", "I cycle at East Coast Park on Saturdays"
    Schema: {"activities": [], "pattern": ""}

15. dislikes_or_pet_peeves
    What to look for: Things they explicitly dislike or want to avoid
    Examples: "I hate being called on weekends", "I can't stand high-risk investments"
    Schema: ["hates cold calls", "dislikes high volatility"]

16. family_and_relationships
    What to look for: Spouse, children details, parents, family activities, family dynamics
    Examples: "My wife Sarah works at DBS", "Our eldest is in NUS engineering"
    Schema: {"spouse": "", "children": [{"name": "", "age": null, "details": ""}], "parents": "", "family_activities": []}

17. health_and_fitness
    What to look for: Exercise habits, health conditions, fitness goals, medical concerns
    Examples: "I run marathons", "I was diagnosed with diabetes last year"
    Schema: {"activities": [], "conditions": "", "goals": ""}

18. career_and_business
    What to look for: Current job details, side businesses, career plans, industry
    Examples: "I'm thinking of starting a cafe", "I might retire early at 55"
    Schema: {"industry": "", "role": "", "side_projects": [], "plans": ""}

19. education_and_learning
    What to look for: Client's own education, children's schools, courses, certifications
    Examples: "I studied at NUS", "My son is at ACS Independent", "Taking a wine appreciation course"
    Schema: {"client_education": "", "children_schools": [], "courses": []}
"""


class ClientPreferenceService:
    """LLM-based client preference extraction service.
    
    Extracts 19 categories of personal facts/preferences from meeting transcripts.
    Follows the exact same pattern as ProductRecommendationService.
    """
    
    def __init__(self):
        pass
    
    def extract_preferences(self, transcript: str, meeting_id: str, conn) -> dict:
        """
        Extract client preferences from transcript.
        
        Args:
            transcript: Raw meeting transcript
            meeting_id: Meeting ID for context
            conn: Database connection
        
        Returns:
            Preferences dictionary with 19 categories
        """
        logger.info(f"[{meeting_id}] Starting preference extraction...")
        
        # Generate preferences using LLM
        preferences = self._extract_preferences_with_llm(transcript)
        
        logger.info(f"[{meeting_id}] Preference extraction complete. "
                     f"Categories found: {preferences.get('extraction_summary', {}).get('total_categories_found', 'N/A')}")
        
        return preferences
    
    def _extract_preferences_with_llm(self, transcript: str) -> dict:
        """
        Use LLM to scan transcript and extract personal preferences into 19 categories.
        """
        
        system_prompt = f"""You are a Client Relationship Intelligence Analyst at Providend, Singapore's leading fee-only financial advisory firm.

Your task is to carefully scan an entire meeting transcript between a financial advisor and their client, and extract any personal facts, preferences, or lifestyle information mentioned by the client into 19 predefined categories.

{PREFERENCE_CATEGORIES_GUIDE}

=== ANALYSIS APPROACH ===

Step 1: Read the entire transcript carefully
Step 2: Identify any personal/lifestyle mentions (these often appear in small talk, opening/closing conversations, or casual asides during financial discussions)
Step 3: For each mention found, classify it into the correct category
Step 4: Record the direct quote as evidence

=== RESPONSE FORMAT (JSON) ===

Return a JSON object with this EXACT structure:
{{
  "client_preferences": {{
    "hobbies_and_activities": {{
      "found": true/false,
      "details": {{"activities": ["golf", "reading"], "frequency": "weekly"}},
      "evidence": "Client said: 'I play golf every Saturday morning at Sentosa Golf Club'"
    }},
    "favorite_sports_teams": {{
      "found": true/false,
      "details": [{{"team": "Liverpool FC", "sport": "Football"}}],
      "evidence": "Client mentioned: 'Did you catch the Liverpool match last night?'"
    }},
    "food_and_dietary_preferences": {{
      "found": true/false,
      "details": {{"favorites": [], "dietary_restrictions": [], "favorite_restaurants": [], "allergies": []}},
      "evidence": "..."
    }},
    "beverage_preferences": {{
      "found": true/false,
      "details": {{"preferred_drinks": [], "favorites": ""}},
      "evidence": "..."
    }},
    "travel_preferences": {{
      "found": true/false,
      "details": {{"style": "", "frequent_destinations": [], "frequency": ""}},
      "evidence": "..."
    }},
    "pet_ownership": {{
      "found": true/false,
      "details": [{{"type": "", "breed": "", "name": ""}}],
      "evidence": "..."
    }},
    "favorite_media": {{
      "found": true/false,
      "details": {{"tv_shows": [], "movies": [], "books": [], "podcasts": [], "music": []}},
      "evidence": "..."
    }},
    "real_estate_status": {{
      "found": true/false,
      "details": {{"properties_owned": null, "types": [], "preference": "", "plans": ""}},
      "evidence": "..."
    }},
    "vehicle_preferences": {{
      "found": true/false,
      "details": {{"current_vehicles": [], "interests": ""}},
      "evidence": "..."
    }},
    "upcoming_milestones": {{
      "found": true/false,
      "details": [{{"event": "", "timeline": ""}}],
      "evidence": "..."
    }},
    "charitable_causes": {{
      "found": true/false,
      "details": {{"causes": [], "organizations": [], "involvement": ""}},
      "evidence": "..."
    }},
    "communication_style": {{
      "found": true/false,
      "details": {{"preferred_method": "", "availability_notes": "", "meeting_preference": ""}},
      "evidence": "..."
    }},
    "tech_savviness": {{
      "found": true/false,
      "details": {{"level": "low/medium/high", "notes": ""}},
      "evidence": "..."
    }},
    "weekend_routines": {{
      "found": true/false,
      "details": {{"activities": [], "pattern": ""}},
      "evidence": "..."
    }},
    "dislikes_or_pet_peeves": {{
      "found": true/false,
      "details": [],
      "evidence": "..."
    }},
    "family_and_relationships": {{
      "found": true/false,
      "details": {{"spouse": "", "children": [], "parents": "", "family_activities": []}},
      "evidence": "..."
    }},
    "health_and_fitness": {{
      "found": true/false,
      "details": {{"activities": [], "conditions": "", "goals": ""}},
      "evidence": "..."
    }},
    "career_and_business": {{
      "found": true/false,
      "details": {{"industry": "", "role": "", "side_projects": [], "plans": ""}},
      "evidence": "..."
    }},
    "education_and_learning": {{
      "found": true/false,
      "details": {{"client_education": "", "children_schools": [], "courses": []}},
      "evidence": "..."
    }}
  }},
  "extraction_summary": {{
    "total_categories_found": 0,
    "total_categories_not_found": 19,
    "confidence": "Low/Medium/High",
    "notes": "Brief note about the transcript content"
  }}
}}

=== CRITICAL RULES ===

1. ONLY extract EXPLICITLY STATED facts. NEVER infer, assume, or guess.
2. Context matters — distinguish personal facts from financial discussions:
   CORRECT: Client says "I play golf every Saturday" → hobbies_and_activities: golf
   INCORRECT: Client says "The golf ETF performed well" → This is NOT a hobby, it's a financial discussion. Do NOT extract.
   CORRECT: Client says "My wife and I just bought a condo" → real_estate_status + family_and_relationships
   INCORRECT: Client says "Property prices are rising" → This is market commentary, NOT real estate ownership. Do NOT extract.
3. If a category has NO explicitly mentioned facts, set "found": false and "details": null and "evidence": null.
4. For "evidence", use DIRECT QUOTES from the transcript. If paraphrasing, clearly indicate so.
5. One fact can appear in multiple categories if relevant (e.g., "My wife Sarah and I cycle every weekend" → family_and_relationships AND weekend_routines AND health_and_fitness).
6. This is a FINANCIAL ADVISORY meeting — most of the transcript will be about finances. Personal facts often emerge in:
   - Opening small talk ("How was your weekend?")
   - Casual asides during discussion ("My daughter just started uni, so we need education funds")
   - Closing remarks ("We're heading to Bali next week")
   - Goal-setting conversations ("I want to retire early and travel")
7. Do NOT hallucinate facts. If you're uncertain, do NOT include it.
8. Count "total_categories_found" as the number of categories where "found" is true."""

        user_prompt = f"""Analyze this financial advisory meeting transcript and extract all personal preferences and lifestyle facts into the 19 categories.

=== MEETING TRANSCRIPT ===
{transcript}

=== YOUR TASK ===
1. Scan the entire transcript for any personal, lifestyle, or preference mentions
2. Classify each finding into the correct category from the 19 defined categories
3. Include direct quotes as evidence for each finding
4. Set "found": false for any category with no explicit mentions
5. Do NOT infer or guess — only extract what is explicitly stated"""

        # Call Azure OpenAI with low temperature for extraction consistency
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        
        return response
