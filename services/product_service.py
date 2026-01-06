from services.azure_openai_service import azure_openai_service
from utils.db_utils import DatabaseUtils
from typing import Dict, Optional
import json

# Import the decision tree
PRODUCT_DECISION_TREE = """
PROVIDEND PRODUCT RECOMMENDATION TREE
├─── 1. PROTECTION NEEDS
│    │
│    ├─── 1.1 Income Protection
│    │    ├─── Client has dependents + working age (< 65)
│    │    │    └─── Critical Illness Insurance (3-5 years income protection)
│    │    ├─── Client has young children + single income household
│    │    │    └─── Term Life Insurance with Income Replacement Rider
│    │    └─── Client concerned about disability
│    │         └─── Disability Income Insurance
│    │
│    ├─── 1.2 Healthcare Coverage
│    │    ├─── Client wants private hospital option
│    │    │    └─── Integrated Shield Plan (Private Hospital Coverage)
│    │    ├─── Client wants overseas treatment option
│    │    │    └─── Integrated Shield Plan + International Medical Coverage
│    │    └─── Client has existing health conditions
│    │         └─── Guaranteed Acceptance Medical Plans
│    │
│    └─── 1.3 Family Protection
│         ├─── Client has young children (education goals)
│         │    └─── Education Endowment Plan + Term Life
│         ├─── Spouse not working / needs income if client passes
│         │    └─── Whole Life Insurance with Living Benefits
│         └─── Elderly parents need support
│              └─── Long-Term Care Insurance
│
└─── 2. WEALTH ACCUMULATION
     │
     ├─── 2.1 Retirement Planning
     │    ├─── Client age < 45 + moderate risk tolerance
     │    │    └─── Global Equity Portfolio (80% Equities / 20% Bonds)
     │    ├─── Client age 45-55 + balanced approach
     │    │    └─── Balanced Portfolio (60% Equities / 40% Bonds)
     │    └─── Client age > 55 + conservative
     │         └─── Income-Focused Portfolio (40% Equities / 60% Bonds)
     │
     ├─── 2.2 Specific Goals (< 10 years)
     │    ├─── Child's tertiary education in 5-10 years
     │    │    └─── Education Savings Portfolio (Conservative Growth)
     │    ├─── Property purchase within 5 years
     │    │    └─── Short-Term Bond Fund + Fixed Deposits
     │    └─── Quality of life goals (travel, car, renovation)
     │         └─── Balanced Growth Portfolio
     │
     └─── 2.3 Long-Term Wealth Building
          ├─── High income + tax efficiency concerns
          │    └─── SRS Account + CPF Top-ups + Investment Portfolio
          ├─── Business owner + irregular income
          │    └─── Dollar-Cost Averaging Investment Plan
          └─── Inheritance expected + preservation focus
               └─── Multi-Asset Conservative Portfolio
"""


class ProductRecommendationService:
    """LLM-based product recommendation service using transcript and decision tree"""
    
    def __init__(self):
        pass
    
    def generate_recommendations(self, transcript: str, meeting_id: str, conn) -> dict:
        """
        Generate product recommendations from transcript using decision tree.
        
        Args:
            transcript: Raw meeting transcript
            meeting_id: Meeting ID for context
            conn: Database connection
        
        Returns:
            Recommendations dictionary with products, reasoning, and priority
        """
        
        # Get client info for context (optional - mainly for updating current_recommendation)
        db = DatabaseUtils(conn)
        meeting = db.get_meeting(meeting_id)
        client = db.get_client(meeting["client_id"]) if meeting else None
        
        # Generate recommendations using LLM
        recommendations = self._generate_recommendations_with_llm(transcript)
        
        # Update client current_recommendation if available
        if recommendations.get("top_recommendation") and client:
            top_rec = recommendations["top_recommendation"]
            db.update_client(
                client_id=client["client_id"],
                current_recommendation=top_rec.get("product", "")
            )
        
        return recommendations
    
    def _generate_recommendations_with_llm(self, transcript: str) -> dict:
        """
        Use LLM to analyze transcript, extract client info, and apply decision tree.
        """
        
        system_prompt = f"""You are an expert financial advisor at Providend, Singapore's leading fee-only financial advisory firm.

Your task is to:
1. Analyze the meeting transcript to understand the client's situation
2. Extract key information about the client (age, dependents, income, goals, risk tolerance, etc.)
3. Apply the decision tree below to recommend appropriate products
4. Provide clear reasoning for each recommendation

{PRODUCT_DECISION_TREE}

ANALYSIS FRAMEWORK:
First, extract from the transcript:
- Client demographics (age, occupation, income)
- Family situation (dependents, children ages, spouse employment)
- Financial goals (retirement, education, property, etc.)
- Risk tolerance and investment preferences
- Healthcare preferences (private hospital, overseas treatment)
- Existing coverage (insurance, investments)
- Concerns or pain points mentioned

Then, systematically walk through the decision tree:

**PROTECTION NEEDS:**
1.1 Income Protection
- Has dependents + working age (<65)? → Critical Illness Insurance
- Young children + single income? → Term Life with Income Replacement
- Disability concerns? → Disability Income Insurance

1.2 Healthcare Coverage
- Wants private hospital? → Integrated Shield Plan (Private)
- Wants overseas treatment? → Integrated Shield + International Coverage
- Existing health conditions? → Guaranteed Acceptance Plans

1.3 Family Protection
- Young children + education goals? → Education Endowment + Term Life
- Non-working spouse? → Whole Life with Living Benefits
- Elderly parents needing support? → Long-Term Care Insurance

**WEALTH ACCUMULATION:**
2.1 Retirement Planning
- Age <45 + moderate risk? → Global Equity Portfolio (80/20)
- Age 45-55 + balanced? → Balanced Portfolio (60/40)
- Age >55 + conservative? → Income-Focused Portfolio (40/60)

2.2 Specific Goals (<10 years)
- Child's education 5-10 years? → Education Savings Portfolio
- Property purchase <5 years? → Short-Term Bond Fund + Fixed Deposits
- Quality of life goals? → Balanced Growth Portfolio

2.3 Long-Term Wealth
- High income + tax concerns? → SRS + CPF Top-ups + Investment Portfolio
- Business owner + irregular income? → Dollar-Cost Averaging Plan
- Inheritance expected? → Multi-Asset Conservative Portfolio

RESPONSE FORMAT (JSON):
{{
  "client_profile_extracted": {{
    "age": "extracted or 'not mentioned'",
    "has_dependents": true/false,
    "num_children": number or null,
    "children_ages": [ages] or null,
    "annual_income": "amount or 'not mentioned'",
    "risk_tolerance": "low/moderate/high or 'not mentioned'",
    "key_goals": ["list of goals mentioned"],
    "existing_coverage": ["list of existing insurance/investments"],
    "healthcare_preferences": "private/public/overseas or 'not mentioned'",
    "other_relevant_info": "any other key details"
  }},
  "protection_needs": [
    {{
      "product": "Exact product name from decision tree",
      "category": "Income Protection / Healthcare Coverage / Family Protection",
      "priority": "High / Medium / Low",
      "reasoning": "Why this matches (quote from transcript if relevant)",
      "coverage_details": "Specific details (e.g., '3-5 years income protection = $XXX')",
      "decision_tree_criteria_met": ["List criteria from tree that apply"]
    }}
  ],
  "wealth_accumulation": [
    {{
      "product": "Exact product name from decision tree",
      "category": "Retirement Planning / Specific Goals / Long-Term Wealth",
      "priority": "High / Medium / Low",
      "reasoning": "Why this matches",
      "investment_details": "Allocation details if applicable",
      "decision_tree_criteria_met": ["List criteria from tree that apply"]
    }}
  ],
  "top_recommendation": {{
    "product": "1-3 of the most important recommendation, if more than 1 recommendation, please try to reccomend 1 from protection and 1 from wealth accumulation",
    "reasoning": "Why this is top priority based on conversation",
    "immediate_action": "What client should do next"
  }},
  "summary": "2-3 sentence summary of recommended approach for this client",
  "confidence_level": "High/Medium/Low - based on how much info was gathered in transcript"
}}

CRITICAL RULES:
1. ONLY recommend products that appear EXACTLY in the decision tree
2. Use EXACT product names from the tree (don't invent variations)
3. If info is missing from transcript, note it in client_profile_extracted
4. If no criteria match, return empty array for that category
5. Protection needs generally have higher priority than wealth accumulation
6. Quote specific parts of transcript to support recommendations
7. If transcript lacks key information, note this in confidence_level and summary
"""

        user_prompt = f"""Analyze this meeting transcript and provide product recommendations following the decision tree:

=== MEETING TRANSCRIPT ===
{transcript}

=== YOUR TASK ===
1. Extract client information from the conversation
2. Apply the decision tree systematically
3. Recommend appropriate products with clear reasoning
4. Provide specific coverage amounts or allocation percentages where applicable"""

        # Call Azure OpenAI
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2  # Very low temperature for consistent rule-following
        )
        
        return response